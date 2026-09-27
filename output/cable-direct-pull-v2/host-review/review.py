#!/usr/bin/env python3
"""Finite v2 added-geometry/known-host intersections; official sources read only."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib,json,re,subprocess,sys,time
R=Path(__file__).resolve().parents[3]
O=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'analysis'))
from feeder_integration import classify
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
C=R/'output/cable-direct-pull-v2/candidate.scad'
V=R/'output/cable-direct-pull-v2/housing-route/equal-length-route.scad'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
HEADER=f'''include <{C}>
use <{V}>
use <{R/'cad/launcher-final-assembly.scad'}>
use <{R/'cad/cable-trigger-system.scad'}>
use <{R/'cad/cable-trigger-input.scad'}>
use <{R/'cad/cable-output-interface.scad'}>
use <{R/'cad/cable-route-retention.scad'}>
use <{R/'cad/cable-housing-route.scad'}>
use <{R/'cad/feeder-return-spring.scad'}>
use <{R/'cad/outlet-retention.scad'}>
use <{R/'cad/inlet-retention-final.scad'}>
u=0;delta=0;kind="moving-host";fault=false;
assert(u==0||u==10||u==20);
assert(delta==-2||delta==0||delta==2);
module known_host(t,guide=true){{
 la_fixed_printed();ct_original_other_moving(t);co_frame(t);co_lug_cap(t);
 ct_original_fixed_hardware();la_moving_hardware(t);co_fixed_bridge();co_hardware(t);
 rs_spring(t,true);or_pipe();ir_hose_reference();
 if(guide){{crr_base();crr_cap();crr_lower();crr_hardware();}}
}}
module body_growth(){{difference(){{cdp_body();ci_body();}}}}
module nonmount_input_metal(d){{cdp_to_cad()cdp_local_fixed_hardware(d);}}
module local_current_input(t,d){{
 cdp_body();cdp_cover();cdp_moving(20*t);cdp_fixed_hardware(d);
}}
// Clear route against actual host and input metal/printed geometry, with no
// own steel core. Full 1 mm clearance would intentionally enter the third
// guide's 6.2 mm bore; that guide is tested separately with nominal OD5.
if(kind=="moving-host")union(){{
 intersection(){{cdp_moving(u);union(){{known_host(u/20);cv_housing(delta);if(fault)cdp_lever(u);}}}}
 intersection(){{cdp_cable(u,delta);known_host(u/20);}}
}}
else if(kind=="body-growth-host")intersection(){{body_growth();union(){{known_host(u/20);cv_housing(delta);if(fault)body_growth();}}}}
else if(kind=="input-fixed-metal-host")intersection(){{nonmount_input_metal(delta);known_host(u/20);}}
else if(kind=="route-clearance-host")intersection(){{cv_envelope(delta,1,true);union(){{
 known_host(u/20,false);local_current_input(u/20,delta);
 if(fault)translate(cv_arc_point(1,.5,delta,cv_shift(delta)))sphere(d=12,$fn=24);
}}}}
else if(kind=="route-nominal-guide")intersection(){{cv_housing(delta);union(){{crr_base();crr_cap();crr_lower();crr_hardware();}}}}
else if(kind=="cover-added")difference(){{cdp_cover();ci_cover();}}
else if(kind=="cover-removed")difference(){{ci_cover();cdp_cover();}}
else assert(false,"Unknown host review kind");
'''
def sources(wrapper):
 paths={Path(__file__).resolve(),R/'analysis/feeder_integration.py',R/'analysis/exact_mesh.py'}
 todo=[wrapper]
 while todo:
  p=todo.pop().resolve()
  if p in paths:continue
  paths.add(p)
  for n in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()):todo.append(p.parent/n)
 return {str(p.relative_to(R)):sha(p) for p in sorted(paths)}
def execute(out,wrapper,job):
 kind,u,d,fault=job
 name=f'{kind}-u{u}-d{d}'+('-positive-control' if fault else '')
 target=out/(name+'.stl')
 defs={'kind':kind,'u':u,'delta':d,'fault':fault}
 cmd=[EXE,'--hardwarnings','--backend','Manifold','--export-format','asciistl']
 for k,v in defs.items():cmd+=['-D',k+'='+json.dumps(v)]
 cmd+=['-o',str(target),str(wrapper)]
 start=time.time();p=subprocess.run(cmd,cwd=R,capture_output=True,text=True)
 log=p.stdout+p.stderr;(out/(name+'.log')).write_text(log)
 empty='Current top level object is empty' in log and not target.exists()
 good=not any(x in log for x in ['WARNING:','ERROR:']) and (p.returncode==0 or empty) and (target.exists() or empty)
 info=classify(target) if target.exists() else {'components':[],'has_solid_or_unclassified_overlap':False}
 passed=good and info['has_solid_or_unclassified_overlap']==fault
 row={'name':name,'kind':kind,'u_mm':u,'delta_mm':d,'expected_solid_overlap':fault,'command':cmd,'returncode':p.returncode,'seconds':time.time()-start,'execution_ok':good,'explicit_empty_log_and_no_mesh':empty,'file':str(target.relative_to(R)) if target.exists() else None,'sha256':sha(target) if target.exists() else None,'classification':info,'passed':passed}
 print(name,passed,'empty',empty,round(row['seconds'],2),flush=True)
 return row
def main():
 out=O/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir()
 wrapper=out/'probes.scad';wrapper.write_text(HEADER)
 before=sources(wrapper)
 (out/'sources-at-start.json').write_text(json.dumps(before,indent=2)+'\n')
 jobs=[(k,u,d,False) for k in ['moving-host','body-growth-host','input-fixed-metal-host','route-clearance-host'] for u in [0,10,20] for d in [-2,0,2]]
 jobs += [('route-nominal-guide',0,d,False) for d in [-2,0,2]]
 jobs += [('cover-added',0,0,False),('cover-removed',0,0,False)]
 jobs += [(k,0,0,True) for k in ['moving-host','body-growth-host','route-clearance-host']]
 rows=[]
 with ThreadPoolExecutor(max_workers=2) as pool:
  for row in pool.map(lambda job:execute(out,wrapper,job),jobs):
   rows.append(row);(out/'progress.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 after=sources(wrapper);stable=before==after
 passed=stable and all(x['passed'] for x in rows)
 report={'status':'V2_SAMPLED_ADDED_GEOMETRY_HOST_PASS' if passed else 'FAIL_OR_STALE','sources_stable':stable,'source_sha256':before,'source_sha256_at_end':after,'candidate_sha256':before[str(C.relative_to(R))],'route_sha256':before[str(V.relative_to(R))],'results':rows,'samples':{'u_mm':[0,10,20],'delta_mm':[-2,0,2]},'scope':'Finite pose intersections of new moving lever/cap/hardware and core, exact new body material, nonmount input fixed metal, and an equal-length route family against explicitly listed current local host. Not full continuous motion or an unsupported real hose shape guarantee.','body_partition':'body_growth is exact Boolean candidate body minus official ci_body. No mount contact surfaces are removed by tolerance. Existing body remaining inside baseline is outside this added-material check. Symmetric cover differences are checked empty.','known_host_modules':['la_fixed_printed','ct_original_other_moving','co_frame','co_lug_cap','ct_original_fixed_hardware','la_moving_hardware','co_fixed_bridge','co_hardware','rs_spring(t,true)','or_pipe','ir_hose_reference','crr_base/cap/lower/hardware'], 'intentional_mates':'Own steel core is excluded from housing collisions. Moving/core separately tested so core is not intersected with its own housing. Mount bolts omitted only from nonmount metal check; existing thread engagement is not re-certified. Full route 1mm envelope excludes first/last15mm and third-arc retainer; nominal OD5 housing is independently intersected with full retainer at all delta samples. Retainer 6.2 bore is expected to be within inflated OD7 clearance, so inflated-route/retainer overlap is not called a collision.','unverified':['baseline remaining input body contact acceptance is inherited and not re-certified','continuous u or delta between samples','actual unrestrained hose shape/minimum radius','ferrule seating and first/last15mm route clearance','unknown blower/tee/hand/backpack geometry','loads, friction, return, clearances after printing, one-ball release'],'manufacturing_release':False,'physical_acceptance':False}
 (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (O/'latest-run.json').write_text(json.dumps({'report':str((out/'report.json').relative_to(R)),'status':report['status']},indent=2)+'\n')
 print(report['status'],out/'report.json',flush=True)
 return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
