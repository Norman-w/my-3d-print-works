#!/usr/bin/env python3
"""CW-01 machining contract, algebra and bounded native geometry only."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import json,hashlib,math,subprocess,re,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SUP=ROOT/'output/current-axis-root-interface/supplier/report.json'
sys.path.insert(0,'/Users/norman/.codex/skills/openscad-stl-print/scripts')
from inspect_stl import inspect
def main():
 run=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
 srcs=[OUT/'candidate.scad',Path(__file__),SUP,ROOT/'output/current-axis-precision-selection/report.json']
 identity={str(p.relative_to(ROOT)):sha(p)for p in srcs}
 sup=json.loads(SUP.read_text())['proposed_tail_procurement_acceptance_contract']
 assert not sup['supplier_confirmed']
 assert sup['shaft']['guaranteed_flat_shoulder_material_annulus_diameter_mm']==[7.,7.8]
 assert sup['shaft']['full_M6x1_external_thread_interval_at_least_s_mm']==[1.2,11.]
 efit=(8.04-7.986)/2;eaxis=.02/2;tilt=math.radians(.2);zmax=3.05-.50+.05
 etilt=zmax*math.tan(tilt);etotal=efit+eaxis+etilt
 d={'pilot_diametral_clearance_mm':[8.02-7.995,8.04-7.986],
  'pilot_radial_clearance_max_mm':efit,'feature_position_radial_budget_mm':eaxis,
  'seated_tilt_deg_max':.2,'furthest_feature_from_first_full_pilot_section_mm':zmax,
  'first_full_g6_section_shoulderward_of_seating_plane_mm':.05,
  'tilt_radial_budget_mm':etilt,'total_radial_error_bound_mm':etotal,
  'remaining_to_0_05_radial_limit_mm':.05-etotal,
  'root_radial_clearance_after_tilt_at_e_0_05_mm':(6.8-6.6/math.cos(tilt))/2-.05,
  'thread_radial_clearance_after_tilt_at_e_0_05_mm':(6.4-6/math.cos(tilt))/2-.05,
  'root_axial_clearance_after_face_and_tilt_mm':.60-.50-.02-3.3*math.sin(tilt),
  'root_native_axial_growth_mm':.032,
  'minimum_bulk_web_below_relief_mm':2.95-.55-.65,
  'minimum_pilot_outer_wall_mm':(11.95-8.04)/2,
  'shoulder_to_nut_face_mm':[2.95-.55,3.05-.50],
  'guaranteed_shoulder_ring_diameters_mm':[7.,7.8],
  'shoulder_annulus_area_mm2':math.pi/4*(7.8**2-7**2),
  'guaranteed_projected_shoulder_area_mm2':math.pi/4*(7.8**2-7**2)*math.cos(tilt),
  'relief_aperture_radial_clearance_to_ring_after_tilt_mm':3.5-(6.88/2+.05)/math.cos(tilt),
  'pilot_floor_corner_radial_clearance_to_ring_mm':8.02/2-.05-.05-(7.8/2)/math.cos(tilt),
  'minimum_useful_pilot_length_after_entry_and_end_break_mm':.50-.05-.05,
  'new_L27_effective_capture_span_mm':[26.95-.55,27.05-.50],
  'new_L27_float_if_nominal_external_span_26_mm':[26.95-.55-26,27.05-.50-26],
  'obsolete_L24_5_span_if_used_mm':[24.45-.55,24.55-.50],
  'nut_occupied_s_union_mm':[2.95-.55,3.05-.50+6],
  'full_thread_start_margin_mm':2.95-.55-1.2,
  'full_thread_beyond_nut_margin_mm':11-(3.05-.50+6),
  'physical_tip_projection_mm':[11.5-(3.05-.50)-6,12.5-(2.95-.55)-5.7],
  'new_L27_washer_nut_local_bounds_if_body_minus12_cover14':{
    'washer_mouth_z_mm':[-12.55,-12],
    'washer_back_nut_front_z_mm':[14-27.05-3.05+.50,-12-2.95],
    'nut_full_union_z_mm':[14-27.05-3.05+.50-6,-12-2.95]},
  'axial_preload_stress_expression':'sigma = F / 9.2991142546 mm^2; no allowable F assigned'}
 assert etotal<.05 and d['root_axial_clearance_after_face_and_tilt_mm']>0
 assert d['pilot_floor_corner_radial_clearance_to_ring_mm']>0
 assert d['full_thread_start_margin_mm']>0 and d['full_thread_beyond_nut_margin_mm']>0
 def one(name):
  p=run/(name+'.stl');log=run/(name+'.log')
  cmd=['/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD','--hardwarnings','--backend','Manifold','--export-format','asciistl','-D','cw_part='+json.dumps(name),'-o',str(p),str(OUT/'candidate.scad')]
  q=subprocess.run(cmd,capture_output=True,text=True);s=q.stdout+q.stderr;log.write_text(s)
  empty='Current top level object is empty.'in s and not p.exists()
  assert not re.search(r'(?m)(ERROR|WARNING):',s)
  assert q.returncode==0 or(q.returncode==1 and empty)
  return {'case':name,'command':cmd,'returncode':q.returncode,'native_empty':empty,
   'artifact':str(p.relative_to(ROOT))if p.exists()else None,'artifact_sha256':sha(p)if p.exists()else None,
   'mesh':inspect(p,1e-7)if p.exists()else None,'log_sha256':sha(log)}
 with ThreadPoolExecutor(max_workers=2)as pool:cases=list(pool.map(one,['washer','root-clearance','eccentric-positive']))
 assert cases[0]['mesh']['watertightByEdgeTopology']
 assert cases[1]['native_empty'] and not cases[2]['native_empty']
 assert all(sha(ROOT/p)==h for p,h in identity.items())
 r={'status':'ISOLATED_CONDITIONAL_CENTERING_WASHER_CANDIDATE','source_sha256':identity,'sources_stable':True,
  'supplied_root_conditions_are_design_acceptance_not_supplier_guarantee':True,
  'native_cases':cases,'calculated':d,
  'machining_requirements':{'material':'machined SUS304, grade/strength/torque unqualified',
    'OD_mm':[11.95,12.00],'overall_T_mm':[2.95,3.05],'pilot_ID_mm':[8.02,8.04],'pilot_depth_p_mm':[.50,.55],
    'relief_finished_aperture_ID_mm':[6.80,6.88],'relief_depth_from_seat_mm':[.60,.65],'through_ID_mm':[6.40,6.50],
    'datum_A':'pilot cylindrical axis; finished size envelopes apply including form',
    'datum_B':'pilot floor / metal shoulder-contact annulus; not mouth face',
    'datum_C':'shoulder-facing cup mouth; plastic capture face',
    'datum_D':'nut-facing back plane',
    'relief_through_OD_true_position_diameter_to_A_max_mm':.02,
    'B_flatness_mm':.005,'B_perpendicularity_to_A_mm':.005,'C_flatness_mm':.005,'C_parallelism_to_B_mm':.01,
    'D_flatness_mm':.005,'D_parallelism_to_B_mm':.01,
    'pilot_floor_corner_R_max_mm':.05,'pilot_mouth_leadin_axial_depth_max_mm':.05,
    'relief_bore_edge_break':'Deburr only; all edge break included inside finished D6.88 maximum aperture',
    'surface_finish_request':'Ra1.6 or better on A/B/C/D; no ridges/burrs intruding functional envelopes'},
  'paired_shaft_new_acceptance_requirements':{
    'not_proven_by_catalogue':True,'continuous_g6_pilot_region_before_tail_shoulder_mm':.60,
    'g6_region_diameter_mm':[7.986,7.995],'tail_outer_edge_break_max_mm':.05,
    'shoulder_annulus_diameters_mm':[7.,7.8],'shoulder_face_flatness_mm_max':.005,
    'shoulder_face_perpendicularity_to_g6_axis_mm_max':.005,
    'fully_seated_axis_angle_deg_max':.2,
    'seating_condition':'Metal shoulder annulus seats on B without root or pilot-corner bottoming; do not treat a tilted edge-only seat as accepted',
    'short_pilot_warning':'A 0.5 mm pilot by itself does not geometrically prevent all tilt. The seated angular criterion must be confirmed together with the faces; not inferred from clearance alone.'},
  'capture_contract':{'effective_span':'shoulder_L - pilot_depth_p',
    'clamp_loop':'nut -> D -> solid washer web -> B -> shoulder -> integral thread -> nut',
    'plastic_contact':'C, not B; tightening does not use PETG as the clamp stack',
    'new_assembly_reference':'Root-requested L27+/-0.05 and external shell span26; pivot translation/cover/host handled by root, not tested here'},
  'not_checked':['Whole candidate host collision/tool updates after thicker washer','Printing/fit/actual manufacture',
    'Nut tightening load, washer bending, strength, galling or repeated service','Nylon-zone details and actual locking torque',
    'Arbitrary non-seated tilt or real acceptance of the added shaft drawing requirements'],
  'production_CAD_modified':False,'purchased':False,'manufacturing_release':False,'physical_acceptance':False}
 (run/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 (OUT/'latest.json').write_text(json.dumps({'directory':str(run.relative_to(ROOT)),'report_sha256':sha(run/'report.json')},indent=2)+'\n')
 print(json.dumps({'run':str(run.relative_to(ROOT)),'calculated':d,'native':[{k:x[k]for k in ['case','native_empty']}for x in cases]},indent=2))
if __name__=='__main__':main()
