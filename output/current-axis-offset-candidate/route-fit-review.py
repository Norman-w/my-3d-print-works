#!/usr/bin/env python3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import subprocess,json,hashlib,re
out=Path(__file__).resolve().parent;root=out.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 run=out/'route-fit'/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
 found={str(Path(__file__).relative_to(root)):sha(Path(__file__))};pending=[out/'route-fit.scad']
 while pending:
  p=pending.pop().resolve();n=str(p.relative_to(root))
  if n in found:continue
  found[n]=sha(p);pending.extend(p.parent/d for d in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
 def job(name):
  target=run/(name+'.stl');log=run/(name+'.log')
  cmd=['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--hardwarnings','--export-format','asciistl','-D','ci_origin=[75,-85,5]','-D',f'part="{name}"','-o',str(target),str(out/'route-fit.scad')]
  p=subprocess.run(cmd,capture_output=True,text=True);s=p.stdout+p.stderr;log.write_text(s);empty='Current top level object is empty.' in s
  assert 'WARNING:' not in s and 'ERROR:' not in s,s
  assert p.returncode==0 or empty and p.returncode==1
  print(name,empty,flush=True)
  return {'case':name,'command':cmd,'returncode':p.returncode,'native_empty':empty,'log_sha256':sha(log),'artifact_sha256':None if empty else sha(target)}
 with ThreadPoolExecutor(max_workers=2) as pool:cases=list(pool.map(job,['axis','body','cover']))
 assert all(sha(root/n)==h for n,h in found.items())
 r={'status':'NOMINAL_REVISED_ROUTE_STATIC_CLEAR' if all(c['native_empty'] for c in cases) else 'REVIEW_REQUIRED','source_sha256':found,'cases':cases,
 'scope':'Explicit fn72 wrapper; nominal revised housing/core route at adjustment zero versus shifted body, cover and continuous coaxial shoulder envelope. Not all route adjustments, free flexible hose or actual manufacturing.','adopted':False,'physical_acceptance':False}
 (run/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 (out/'route-fit'/'latest.json').write_text(json.dumps({'directory':str(run.relative_to(root)),'report_sha256':sha(run/'report.json')},indent=2)+'\n')
 print(json.dumps({'directory':str(run.relative_to(root)),'status':r['status']},indent=2))
if __name__=='__main__':main()
