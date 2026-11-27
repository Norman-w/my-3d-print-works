#!/usr/bin/env python3
"""Bounded native continuous service-envelope checks; no production writes."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, re, subprocess, importlib.util
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SNAP=ROOT/'output/cable-scene-export/20260927T091627124663Z/report.json'
sp=importlib.util.spec_from_file_location('axis_helper',ROOT/'output/current-axis-through-candidate/review.py')
helper=importlib.util.module_from_spec(sp);sp.loader.exec_module(helper)
def main():
 run=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
 snapshot=json.loads(SNAP.read_text());sources=dict(snapshot['source_sha256'])
 more=[Path(__file__),OUT/'probes.scad',SNAP,
  ROOT/'output/current-axis-shoulder-candidate/candidate.scad',
  ROOT/'output/current-axis-through-candidate/candidate.scad',
  ROOT/'output/current-axis-through-candidate/review.py',
  ROOT/'output/current-axis-retention-review/candidate.scad',
  ROOT/'output/current-axis-precision-selection/report.json',
  ROOT/'output/cable-scene-export/20260927T091627124663Z/feeder__beam-grip.stl']
 for p in more:sources[str(p.relative_to(ROOT))]=sha(p)
 assert all(sha(ROOT/n)==h for n,h in sources.items())
 def one(name):
  p=run/(name+'.stl');log=run/(name+'.log')
  cmd=['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--hardwarnings','--backend','Manifold',
   '--export-format','asciistl','-D','at_case='+json.dumps(name),'-o',str(p),str(OUT/'probes.scad')]
  s=subprocess.run(cmd,capture_output=True,text=True);txt=s.stdout+s.stderr;log.write_text(txt)
  empty='Current top level object is empty.' in txt and not p.exists()
  assert not re.search(r'(?m)(ERROR|WARNING):',txt),txt
  assert s.returncode==0 or(s.returncode==1 and empty)
  mesh=None if empty else helper.inspect(p)
  if mesh:
   for k in ['all_vertices_on_external_contact_planes','each_triangle_on_one_contact_plane']:mesh.pop(k,None)
   v=[tuple(map(float,m)) for m in re.findall(r'vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)',p.read_text())]
   mesh['each_triangle_on_recess_floor_11_5']=all(all(abs(t[2]-11.5)<1e-7 for t in v[i:i+3]) for i in range(0,len(v),3))
  print(name,'empty',empty,flush=True)
  return {'case':name,'command':cmd,'returncode':s.returncode,'native_empty':empty,'mesh':mesh,
   'log_sha256':sha(log),'artifact':str(p.relative_to(ROOT)) if p.exists() else None,
   'artifact_sha256':sha(p) if p.exists() else None}
 names=['head-bench','nut-bench','tools-mutual','head-drive-fit','nut-drive-fit','shaft-insertion','installed-head-positive']
 with ThreadPoolExecutor(max_workers=2)as pool:cases=list(pool.map(one,names))
 by={c['case']:c for c in cases}
 verdict={n:by[n]['native_empty'] for n in names[:5]}
 si=by['shaft-insertion'];verdict['shaft-insertion']=si['native_empty'] or(abs(si['mesh']['signed_volume_mm3'])<1e-7 and si['mesh']['each_triangle_on_recess_floor_11_5'])
 po=by['installed-head-positive'];verdict['installed-head-positive']=not po['native_empty'] and po['mesh']['signed_volume_mm3']>.01
 assert all(sha(ROOT/n)==h for n,h in sources.items())
 report={'status':'LIMITED_BENCH_SERVICE_GEOMETRY_PASS' if all(verdict.values()) else 'REVIEW_REQUIRED',
  'source_sha256':sources,'sources_stable':True,'cases':cases,'criteria':verdict,
  'mechanical_contract':{'units':'mm','basis':'input-local +Z = feeder CAD +Y; -Z = CAD -Y',
   'pose':'lever u=0, adjuster delta=0, unloaded bench module, mounting bolts absent',
   'neighbor_union':['shoulder_plastics()','ar_rotor(0)','other_fixed_metal()','ci_local_cable(0,0)'],
   'intentional_omissions':['target shoulder/washer/nut group checked separately at nominal drive engagement','four M4x60 not installed on bench','disconnected flexible housing/free wire parked outside'],
   'head_tool':{'supply':'unselected maximum allowed geometric budget','drive':'SW5 nominal source socket, test key AF4.98',
     'engagement_mm':2.5,'shank_circumscribed_OD_max_mm':5.8,'long_leg_to_elbow_mm':60,'short_arm_mm_max':25,
     'bend_half_envelope_mm_max':4,'axial_entry_distance_mm':40,'rotation_deg':360,'tip_z_range_mm':[14.8,16.25]},
   'nut_tool':{'supply':'unselected deep-socket/extension maximum allowed geometric budget','drive':'SW10, model socket AF10.2',
     'socket_OD_max_mm':14,'socket_length_mm':40,'clear_cavity_depth_mm':20,'minimum_clear_hex_AF_mm':10.2,
     'through_extension_bore_min_mm':8,'mouth_recess_from_nut_washer_face_mm':.5,
     'minimum_hex_metal_engagement_from_HNN_M6_min_4_mm':3.5,
     'axial_entry_distance_mm':40,'rotation_deg':360,'handle_radius_mm_max':70,'handle_thickness_mm_max':12,
     'handle_center_distance_behind_mouth_mm':55,'mouth_z_range_mm':[-15.35,-13.9]},
   'shaft_insertion':{'direction':[0,0,-1],'approach_from':'+Z','continuous_translation_mm':40,
      'conditions':'coaxially align rotor/bush/thrust stack and cheeks; washer/nut added later from -Z'},
   'formulae':{'head_hi':'11.5..12.55','head_top':'hi+[5.8,6.2] = 17.3..18.75',
     'key_tip':'head_top - 2.5 = 14.8..16.25','nut_front':'lo - washer_t = -14.85..-13.4',
     'socket_mouth':'nut_front - .5 = -15.35..-13.9',
     'socket_tip_clearance_min_mm':20-(6+5.4-.5),
     'tool_to_tool_axial_gap_lower_mm':14.8-(-13.9)}},
  'limits':['No real wrench/socket selected; socket depth/hex tolerance of purchased shoulder not supplied',
    'No torque, hand grip, nylon lock reuse or underhead/thread-root seating proof',
    'Bench rigid probes include rest-pose wire only; free flexible cable deliberately disconnected/parked',
    'Installed positive control is one actual beam-grip obstacle, sufficient to reject the tested frontal access, not all imaginable offset tools',
    'Does not authorize opening cover/shaft service without removing all four shared host bolts and separately supporting both assemblies',
    'Nominal concentric print geometry; not manufacturing fit/tilt/deformation acceptance'],
  'production_CAD_modified':False,'adopted':False,'manufacturing_release':False,'physical_acceptance':False,'sent_to_printer':False}
 (run/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (OUT/'latest.json').write_text(json.dumps({'directory':str(run.relative_to(ROOT)),'report_sha256':sha(run/'report.json')},indent=2)+'\n')
 print(json.dumps({'run':str(run.relative_to(ROOT)),'status':report['status'],'criteria':verdict},indent=2))
if __name__=='__main__':main()
