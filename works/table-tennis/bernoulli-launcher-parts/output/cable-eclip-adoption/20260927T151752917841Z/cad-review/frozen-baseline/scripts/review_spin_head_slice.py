#!/usr/bin/env python3
"""Slice ten spin-head parts offline with isolated PETG/TPU settings. No printer IO."""
from pathlib import Path
import argparse, collections, hashlib, json, re, shutil, subprocess, sys, zipfile
import numpy as np
import xml.etree.ElementTree as ET
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'analysis'))
from feeder_body_geometry import read_mesh, mesh_topology
from review_hold_fork_slice import canonical_mesh, stl_faces, project_facts, FIELDS
import review_integrated_shell_slice as shell
shell.np=np; shell.collections=collections
OUT=ROOT/'output/print-review/spin-head';CONFIG=ROOT/'output/print-review/config'
BAMBU='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
PROFILES=Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL')
SPECS={
 'body':(0,True,'inlet down; exterior tree supports accessible through open service sides'),
 'carriage':(-90,False,'pad side down; guide posts vertical'),
 'pad':(-90,False,'TPU working face down; tapered edge grows toward dovetail'),
 'pad-keeper':(0,False,'flat underside down; countersinks open upward'),
 'opposite-guide':(-90,False,'external flange down; curved guide grows upward'),
 'cover':(-90,True,'four stop ends down; open external supports under cover plate'),
 'spring-cage':(-90,True,'small annular end down; accessible external ears supported'),
 'spring-seat':(90,False,'full back disk down; pilot grows upward'),
 'pull-cap':(-90,False,'axis vertical; open bore'),
 'hold-fork':(-90,False,'axis vertical; fork slot and screw bore open'),
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def flatten(name,kind,record):
 p=PROFILES/kind/(name+'.json');d=json.loads(p.read_text());record[str(p)]=sha(p)
 r=flatten(d['inherits'],kind,record) if d.get('inherits') else {}
 for inc in d.get('include',[]):
  ip=PROFILES/kind/(inc+'.json');frag=json.loads(ip.read_text());record[str(ip)]=sha(ip)
  r.update({k:v for k,v in frag.items()if k not in ['name','type','from','instantiation','inherits','include']})
 r.update(d);r.pop('inherits',None);r.pop('include',None);return r
def prepare(folder,name):
 folder.mkdir(parents=True,exist_ok=True)
 shutil.copy2(CONFIG/'machine.json',folder/'machine.json')
 proc=json.loads((CONFIG/'process.json').read_text());support=SPECS[name][1]
 proc.update(enable_support='1'if support else'0',support_type='tree(auto)',support_on_build_plate_only='1',enable_prime_tower='0')
 record={}
 if name=='pad':
  filament=flatten('Bambu TPU 95A HF @BBL X1C','filament',record)
  filament.update(name='Spin pad TPU95A HF offline',nozzle_temperature=['230'],nozzle_temperature_initial_layer=['230'])
  for k in list(filament):
   if 'plate_temp'in k:filament[k]=['35']
  proc.update(sparse_infill_density='100%',sparse_infill_pattern='concentric',outer_wall_speed=['20','20'],inner_wall_speed=['30','30'],top_surface_speed=['20','20'],initial_layer_speed=['15','15'],initial_layer_infill_speed=['15','15'],overhang_1_4_speed=['10','10'],overhang_2_4_speed=['10','10'],overhang_3_4_speed=['10','10'],overhang_4_4_speed=['10','10'],bridge_speed=['15','15'])
 else:filament=json.loads((CONFIG/'filament.json').read_text())
 dump(folder/'process.json',proc);dump(folder/'filament.json',filament)
 return record
def slice_one(name):
 folder=OUT/name; stl=ROOT/f'output/spin-head/spin-{name}.stl'
 sources=prepare(folder,name);rotation=SPECS[name][0]
 cmd=[BAMBU,'--datadir',str(folder/'app-data'),'--load-settings',str(folder/'machine.json')+';'+str(folder/'process.json'),'--load-filaments',str(folder/'filament.json'),'--orient','0']
 if rotation:cmd+=['--rotate-y',str(rotation)]
 cmd+=['--arrange','1','--ensure-on-bed','--slice','0','--export-3mf','spin-slice-review.3mf','--outputdir',str(folder),str(stl)]
 identity={'input':str(stl.relative_to(ROOT)),'input_sha256':sha(stl),'cad_sha256':{f'cad/{n}':sha(ROOT/'cad'/n)for n in ['parameters.scad','spin-parameters.scad','spin-head.scad']},'command':cmd,'profile_sources':sources,'private_profiles':{n:sha(folder/(n+'.json'))for n in ['machine','process','filament']},'sent_to_printer':False}
 for n in ['result.json','plate_1.gcode','spin-slice-review.3mf']:(folder/n).unlink(missing_ok=True)
 dump(folder/'invocation.json',identity)
 p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
 (folder/'bambu-cli.log').write_text(p.stdout+p.stderr)
 identity['returncode']=p.returncode;dump(folder/'invocation.json',identity)
 if p.returncode:raise RuntimeError(f'{name}: Bambu CLI {p.returncode}')
 with zipfile.ZipFile(folder/'spin-slice-review.3mf')as z:(folder/'plate-preview.png').write_bytes(z.read('Metadata/plate_1.png'))
 print('SLICED',name,flush=True)
def audit_one(name):
 folder=OUT/name;inv=json.loads((folder/'invocation.json').read_text());stl=ROOT/inv['input']
 native=json.loads((folder/'result.json').read_text());g=(folder/'plate_1.gcode').read_text();first=g.index('; CHANGE_LAYER')
 temps=re.findall(r'^M10[49]\b[^\n;]*?\bS([-+\d.]+)',g[:first],re.M)
 waits=re.findall(r'^M109\b[^\n;]*?\bS([-+\d.]+)',g[:first],re.M)
 fact=project_facts(folder/'spin-slice-review.3mf');face_hash=canonical_mesh(stl_faces(stl));t,_=read_mesh(stl)
 # 3MF re-centres then serializes vertices; decimal-bin hashes can disagree
 # at a rounding boundary. Require one-to-one nearest-vertex identity AND
 # identical triangle connectivity, with a recorded small numerical bound.
 ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
 with zipfile.ZipFile(folder/'spin-slice-review.3mf')as z:
  main=ET.fromstring(z.read('3D/3dmodel.model'));comp=main.find('./m:resources/m:object/m:components/m:component',ns)
  obj=ET.fromstring(z.read(next(v.lstrip('/')for k,v in comp.attrib.items()if k.endswith('}path'))))
  verts=np.array([[float(v.attrib[a])for a in 'xyz']for v in obj.findall('.//m:vertex',ns)])+np.array(fact['source_offset'])
  indices=np.array([[int(v.attrib[a])for a in ['v1','v2','v3']]for v in obj.findall('.//m:triangle',ns)])
 unique,original_index=np.unique(t.reshape(-1,3),axis=0,return_inverse=True)
 dist,nearest=cKDTree(unique).query(verts)
 same_faces=collections.Counter(tuple(sorted(v))for v in original_index.reshape(-1,3))==collections.Counter(tuple(sorted(v))for v in nearest[indices])
 embedded={'max_vertex_displacement_mm':float(dist.max()),'vertex_bijection':len(verts)==len(unique)and len(set(nearest.tolist()))==len(unique),'same_triangle_connectivity':same_faces,'numerical_tolerance_mm':1e-5,'decimal_bin_hash_equal':fact['canonical_source_mesh_sha256_5dp']==face_hash}
 embedded_ok=embedded['vertex_bijection']and same_faces and dist.max()<=1e-5
 links=shell.mesh_links(t);top=mesh_topology(t)
 # float32 inputs converted to float64: exact-zero area checked independently
 # of any triangle-area threshold. Positive tiny triangles are retained.
 cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);exact_zero=int(np.all(cross==0,axis=1).sum())
 c=np.array(fact['component_transform']);b=np.array(fact['build_transform']);R=c[:9].reshape(3,3).T
 e=np.array([*map(float,re.search(r'^; extruder_offset = ([^\n]+)',g,re.M)[1].split(',')[0].split('x')),0.])
 tr=-R@np.array(fact['source_offset'])+c[9:]+b[9:]-e
 support=[];model=[];features=collections.Counter();widths=collections.defaultdict(set);layers=set()
 for layer,lh,feature,width,pts in shell.paths(folder/'plate_1.gcode'):
  q=(pts-tr)@R;features[feature]+=1;widths[feature].add(width);layers.add((layer,lh))
  if feature.startswith('Support'):support.append((q,width,lh))
  elif feature not in ['Skirt','Brim','Custom']:model.append(q)
 support_points=np.concatenate([v[0]for v in support])if support else np.empty((0,3))
 model_points=np.concatenate(model)if model else np.empty((0,3))
 support_report={'segments':len(support),'assembly_centerline_bounds_mm':shell.bounds(support_points),'maximum_reported_line_width_mm':max([v[1]for v in support],default=0),'maximum_layer_height_mm':max([v[2]for v in support],default=0),'interpretation':'Centerline bounds only; footprint expands laterally by half line width and downward by full layer height. Not a proof of support removal.'}
 # Persist actual support paths in assembly coordinates for independent access
 # review. Per-segment widths/heights remain present; not only head centrelines.
 np.savez_compressed(folder/'support-paths.npz',points=support_points,width=np.concatenate([np.full(len(q),w)for q,w,h in support])if support else [],height=np.concatenate([np.full(len(q),h)for q,w,h in support])if support else [],rotation=R,translation=tr)
 machine=json.loads((folder/'machine.json').read_text());official=json.loads((PROFILES/'machine/Bambu Lab X1 Carbon 0.4 nozzle.json').read_text());fields={}
 for inc in official['include']:
  d=json.loads((PROFILES/'machine'/(inc+'.json')).read_text())
  for f in FIELDS:
   if f in d:fields[f]=machine.get(f)==d[f]
 warnings=[p.get('warning_message')for p in native.get('sliced_plates',[])if p.get('warning_message')]
 target=230 if name=='pad'else 255
 checks={'native_zero':inv['returncode']==0 and native.get('return_code')==0,'no_native_warning':not warnings,'five_official_templates':len(fields)==5 and all(fields.values()),'first_layer_setpoint':bool(temps)and float(temps[-1])==target,'first_layer_M109':bool(waits)and float(waits[-1])==target,'source_stl_identity':sha(stl)==inv['input_sha256'],'source_cad_identity':all(sha(ROOT/p)==h for p,h in inv['cad_sha256'].items()),'embedded_mesh_matches':bool(embedded_ok),'mesh_single_closed_surface':top['boundary_edges']==0 and top['nonmanifold_edges']==0 and top['edge_connected_surface_components']==1,'vertex_links_single_cycle':not links['vertex_link_faults'],'no_exact_zero_area_triangles':exact_zero==0}
 plate=native['sliced_plates'][0]
 report={'part':name,'checks':checks,'input_sha256':inv['input_sha256'],'material':'Bambu TPU95A HF'if name=='pad'else'PETG','orientation':SPECS[name][2],'warnings':warnings,'first_layer_M109_c':float(waits[-1])if waits else None,'template_matches':fields,'three_mf':fact,'model_path_assembly_bounds_mm':shell.bounds(model_points),'support':support_report,'feature_segment_counts':dict(features),'actual_line_widths_mm':{k:sorted(v)for k,v in widths.items()},'actual_layer_heights_mm':sorted({h for z,h in layers}),'layer_count':len(layers),'mesh_topology':top,'vertex_links':links,'exact_zero_area_triangles':exact_zero,'seconds_estimate':plate['total_predication'],'grams_estimate':sum(v['total_used_g']for v in plate['filaments']),'artifact_sha256':{n:sha(folder/n)for n in ['spin-slice-review.3mf','plate_1.gcode','support-paths.npz']},'sent_to_printer':False}
 report['embedded_mesh_comparison']=embedded
 dump(folder/'review.json',report);print('AUDITED',name,checks,flush=True);return report
def main():
 a=argparse.ArgumentParser();a.add_argument('--part',choices=list(SPECS),action='append');a.add_argument('--audit-only',action='store_true');o=a.parse_args()
 OUT.mkdir(parents=True,exist_ok=True);shared={n:sha(CONFIG/(n+'.json'))for n in ['machine','process','filament']};names=o.part or list(SPECS);rows=[]
 for n in names:
  if not o.audit_only:slice_one(n)
  rows.append(audit_one(n))
 stable=all(sha(CONFIG/(n+'.json'))==v for n,v in shared.items())
 report={'status':'OFFLINE_SLICES_GEOMETRY_IDENTITY_PASS_SUPPORT_REVIEW_SEPARATE'if stable and all(all(v['checks'].values())for v in rows)else'REVIEW_OPEN','parts':rows,'script_sha256':sha(Path(__file__)),'shared_configs':shared,'shared_unchanged':stable,'support_removal_evidence':'See docs/final-spin-print.md; native no-warning is not removal evidence.','assumptions':['X1C .4; 0.20mm layers; PETG 4 walls and25% infill; TPU100% concentric infill.','Textured PEI analysis assumption: user confirmed PEI, not its texture.','TPU uses external spool, no print task or AMS operation sent.'],'physical_acceptance':False,'sent_to_printer':False}
 access=OUT/'support-access-review.json'
 if access.exists()and len(names)==10:
  ar=json.loads(access.read_text());ar_stable=all(sha(ROOT/f"output/spin-head/spin-{p['part']}.stl")==p['input_stl_sha256']and sha(OUT/p['part']/'plate_1.gcode')==p['gcode_sha256']and sha(OUT/p['part']/'support-paths.npz')==p['support_path_sha256']for p in ar['parts'])
  report['support_access_review']={'path':str(access.relative_to(ROOT)),'sha256':sha(access),'inputs_current':ar_stable,'all_defined_corridors_clear':all(p['all_corridors_clear_in_stl']and p['all_corridors_clear_of_declared_model_beads']for p in ar['parts']),'scope':'Nominal specified tool access and actual model bead envelopes; no support fracture-force or complete physical extraction proof.'}
  if report['status'].startswith('OFFLINE')and ar_stable and report['support_access_review']['all_defined_corridors_clear']:report['status']='OFFLINE_SPIN_SLICES_AND_BOUNDED_SUPPORT_ACCESS_PASS_PHYSICAL_OPEN'
 dump(OUT/('report.json'if len(names)==10 else'partial-report.json'),report)
 if len(names)==10:
  final=ROOT/'output/print-review/final-spin';final.mkdir(exist_ok=True)
  report['selected_plates']=[{'id':'spin-'+v['part'],'inputs':[{'path':f"output/spin-head/spin-{v['part']}.stl",'sha256':v['input_sha256']}],'three_mf_path':str((OUT/v['part']/'spin-slice-review.3mf').relative_to(ROOT)),'three_mf_sha256':v['artifact_sha256']['spin-slice-review.3mf'],'material':v['material'],'time_seconds':v['seconds_estimate'],'filament_grams':v['grams_estimate'],'warnings':v['warnings']}for v in rows]
  dump(final/'report.json',report)
 return 0 if report['status'].startswith('OFFLINE')else 1
if __name__=='__main__':raise SystemExit(main())
