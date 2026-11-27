from pathlib import Path
import json,hashlib,math,re,sys,importlib.util,collections
import numpy as np
B=Path(__file__).resolve().parent;ROOT=B.parents[1]
R=Path(json.loads((B/'latest-run.json').read_text())['folder'])
sys.path.insert(0,str(ROOT/'analysis'))
from exact_mesh import exact_area_and_links
from feeder_integration import classify
ip=Path('/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
sp=importlib.util.spec_from_file_location('inspect_stl',ip);ins=importlib.util.module_from_spec(sp);sp.loader.exec_module(ins)
native=json.loads((R/'native-report.json').read_text());H=hashlib.sha256((B/'candidate.scad').read_bytes()).hexdigest()
assert H==native['source_sha256_before']==native['source_sha256_after']
def data(path):
 t=np.array(re.findall(rb'vertex\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)',path.read_bytes()),float).reshape(-1,3,3)
 a=t.reshape(-1,3);q=math.sqrt(.5);loc=np.column_stack([q*(-a[:,0]+75+a[:,2]-5),q*(a[:,0]-75+a[:,2]-5),a[:,1]+82])
 return t,loc
def stats(path):
 t,p=data(path)
 return dict(triangles=len(t),signed_volume_mm3=float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6),local_bounds=[p.min(0).tolist(),p.max(0).tolist()])
solids={};evidence=[];fail=[]
planes={'split-plane-contact':[3.1],'head-seat-contact':[4.5],'post-plane-contact':[8],'clamping-contact':[-.6,4.5]}
for v in native['results']:
 n,ex=v['name'],v['expect'];row={'name':n,'expect':ex,'native_empty':v['empty'],'native_warnings_or_errors':v['warnings_or_errors']}
 if ex=='solid':
  p=Path(v['file']);fmt,tt=ins._read_triangles(p);report=ins.inspect(p,1e-6);exact=exact_area_and_links(p);comp=classify(p)
  edges=collections.defaultdict(list)
  for tri in tt:
   for a,b in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])):
    a,b=tuple(a),tuple(b);k=tuple(sorted((a,b)));edges[k].append(1 if (a,b)==k else -1)
  rawbad=sum(len(x)!=2 or sum(x)!=0 for x in edges.values())
  ok=report['watertightByEdgeTopology'] and not exact['exact_zero_area_face_indices'] and not exact['non_ring_vertex_links'] and len(comp['components'])==1 and rawbad==0
  solids[n]={'sha256':v['sha256'],'backend':v['backend'],'inspection':report,'exact_area_and_links':exact,'components':comp['components'],'raw_bad_edge_count':rawbad,'strict_pass':ok}
  row['pass']=ok
 elif ex=='empty':row['pass']=v['empty'] and not v['warnings_or_errors']
 elif ex=='echo':row['pass']=v['returncode']==0 and not v['warnings_or_errors']
 elif v['empty']:
  row['pass']=ex!='positive-solid'
 else:
  p=Path(v['file']);m=stats(p);row['mesh']=m;t,local=data(p)
  if ex in planes:
   err=np.min(np.abs(local[:,2,None]-np.array(planes[ex])),axis=1).max()
   row['identified_contact_planes_local_z']=planes[ex];row['max_plane_arithmetic_residual_mm']=float(err)
   row['pass']=bool(err<=1e-10) # only named source seating planes; never a volume cutoff
  elif ex=='analytic-contact':
   radial=np.hypot(local[:,0]+24,local[:,1]);penetration=max(0,float(59.25-radial.min()));bound=59.25*(1-math.cos(math.radians(.025)))
   row.update(guide_radial_interval=[float(radial.min()),float(radial.max())],radial_mesh_penetration_mm=penetration,wire_arc_chord_bound_mm=bound)
   row['pass']=penetration<=bound+1e-8
  elif ex=='positive-solid':row['pass']=m['signed_volume_mm3']>0
  else:row['pass']=False
 if v['warnings_or_errors']:row['pass']=False
 if not row['pass']:fail.append(n)
 evidence.append(row)
report=dict(source_sha256=H,source_unchanged=True,status='LOCAL_NOMINAL_CHECKS_PASS' if not fail else 'LOCAL_CHECKS_REQUIRE_REVIEW',failures=fail,solid_meshes=solids,checks=evidence,limitations=['Actual core must remain seated under positive tension for the nominal path.','Only the named bearing/clamp seating planes and analytically derived guide/steel contact are classified as intentional.','21 stroke poses plus 22 mm are discrete; adjuster/ferrule external translation range is separately a continuous primitive-union envelope.','No whole-host/route/service, physical load, wear, return-force or manufacturing release is implied.'])
(R/'interpretation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'failures':fail,'solids':{k:{'strict':v['strict_pass'],'faces':v['inspection']['triangleCount'],'volume':v['inspection']['volume']} for k,v in solids.items()}},indent=2))
