#!/usr/bin/env python3
"""Render the actual current local feeder assembly; no generated geometry."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import struct
import subprocess

ROOT=Path(__file__).resolve().parents[1]
CAD=ROOT/'cad/cable-complete-review.scad'
EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def sources():
    paths={Path(__file__).resolve()};pending=[CAD]
    while pending:
        p=pending.pop().resolve()
        if p in paths:continue
        paths.add(p)
        pending.extend(p.parent/n for n in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}

def main():
    out=ROOT/'output/cable-direct-adoption/render'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    before=sources()
    def render(spec):
        name,t,camera=spec;target=out/(name+'.png')
        command=[EXE,'--hardwarnings','--backend','Manifold','--render','--imgsize=2200,1800',
          '--projection=o','--autocenter','--viewall','--colorscheme=Tomorrow','--camera='+camera,
          '-D','ccr_t='+str(t),'-o',str(target),str(CAD)]
        r=subprocess.run(command,cwd=ROOT,text=True,capture_output=True);log=r.stdout+r.stderr
        (out/(name+'.log')).write_text(log)
        ok=r.returncode==0 and target.is_file() and not any(x in log for x in ['WARNING:','ERROR:'])
        dimensions=list(struct.unpack('>II',target.read_bytes()[16:24])) if target.exists() else None
        return {'name':name,'t':t,'camera':camera,'command':command,'returncode':r.returncode,
          'execution_ok':ok,'file':str(target.relative_to(ROOT)),'sha256':sha(target) if target.exists() else None,
          'dimensions_px':dimensions}
    with ThreadPoolExecutor(max_workers=2) as pool:
        renders=list(pool.map(render,[('whole-rest',0,'0,0,0,60,0,135,850'),
          ('whole-pulled',1,'0,0,0,60,0,135,850'),('whole-pulled-reverse',1,'0,0,0,75,0,315,850')]))
    stable=before==sources()
    report={'status':'NATIVE_CAD_PNG_EXPORTED_NOT_YET_VISUALLY_CHECKED' if stable and all(r['execution_ok'] for r in renders) else 'FAIL_OR_STALE',
      'source_sha256':before,'sources_stable':stable,'renders':renders,'visual_review':{'performed':False},
      'scope':'Current complete local feeder and cable mechanism with terminal cap, fasteners, return spring, housing route and bend retainer. Does not include unmeasured blower, tee, backpack, hand or the separately located spin head.',
      'manufacturing_release':False,'physical_acceptance':False}
    target=out/'report.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['status'],target)
    return 0 if stable and all(r['execution_ok'] for r in renders) else 1

if __name__=='__main__':raise SystemExit(main())
