#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,hashlib,re,sys
ROOT=Path(__file__).resolve().parents[2];BASE=Path(__file__).resolve().parent
RUN=BASE/'native'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');RUN.mkdir(parents=True)
SCAD=BASE/'candidate.scad';EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
identity={str(p.relative_to(ROOT)):sha(p)for p in [SCAD,ROOT/'cad/cable-trigger-input.scad',ROOT/'cad/parameters.scad',Path(__file__)]}
sys.path.insert(0,'/Users/norman/.codex/skills/openscad-stl-print/scripts');from inspect_stl import inspect

def run(name):
 p=RUN/(name+'.stl');cmd=[EXE,'--hardwarnings','--backend','Manifold','--export-format','asciistl','-D','ar_part='+json.dumps(name),'-o',str(p),str(SCAD)]
 r=subprocess.run(cmd,text=True,capture_output=True);log=r.stdout+r.stderr;(RUN/(name+'.log')).write_text(log)
 empty='Current top level object is empty'in log and not p.exists();assert not re.search(r'(?m)(ERROR|WARNING):',log)
 assert r.returncode==0 or(empty and r.returncode==1)
 out={'selector':name,'command':cmd,'returncode':r.returncode,'native_empty':empty,'log_sha256':sha(RUN/(name+'.log')),'artifact':str(p.relative_to(ROOT))if p.exists()else None,'artifact_sha256':sha(p)if p.exists()else None}
 if p.exists():out['mesh']=inspect(p,1e-7)
 print(name,'empty',empty,flush=True);return out
with ThreadPoolExecutor(max_workers=2)as pool:rows=list(pool.map(run,['lever','bush','thrust-washers','local-fit']))
assert rows[-1]['native_empty']
assert all(sha(ROOT/p)==h for p,h in identity.items())
r={'status':'LOCAL_CANDIDATE_EXPORT_AND_ZERO_POSE_FIT_COMPLETE_NOT_MANUFACTURING_RELEASE','source_sha256':identity,'sources_stable':True,'parts':rows,'scope':'Exports and nominal concentric zero-pose fit only; no force/tilt/whole-system/print claim.'}
(RUN/'report.json').write_text(json.dumps(r,indent=2)+'\n');(BASE/'native-latest.json').write_text(json.dumps({'directory':str(RUN.relative_to(ROOT)),'report_sha256':sha(RUN/'report.json')},indent=2)+'\n');print(RUN/'report.json')
