#!/usr/bin/env python3
"""Offline final feeder slicing. Never connects to a printer or edits CAD/presets."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse, collections, hashlib, importlib.util, json, re, shutil, subprocess, sys, zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/print-review/final-feeder'
CONFIG=ROOT/'output/print-review/config'
BAMBU='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
FIELDS=['machine_start_gcode','machine_end_gcode','time_lapse_gcode','change_filament_gcode','layer_change_gcode']
# These are specified orientations, not the slicer's automatic orient feature.
# Rotation X+90 maps original +Y to print +Z; Y+90 maps -X to +Z.
PLAN={
 'positive-half':([],True,'inlet-down','Original Z=-126 inlet end down; seam vertical'),
 'negative-half':([],True,'inlet-down','Original Z=-126 inlet end down; repaired groove vertical'),
 'beam-grip':(['--rotate-x','90'],True,'back-down','Original minimum Y back plane down'),
 'liner':([],False,'shoulder-down','Original Z=44 shoulder down; bore vertical'),
 'right-support':(['--rotate-y','90'],True,'outer-x-down-xy050-z040','Original X=75 outer face down; support XY gap .50 mm, top gap .40 mm'),
 'left-support':(['--rotate-y','-90'],True,'outer-x-down','Original X=-76 spring-post face down; external supports'),
 'x-gib':(['--rotate-x','90'],False,'back-down','Original Y=21 flat face down'),
 'x-cover':(['--rotate-y','90'],False,'outside-down','Original X=80.5 outside face down'),
 'frame':(['--rotate-x','90'],True,'plate-normal-up','Original +Y normal up; external underside supports'),
 'fixed-spacer':(['--rotate-x','90'],False,'axis-up','Original +Y shoulder-screw axis up'),
 'moving-spacer':(['--rotate-x','90'],False,'axis-up','Original +Y shoulder-screw axis up'),
 'capture-1':([],True,'lower-z-down','Original Z=40 lower flat face down'),
 'capture--1':([],True,'lower-z-down','Original Z=40 lower flat face down'),
 'pipe-clamp-1':([],True,'lower-z-down','Original Z=90 lower flat face down'),
 'pipe-clamp--1':([],True,'lower-z-down','Original Z=90 lower flat face down'),
 'y-cap':(['--rotate-x','-90'],False,'outside-down','Original Y=28 outer flat face down'),
 'y-gib':(['--rotate-x','90'],False,'back-down','Original minimum Y back plane down; contact teeth up'),
 'y-keeper':(['--rotate-x','90'],False,'back-down','Original Y=-17.5 back plane down; nut mouths up'),
 'finger':(['--rotate-x','90'],True,'back-down','Original local Y=-4.5 rear face down; V and M2 nut entry upwards; rod underside supported'),
 'pin-block':(['--rotate-x','-90'],False,'lip-down','Original Y=4.5 full L-shaped lip face down'),
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def load_module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def prepare():
 sys.path.insert(0,str(ROOT/'analysis'));model=load_module('final_geometry',ROOT/'analysis/launcher_final_assembly.py')
 rows=[v for v in model.inventory()if v['role']=='printed'];groups=collections.defaultdict(list)
 for row in rows:
  p=ROOT/'output/launcher-final'/f'{row["id"]}.stl'
  row.update(file=str(p.relative_to(ROOT)),path=str(p.relative_to(ROOT)),sha256=sha(p));groups[row['family']].append(row)
 assert len(rows)==33 and len(groups)==20 and set(groups)==set(PLAN)
 snapshot={'source_sha256':model.sources(),'parts':[{**r,'name':r['id']}for r in rows],
  'shared_profile_sha256':{n:sha(CONFIG/f'{n}.json')for n in ['machine','process','filament']},
  'printed_instances':33,'unique_geometry_families':20,'groups':dict(groups)}
 dump(OUT/'input-snapshot.json',snapshot);return snapshot
def slice_family(family,snapshot,variant=None,support_override=None):
 rotations,supported,orientation,description=PLAN[family]
 if support_override is not None:supported=support_override
 folder=OUT/(family+'-'+orientation+('-supported'if supported else'-unsupported')+(('-'+variant)if variant else''));folder.mkdir(parents=True,exist_ok=True)
 rows=snapshot['groups'][family]
 for row in rows:assert sha(ROOT/row['file'])==row['sha256']
 for n in ['machine','filament']:shutil.copy2(CONFIG/f'{n}.json',folder/f'{n}.json')
 process=json.loads((CONFIG/'process.json').read_text());process.update(enable_support='1'if supported else'0',support_type='tree(auto)',support_on_build_plate_only='1')
 if family=='right-support':process.update(support_object_xy_distance='0.5',support_top_z_distance='0.4')
 dump(folder/'process.json',process)
 name='shell-slice-review.3mf'if family in ['positive-half','negative-half']else'slice-review.3mf'
 cmd=[BAMBU,'--datadir',str(folder/'app-data'),'--load-settings',str(folder/'machine.json')+';'+str(folder/'process.json'),'--load-filaments',str(folder/'filament.json'),'--orient','0',*rotations,'--arrange','1','--ensure-on-bed','--slice','0','--export-3mf',name,'--outputdir',str(folder),*[str(ROOT/r['file'])for r in rows]]
 inv={'family':family,'part':family,'orientation':orientation,'orientation_description':description,'supports':'supported'if supported else'unsupported','command':cmd,'inputs':rows,'input':rows[0],
 'source_sha256_at_start':snapshot['source_sha256'],'shared_profile_sha256':snapshot['shared_profile_sha256'],'local_profile_sha256':{n:sha(folder/f'{n}.json')for n in ['machine','process','filament']},
 'assumptions':{'machine':'X1C 0.4 confirmed','material':'Generic PETG; brand unconfirmed','plate':'Textured PEI analysis assumption; only PEI confirmed','layer_height_mm':.2,'walls':4,'infill_percent':25,'supports':'tree(auto), build plate only'if supported else'disabled'},'sent_to_printer':False,'physical_acceptance':False}
 dump(folder/'invocation.json',inv)
 p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);(folder/'bambu-cli.log').write_text(p.stdout+p.stderr);inv['return_code']=p.returncode
 if(folder/'result.json').exists():inv['native_result']=json.loads((folder/'result.json').read_text())
 inv['input_and_cad_stable']=all(sha(ROOT/r['file'])==r['sha256']for r in rows)and all(sha(ROOT/p)==h for p,h in snapshot['source_sha256'].items())
 inv['shared_profiles_untouched']=all(sha(CONFIG/f'{n}.json')==h for n,h in snapshot['shared_profile_sha256'].items())
 inv['artifact_sha256']={n:sha(folder/n)for n in ['plate_1.gcode',name]if(folder/n).exists()}
 if(folder/'plate_1.gcode').exists():
  g=(folder/'plate_1.gcode').read_text();first=g.index('; CHANGE_LAYER');heats=re.findall(r'^M10[49]\b[^\n;]*?\bS([-+\d.]+)',g[:first],re.M);inv['last_temperature_before_first_layer_c']=float(heats[-1])if heats else None
 if(folder/name).exists():
  with zipfile.ZipFile(folder/name)as z:
   if'Metadata/plate_1.png'in z.namelist():(folder/'plate-preview.png').write_bytes(z.read('Metadata/plate_1.png'))
 dump(folder/'invocation.json',inv)
 print(json.dumps({'family':family,'count':len(rows),'exit':p.returncode,'native':inv.get('native_result',{}).get('return_code'),'warnings':[p.get('warning_message')for p in inv.get('native_result',{}).get('sliced_plates',[])]}),flush=True)
 return folder
def helper():
 import numpy as np, shapely, os, struct
 from shapely.geometry import Polygon,LineString,box
 from shapely.ops import unary_union
 h=load_module('shell_review',ROOT/'scripts/review_integrated_shell_slice.py')
 for k,v in locals().copy().items():setattr(h,k,v)
 h.collections=collections;h.IDENTITY=OUT/'input-snapshot.json'
 return h
def family_folder(family):
 _,supported,orientation,_=PLAN[family]
 return OUT/(family+'-'+orientation+('-supported'if supported else'-unsupported'))
def generic_review(family,h):
 import numpy as np, xml.etree.ElementTree as ET, os
 from shapely.geometry import LineString
 from shapely.ops import unary_union
 folder=family_folder(family);inv=json.loads((folder/'invocation.json').read_text());archive=folder/('shell-slice-review.3mf'if family in ['positive-half','negative-half']else'slice-review.3mf')
 ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'};maps=[];repairs=[]
 with zipfile.ZipFile(archive)as z:
  main=ET.fromstring(z.read('3D/3dmodel.model'));settings=ET.fromstring(z.read('Metadata/model_settings.config'))
  objects={n.attrib['id']:n for n in main.findall('./m:resources/m:object',ns)}
  config={n.attrib['id']:n for n in settings.findall('./object')}
  for build in main.findall('./m:build/m:item',ns):
   oid=build.attrib['objectid'];part=config[oid].find('./part');meta={m.attrib.get('key'):m.attrib.get('value')for m in part.findall('./metadata')};c=np.array(list(map(float,objects[oid].find('./m:components/m:component',ns).attrib['transform'].split())));b=np.array(list(map(float,build.attrib['transform'].split())));offset=np.array([float(meta['source_offset_'+a])for a in 'xyz']);R=b[:9].reshape(3,3).T@c[:9].reshape(3,3).T;shift=-R@offset+b[:9].reshape(3,3).T@c[9:]+b[9:]
   maps.append({'source_file':meta['source_file'],'R':R.tolist(),'shift':shift.tolist(),'offset':offset.tolist(),'component':c.tolist(),'build':b.tolist()});repairs.append(part.find('./mesh_stat').attrib)
 gcode=folder/'plate_1.gcode';header=gcode.read_text();raw=re.search(r'^; extruder_offset = ([^\n]+)',header,re.M).group(1).split(',')[0];nozzle=np.array([*map(float,raw.split('x')),0.])
 for m in maps:m['shift']=(np.array(m['shift'])-nozzle).tolist()
 # Actual G-code paths; only support points and selected layer paths retained.
 plate=inv['native_result']['sliced_plates'][0];zmax=max(float(o['bbox']['max'][2])for o in plate['objects'])if False else max(float(np.max(h.read_mesh(ROOT/r['file']).reshape(-1,3)@np.array(m['R']).T+np.array(m['shift']),axis=0)[2])for r,m in zip(inv['inputs'],maps))
 selected=sorted(set([.2]+[round(max(.2,zmax*f)/.2)*.2 for f in [.08,.2,.35,.5,.7,.85,.98]]))
 groups=collections.defaultdict(list);counts=collections.Counter();first=[];support=[];support_w=[];support_lh=[];bridges=[];all_bounds=[]
 for layer,lh,feature,width,pts in h.paths(gcode):
  counts[feature]+=1
  if feature not in ['Skirt','Brim','Prime tower'] and not feature.startswith('Support'):
   all_bounds.extend([pts.min(axis=0),pts.max(axis=0)])
   if abs(layer-.2)<1e-6:first.append(LineString(pts[:,:2]).buffer(width/2,quad_segs=12))
  if feature.startswith('Support'):
   support.append(pts);support_w.append(np.full(len(pts),width));support_lh.append(np.full(len(pts),lh))
  if feature=='Bridge':bridges.append(float(np.linalg.norm(np.diff(pts,axis=0),axis=1).sum()))
  if any(abs(layer-z)<1e-6 for z in selected):groups[round(layer,5)].append((feature,pts))
 footprint=unary_union(first);q=np.concatenate(support)if support else np.empty((0,3));w=np.concatenate(support_w)if support_w else np.empty(0);lh=np.concatenate(support_lh)if support_lh else np.empty(0)
 os.environ['MPLCONFIGDIR']=str(OUT/'matplotlib-config');os.environ['XDG_CACHE_HOME']=str(OUT/'cache')
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.collections import LineCollection
 fig,axs=plt.subplots(2,4,figsize=(16,8),layout='constrained');bounds=np.array(all_bounds);lo=bounds.min(axis=0);hi=bounds.max(axis=0)
 for ax,z in zip(axs.flat,selected):
  for sup,color in [(False,'#21678a'),(True,'#d58414')]:
   seg=[np.stack([p[:-1,:2],p[1:,:2]],axis=1)for feature,p in groups[round(z,5)]if feature.startswith('Support')==sup]
   if seg:ax.add_collection(LineCollection(np.concatenate(seg),colors=color,linewidths=.45))
  ax.set_xlim(lo[0]-6,hi[0]+6);ax.set_ylim(lo[1]-6,hi[1]+6);ax.set_aspect('equal');ax.set_title(f'Print Z={z:g}');ax.set_xlabel('X/mm');ax.set_ylabel('Y/mm')
 fig.suptitle(f'{family}: actual model (blue) and support (orange) paths');fig.savefig(folder/'layer-paths-overview.png',dpi=140);plt.close(fig)
 machine=json.loads((folder/'machine.json').read_text());official=Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL/machine')
 checks={'native_success_no_warning':inv['return_code']==0 and inv['native_result']['return_code']==0 and not plate['warning_message'],
 'correct_3mf_object_count':len(maps)==len(inv['inputs']),'correct_input_names':sorted(m['source_file']for m in maps)==sorted(Path(r['file']).name for r in inv['inputs']),
 'no_mesh_repair_by_slicer':all(int(s.get(k,'0'))==0 for s in repairs for k in ['edges_fixed','degenerate_facets','facets_removed','facets_reversed','backwards_edges']),
 'official_machine_templates_preserved':all(machine[f]==json.loads((official/f'Bambu Lab X1 Carbon 0.4 nozzle template {f}.json').read_text())[f]for f in FIELDS),
 'setpoint_255':inv['last_temperature_before_first_layer_c']==255,
 'proper_rotation_no_scaling':all(np.allclose(np.array(m['R']).T@np.array(m['R']),np.eye(3))and abs(np.linalg.det(m['R'])-1)<1e-6 for m in maps),
 'inside_X1C_build_box':bool((lo>=[0,0,0]).all()and(hi<=[256,256,250]).all()),
 'source_identity':inv['input_and_cad_stable']and all(sha(ROOT/r['file'])==r['sha256']for r in inv['inputs']),
 'shared_presets_unchanged':inv['shared_profiles_untouched']}
 result={'family':family,'folder':str(folder.relative_to(ROOT)),'count':len(inv['inputs']),'orientation':inv['orientation_description'],'checks':checks,'mapping':maps,'mesh_repair_stats':repairs,
 'first_layer_model_area_mm2':footprint.area,'first_layer_model_components':len(footprint.geoms)if hasattr(footprint,'geoms')else 1,
 'model_path_bounds_mm':[lo.tolist(),hi.tolist()],'support_sample_count':len(q),'feature_command_counts':dict(counts),'max_bridge_command_path_mm':max(bridges,default=0),'estimated_time_s':plate.get('total_predication'),'estimated_filament_g':sum(f['total_used_g']for f in plate.get('filaments',[])),
 'native_warnings':plate['warning_message'],'gcode_sha256':sha(gcode),'project_sha256':sha(archive),'sent_to_printer':False,
 'limits':['First-layer area is emitted-bead footprint, not adhesion strength.','Bridge command length is not unsupported span.','Bounds/CLI success do not prove physical fit, removal force, shrinkage or PETG finish.']}
 if len(maps)==1:
  m=maps[0];assembly=(q-np.array(m['shift']))@np.array(m['R']);np.savez_compressed(folder/'support-path-samples.npz',points=assembly,width=w,layer_height=lh)
  result['support_bounds_in_assembly_mm']=h.bounds(assembly)
 np.savez_compressed(folder/'support-print-path-samples.npz',points=q,width=w,layer_height=lh)
 dump(folder/'plate-review.json',result);print(f'review {family}: {all(checks.values())}',flush=True);return result
def review_all():
 h=helper();snapshot=json.loads((OUT/'input-snapshot.json').read_text());final=json.loads((ROOT/'output/launcher-final/report.json').read_text());index={r['id']:r for r in final['parts']};identity={'final_report_pass':final['status']=='INTEGRATED_FEEDER_DIGITAL_CHECKS_PASS','source_snapshot_matches_final':snapshot['source_sha256']==final['source_sha256'],'all33_STL_hashes_match':all(r['sha256']==index[r['id']]['sha256']==sha(ROOT/r['file'])for r in snapshot['parts'])}
 rows=[generic_review(f,h)for f in PLAN]
 for f in ['positive-half','negative-half']:h.review(family_folder(f),ROOT,sha,dump)
 report={'status':'TOOLPATH_REVIEW_IN_PROGRESS','input_identity':identity,'printed_instances':sum(r['count']for r in rows),'unique_geometry_families':len(rows),'plates':rows,'final_geometry_report_sha256':sha(ROOT/'output/launcher-final/report.json'),'source_sha256':snapshot['source_sha256'],'sent_to_printer':False,'physical_acceptance':False}
 dump(OUT/'report.json',report)
def critical_shells():
 """Reuse the explicit extrusion-envelope algorithm against CURRENT shell meshes."""
 from shapely.geometry import LineString,box,Polygon
 from shapely.ops import unary_union
 import numpy as np
 c=load_module('shell_critical',ROOT/'analysis/shell_critical_features.py');snapshot=json.loads((OUT/'input-snapshot.json').read_text());parts=[]
 for name,side in [('negative-half',-1),('positive-half',1)]:
  folder=family_folder(name);shift,mapping=c.mapping(folder);row=next(r for r in snapshot['parts']if r['id']==name);mesh=ROOT/row['file'];assert sha(mesh)==row['sha256'];features=[]
  if side<0:
   floor=c.floor_shapes(mesh,-.2)
   for i,p in enumerate(sorted(c.polygons(floor),key=lambda p:(p.centroid.y,p.centroid.x))):features.append({'id':f'groove_{i+1:02d}','kind':'groove','depth':.2,'shape':p})
   assert len(features)==10
  holes=c.floor_shapes(mesh,side*3.2)
  for i,(yy,zz)in enumerate([(40,-59),(-40,3)]):
   shape=holes.intersection(box(yy-4,zz-4,yy+4,zz+4));assert shape.area>6;features.append({'id':f'locator_{i+1}','kind':'capsule_locator'if side>0 and i==1 else'round_locator','depth':3.2,'shape':shape})
  grouped=collections.defaultdict(list)
  for p in c.model_paths(folder/'plate_1.gcode',shift,side):grouped[p['z_top']].append(p)
  layers={}
  for z,paths in grouped.items():
   low=[];high=[]
   for p in paths:
    line=LineString(p['points']);low.append(line.buffer(max(.00001,p['width']/2-c.ERROR),quad_segs=64));high.append(line.buffer(p['width']/2+c.ERROR,quad_segs=64))
   layers[z]={'z_top':z,'height':paths[0]['height'],'lower':unary_union(low),'upper':unary_union(high),'paths':paths}
  summaries=[]
  for f in features:
   assert f['shape'].convex_hull.difference(f['shape']).area<1e-8
   rows=[c.inspect_layer(f,l)for z,l in sorted(layers.items())if z>f['shape'].bounds[1]+1e-8 and z-l['height']<f['shape'].bounds[3]-1e-8];resolved=[r for r in rows if r['status']!='CAP_OR_PARTIAL_LAYER_NO_FULL_HEIGHT_CORE'];assert resolved
   summaries.append({'id':f['id'],'kind':f['kind'],'floor_bounds_YZ':list(f['shape'].bounds),'full_core_layers':len(resolved),'unresolved_layers':sum(r['status']=='NO_RESOLVED_CONNECTED_CORE'for r in resolved),'minimum_depth_lower_mm':min(r['center_Y_continuous_depth_lower_mm']for r in resolved),'minimum_clear_area_fraction_lower':min(r['connected_clear_area_lower_mm2']/r['nominal_core_area_mm2']for r in resolved),'layers':rows})
  repaired=[]
  if side<0:
   for yy in [-26.75,26.75]:
    area=floor.intersection(box(yy-.4,45,yy+.4,48)).area;check=[]
    for z,l in layers.items():
     if z-l['height']>=45.4-1e-7 and z<=48+1e-7:
      probe=box(.01,yy-.35,.19,yy+.35);free=c.externally_connected_void(l['upper'],box(-.5,yy-.8,.7,yy+.8));check.append({'z':z,'connected_core_area_mm2':probe.intersection(free).area})
    repaired.append({'center_Y':yy,'floor_area_Z45_to48_mm2':area,'all_repaired_interval_layers_have_exterior_connected_clear_core':all(r['connected_core_area_mm2']>1e-8 for r in check),'layers':check})
  part={'part':name,'stl_sha256':sha(mesh),'gcode_sha256':sha(folder/'plate_1.gcode'),'features':summaries,'repaired_outlet_interval':repaired};parts.append(part);print('critical',name,[(r['id'],r['unresolved_layers'])for r in summaries],flush=True)
 control={'empty_space_probe_mm2':c.externally_connected_void(Polygon(),box(-.5,-1,1.5,1)).intersection(box(0,-.4,1,.4)).area,'mouth_blocker_connected_probe_mm2':c.externally_connected_void(box(-.1,-2,.1,2),box(-.5,-1,1.5,1)).intersection(box(0,-.4,1,.4)).area}
 dump(OUT/'shell-critical-features.json',{'method':'Declared-width XY swept disks, emitted full layer height; ±.003 mm numerical envelope; arc chord error <=.0002 mm. Not measured PETG.', 'helper_sha256':sha(ROOT/'analysis/shell_critical_features.py'),'parts':parts,'controls':control,'passed':all(f['unresolved_layers']==0 for p in parts for f in p['features'])and all(r['all_repaired_interval_layers_have_exterior_connected_clear_core']for p in parts for r in p['repaired_outlet_interval']), 'physical_fit_or_sealing_proven':False})
def access_review():
 import numpy as np
 from shapely.geometry import Polygon
 from shapely.ops import unary_union
 h=helper();rows=[]
 for family in PLAN:
  folder=family_folder(family);r=json.loads((folder/'plate-review.json').read_text());d=np.load(folder/'support-print-path-samples.npz');q=d['points'];w=d['width'];lh=d['layer_height'];findings=[]
  corridors=[];exact_faces=[]
  for mapping in r['mapping']:
   R=np.array(mapping['R']);shift=np.array(mapping['shift']);center=(q-np.column_stack([np.zeros(len(q)),np.zeros(len(q)),lh/2])-shift)@R
   half=np.column_stack([w/2+.052,w/2+.052,lh/2])@abs(R)
   lower=center-half;upper=center+half
   def region(label,lo,hi,classification):
    mask=(upper>=lo).all(axis=1)&(lower<=hi).all(axis=1)
    findings.append({'source_file':mapping['source_file'],'region':label,'box_min':lo,'box_max':hi,'support_envelope_sample_hits':int(mask.sum()),'classification':classification,'hit_centers_bounds':h.bounds(center[mask])})
   def corridor(mesh,label,lo,hi):
    lo=np.array(lo);hi=np.array(hi);candidate=mesh[(mesh.max(axis=1)>=lo).all(axis=1)&(mesh.min(axis=1)<=hi).all(axis=1)]
    hits=sum(h.clipped_triangle_in_box(t,lo,hi)for t in candidate);reach=((center>=lo)&(center<=hi)).all(axis=1)
    corridors.append({'source_file':mapping['source_file'],'label':label,'min':lo.tolist(),'max':hi.tolist(),'pick_section_XZ_mm':[float((hi-lo)[0]),float((hi-lo)[2])],'actual_mesh_triangle_hits':hits,'support_center_samples_reached':int(reach.sum()),'scope':'Rectangular pick-tip access before hardware; section dimensions explicitly recorded; no force/debris test'})
   if family in ['left-support','right-support']:
    side=-1 if family=='left-support'else 1
    mesh=h.read_mesh(ROOT/'output/launcher-final'/mapping['source_file'])
    for z in [0,-28.5]:
     region(f'carrier_open_channel_Z{z}',[43.9 if side>0 else-57.7,-4.4,z-3.9],[57.7 if side>0 else-43.9,4.4,z+3.9],'internal_functional_channel')
     for zz in [(-4.1,-2.5),(2.5,4.1)]:region(f'Y_datum_band_Z{z}_{zz}',[44.4 if side>0 else-57.2,4.48,z+zz[0]],[57.2 if side>0 else-44.4,4.52,z+zz[1]],'functional_datum_face')
     for xx in [47,51,55]:corridor(mesh,f'open_minus_Y_channel_Z{z}_X{side*xx}',[side*xx-1,-25,z-1],[side*xx+1,3,z+1])
    if side>0:
     region('X_master_datum',[53.98,21.05,-34.9],[54.02,23.95,4.9],'functional_datum_face')
     # Resolve the AABB corner flags against the ACTUAL coplanar datum triangles.
     from shapely.geometry import LineString,box
     face=unary_union([Polygon(t[:,1:])for t in mesh[(abs(mesh[:,:,0]-54)<1e-5).all(axis=1)]if Polygon(t[:,1:]).area>1e-10]).intersection(box(21,-35,24,5));patches=[]
     for layer,height,feature,width,pts in h.paths(folder/'plate_1.gcode'):
      if not feature.startswith('Support'):continue
      a=(pts-shift)@R
      if a[:,0].min()<=54+1e-6 and a[:,0].max()+height>=54-1e-6:
       footprint=LineString(a[:,1:]).buffer(width/2+.002,quad_segs=32);hit=footprint.intersection(face)
       if hit.area>1e-8:patches.append({'area_mm2':hit.area,'bounds_YZ':list(hit.bounds)})
     control=face.intersection(box(21.5,-34,22.5,-33)).area
     exact_faces.append({'plane':'X54 master datum actual STL face','support_footprint_hit_patches':patches,'solid_face_positive_control_area_mm2':control,'reason':'3 coarse AABB corner flags require this circular-footprint intersection, not automatic dismissal.'})
   if family=='finger':
    stem=Path(mapping['source_file']).stem;item=next(v for v in json.loads((OUT/'input-snapshot.json').read_text())['parts']if v['id']==stem);side=item['definitions']['la_side'];rear=item['definitions']['la_rear'];mesh=h.read_mesh(ROOT/item['file']);bb=[mesh.min(axis=(0,1)),mesh.max(axis=(0,1))];gate=(bb[0][2]+bb[1][2])/2
    region('V_and_M2_entry_upper_region',[float(bb[0][0]),1.7,gate-4],[float(bb[1][0]),4.5,gate+4],'functional_V_and_nut_entry')
    region('rear_M3_nut_mouth',[float(bb[0][0]),-4.51,gate-3.3],[float(bb[1][0]),-1.85,gate+3.3],'open_rear_mouth_remove_before_nut')
    pinx=side*(41 if not rear else 46)
    for dz in [-1,0,1]:corridor(mesh,f'M3_open_rear_mouth_Zoffset{dz}',[pinx-.75,-10,gate+dz-.75],[pinx+.75,-2.2,gate+dz+.75])
   if family=='frame':
    mesh=h.read_mesh(ROOT/'output/launcher-final/frame.stl');tri=mesh[(abs(mesh[:,:,1]-8)<1e-5).all(axis=1)];face=unary_union([Polygon(t[:,[0,2]])for t in tri if Polygon(t[:,[0,2]]).area>1e-10]);holes=[Polygon(i)for p in ([face]if face.geom_type=='Polygon'else face.geoms)for i in p.interiors];count=0
    # Full closed slots are recovered from actual exported STL planar faces.
    import shapely
    active=(upper[:,1]>=8.01)&(lower[:,1]<=12.99)
    for hole in holes:
     xy=center[active][:,[0,2]];radius=np.linalg.norm(half[active][:,[0,2]],axis=1)
     count+=int(np.sum(shapely.distance(shapely.points(xy),hole)<=radius))
    findings.append({'region':'four_actual_STL_cam_slots_Y8_to13','actual_holes':len(holes),'support_envelope_sample_hits':count,'classification':'internal_cam_slots'})
  rows.append({'family':family,'count':r['count'],'support_sample_count':r['support_sample_count'],'findings':findings,'removal_tool_corridors':corridors,'exact_face_checks':exact_faces})
 dump(OUT/'support-access.json',{'method':'Actual positive-E support samples <=.1mm spacing; expanded by declared bead half-width + .052 mm in print XY and full emitted layer height, inverse 3MF transform. Region hits are conservative flags, not measured contact. Frame slot interiors recovered from current STL plane Y8.','families':rows,'physical_support_removal_tested':False})
 print(json.dumps([{'family':r['family'],'findings':r['findings']}for r in rows if r['findings']],ensure_ascii=False),flush=True)
def finalize():
 snapshot=json.loads((OUT/'input-snapshot.json').read_text());final=json.loads((ROOT/'output/launcher-final/report.json').read_text());index={r['id']:r for r in final['parts']};rows=[];selected=[];dest=OUT/'selected';dest.mkdir(exist_ok=True)
 for family in PLAN:
  folder=family_folder(family);inv=json.loads((folder/'invocation.json').read_text());r=json.loads((folder/'plate-review.json').read_text());rows.append(r);archive=folder/('shell-slice-review.3mf'if family in ['positive-half','negative-half']else'slice-review.3mf');copy=dest/(family+'.gcode.3mf');shutil.copy2(archive,copy)
  assert sha(archive)==r['project_sha256'] and sha(folder/'plate_1.gcode')==r['gcode_sha256']
  selected.append({'id':family,'quantity':len(inv['inputs']),'source_stls':[{'id':v['id'],'path':v['file'],'sha256':v['sha256']}for v in inv['inputs']],
   'gcode_3mf_path':str(copy.relative_to(ROOT)),'gcode_3mf_sha256':sha(copy),'gcode_path':str((folder/'plate_1.gcode').relative_to(ROOT)),'gcode_sha256':r['gcode_sha256'],
   'slice_folder':str(folder.relative_to(ROOT)),'orientation':r['orientation'],'supports':inv['supports'],'process_sha256':sha(folder/'process.json'),'filament_profile_sha256':sha(folder/'filament.json'),
   'estimated_time_seconds':r['estimated_time_s'],'estimated_filament_g':r['estimated_filament_g'],'material':'Generic PETG / actual brand unconfirmed','plate':'Textured PEI assumed; only PEI confirmed','warnings':r['native_warnings'],
   'preview_path':str((folder/'plate-preview.png').relative_to(ROOT)),'toolpath_preview_path':str((folder/('layer-paths.png'if family in ['positive-half','negative-half']else'layer-paths-overview.png')).relative_to(ROOT))})
 access=json.loads((OUT/'support-access.json').read_text());critical=json.loads((OUT/'shell-critical-features.json').read_text());shell=[json.loads((family_folder(f)/'toolpath-review.json').read_text())for f in ['positive-half','negative-half']]
 identity={'final_report_pass':final['status']=='INTEGRATED_FEEDER_DIGITAL_CHECKS_PASS','source_snapshot_matches_final':snapshot['source_sha256']==final['source_sha256'],'current_sources_match':all(sha(ROOT/p)==h for p,h in snapshot['source_sha256'].items()),'all33_STL_hashes_match':all(r['sha256']==index[r['id']]['sha256']==sha(ROOT/r['file'])for r in snapshot['parts']),'shared_profiles_untouched':all(sha(CONFIG/f'{n}.json')==h for n,h in snapshot['shared_profile_sha256'].items())}
 expected_z={f:([-1,0,0]if '--rotate-y'in PLAN[f][0]and PLAN[f][0][1]=='90'else[1,0,0]if '--rotate-y'in PLAN[f][0]else[0,1,0]if '--rotate-x'in PLAN[f][0]and PLAN[f][0][1]=='90'else[0,-1,0]if '--rotate-x'in PLAN[f][0]else[0,0,1])for f in PLAN}
 checks={'identity':all(identity.values()),'all20_native_and_instance_checks':all(all(r['checks'].values())for r in rows),'specified_face_to_bed_preserved':all(all(abs(v-e)<1e-6 for v,e in zip(m['R'][2],expected_z[r['family']]))for r in rows for m in r['mapping']),'both_shell_support_audits':all(all(s['checks'].values())for s in shell),'shell_model_features_resolved':critical['passed'],
  'all_measured_removal_corridors_clear_and_reach_support':all(c['actual_mesh_triangle_hits']==0 and c['support_center_samples_reached']>0 for a in access['families']for c in a['removal_tool_corridors']),
  'V_and_cam_slots_and_Y_datums_support_free':all(f['support_envelope_sample_hits']==0 for a in access['families']for f in a['findings']if f['classification']in ['functional_V_and_nut_entry','internal_cam_slots']or(f['classification']=='functional_datum_face'and f['region']!='X_master_datum')),
  'X_datum_exact_footprint_clear':all(not f['support_footprint_hit_patches']and f['solid_face_positive_control_area_mm2']>0 for a in access['families']for f in a['exact_face_checks']),
  '33_instances_20_families':sum(s['quantity']for s in selected)==33 and len(selected)==20}
 report={'status':'BOUNDED_OFFLINE_SLICE_REVIEW_PASS_PHYSICAL_OPEN'if all(checks.values())else'REVIEW_FLAGGED','checks':checks,'input_identity':identity,'printed_instances':33,'unique_geometry_families':20,'selected_plates':selected,'plates':rows,
  'source_sha256':snapshot['source_sha256'],'final_geometry_report_sha256':sha(ROOT/'output/launcher-final/report.json'),'review_script_sha256':sha(Path(__file__)),'support_access_report_sha256':sha(OUT/'support-access.json'),'shell_feature_report_sha256':sha(OUT/'shell-critical-features.json'),
  'total_estimated_time_seconds':sum(s['estimated_time_seconds']for s in selected),'total_estimated_filament_g':sum(s['estimated_filament_g']for s in selected),
  'not_selected':['finger-z-side-down-unsupported','finger-back-down-unsupported','right-support-outer-x-down-supported','right-support-outer-x-down-xy050-supported'],
  'support_removal_scope':'Two shell M4 side entries, left/right open carrier channels and finger rear nut mouths have actual-STL straight pick-tip access reaching support. Other support lies in split capture recesses/open exterior pockets or large frame/beam underside openings, inspected in actual layer plots. No physical removal force, scars or debris test.',
  'arrangement':'Bambu arrangement sometimes adds in-plane yaw; all actual 3MF matrices retained. Selected face-to-bed direction retained; no automatic out-of-plane orient or scaling.',
  'limits':['Offline slicing and bounded toolpath inspection only; no printer connected or job sent.','Generic PETG and Textured PEI remain profile assumptions; actual PETG brand and precise PEI texture were not provided.','Tree support removal and first-layer adhesion not physically tested.','Supported rod undersides and blind-nut roofs require careful clean-up without enlarging datum surfaces.','No claim of measured clearance, pressure seal, clamp load, fatigue, throughput or single-ball success rate.'],
  'sent_to_printer':False,'coupon_prerequisite':False,'manufacturing_release':False,'physical_acceptance':False}
 dump(OUT/'report.json',report)
 lines=['| 板ID | 件数 | 估算时间 | PETG估算 | 支撑 |','|---|---:|---:|---:|---|']
 for s in selected:
  secs=s['estimated_time_seconds'];lines.append(f'| `{s["id"]}` | {s["quantity"]} | {int(secs//3600)}h {int(secs%3600//60)}m | {s["estimated_filament_g"]:.1f} g | {"树支撑" if s["supports"]=="supported" else "无"} |')
 (OUT/'selected-plates-table.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'status':report['status'],'checks':checks,'seconds':report['total_estimated_time_seconds'],'grams':report['total_estimated_filament_g']},indent=2))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true');p.add_argument('--slice',nargs='*');p.add_argument('--workers',type=int,default=2);p.add_argument('--variant');p.add_argument('--support',choices=['on','off']);p.add_argument('--review',action='store_true');p.add_argument('--critical',action='store_true');p.add_argument('--access',action='store_true');p.add_argument('--generic-only',nargs='*');p.add_argument('--finalize',action='store_true');a=p.parse_args()
 snapshot=prepare()if a.prepare or not(OUT/'input-snapshot.json').exists()else json.loads((OUT/'input-snapshot.json').read_text())
 if a.slice is not None:
  families=a.slice or list(PLAN)
  with ThreadPoolExecutor(max_workers=a.workers)as pool:list(pool.map(lambda f:slice_family(f,snapshot,a.variant,None if a.support is None else a.support=='on'),families))
 if a.review:review_all()
 if a.critical:critical_shells()
 if a.generic_only is not None:
  h=helper()
  for f in a.generic_only or list(PLAN):generic_review(f,h)
 if a.access:access_review()
 if a.finalize:finalize()
if __name__=='__main__':main()
