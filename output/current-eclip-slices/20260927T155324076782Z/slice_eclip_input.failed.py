#!/usr/bin/env python3
"""Rebuild and slice current eclip input geometry offline; never submit to a printer.

Uses current exported STL only. Historical plates supply reviewed profiles,
XY placement, and local support intentions, never their normal mesh or cache.
Run with /Applications/FreeCAD.app/Contents/Resources/bin/python.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse, copy, hashlib, json, math, re, shutil, struct, subprocess, sys, traceback, uuid, zipfile
import xml.etree.ElementTree as ET
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BAMBU=Path('/Applications/BambuStudio.app/Contents/MacOS/BambuStudio')
DEFAULT_EXPORT=ROOT/'output/cable-scene-export/20260927T153058669616Z/report.json'
DEFAULT_BINDING=ROOT/'output/cable-eclip-adoption/20260927T151752917841Z/manufacturing/binding-02/manifest.json'
PARTS=['cable-input-body','cable-input-lever','cable-input-cover']
CORE='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
PROD='http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
NS={'m':CORE};ET.register_namespace('',CORE);ET.register_namespace('p',PROD)
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,obj):Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def abs_path(p):return Path(p)if Path(p).is_absolute()else ROOT/p
def rel(p):return str(Path(p).resolve().relative_to(ROOT))
def affine(v,m):return np.asarray(v)@np.asarray(m)[:3,:3].T+np.asarray(m)[:3,3]
def matrix(text):
 if not text:return np.eye(4)
 a=np.array(list(map(float,text.split())));assert len(a)==12
 m=np.eye(4);m[:3,:]=a.reshape(4,3).T;return m
def transform(m):return ' '.join(format(x,'.17g')for x in np.asarray(m)[:3,:].T.reshape(-1))
def xml(root):return ET.tostring(root,encoding='utf-8',xml_declaration=True)
def read_stl(path):
 b=Path(path).read_bytes();n=struct.unpack_from('<I',b,80)[0]if len(b)>=84 else 0
 if len(b)==84+50*n:
  d=np.dtype([('normal','<f4',3),('vertices','<f4',(3,3)),('attr','<u2')]);return np.frombuffer(b,d,offset=84)['vertices'].astype(float)
 return np.array(re.findall(rb'vertex\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)',b),float).reshape(-1,3,3)
def write_stl(path,t):
 n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);length=np.linalg.norm(n,axis=1);assert np.all(length>0);n/=length[:,None]
 with Path(path).open('w')as f:
  f.write('solid current_eclip_input\n')
  for nn,tri in zip(n,t):
   f.write('facet normal '+' '.join(format(v,'.17g')for v in nn)+'\nouter loop\n')
   for v in tri:f.write('vertex '+' '.join(format(x,'.17g')for x in v)+'\n')
   f.write('endloop\nendfacet\n')
  f.write('endsolid current_eclip_input\n')
def mesh_object(resources,oid,verts,faces):
 ob=ET.SubElement(resources,'{'+CORE+'}object',id=str(oid),type='model');me=ET.SubElement(ob,'{'+CORE+'}mesh');vs=ET.SubElement(me,'{'+CORE+'}vertices');ts=ET.SubElement(me,'{'+CORE+'}triangles')
 for v in verts:ET.SubElement(vs,'{'+CORE+'}vertex',**{k:format(x,'.17g')for k,x in zip('xyz',v)})
 for f in faces:ET.SubElement(ts,'{'+CORE+'}triangle',**{k:str(x)for k,x in zip(['v1','v2','v3'],f)})
def md(parent,k,v):ET.SubElement(parent,'metadata',key=k,value=str(v))
def enforcer_geometry(part,cfg):
 out=[];boxfaces=np.array([[0,2,1],[1,2,3],[4,5,6],[5,7,6],[0,1,4],[1,5,4],[2,6,3],[3,6,7],[0,4,2],[2,4,6],[1,3,5],[3,7,5]])
 for i,c in enumerate(cfg['centres']):
  if part=='cable-input-body':
   h=cfg['half'];v=np.array([[c[0]+sx*h,c[1]+sy*h,z]for z in cfg['z']for sy in [-1,1]for sx in [-1,1]]);faces=boxfaces
  else:
   assert cfg['opening']=='hex5.8';r=5.8/math.sqrt(3);v=np.array([[c[0]+r*math.cos(math.pi/6+j*math.pi/3),c[1]+r*math.sin(math.pi/6+j*math.pi/3),z]for z in cfg['z']for j in range(6)])
   faces=np.array([[0,j+1,j]for j in range(1,5)]+[[6,6+j,6+j+1]for j in range(1,5)]+[t for j in range(6)for t in [[j,(j+1)%6,6+j],[(j+1)%6,6+(j+1)%6,6+j]]])
  out.append((f'M3_shoulder_enforcer_{i+1}',v,faces))
 return out

def build_input(folder,part,row,historical,ci):
 old=abs_path(historical['historical_selected_3mf']);assert SHA(old)==historical['historical_selected_3mf_sha256']
 oldinv=old.parent/'invocation.json';olddata=json.loads(oldinv.read_text());source=abs_path(row['file']);assert SHA(source)==row['sha256'];tri=read_stl(source)
 rotation=np.array([[1.,0,0],[0,0,-1],[0,1,0]])if part!='cable-input-cover'else np.array([[1.,0,0],[0,0,1],[0,-1,0]])
 rotated=tri@rotation.T;lo=rotated.min((0,1));hi=rotated.max((0,1));shift=-(lo+hi)/2;shift[2]=-lo[2];A=np.eye(4);A[:3,:3]=rotation;A[:3,3]=shift;oriented=rotated+shift
 write_stl(folder/'oriented.stl',oriented);assert np.array_equal(read_stl(folder/'oriented.stl'),oriented)
 L=np.eye(4);L[:3,:3]=np.array([ci['basis_x'],ci['basis_y'],ci['basis_z']]).T;L[:3,3]=ci['origin'];local_to_oriented=A@L
 with zipfile.ZipFile(old)as z:
  oldmain=ET.fromstring(z.read('3D/3dmodel.model'));oldcfg=ET.fromstring(z.read('Metadata/model_settings.config'));project=json.loads(z.read('Metadata/project_settings.config'));oldnames=z.namelist()
 build=oldmain.findall('./m:build/m:item',NS);assert len(build)==1;BM=matrix(build[0].attrib.get('transform'));assert np.allclose(BM[2],[0,0,1,0],atol=1e-8)
 # Recreate all geometry resources. No normal/support mesh is copied from history.
 main=ET.Element('{'+CORE+'}model',{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'en-US','requiredextensions':'p'});ET.SubElement(main,'{'+CORE+'}metadata',name='Application').text='BambuStudio-current-eclip-offline-rebuild'
 resources=ET.SubElement(main,'{'+CORE+'}resources');ob=ET.SubElement(resources,'{'+CORE+'}object',id='1000',type='model');components=ET.SubElement(ob,'{'+CORE+'}components')
 b=ET.SubElement(main,'{'+CORE+'}build');ET.SubElement(b,'{'+CORE+'}item',objectid='1000',transform=transform(BM),printable='1')
 model=ET.Element('{'+CORE+'}model',unit='millimeter');res=ET.SubElement(model,'{'+CORE+'}resources')
 cfg=ET.Element('config');oc=ET.SubElement(cfg,'object',id='1000');md(oc,'name',part);md(oc,'extruder',1)
 vertices,index=np.unique(oriented.reshape(-1,3),axis=0,return_inverse=True);faces=index.reshape(-1,3)
 assert np.array_equal(vertices[faces],oriented)
 boxes=[]
 def component(oid,name,subtype,v,f):
  mesh_object(res,oid,v,f);ET.SubElement(components,'{'+CORE+'}component',{'{'+PROD+'}path':'/3D/Objects/current.model','objectid':str(oid),'{'+PROD+'}UUID':str(uuid.uuid4()),'transform':transform(np.eye(4))})
  p=ET.SubElement(oc,'part',id=str(oid),subtype=subtype,uuid=str(uuid.uuid4()));md(p,'name',name);md(p,'matrix',' '.join(format(x,'.17g')for x in np.eye(4).reshape(-1)));md(p,'source_file',str(folder/'oriented.stl')if subtype=='normal_part'else'current-local-support-contract');md(p,'source_object_id',0);md(p,'source_volume_id',0 if subtype=='normal_part'else oid)
  for axis in 'xyz':md(p,'source_offset_'+axis,0)
  ET.SubElement(p,'mesh_stat',face_count=str(len(f)),edges_fixed='0',degenerate_facets='0',facets_removed='0',facets_reversed='0',backwards_edges='0')
 component(1,part,'normal_part',vertices,faces)
 pocket=olddata.get('pocket_contract')
 if part!='cable-input-cover':
  assert pocket and len(olddata['enforcers'])==2
  for j,(name,v,f)in enumerate(enforcer_geometry(part,pocket)):
   bounds=[v.min(0).tolist(),v.max(0).tolist()];prior=next(e for e in olddata['enforcers']if e['name']==name);assert np.max(np.abs(np.array(bounds)-np.array(prior['local_bounds'])))<1e-12
   ov=affine(v,local_to_oriented);component(20+j,name,'support_enforcer',ov,f);boxes.append({'name':name,'objectid':str(20+j),'subtype':'support_enforcer','shape':'box'if part=='cable-input-body'else'hex_AF5.8','local_bounds':bounds,'local_vertices':v.tolist(),'faces':f.tolist(),'oriented_vertices':ov.tolist(),'mesh_file':'3D/Objects/current.model'})
 else:assert not pocket
 pl=ET.SubElement(cfg,'plate');md(pl,'plater_id',1);md(pl,'locked','false');md(pl,'filament_map_mode','Auto For Flush');md(pl,'filament_maps',1);md(pl,'filament_volume_maps',0);inst=ET.SubElement(pl,'model_instance');md(inst,'object_id',1000);md(inst,'instance_id',0);md(inst,'identify_id',15);ET.SubElement(cfg,'assemble')
 rr=ET.Element('Relationships',xmlns=REL);ET.SubElement(rr,'Relationship',Target='/3D/3dmodel.model',Id='rel-model',Type='http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel')
 mr=ET.Element('Relationships',xmlns=REL);ET.SubElement(mr,'Relationship',Target='/3D/Objects/current.model',Id='rel-current-mesh',Type='http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel')
 types=ET.Element('Types',xmlns=CT)
 for ext,typ in [('rels','application/vnd.openxmlformats-package.relationships+xml'),('model','application/vnd.ms-package.3dmanufacturing-3dmodel+xml'),('config','application/xml')]:ET.SubElement(types,'Default',Extension=ext,ContentType=typ)
 entries={'[Content_Types].xml':xml(types),'_rels/.rels':xml(rr),'3D/3dmodel.model':xml(main),'3D/_rels/3dmodel.model.rels':xml(mr),'3D/Objects/current.model':xml(model),'Metadata/model_settings.config':xml(cfg),'Metadata/project_settings.config':json.dumps(project).encode()}
 inp=folder/'support-input.3mf'
 with zipfile.ZipFile(inp,'w',compression=zipfile.ZIP_DEFLATED)as z:
  for n,data in entries.items():z.writestr(n,data)
 # Re-read our archive to prove the normal triangle array is the current input,
 # not merely a matching box. Native output identity is independently reviewed.
 with zipfile.ZipFile(inp)as z:
  root=ET.fromstring(z.read('3D/Objects/current.model'));me=root.find('./m:resources/m:object[@id="1"]/m:mesh',NS);vv=np.array([[float(v.attrib[k])for k in 'xyz']for v in me.findall('./m:vertices/m:vertex',NS)]);ff=np.array([[int(f.attrib[k])for k in ['v1','v2','v3']]for f in me.findall('./m:triangles/m:triangle',NS)]);assert np.array_equal(vv[ff],oriented)
 for n in ['machine','process','filament']:shutil.copy2(old.parent/(n+'.json'),folder/(n+'.json'))
 process=json.loads((folder/'process.json').read_text());assert process['layer_height']=='0.1'and process['initial_layer_print_height']=='0.1';assert process['enable_support']==('0'if part=='cable-input-cover'else'1')
 if boxes:assert process['support_type']=='normal(manual)'and process['raft_first_layer_expansion']=='0'
 return {'cad_to_oriented':A.tolist(),'input_local_to_cad':L.tolist(),'input_local_to_oriented':local_to_oriented.tolist(),'oriented':{'file':str(folder/'oriented.stl'),'sha256':SHA(folder/'oriented.stl')},'oriented_bounds_mm':[oriented.min((0,1)).tolist(),oriented.max((0,1)).tolist()],'triangle_count':len(tri),'input_3mf_normal_triangle_array_exact_match':True,'input_3mf_build_transform':BM.tolist(),'input_3mf_component_transform':np.eye(4).tolist(),'input_3mf_source_offset':[0,0,0],'input3mf':{'file':str(inp),'sha256':SHA(inp)},'input3mf_sha256':SHA(inp),'historical_selected_3mf':{'file':str(old),'sha256':SHA(old)},'historical_invocation':{'file':str(oldinv),'sha256':SHA(oldinv)},'historical_profile_sha256':{n:SHA(old.parent/(n+'.json'))for n in ['machine','process','filament']},'historical_3mf_geometry_reused':False,'historical_cached_artifacts_reused':False,'input_3mf_entries':list(entries),'discarded_historical_entries':[n for n in oldnames if n not in entries],'enforcers':boxes,'pocket_contract':pocket,'orientation':'CAD +Y growth; current lowest surface on bed'if part!='cable-input-cover'else'CAD -Y growth; localZ14 on bed','assumptions':{'machine':'X1C 0.4','material':'Generic PETG; user brand unknown','plate':'Textured PEI inherited process assumption; user confirmed PEI only','layer_height_mm':.1,'support_scope':'historical two local M3 enforcers only; NOT proof of adequate support for new geometry'if boxes else'disabled diagnostic','new_body_backplate_height_mm':3 if part=='cable-input-body'else None}}

def native_mapping(folder):
 with zipfile.ZipFile(folder/'slice-review.3mf')as z:
  main=ET.fromstring(z.read('3D/3dmodel.model'));cfg=ET.fromstring(z.read('Metadata/model_settings.config'));build=main.findall('./m:build/m:item',NS);components=main.findall('./m:resources/m:object/m:components/m:component',NS);out=[]
  for p in cfg.findall('./object/part'):
   c=next(c for c in components if c.attrib['objectid']==p.attrib['id']);meta={m.attrib.get('key'):m.attrib.get('value')for m in p.findall('./metadata')if 'key'in m.attrib}
   out.append({'objectid':p.attrib['id'],'subtype':p.attrib['subtype'],'mesh_file':c.attrib['{'+PROD+'}path'],'component_transform':matrix(c.attrib.get('transform')).tolist(),'source_offset':[float(meta.get('source_offset_'+x,0))for x in 'xyz'],'metadata_matrix':meta.get('matrix'),'mesh_stat':p.find('./mesh_stat').attrib})
  assert len(build)==1 and sum(p['subtype']=='normal_part'for p in out)==1
  project=json.loads(z.read('Metadata/project_settings.config'));g=z.read('Metadata/plate_1.gcode');assert hashlib.sha256(g).hexdigest()==SHA(folder/'plate_1.gcode')
  for n in ['Metadata/plate_1.png','Metadata/plate_1_small.png']:
   if n in z.namelist():(folder/Path(n).name).write_bytes(z.read(n))
  return {'build_transform':matrix(build[0].attrib.get('transform')).tolist(),'parts':out,'embedded_gcode_sha256':hashlib.sha256(g).hexdigest(),'actual_settings':{k:project.get(k)for k in ['printer_model','printer_variant','nozzle_diameter','filament_type','curr_bed_type','layer_height','initial_layer_print_height','enable_support','support_type','support_on_build_plate_only','support_top_z_distance','support_bottom_z_distance','support_interface_top_layers','support_interface_spacing','support_object_xy_distance','raft_first_layer_expansion','wall_loops','sparse_infill_density','brim_width']}}

def run_one(part,export,ep,binding,bp,inventory,ip,out,common):
 folder=out/part;folder.mkdir();row=next(r for r in export['parts']if r['id']=='feeder/'+part);hist=next(r for r in binding['items']if r['instance_id']==row['id']);assert row['sha256']==hist['current_stl_sha256']
 inv={'part':part,'selector':'ci_'+part.removeprefix('cable-input-'),'input':{k:row[k]for k in ['id','file','sha256']},'input_stl':{'file':str(abs_path(row['file'])),'sha256':row['sha256']},'export_report':str(ep),'export_report_sha256':SHA(ep),'inventory':{'file':str(ip),'sha256':SHA(ip)},'historical_binding':{'file':str(bp),'sha256':SHA(bp)},'source_sha256_at_start':export['source_sha256'],'local_profile_sha256':{},'runner_sha256':SHA(__file__),'bambu_binary_sha256':SHA(BAMBU),'sent_to_printer':False,'manufacturing_release':False,'physical_acceptance':False,'status':'PREPARING'}
 dump(folder/'invocation.json',inv)
 try:
  inv.update(build_input(folder,part,row,hist,inventory['scene_contract']['ci']));inv['local_profile_sha256']={n:SHA(folder/(n+'.json'))for n in ['machine','process','filament']};inv['shared_profile_sha256']=common
  command=[str(BAMBU),'--datadir',str(folder/'app-data'),'--load-settings',str(folder/'machine.json')+';'+str(folder/'process.json'),'--load-filaments',str(folder/'filament.json'),'--orient','0','--arrange','0','--ensure-on-bed','--slice','0','--export-3mf','slice-review.3mf','--outputdir',str(folder),inv['input3mf']['file']]
  inv.update(command=command,status='NATIVE_SLICE_RUNNING');dump(folder/'invocation.json',inv)
  run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True);(folder/'bambu-cli.log').write_text(run.stdout+run.stderr);inv['return_code']=run.returncode;inv['native_result']=json.loads((folder/'result.json').read_text())if(folder/'result.json').exists()else None
  inv['artifact_sha256']={n:SHA(folder/n)for n in ['slice-review.3mf','plate_1.gcode']if(folder/n).exists()};inv['input_and_cad_stable']=all(SHA(ROOT/p)==h for p,h in export['source_sha256'].items())and SHA(abs_path(row['file']))==row['sha256'];inv['shared_profiles_untouched']=all(SHA(ROOT/p)==h for p,h in common.items())
  inv['status']='SLICE_FAILED_OR_STALE'
  if run.returncode==0 and (inv['native_result']or{}).get('return_code')==0 and len(inv['artifact_sha256'])==2 and inv['input_and_cad_stable']and inv['shared_profiles_untouched']:
   inv['actual_3mf']=native_mapping(folder);dump(folder/'native-mapping.json',inv['actual_3mf']);inv['status']='SLICE_GENERATED_REVIEW_REQUIRED'
 except Exception as e:inv.update(status='EXECUTION_ERROR',error=repr(e),traceback=traceback.format_exc())
 dump(folder/'invocation.json',inv);brief={'part':part,'folder':str(folder),'status':inv['status'],'invocation_sha256':SHA(folder/'invocation.json'),'warnings':[p.get('warning_message')for p in (inv.get('native_result')or{}).get('sliced_plates',[])],'error':inv.get('error')};print(json.dumps(brief,ensure_ascii=False),flush=True);return brief

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--export-report',type=Path,default=DEFAULT_EXPORT);ap.add_argument('--binding',type=Path,default=DEFAULT_BINDING);ap.add_argument('--parts',nargs='+',choices=PARTS,default=PARTS);ap.add_argument('--workers',type=int,choices=[1,2],default=2);args=ap.parse_args();ep=args.export_report.resolve();bp=args.binding.resolve();export=json.loads(ep.read_text());binding=json.loads(bp.read_text());ip=ROOT/'docs/cable-assembly-inventory.json';inventory=json.loads(ip.read_text())
 assert export['status']=='CURRENT_SCENE_EXPORT_PASS' and export['sources_stable'];assert all(SHA(ROOT/p)==h for p,h in export['source_sha256'].items());assert SHA(ip)==export['inventory_sha256'];assert inventory['scene_contract']['ci']['origin']==[75,-85,5]
 out=ROOT/'output/current-eclip-slices'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);shared={rel(p):SHA(p)for p in (ROOT/'output/print-review/config').glob('*.json')};dump(out/'snapshot.json',{'export_report':str(ep),'sha256':SHA(ep),'binding':str(bp),'binding_sha256':SHA(bp),'inventory_sha256':SHA(ip),'source_sha256':export['source_sha256'],'script_sha256':SHA(__file__),'bambu_binary_sha256':SHA(BAMBU),'parts':args.parts,'shared_profile_sha256':shared});dump(out.parent/'latest.json',{'folder':str(out),'status':'STARTED'});print('OUTPUT='+str(out),flush=True)
 results=[]
 with ThreadPoolExecutor(max_workers=args.workers)as pool:
  futures={pool.submit(run_one,p,export,ep,binding,bp,inventory,ip,out,shared):p for p in args.parts}
  for f in as_completed(futures):results.append(f.result());dump(out/'progress.json',results)
 stable=all(SHA(ROOT/p)==h for p,h in export['source_sha256'].items());report={'status':'OFFLINE_SLICES_GENERATED_REVIEW_REQUIRED'if stable and all(r['status']=='SLICE_GENERATED_REVIEW_REQUIRED'for r in results)else'SLICE_BATCH_INCOMPLETE','parts':results,'source_stable':stable,'export_report':str(ep),'export_report_sha256':SHA(ep),'script_sha256':SHA(__file__),'sent_to_printer':False,'manufacturing_release':False,'physical_acceptance':False,'scope':'Current normal geometry rebuilt exactly before native import. Inherited process is diagnostic; actual output mesh, support and features require independent review.'};dump(out/'report.json',report);dump(out.parent/'latest.json',{'folder':str(out),'report':str(out/'report.json'),'report_sha256':SHA(out/'report.json'),'status':report['status']});print(json.dumps({'status':report['status'],'report':str(out/'report.json')}),flush=True)
if __name__=='__main__':main()
