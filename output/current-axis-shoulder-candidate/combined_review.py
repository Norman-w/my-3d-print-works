#!/usr/bin/env python3
"""Small native integration check for the two isolated pivot revisions."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,hashlib,datetime,importlib.util
out=Path(__file__).resolve().parent
root=out.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('axis_review',root/'output/current-axis-through-candidate/review.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def main():
 run=out/'combined'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
 sources=['cad/cable-trigger-input.scad','cad/parameters.scad',
  'output/current-axis-through-candidate/candidate.scad','output/current-axis-through-candidate/review.py',
  'output/current-axis-shoulder-candidate/candidate.scad','output/current-axis-shoulder-candidate/assembly.scad',
  'output/current-axis-shoulder-candidate/combined_review.py','output/current-axis-retention-review/candidate.scad']
 ident={s:sha(root/s) for s in sources}
 def job(case):
  kind,u=case;n=f'{kind}-{u}';stl=run/(n+'.stl');log=run/(n+'.log')
  cmd=['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--export-format=asciistl','-o',str(stl),'-D',f'part="{kind}"','-D',f'input_u={u}',str(out/'assembly.scad')]
  p=subprocess.run(cmd,capture_output=True,text=True);s=p.stdout+p.stderr;log.write_text(s)
  assert 'ERROR:' not in s and 'WARNING:' not in s,s
  empty='Current top level object is empty.' in s
  return {'case':n,'command':cmd,'native_empty':empty,'returncode':p.returncode,'log_sha256':sha(log),
   'stl_sha256':None if empty else sha(stl),'mesh':None if empty else helper.inspect(stl)}
 with ThreadPoolExecutor(max_workers=2) as pool:
  cases=list(pool.map(job,[('axis-rotor-probe',0),('rotor-plastic-probe',0),('rotor-plastic-probe',20),('bush-solid-control',0)]))
 assert all(sha(root/s)==v for s,v in ident.items())
 assert all(c['native_empty'] for c in cases[:3])
 assert cases[3]['mesh']['signed_volume_mm3']>100
 r={'status':'COMBINED_ISOLATED_LIMITED_PASS','source_sha256':ident,'sources_stable':True,'cases':cases,
  'scope':'Nominal combined geometry; two rotor/plastic poses. Continuous circumscribed axle Z envelope with rest rotor; shared central bore is rotation invariant. Solid bush control must be nonempty. Does not prove complete tolerance, tilted escape, material, load or supply acceptance.',
  'adopted':False,'physical_acceptance':False}
 (run/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 (out/'combined-latest.json').write_text(json.dumps({'directory':str(run.relative_to(root)),'report_sha256':sha(run/'report.json')},indent=2)+'\n')
 print(json.dumps({'run':str(run.relative_to(root)),'status':r['status'],'control_volume_mm3':cases[3]['mesh']['signed_volume_mm3']},ensure_ascii=False))
if __name__=='__main__':main()
