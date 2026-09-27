#!/usr/bin/env python3
"""Current-source terminal-cap bench service; no physical or installed-hose claim."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,math,re,subprocess,sys
import numpy as np
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;CAD=R/'cad/cable-service-review.scad';EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
sys.path.insert(0,str(R/'analysis'))
from feeder_integration import classify

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sources():
 paths={Path(__file__).resolve(),R/'analysis/feeder_integration.py'};todo=[CAD]
 while todo:
  p=todo.pop().resolve()
  if p in paths:continue
  paths.add(p);todo.extend(p.parent/n for n in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
 return {str(p.relative_to(R)):sha(p) for p in sorted(paths)}
def triangles(p):
 return np.array(re.findall(rb'vertex\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)',p.read_bytes()),float).reshape(-1,3,3)
def local(t):
 x,y,z=t[...,0],t[...,1],t[...,2];q=math.sqrt(.5)
 return np.stack([q*(-x+75+z-5),q*(x-75+z-5),y+82],axis=-1)
def contact_review(kind,path):
 t=triangles(path);p=local(t);tol=1e-10;valid=[];labels=[];errors=[]
 for tri in p:
  matches=[]
  if kind=='terminal-tools':
   for j,c in enumerate([[2,54],[2,66]]):
    if np.min(tri[:,2])<6-tol or np.max(tri[:,2])>7.5+tol or np.max(np.linalg.norm(tri[:,:2]-c,axis=1))>2.5/math.sqrt(3)+tol:continue
    for k in range(6):
     a=k*math.pi/3;n=np.array([math.cos(a),math.sin(a)])
     err=float(np.max(np.abs((tri[:,:2]-c)@n-1.25)))
     if err<=tol:matches.append((f'bolt{j}-SW2.5-face{k}',err))
  elif kind=='terminal-bolts':
   err=float(np.max(np.abs(tri[:,2]-4.5)))
   if err<=tol and any(np.max(np.linalg.norm(tri[:,:2]-c,axis=1))<=2.75+tol for c in [[2,54],[2,66]]):matches.append(('head-seat-Z4.5',err))
  elif kind=='terminal-cap':
   err=float(np.max(np.abs(tri[:,2]-3.1)));q=tri[:,:2].copy();q[:,1]-=np.clip(q[:,1],54,66)
   if err<=tol and np.max(np.linalg.norm(q,axis=1))<=7+tol:matches.append(('lever-cap-Z3.1',err))
  elif kind=='main-cover':
   err=float(np.max(np.abs(tri[:,2]-8)))
   if err<=tol and any(np.max(np.linalg.norm(tri[:,:2]-c,axis=1))<=7+tol for c in [[-30,20],[74,20]]):matches.append(('cheek-post-Z8',err))
  valid.append(bool(matches));labels.append(matches[0][0] if matches else None);errors.append(matches[0][1] if matches else None)
 vol=float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6)
 return {'triangle_count':len(t),'signed_volume_mm3_diagnostic_only':vol,'all_triangles_on_named_bounded_contact_faces':bool(all(valid)),'unclassified_triangle_indices':[i for i,v in enumerate(valid) if not v],'max_named_face_residual_mm':max([e for e in errors if e is not None],default=None),'face_counts':{k:labels.count(k)for k in set(labels) if k},'local_bounds':[p.min(axis=(0,1)).tolist(),p.max(axis=(0,1)).tolist()],'criterion':'Each entire triangle must lie in one source-named bounded seating/socket face within 1e-10mm arithmetic residual; no volume threshold hides penetration.'}
def execute(out,kind,fault=False):
 name=kind+('-wrong-stage-positive' if fault else '')
 target=out/(name+'.stl');cmd=[EXE,'--hardwarnings','--backend','Manifold','--export-format','asciistl','-D','csr_part="bench-probe"','-D','csr_kind='+json.dumps(kind),'-D','csr_fault='+str(fault).lower(),'-o',str(target),str(CAD)]
 r=subprocess.run(cmd,cwd=R,capture_output=True,text=True);log=r.stdout+r.stderr;(out/(name+'.log')).write_text(log)
 empty='Current top level object is empty' in log and not target.exists()
 ok=not any(s in log for s in ['WARNING:','ERROR:']) and (r.returncode==0 or empty) and (target.exists() or empty)
 row={'name':name,'kind':kind,'expected_solid_overlap':fault,'command':cmd,'returncode':r.returncode,'execution_ok':ok,'explicit_empty':empty,'file':str(target.relative_to(R)) if target.exists() else None,'sha256':sha(target) if target.exists() else None}
 if target.exists():
  info=contact_review(kind,target);row['contact_review']=info
  if fault:
   generic=classify(target);row['generic_classification']=generic
   row['passed']=ok and generic['has_solid_or_unclassified_overlap'] and abs(info['signed_volume_mm3_diagnostic_only'])>1e-4 and not info['all_triangles_on_named_bounded_contact_faces']
  else:row['passed']=ok and info['all_triangles_on_named_bounded_contact_faces']
 else:row['passed']=ok and empty and not fault
 print(name,row['passed'],'empty',empty,flush=True);return row

def main():
 out=O/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir()
 before=sources();(out/'sources-at-start.json').write_text(json.dumps(before,indent=2)+'\n')
 # Fail if the explicitly copied screw envelope stops matching its source.
 source=(R/'cad/cable-trigger-input.scad').read_text()
 assert 'ci_zbolt(p[0],p[1],4.5,8,3,5.5,3,2.5)' in source
 assert 'ci_zhex(p[0],p[1],-3,2.4,5.5)' in source
 assert 'ci_zcyl(p[0],p[1],-3.1,2.6,3.1)' in source
 assert 'ci_zring(0,0,-3.5,11,12,8.2)' in source
 contract_cmd=[EXE,'--hardwarnings','-o',str(out/'contract.echo'),'-D','csr_part="contract"',str(CAD)]
 p=subprocess.run(contract_cmd,cwd=R,capture_output=True,text=True);(out/'contract.log').write_text(p.stdout+p.stderr)
 assert p.returncode==0 and not any(s in p.stdout+p.stderr for s in ['WARNING:','ERROR:'])
 jobs=[(k,False) for k in ['terminal-tools','terminal-bolts','terminal-cap','terminal-ball','main-cover']]+[(k,True) for k in ['terminal-tools','terminal-bolts','terminal-cap','terminal-ball']]
 with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(lambda j:execute(out,*j),jobs))
 after=sources();stable=before==after;passed=stable and all(r['passed'] for r in rows)
 report={'status':'TERMINAL_BENCH_SERVICE_NOMINAL_PASS' if passed else 'FAIL_OR_STALE','source_sha256':before,'source_sha256_at_end':after,'sources_stable':stable,'results':rows,'contract_command':contract_cmd,'contract_file':str((out/'contract.echo').relative_to(R)),'reused_facts':'Frozen v2 interpretation.json had cap/bolt sweeps at u0/10/20/22 and terminal insertion at u0. This run uses the adopted current source, adds local fixed metal/tool/socket constraints and a terminal+12mm-wire-stub exit corridor; no redesign.','scope':'Disconnected complete input module on bench at unloaded u0. Main cover/axis/cover bolts removed before terminal tools. Two M3 screws removed before terminal cap. Terminal cap removed before ball. Continuous straight local+Z sweeps at one service pose.','preconditions':['release output clamp and withdraw tail from its transverse bore','disconnect/park housing and open intermediate retainers, remove module','remove main cover and relevant axis/cover hardware; support unloaded lever at u0','keep the two rear M3 nuts from falling out','provide free wire slack for terminal lifting; remaining flexible wire path is unverified'],'positive_controls':'Real wrong-stage obstacles, not fake passes: leave main cover on for tool/bolt/cap paths; leave terminal cap on for ball exit. Each must produce volume.','unverified':['actual purchased tool/handle and hand clearance or torque','whole flexible remainder of core and housing during disconnection','physical PETG fit, loaded handling or screw retention','unmeasured rig environment'],'manufacturing_release':False,'physical_acceptance':False}
 p=out/'report.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(O/'latest-run.json').write_text(json.dumps({'report':str(p.relative_to(R)),'status':report['status']},indent=2)+'\n');print(report['status'],p)
 return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
