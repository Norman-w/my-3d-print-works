#!/usr/bin/env python3
"""Bounded metal-fastener revision, including continuous feeder broad phase."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib, importlib.util, json, math, re, subprocess

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
SNAP=ROOT/'output/cable-scene-export/20260927T091627124663Z'
SCAD=OUT/'candidate.scad'
BIN='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sp=importlib.util.spec_from_file_location('parent_review',OUT.parent/'review.py')
parent=importlib.util.module_from_spec(sp);sp.loader.exec_module(parent)

def main():
 run=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
 run.mkdir(parents=True)
 snapshot=json.loads((SNAP/'report.json').read_text())
 sources=dict(snapshot['source_sha256'])
 for p in [SCAD,Path(__file__).resolve(),OUT.parent/'candidate.scad',OUT.parent/'review.py',SNAP/'report.json']:
  sources[str(p.relative_to(ROOT))]=sha(p)
 assert all(sha(ROOT/n)==h for n,h in sources.items())
 broad=[]; narrow=[]
 # Conservative CAD-axis AABB: maximum round radial extent 6 around
 # [75,-82,5], with local Z mapped onto CAD Y. It covers round washers
 # as well as the rotating nut corner envelope.
 alo=[69,-108.1,-1];ahi=[81,-61.88,11]
 for it in snapshot['parts']:
  if it['group']!='feeder' or 'cable-input' in it['id'] or it['id']=='feeder/cable-core-input':continue
  p=ROOT/it['file'];assert sha(p)==it['sha256'];sources[it['file']]=it['sha256']
  # Re-read actual vertices; do not rely on saved bounding-box numbers alone.
  v=[tuple(map(float,m)) for m in re.findall(r'vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)',p.read_text())]
  assert v
  mn=[min(a[i] for a in v) for i in range(3)];mx=[max(a[i] for a in v) for i in range(3)]
  m=it['motion'];k=m['kind']
  if k=='fixed':basis='fixed geometry'
  elif k=='radial':
   assert m['closed_mm']==21 and m['open_mm']==26 and m['axis']==[1,0,0]
   mn[0]-=5;mx[0]+=5;basis='all radial displacements enclosed by +/-5 in X'
  elif k=='translate':
   assert m['axis']==[0,0,1] and m['distance_mm']==20
   mn[2]-=20;mx[2]+=20;basis='full 20 mm Z stroke (symmetric outer bound)'
  elif k in ['spring','output-wire']:
   # Only X is used for these sources: source equations keep X constant.
   basis='source-defined constant-X slab; do not assert Z envelope'
  else:raise AssertionError((it['id'],m))
  gaps=[max(alo[i]-mx[i],mn[i]-ahi[i]) for i in range(3)]
  axis=0 if k in ['spring','output-wire'] else max(range(3),key=lambda i:gaps[i])
  separated=gaps[axis]>0
  if not separated:
   assert k=='fixed';narrow.append(it['id'])
  broad.append({'id':it['id'],'motion_basis':basis,'bounds_mm':[mn,mx],
    'separation_axis':'XYZ'[axis],'separation_mm':gaps[axis],'aabb_separated':separated})
 assert sorted(narrow)==sorted(['feeder/beam-grip','feeder/cable-housing','feeder/cable-core-route'])
 def one(name):
  stl=run/(name+'.stl');log=run/(name+'.log')
  cmd=[BIN,'--export-format=asciistl','-D','part="'+name+'"','-o',str(stl),str(SCAD)]
  p=subprocess.run(cmd,capture_output=True,text=True);log.write_text(p.stdout+p.stderr)
  assert 'ERROR:' not in log.read_text() and 'WARNING:' not in log.read_text(),str(log)
  empty='Current top level object is empty.' in log.read_text()
  return {'case':name,'command':cmd,'returncode':p.returncode,'native_empty':empty,
   'mesh':None if empty else parent.inspect(stl),'log_sha256':sha(log),'stl_sha256':None if empty else sha(stl)}
 with ThreadPoolExecutor(max_workers=2) as pool:
  cases=list(pool.map(one,['plastic-probe','metal-probe','rotor-probe','external-probe','external-nominal-witness','short-positive']))
 by={r['case']:r for r in cases}
 for name in ['metal-probe','rotor-probe']:assert by[name]['native_empty'],by[name]
 external_ok=by['external-probe']['native_empty']
 r=by['plastic-probe']
 assert r['native_empty'] or (abs(r['mesh']['signed_volume_mm3'])<1e-7 and r['mesh']['each_triangle_on_one_contact_plane'])
 assert by['short-positive']['mesh']['signed_volume_mm3']>.001
 assert all(sha(ROOT/n)==h for n,h in sources.items())
 # Axial float cancels in protrusion; independent washer thicknesses used.
 projection=[39-27.02-2*1.1-5,41-26.98-2*.9-4.7]
 full_projection=projection[0]-1.4
 assert full_projection>=2*.7
 # Nut entry (metal face) is nearer the head than the distal nylon end.
 nut_entry=[26.98+2*.9,27.02+2*1.1]
 guaranteed_thread_start=41-20
 assert guaranteed_thread_start<nut_entry[0]
 report={'status':'ISOLATED_LOCKING_AXLE_LIMITED_CHECKS_PASSED' if external_ok else 'REJECTED_EXTERNAL_COLLISION',
  'external_clearance_passed':external_ok,'source_sha256':sources,
  'reachable_collision_witness':by['external-nominal-witness'],
  'sources_stable':True,'cases':cases,'axis_cad_aabb_mm':[alo,ahi],
  'feeder_noninput_broad_phase':broad,'fixed_native_candidates':narrow,
  'supplier_dimensions':{
   'nut':{'code':'HNN-M4-A2','url':'https://www.accu.co.uk/hexagon-nylon-locking-nuts/7946-HNN-M4-A2',
    'standard':'DIN985','height_mm':[4.7,5],'across_flats_mm':[6.78,7],'pitch_mm':.7},
   'bolt_reference':{'code':'SSC-M4-40-A2-BL','url':'https://www.accu.co.uk/api/product-datasheet?id=151797',
    'length_nominal_mm':40,'head_d_mm':[6.78,7],'head_h_mm':[3.82,4],'minimum_thread_length_mm':20,'socket_mm':3}},
  'design_acceptance_requirements_not_supplier_tolerances':{
   'bolt_underhead_length_mm':[39,41],'distal_incomplete_thread_length_max_mm':1.4,
   'full_thread_projection_min_pitches':2,
   'note':'These are generous design acceptance limits. Supplier length and end geometry have not been certified against them.'},
  'computed':{'physical_tip_projection_mm':projection,'full_thread_projection_min_mm':full_projection,
   'nut_metal_entry_distance_from_head_mm':nut_entry,'latest_guaranteed_thread_start_mm':guaranteed_thread_start,
   'old_35mm_bolt_min_nominal_projection_with_locknut_mm':35-27.02-2*1.1-5},
  'scope':'Continuous coaxial axle envelope and continuous trigger stroke for nominal registered feeder. Other rotating input geometry uses rotationally invariant central bore/Z separation plus remote cap radius; the native rotor case is at rest. Excludes spin head pose, actual tolerances/tilt/loads and unmodelled blower/human geometry.',
  'not_checked':['Socket/wrench approach and hand clearance','Applied torque, prevailing torque and reuse limits','Actual bearing surface/axis selection','Actual bush/thrust capture','PETG support deflection/creep','Whole candidate manufacturing adoption'],
  'adopted':False,'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
 (run/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (OUT/'latest.json').write_text(json.dumps({'directory':str(run.relative_to(ROOT)),'report_sha256':sha(run/'report.json')},indent=2)+'\n')
 print(json.dumps({'run':str(run.relative_to(ROOT)),'status':report['status'],'native_cases':[{k:r[k] for k in ['case','native_empty','mesh']} for r in cases],'broad_phase_count':len(broad),'projection_mm':projection},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
