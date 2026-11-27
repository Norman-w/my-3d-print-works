"""Process-only support-enforcer diagnostic. No CAD edits or print submission."""
from pathlib import Path
import json,hashlib,datetime,sys,subprocess,zipfile,xml.etree.ElementTree as ET,uuid,copy,concurrent.futures,shutil,itertools
import numpy as np
B=Path(__file__).resolve().parent;ROOT=B.parents[1];V2=ROOT/'output/cable-direct-pull-v2';sys.path.insert(0,str(ROOT/'analysis'));sys.path.insert(0,str(ROOT/'scripts'))
import cable_input_slice_review as p
import review_cable_slice as s
H='f76a83eeb95644bd3c856922b31da749cc47c083d688d271116f946493994588';assert s.sha(V2/'candidate.scad')==H
CORE='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';PROD='http://schemas.microsoft.com/3dmanufacturing/production/2015/06';REL='http://schemas.openxmlformats.org/package/2006/relationships';NS={'m':CORE}
ET.register_namespace('',CORE);ET.register_namespace('p',PROD)
O=B/'slices'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');O.mkdir(parents=True)
s.dump(B/'latest-slices.json',dict(folder=str(O),source_sha256=H))
S=V2/'slices/20260927T084928459673Z-f76a83eeb9'
FOLDERS={'cable-input-body':S/'cable-input-body','cable-input-lever':S/'cable-input-lever','cable-input-terminal-cap':ROOT/'output/print-review/current-cable/20260927T082206132152Z/cable-input-terminal-cap'}
POCKETS={'cable-input-body':dict(centres=[[-30,20],[74,20]],half=3.6,z=[-12,-8.8],contact=-9,opening='hex5.8',growth=1),'cable-input-lever':dict(centres=[[2,54],[2,66]],half=3.6,z=[-3.5,-.4],contact=-.6,opening='hex5.8',growth=1),'cable-input-terminal-cap':dict(centres=[[2,54],[2,66]],half=3.4,z=[4.3,7.5],contact=4.5,opening='circle6.2',growth=-1)}
SQT=np.sqrt(.5);LOCAL=np.array([[-SQT,SQT,0,75],[0,0,1,-82],[SQT,SQT,0,5],[0,0,0,1.]])
FACES=[[0,2,1],[1,2,3],[4,5,6],[5,7,6],[0,1,4],[1,5,4],[2,6,3],[3,6,7],[0,4,2],[2,4,6],[1,3,5],[3,7,5]]
def xml_bytes(root):
 # Bambu's relationship reader expects the default package namespace.
 ET.register_namespace('',REL if root.tag.startswith('{'+REL+'}')else CORE)
 data=ET.tostring(root,encoding='utf-8',xml_declaration=True);ET.register_namespace('',CORE);return data
def run(part):
 old=FOLDERS[part];f=O/part;f.mkdir();base=json.loads((old/'invocation.json').read_text());assert all(s.sha(old/n)==h for n,h in base['artifact_sha256'].items())
 selector={'cable-input-body':'body','cable-input-lever':'lever','cable-input-terminal-cap':'terminal-cap'}[part];native=V2/'runs/20260927T084134904834Z-f76a83eeb9'/(selector+'.stl');assert s.sha(native)==base['input']['sha256']
 with zipfile.ZipFile(old/'slice-review.3mf')as z:data={n:z.read(n)for n in z.namelist()}
 main=ET.fromstring(data['3D/3dmodel.model']);settings=ET.fromstring(data['Metadata/model_settings.config']);rels=ET.fromstring(data['3D/_rels/3dmodel.model.rels']);obj=main.find('./m:resources/m:object',NS);cs=obj.find('./m:components',NS);basec=cs.find('./m:component',NS);partcfg=settings.find('./object');assert len(partcfg.findall('./part'))==1
 C=p.three_mf_matrix(basec.attrib['transform']);pre=np.array(base['cad_to_oriented']);local_to_raw=np.linalg.inv(C)@pre@LOCAL
 cfg=POCKETS[part];boxes=[]
 for k,centre in enumerate(cfg['centres']):
  oid=str(20+k);name='M3_shoulder_enforcer_'+str(k+1);corn=np.array(list(itertools.product([centre[0]-cfg['half'],centre[0]+cfg['half']],[centre[1]-cfg['half'],centre[1]+cfg['half']],cfg['z'])))
  # Product order xyz makes z fastest; face order above assumes x fastest.
  corners=np.array([[centre[0]+sx*cfg['half'],centre[1]+sy*cfg['half'],zz]for zz in cfg['z']for sy in [-1,1]for sx in [-1,1]])
  vertices=p.affine(corners,local_to_raw)
  model=ET.Element('{'+CORE+'}model',{'unit':'millimeter'});resources=ET.SubElement(model,'{'+CORE+'}resources');ob=ET.SubElement(resources,'{'+CORE+'}object',id=oid,type='model');mesh=ET.SubElement(ob,'{'+CORE+'}mesh');vs=ET.SubElement(mesh,'{'+CORE+'}vertices');ts=ET.SubElement(mesh,'{'+CORE+'}triangles')
  for v in vertices:ET.SubElement(vs,'{'+CORE+'}vertex',**{a:format(x,'.17g')for a,x in zip('xyz',v)})
  for t in FACES:ET.SubElement(ts,'{'+CORE+'}triangle',**{a:str(x)for a,x in zip(['v1','v2','v3'],t)})
  file='3D/Objects/support_enforcer_'+oid+'.model';data[file]=xml_bytes(model)
  c=copy.deepcopy(basec);c.attrib['objectid']=oid;c.attrib['{'+PROD+'}path']='/'+file;c.attrib['{'+PROD+'}UUID']=str(uuid.uuid4());cs.append(c)
  pc=ET.SubElement(partcfg,'part',id=oid,subtype='support_enforcer',uuid=str(uuid.uuid4()));ET.SubElement(pc,'metadata',key='name',value=name)
  ET.SubElement(pc,'metadata',key='matrix',value=' '.join(format(v,'.17g')for v in C.reshape(-1)))
  ET.SubElement(pc,'metadata',key='source_file',value='process-only-enforcer');ET.SubElement(pc,'metadata',key='source_object_id',value='0');ET.SubElement(pc,'metadata',key='source_volume_id',value=str(k+1))
  ET.SubElement(pc,'mesh_stat',face_count='12',edges_fixed='0',degenerate_facets='0',facets_removed='0',facets_reversed='0',backwards_edges='0')
  ET.SubElement(rels,'{'+REL+'}Relationship',Target='/'+file,Id='rel-support-'+oid,Type='http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel')
  boxes.append(dict(name=name,objectid=oid,local_bounds=[corners.min(0).tolist(),corners.max(0).tolist()],mesh_file=file,raw_vertices=vertices.tolist()))
 data['3D/3dmodel.model']=xml_bytes(main);data['Metadata/model_settings.config']=xml_bytes(settings);data['3D/_rels/3dmodel.model.rels']=xml_bytes(rels)
 # Retain old preview only as explicitly inherited; never keep cached G-code.
 for n in list(data):
  if '.gcode'in n or n in ['Metadata/slice_info.config','Metadata/plate_1.json']:data.pop(n)
 input3mf=f/'support-input.3mf'
 with zipfile.ZipFile(input3mf,'w',compression=zipfile.ZIP_DEFLATED)as z:
  for n,v in data.items():z.writestr(n,v)
 for n in ['machine','filament']:shutil.copy2(old/(n+'.json'),f/(n+'.json'))
 proc=json.loads((old/'process.json').read_text());proc.update(enable_support='1',support_type='normal(manual)',support_on_build_plate_only='1',support_top_z_distance='0.2',support_bottom_z_distance='0.2',support_interface_top_layers='2',support_interface_spacing='0',support_object_xy_distance='0.35',raft_first_layer_expansion='0',layer_height='0.1',initial_layer_print_height='0.1');s.dump(f/'process.json',proc)
 cmd=[str(s.BAMBU),'--datadir',str(f/'app-data'),'--load-settings',str(f/'machine.json')+';'+str(f/'process.json'),'--load-filaments',str(f/'filament.json'),'--orient','0','--arrange','0','--ensure-on-bed','--slice','0','--export-3mf','slice-review.3mf','--outputdir',str(f),str(input3mf)]
 inv=dict(part=part,selector='cdp_'+selector.replace('-','_'),process_only=True,mechanical_geometry_changed=False,candidate_source=str(V2/'candidate.scad'),source_sha256=H,input_stl={'file':str(native),'sha256':s.sha(native)},inherited_invocation=str(old/'invocation.json'),inherited_invocation_sha256=s.sha(old/'invocation.json'),inherited_project_sha256=s.sha(old/'slice-review.3mf'),cad_to_oriented=base['cad_to_oriented'],enforcers=boxes,pocket_contract=cfg,command=cmd,input3mf_sha256=s.sha(input3mf),profile_sha256={n:s.sha(f/(n+'.json'))for n in ['machine','process','filament']},script_sha256=s.sha(__file__),sent_to_printer=False,manufacturing_release=False)
 s.dump(f/'invocation.json',inv);r=subprocess.run(cmd,capture_output=True,text=True,cwd=ROOT);(f/'bambu-cli.log').write_text(r.stdout+r.stderr);inv.update(returncode=r.returncode,source_stable=s.sha(V2/'candidate.scad')==H,artifacts={n:s.sha(f/n)for n in ['slice-review.3mf','plate_1.gcode']if(f/n).exists()});inv['native_result']=json.loads((f/'result.json').read_text())if(f/'result.json').exists()else None;inv['status']='SLICED_REVIEW_REQUIRED'if r.returncode==0 and len(inv['artifacts'])==2 else'SLICE_FAILED';s.dump(f/'invocation.json',inv);print(json.dumps({'part':part,'status':inv['status'],'warnings':[r.get('warning_message')for r in (inv['native_result']or{}).get('sliced_plates',[])]}),flush=True);return dict(part=part,folder=str(f),status=inv['status'])
print(str(O),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:results=list(pool.map(run,list(FOLDERS)))
s.dump(O/'report.json',dict(parts=results,source_sha256=H,mechanical_geometry_changed=False,manufacturing_release=False))
