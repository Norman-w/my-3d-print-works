#!/usr/bin/env python3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,importlib.util,json,re,subprocess
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sp=importlib.util.spec_from_file_location('helper',ROOT/'output/current-axis-through-candidate/review.py')
helper=importlib.util.module_from_spec(sp);sp.loader.exec_module(helper)
def main():
 run=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
 sources={Path(__file__),ROOT/'output/current-axis-through-candidate/review.py',ROOT/'output/cable-scene-export/20260927T091627124663Z/feeder__beam-grip.stl'}
 pending=[OUT/'probes.scad']
 while pending:
  p=pending.pop().resolve()
  if p in sources:continue
  sources.add(p);pending.extend(p.parent/d for d in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
 ids={str(p.relative_to(ROOT)):sha(p) for p in sorted(sources)}
 def one(name):
  stl=run/(name+'.stl');log=run/(name+'.log')
  cmd=['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--hardwarnings','--backend','Manifold','--export-format','asciistl','-D','ci_origin=[75,-85,5]','-D',f'at_case="{name}"','-o',str(stl),str(OUT/'probes.scad')]
  p=subprocess.run(cmd,capture_output=True,text=True);s=p.stdout+p.stderr;log.write_text(s)
  assert 'WARNING:' not in s and 'ERROR:' not in s,s
  empty='Current top level object is empty.' in s
  assert p.returncode==0 or p.returncode==1 and empty
  r={'case':name,'command':cmd,'returncode':p.returncode,'native_empty':empty,'mesh':None if empty else helper.inspect(stl),'log_sha256':sha(log),'stl_sha256':None if empty else sha(stl)}
  print(name,empty,flush=True);return r
 names=['head-bench','nut-bench','tools-mutual','head-drive-fit','nut-drive-fit','shaft-insertion','installed-head-positive']
 with ThreadPoolExecutor(max_workers=2) as pool:cases=list(pool.map(one,names))
 by={c['case']:c for c in cases}
 checks={n:by[n]['native_empty'] for n in names[:5]}
 si=by['shaft-insertion'];checks['shaft-insertion']=si['native_empty'] or abs(si['mesh']['signed_volume_mm3'])<1e-7 and si['mesh']['each_triangle_on_one_contact_plane']
 po=by['installed-head-positive'];checks['installed-head-positive']=not po['native_empty'] and po['mesh']['signed_volume_mm3']>.01
 assert all(sha(ROOT/n)==h for n,h in ids.items())
 r={'status':'OFFSET_AXIS_BENCH_ACCESS_LIMITED_PASS' if all(checks.values()) else 'REVIEW_REQUIRED','source_sha256':ids,'sources_stable':True,'checks':checks,'cases':cases,
  'tool_budget':{'head_key':'SW5, 2.5 engagement, long leg60, short arm25, bend half-envelope4, OD5.8, axial insertion40, complete rotation','head_tip_z_mm':[17.3,18.25],'nut_tool':'SW10 socket OD14 length40 cavity20, handle R70 thickness12 center55 behind mouth, axial insertion40, complete rotation','socket_mouth_z_mm':[-16.1,-15.45]},
  'scope':'Unloaded bench module at u=0, disconnected/parked free cable and housing, mounting bolts absent. All current input neighbors included. Coaxial 40mm shoulder insertion includes both root envelopes. Tools are dimensional budgets, not selected supply. Installed head entry rejected by original beam.',
  'assembly_sequence':['Bench-assemble body, lever/POM bush, thrust washers and cover with side fasteners','Insert shoulder from cover side while aligning bore stack','Fit centering cup pocket toward shoulder; install M6 locknut and hold both ends with specified tools','Only then attach module to beam through four shared M4x60 bolts','For central-axis service detach four shared bolts first while independently supporting input and output structures'],
  'unverified':['Actual tooling and hand envelope','Torque, thread locking life, real supplier root and cup seating','Print tolerances and distortion','Flexible cable and housing installation'],
  'adopted':False,'manufacturing_release':False,'physical_acceptance':False}
 (run/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 (OUT/'latest.json').write_text(json.dumps({'directory':str(run.relative_to(ROOT)),'report_sha256':sha(run/'report.json')},indent=2)+'\n')
 print(json.dumps({'status':r['status'],'checks':checks,'directory':str(run.relative_to(ROOT))},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
