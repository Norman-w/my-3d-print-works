#!/usr/bin/env python3
"""Bounded metal-fastener revision, including continuous feeder broad phase."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib, importlib.util, json, math, re, subprocess

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
SNAP=ROOT/'output/cable-scene-export/20260927T091627124663Z'
SCAD=OUT/'candidate.scad'
BIN='/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sp=importlib.util.spec_from_file_location('parent_review',ROOT/'output/current-axis-through-candidate/review.py')
parent=importlib.util.module_from_spec(sp);sp.loader.exec_module(parent)

def on_capture_planes(path):
 v=[tuple(map(float,m)) for m in re.findall(r'vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)',path.read_text())]
 return bool(v) and all(any(all(abs(p[2]-z)<1e-7 for p in v[i:i+3]) for z in [-12,11.5]) for i in range(0,len(v),3))

def main():
 run=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
 run.mkdir(parents=True)
 snapshot=json.loads((SNAP/'report.json').read_text())
 sources=dict(snapshot['source_sha256'])
 for p in [SCAD,Path(__file__).resolve(),ROOT/'output/current-axis-through-candidate/candidate.scad',ROOT/'output/current-axis-through-candidate/review.py',SNAP/'report.json']:
  sources[str(p.relative_to(ROOT))]=sha(p)
 assert all(sha(ROOT/n)==h for n,h in sources.items())
 broad=[]; narrow=[]
 # Conservative CAD-axis AABB: circumscribed radius <=6.607 around
 # [75,-82,5], with local Z mapped onto CAD Y. It covers round washers
 # as well as the rotating nut corner envelope.
 alo=[68.393,-107.55,-1.607];ahi=[81.607,-63.25,11.607]
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
 assert sorted(narrow)==sorted(['feeder/cable-housing','feeder/cable-core-route'])
 def one(name):
  stl=run/(name+'.stl');log=run/(name+'.log')
  cmd=[BIN,'--export-format=asciistl','-D','part="'+name+'"','-o',str(stl),str(SCAD)]
  p=subprocess.run(cmd,capture_output=True,text=True);log.write_text(p.stdout+p.stderr)
  assert 'ERROR:' not in log.read_text() and 'WARNING:' not in log.read_text(),str(log)
  empty='Current top level object is empty.' in log.read_text()
  mesh=None if empty else parent.inspect(stl)
  if mesh:
   mesh.pop('all_vertices_on_external_contact_planes',None)
   mesh.pop('each_triangle_on_one_contact_plane',None)
   mesh['each_triangle_on_one_capture_plane']=on_capture_planes(stl)
   mesh['capture_planes_local_z_mm']=[-12,11.5]
  return {'case':name,'command':cmd,'returncode':p.returncode,'native_empty':empty,
   'mesh':mesh,'log_sha256':sha(log),'stl_sha256':None if empty else sha(stl)}
 with ThreadPoolExecutor(max_workers=2) as pool:
  cases=list(pool.map(one,['plastic-probe','metal-probe','rotor-probe','external-probe','short-positive']))
 by={r['case']:r for r in cases}
 for name in ['metal-probe','rotor-probe']:assert by[name]['native_empty'],by[name]
 external_ok=by['external-probe']['native_empty']
 r=by['plastic-probe']
 assert r['native_empty'] or (abs(r['mesh']['signed_volume_mm3'])<1e-7 and on_capture_planes(run/'plastic-probe.stl'))
 assert by['short-positive']['mesh']['signed_volume_mm3']>.001
 assert all(sha(ROOT/n)==h for n,h in sources.items())
 # Shoulder screw F excludes shoulder L. Float cancels in tail projection.
 projection=[11.5-1.8-6,12.5-1.4-5.7]
 report={'status':'RECESSED_SHOULDER_CANDIDATE_LIMITED_CHECKS_PASSED' if external_ok else 'REJECTED_EXTERNAL_COLLISION',
  'source_sha256':sources,'sources_stable':True,'cases':cases,
  'axis_cad_aabb_mm':[alo,ahi],'feeder_noninput_broad_phase':broad,'fixed_native_candidates':narrow,
  'catalog_configuration':'GDSMSB8-24.5-F12-M6 (directory derived, not configured/ordered)',
  'catalog_dimensions':{'shaft_d_mm':[7.986,7.995],'shoulder_L_mm':[24.45,24.55],
   'head_D_nominal_mm':13,'head_H_nominal_mm':6,'F_nominal_mm':12},
  'hardware_references':[
   {'code':'HNN-M6-A2','url':'https://www.accu.co.uk/hexagon-nylon-locking-nuts/7948-HNN-M6-A2','height_mm':[5.7,6],'AF_mm':[9.78,10],'pitch_mm':1},
   {'code':'HPW-M6-A2','url':'https://www.accu.co.uk/metric-flat-washers/72494-HPW-M6-A2','status':'geometry reference only; current purchasability not verified','OD_mm':[11.6,12],'ID_mm':[6.4,6.62],'thickness_mm':[1.4,1.8]}],
  'design_acceptance_windows_not_published_supplier_tolerances':{'head_D_mm':[12.8,13.2],'head_H_mm':[5.8,6.2],'F_mm':[11.5,12.5]},
  'plastic_nominal':{'through_bore_mm':8.3,'cover_recess_d_mm':13.8,'recess_floor_z_mm':11.5,'remaining_cover_wall_mm':3.5,'capture_span_mm':23.5},
  'calculated':{'capture_float_mm':[.95,1.05],'head_max_z_mm':18.75,'fixed_host_min_z_in_local_mm':19,'host_axial_separation_mm':.25,'nut_tip_projection_mm':projection},
  'assumptions':['Coaxial assembly in nominal body and cover',
   'Head dimensions and F fall within the explicit design acceptance windows',
   'M6 washer actually seats on the shoulder, clearing supplier-unbounded thread-root/relief geometry',
   'Washer stays flat under specified-but-not-yet-defined tightening load'],
  'not_checked':['Head/shoulder/root details not fully dimensioned by supplier',
   'Actual locking torque, nylon engagement and thread runout',
   'Axis tilt and radial registration, PETG creep and cover flexure',
   'Actual replaceable bush and thrust stack; this probe still uses old nominal rotor geometry',
   'Tool approach and access after mounting',
   'Spin head adjustments, real blower, user hand, manufacturing adoption'],
  'scope':'Continuous coaxial shoulder-axis envelope and continuous nominal feeder stroke. External round envelopes are circumscribed 72-gons; internal cuts are inscribed for conservative material coverage. Native rotor at rest plus rotationally invariant central bore/Z separation. This is a geometric candidate, not release.',
  'adopted':False,'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
 (run/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (OUT/'latest.json').write_text(json.dumps({'directory':str(run.relative_to(ROOT)),'report_sha256':sha(run/'report.json')},indent=2)+'\n')
 print(json.dumps({'run':str(run.relative_to(ROOT)),'status':report['status'],'native_cases':[{k:r[k] for k in ['case','native_empty','mesh']} for r in cases],'broad_phase_count':len(broad),'projection_mm':projection},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
