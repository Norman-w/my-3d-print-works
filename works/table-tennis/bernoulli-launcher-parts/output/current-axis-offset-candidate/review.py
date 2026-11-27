#!/usr/bin/env python3
"""Isolated outward-offset shoulder revision; no adopted CAD writes."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib, importlib.util, json, re, subprocess, sys

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
BIN='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
SNAP=ROOT/'output/cable-scene-export/20260927T091627124663Z'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.path.insert(0,str(ROOT/'analysis'))
from exact_mesh import exact_area_and_links
from feeder_integration import classify
sp=importlib.util.spec_from_file_location('mesh_stats',ROOT/'output/current-axis-through-candidate/review.py')
helper=importlib.util.module_from_spec(sp);sp.loader.exec_module(helper)
ip=Path('/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
sp=importlib.util.spec_from_file_location('mesh_inspect',ip)
inspector=importlib.util.module_from_spec(sp);sp.loader.exec_module(inspector)

def dependencies():
 pending=[OUT/'candidate.scad'];found={Path(__file__).resolve(),ROOT/'analysis/exact_mesh.py',ROOT/'analysis/feeder_integration.py',ROOT/'output/current-axis-through-candidate/review.py'}
 while pending:
  p=pending.pop().resolve()
  if p in found:continue
  found.add(p)
  pending.extend(p.parent/d for d in re.findall(r'\b(?:use|include)\s*<([^>]+)>',p.read_text()))
 return {str(p.relative_to(ROOT)):sha(p) for p in sorted(found)}

def main():
 run=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
 src=dependencies()
 def case(job):
  part,u=job;n=f'{part}-{u}';path=run/(n+'.stl');log=run/(n+'.log')
  # The adopted body also requires CGAL: Manifold exports coplanar slivers.
  backend='CGAL' if part=='body' else 'Manifold'
  cmd=[BIN,'--hardwarnings','--backend',backend,'--export-format','asciistl','-D','ci_origin=[75,-85,5]','-D',f'part="{part}"','-D',f'input_u={u}','-o',str(path),str(OUT/'candidate.scad')]
  p=subprocess.run(cmd,capture_output=True,text=True);s=p.stdout+p.stderr;log.write_text(s)
  assert 'WARNING:' not in s and 'ERROR:' not in s,s
  empty='Current top level object is empty.' in s
  r={'case':n,'command':cmd,'returncode':p.returncode,'native_empty':empty,'log_sha256':sha(log),'mesh':None if empty else helper.inspect(path),'stl_sha256':None if empty else sha(path)}
  if not empty and part in ['body-metal-probe','mount-missing-probe']:
   v=[tuple(map(float,m)) for m in re.findall(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)',path.read_text())]
   # Exact intended interfaces, not a volume-only tolerance: every triangle
   # must lie on one declared bearing/mount boundary plane.
   planes=[(0,-29),(0,-37),(0,-45),(2,-9)] if part=='body-metal-probe' else [(0,28.2),(0,19.6)]
   r['expected_contact_planes_axis_value_mm']=planes
   r['each_triangle_on_declared_plane']=all(any(all(abs(t[ax]-z)<1e-7 for t in v[i:i+3]) for ax,z in planes) for i in range(0,len(v),3))
  if part in ['body','cover']:
   assert p.returncode==0
   r['topology']=exact_area_and_links(path);r['mesh_inspector']=inspector.inspect(path,1e-6);r['components']=len(classify(path)['components'])
   r['one_closed_solid']=bool(r['components']==1 and not r['topology']['exact_zero_area_face_indices'] and not r['topology']['non_ring_vertex_links'] and r['mesh_inspector']['watertightByEdgeTopology'])
  print(n, 'empty' if empty else r['mesh']['signed_volume_mm3'],flush=True)
  return r
 jobs=[(p,0) for p in ['body','cover','plastic-probe','metal-probe','body-metal-probe','mount-missing-probe','short-positive','unrelieved-root-positive']]+[(p,u) for p in ['rotor-probe','rotor-plastic-probe'] for u in [0,10,20]]
 with ThreadPoolExecutor(max_workers=2) as pool:cases=list(pool.map(case,jobs))
 by={c['case']:c for c in cases}
 def contact_or_empty(r):
  return r['native_empty'] or abs(r['mesh']['signed_volume_mm3'])<1e-7 and r['mesh']['each_triangle_on_one_contact_plane']
 checks={
  'body_one_solid':by['body-0']['one_closed_solid'],
  'cover_one_solid':by['cover-0']['one_closed_solid'],
  'axis_only_capture_plane_contact':contact_or_empty(by['plastic-probe-0']),
  'axis_other_metal_clear':by['metal-probe-0']['native_empty'],
  'body_other_metal_only_contact_planes':by['body-metal-probe-0']['native_empty'] or (abs(by['body-metal-probe-0']['mesh']['signed_volume_mm3'])<1e-7 and by['body-metal-probe-0']['each_triangle_on_declared_plane']),
  'original_host_mount_difference_only_boundary_planes':by['mount-missing-probe-0']['native_empty'] or (abs(by['mount-missing-probe-0']['mesh']['signed_volume_mm3'])<1e-7 and by['mount-missing-probe-0']['each_triangle_on_declared_plane']),
  'axis_rotor_three_poses_clear':all(by[f'rotor-probe-{u}']['native_empty'] for u in [0,10,20]),
  'rotor_plastic_three_poses_clear':all(by[f'rotor-plastic-probe-{u}']['native_empty'] for u in [0,10,20]),
  'short_axis_positive':not by['short-positive-0']['native_empty'] and by['short-positive-0']['mesh']['signed_volume_mm3']>.001,
  'missing_root_relief_positive':not by['unrelieved-root-positive-0']['native_empty'] and by['unrelieved-root-positive-0']['mesh']['signed_volume_mm3']>.001,
 }
 assert src==dependencies()
 r={'status':'OFFSET_SHOULDER_LOCAL_LIMITED_PASS' if all(checks.values()) else 'FAIL_OR_REVIEW_REQUIRED','source_sha256':src,'sources_stable':True,'external_inspector':{'path':str(ip),'sha256':sha(ip)},'checks':checks,'cases':cases,
  'design':{'origin':[75,-85,5],'shoulder_L_mm':[26.95,27.05],'centering_cup_pocket_depth_mm':[.50,.55],'metal_capture_span_mm':[26.40,26.55],'nominal_housing_span_mm':26,'coaxial_float_mm':[.40,.55],'head_root_max_d_length_mm':[8.7,2.5],'cover_root_relief_d_from_z_mm':[9.2,11.3],'cover_full_shaft_guide_length_mm':3.3,'nominal_host_head_separation_mm':1.25,'thread_projection_mm':[2.95,4.4]},
  'scope':'Local nominal plastic geometry with conservative coaxial axis/root envelope over all accepted axial float. Three rotor poses only. Original fixed host mount retained. Not a full host/route/body sweep or complete tolerance proof.',
  'unverified':['Supplier acceptance of terminal shoulder/root contract and head/F acceptance windows','Metal cup flat seating and actual concentricity','Printed tolerances, axis tilt, deflection, side screw load, creep and friction','Continuous whole-system motion, return with air and balls, real assembly'],
  'adopted':False,'manufacturing_release':False,'physical_acceptance':False}
 (run/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 (OUT/'latest.json').write_text(json.dumps({'directory':str(run.relative_to(ROOT)),'report_sha256':sha(run/'report.json')},indent=2)+'\n')
 print(json.dumps({'status':r['status'],'directory':str(run.relative_to(ROOT)),'checks':checks},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
