from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, re
ROOT=Path(__file__).resolve().parents[3]
RUN=Path('output/cable-eclip-adoption/20260927T151752917841Z')
REPORT=RUN/'report.json'
LATEST=Path('output/cable-eclip-adoption/latest.json')
reports={
 'cad':RUN/'cad-review/report.json',
 'system':Path('output/cable-trigger-system/20260927T152544768903Z/report.json'),
 'route':Path('output/cable-housing-route/20260927T152611143454Z/report.json'),
 'actuation':Path('output/cable-actuation-v2/20260927T152544767413Z/report.json'),
 'export':Path('output/cable-scene-export/20260927T153058669616Z/report.json'),
 'render':Path('output/cable-direct-adoption/render/20260927T152544756846Z/report.json'),
 'browser':Path('output/cable-scene-export/20260927T153058669616Z/browser-review.json'),
 'hardware':Path('output/current-assembly-package/cable-hardware-current/runs/20260927T153831015826Z/hardware.json'),
 'manufacturing':RUN/'manufacturing/binding-02/report.json',
 'package':Path('output/current-assembly-package/runs/20260927T154004364940Z/manifest.json')}
def path(p):
 p=Path(p);return p if p.is_absolute() else ROOT/p
def sha(p):return hashlib.sha256(path(p).read_bytes()).hexdigest()
bindings={};checks=[]
for name,p in reports.items():
 d=json.loads(path(p).read_text());n=0
 for field in ['source_sha256','source_and_artifact_sha256','evidence_sha256']:
  for f,h in d.get(field,{}).items():
   fp=path(f)
   assert fp.is_file() and sha(fp)==h,(name,field,f,'stale')
   key=str(fp.relative_to(ROOT)) if fp.is_relative_to(ROOT) else str(fp)
   assert key not in bindings or bindings[key]==h,(name,key,'conflict')
   bindings[key]=h;n+=1
 bindings[str(p)]=sha(p)
 checks.append({'name':name,'report':str(p),'sha256':sha(p),'status':d['status'],'bindings_verified':n})
docs=[Path('output/cable-eclip-adoption/README.md')]+[Path('docs')/n for n in ['current-status.md','current-mechanical-review.md','cable-trigger-input.md','cable-trigger-integration.md','current-assembly.md','current-manufacturing.md','goal-acceptance-audit.md','cable-assembly-inventory.md','cable-service-contract.md','current-lubrication.md']]
links=[]
for p in docs:
 for link in re.findall(r'\]\(([^)]+)\)',path(p).read_text()):
  if '://' in link or link.startswith('#'):continue
  target=(path(p).parent/link.split('#')[0]).resolve();links.append(target)
  assert target.exists() or target in [path(REPORT),path(LATEST)],(p,link)
 bindings[str(p)]=sha(p)
for p in [Path(__file__),Path('scripts/build_current_manufacturing_manifest.py'),Path('scripts/build_current_assembly_package.py'),Path('web/scene-display.mjs')]:
 fp=path(p);key=str(fp.relative_to(ROOT));bindings[key]=sha(fp)
d={'status':'FORMAL_ECLIP_AXIS_AND_UNIFIED_SCENE_ADOPTED_3_PRINTS_PENDING','created_utc':datetime.now(timezone.utc).isoformat(),'snapshot_id':'20260927T153058669616Z','checks':checks,'source_and_artifact_sha256':bindings,'source_and_artifacts_stable':True,'verified_bindings':len(bindings),'checked_local_doc_links':len(links),'counts':{'scene_items':86,'printed_instances':56,'printed_bound':53,'printed_needs_reslice':3,'selected_plates':39,'bom_specification_rows':45},'previous_failed_export':'output/cable-scene-export/20260927T152609986811Z/report.json','geometry_failure_resolution':'Display-only assembly composition exports pin CGAL and other fixed hardware Manifold separately; no native warning suppression and no printable/fused hardware claim.','open_physical_items':['actual E-ring seating/tool/retention load','machined POM and printed fits','housing seating, wire clamp force and minimum tail','lost motion and input/output stop interval','friction and loaded return','dynamic single-ball feed, airflow and spin'],'adopted':True,'manufacturing_release':False,'physical_acceptance':False,'purchased':False,'sent_to_printer':False,'goal_complete':False}
path(REPORT).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
path(LATEST).write_text(json.dumps({'report':str(REPORT),'sha256':sha(REPORT),'status':d['status'],'snapshot_id':d['snapshot_id'],'adopted':True,'manufacturing_release':False,'physical_acceptance':False},ensure_ascii=False,indent=2)+'\n')
assert all(p.exists() for p in links)
print(json.dumps({'status':d['status'],'verified_bindings':len(bindings),'doc_links':len(links),'report':str(REPORT)},ensure_ascii=False))
