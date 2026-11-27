from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import subprocess,hashlib,json,re,time
O=Path(__file__).resolve().parent;R=O.parents[2];SCAD=O/'assembly.scad';EXE='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashes():
 paths={Path(__file__).resolve()}; todo=[SCAD]
 while todo:
  p=todo.pop().resolve()
  if p in paths:continue
  paths.add(p)
  todo.extend(p.parent/n for n in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
 return {str(p.relative_to(R)):sha(p) for p in sorted(paths)}
before=hashes()
(O/'source-before.json').write_text(json.dumps(before,indent=2)+'\n')
def render(v):
 name,u,camera=v;target=O/(name+'.png')
 cmd=[EXE,'--hardwarnings','--backend','Manifold','--render','--imgsize=2200,1800','--projection=o','--autocenter','--viewall','--colorscheme=Tomorrow','--camera='+camera,'-D','view_u='+str(u),'-D','view_delta=0','-o',str(target),str(SCAD)]
 t=time.time();r=subprocess.run(cmd,cwd=R,capture_output=True,text=True);log=r.stdout+r.stderr;(O/(name+'.log')).write_text(log)
 row={'file':str(target.relative_to(R)),'u_mm':u,'delta_mm':0,'camera':camera,'command':cmd,'returncode':r.returncode,'seconds':time.time()-t,'execution_ok':r.returncode==0 and target.is_file() and not any(e in log for e in ['WARNING:','ERROR:']),'sha256':sha(target) if target.is_file() else None}
 print(json.dumps(row),flush=True);return row
with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(render,[('whole-rest',0,'0,0,0,60,0,135,850'),('whole-pulled',20,'0,0,0,60,0,135,850')]))
after=hashes();stable=before==after
report={'status':'NATIVE_CAD_PNG_EXPORTED_NOT_YET_VISUALLY_CHECKED' if stable and all(x['execution_ok'] for x in rows) else 'FAIL_OR_STALE','utc':datetime.now(timezone.utc).isoformat(),'source_sha256':before,'source_sha256_at_end':after,'sources_stable':stable,'renders':rows,'scope':'Actual local complete feeder plus v2 input body/lever/terminal cap/main cover/all metal/core, current output carriage/guide/hardware, source return spring, current 3rd-bend retainer, and equal-length nominal delta0 housing route. Existing hard tube and soft hose are CAD references. Does not include the spin head, unmeasured blower, tee, hand or backpack. Native original feeder coordinates; transparent shells are display style only.','visual_review':{'performed':False},'geometry_changed':False,'official_cad_web_or_LAN_changed':False,'manufacturing_release':False,'physical_acceptance':False}
(O/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(report['status'])
