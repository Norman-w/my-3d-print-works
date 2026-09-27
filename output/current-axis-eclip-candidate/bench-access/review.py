#!/usr/bin/env python3
"""New E-clip candidate pin/washer insertion, plus unoccupied side-space budget."""
from pathlib import Path
from datetime import datetime,timezone
from fractions import Fraction as F
from concurrent.futures import ThreadPoolExecutor
import importlib.util,hashlib,json,math
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rel=lambda p:str(Path(p).relative_to(ROOT))
helperfile=ROOT/'output/current-axis-offset-candidate/host-review/review.py'
spec=importlib.util.spec_from_file_location('native_helper',helperfile)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def main():
 native=OUT.parent/'runs/20260927T145851957995Z/report.json'
 assert sha(native)=='11e6bded0f460b1963e2818728962315103821cf4b7df76fd3e166906ad9b24c'
 old=json.loads(native.read_text());assert old['status']=='DECLARED_ECLIP_SPACE_BUDGET_CLEAR'
 sources=dict(old['source_sha256'])
 for n,h in sources.items():assert sha(ROOT/n)==h,n
 for p in [native,Path(__file__),OUT/'probes.scad',helperfile]:sources[rel(p)]=sha(p)
 folder=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder.mkdir(parents=True)
 pre='$fn=72;\n'+''.join('use <'+str(p)+'>\n' for p in [OUT/'probes.scad',OUT.parent/'candidate.scad',ROOT/'output/current-axis-retention-review/candidate.scad',ROOT/'cad/cable-trigger-input.scad'])
 jobs=[
 ('pin-insertion-plastics','intersection(){eb_pin_insertion();ec_plastics();}',[14]),
 ('pin-insertion-rotor','intersection(){eb_pin_insertion();ar_rotor(0);}',[]),
 ('pin-insertion-fixed-wire','intersection(){eb_pin_insertion();union(){eb_fixed();ci_local_cable(0);}}',[]),
 ('washers-insertion-plastics','intersection(){eb_washer_sweep();ec_plastics();}',[-12]),
 ('washers-insertion-rotor','intersection(){eb_washer_sweep();ar_rotor(0);}',[]),
 ('washers-insertion-fixed-wire','intersection(){eb_washer_sweep();union(){eb_fixed();ci_local_cable(0);}}',[]),
 ('washers-insertion-new-pin','intersection(){eb_washer_sweep();eb_pin_seated_outer();}',[]),
 ('side-empty-corridor-preassembly','intersection(){eb_empty_side_corridor();eb_preassembly();}',[]),
 ('side-empty-corridor-washers','intersection(){eb_empty_side_corridor();eb_tail_stack_max();}',[]),
 ('side-empty-corridor-pin','intersection(){eb_empty_side_corridor();eb_pin_seated_outer();}',[]),
 ('control-corridor-into-shaft','intersection(){eb_corridor_positive();eb_pin_seated_outer();}',None),
 ]
 def probe(job):
  name,code,planes=job;r=helper.run(pre+code,name,folder)
  if r['native_empty']:r['classification']='NATIVE_EMPTY'
  elif planes is None:
   r['raw_geometry']=helper.classify(ROOT/r['file']);r['classification']='CONTROL_SOLID_INTERSECTION'
  else:
   _,raw=helper.mesh(ROOT/r['file'])
   exact=bool(planes) and all(any(all(F(v[2])==z for v in raw[i:i+3]) for z in planes) for i in range(0,len(raw),3))
   r['expected_Z_contact_planes_mm']=planes;r['classification']='EXACT_FINAL_FACE_CONTACT' if exact else 'UNCLASSIFIED_INTERSECTION'
  print(name,r['classification'],flush=True);return r
 with ThreadPoolExecutor(max_workers=2)as pool:probes=list(pool.map(probe,jobs))
 co=math.cos(math.pi/72);k=1/co
 clearances={
  'new_shaft_to_POM_bore_radial':4.1*co-4*k,
  'new_shaft_to_PETG_bore_radial':4.15*co-4*k,
  'root_to_relief_radial':4.6*co-4.5*k,
  'root_start_above_relief_bottom_axial':.2,
  'washer_min_ID_to_new_shaft_radial':4.2*co-4*k,
  'empty_corridor_endpoint_to_shaft_outer_X':4.2-4*k,
  'empty_corridor_upper_face_to_thickest_tail_stack_Z':.1,
 }
 checks={
  'pin_and_washer_seven_continuous_probes_clear_or_final_contact':all(p['classification'] in ['NATIVE_EMPTY','EXACT_FINAL_FACE_CONTACT']for p in probes[:7]),
  'three_empty_space_probes_native_empty':all(p['native_empty'] for p in probes[7:10]),
  'positive_control_solid':any(c['volume_mm3']>.001 for c in probes[-1].get('raw_geometry',{}).get('components',[])),
  'analytic_nominal_margins_positive':min(clearances.values())>0,
  'sources_stable':all(sha(ROOT/n)==h for n,h in sources.items()),
 }
 result={
  'status':'ECLIP_CANDIDATE_BENCH_PIN_WASHER_PATHS_AND_EMPTY_SIDE_CHANNEL_CONDITIONAL_PASS' if all(checks.values()) else 'REVIEW_REQUIRED',
  'source_sha256':sources,'checks':checks,'parent_native_report':rel(native),'parent_native_report_sha256':sha(native),
  'candidate_sha256':sha(OUT.parent/'candidate.scad'),
  'basis':'input local coordinates, explicit ci_origin=[75,-85,5]; shaft direction localZ=CAD+Y',
  'assembly_state':{
   'present':['ec_body and ec_cover with two M3 cover fasteners and preinserted nuts','ar_rotor(0): lever, POM bush, internal two thrust washers, terminal cap and moving hardware','other_fixed_metal including M6 adjuster and M3 trigger stop; former central hardware removed','internal ci_local_cable(0), installed before cover'],
   'absent':['four shared host M4 bolts and main feeder host','E-clip throughout pin/washer insertion','tail washers during pin insertion','external full housing route prior to host mounting'],
   'required_state':'Coaxial apertures and rotor at u0; hold new pin head onZ14 (q0) while adding rear washers. No central clamp torque through PETG.',
  },
  'new_axis_bound':{'shaft_D_max_mm':8,'L_range_mm':[30,30.1],'tail_N_max_requirement_mm':6,'seated_shaft_Z_mm':[-22.1,14],
    'head_D_max_requirement_mm':16,'head_T_max_mm':2.1,'seated_head_Z_mm':[14,16.1],
    'root_D_max_requirement_mm':9,'root_length_max_requirement_mm':2.5,'seated_root_Z_mm':[11.5,14],
    'root_head_D_tail_N_are_engineering_bounds_not_supplier_guarantees':True,
    'not_inherited':'No clevis transverse hole, cotter or former PIN301M8X35 path is used.'},
  'sequence':[
   {'id':'E1','action':'Bench preassemble captive cover nuts, rotor/POM/internal thrust washers and internal cable/terminal; close cover with its two M3 screws. Four host M4 screws are absent.'},
   {'id':'E2','action':'Insert new pin from+localZ along-Z until its head underside contactsZ14. Continuous s60-to0 sweep includes maxD8 shaft, D9x2.5 conditional root and maxD16/T2.1 head.'},
   {'id':'E3','action':'Hold head atq0. Add both tail washers one after another from-localZ. First stops at bodyZ-12, second at first washer. Do not install the E-clip before washers.'},
   {'id':'E4','action':'A separately validated E-clip insertion/retention process is still required. This report supplies only an empty side-space box and does not authorize substituting it for a clip/tool motion model.'},
   {'id':'E5','action':'Only after the ring installation/retention condition is satisfied, attach the module to the host using its four shared M4 screws.'},
  ],
  'continuous_path_proofs':{
   'pin':'Union of exact straight-Z sweeps of the enclosing shaft/root/head primitives for s in[0,60]. Root never extends below11.5 and head never below14. Groove omitted from pin outer space, which enlarges the obstruction for these clearance tests.',
   'washers':'Annular sweep Z[-76,-12],OD15 nominal externally circumscribed,ID8.4 minimum inscribed. Start and endpoint use exact integers to avoid float overshoot at the final face. No hull fills the washer bore.',
   'matched_washer_thickness':'For t1,t2 in[1.4,1.8], first final[-12-t1,-12], second[-12-t1-t2,-12-t1]. The second top never exceeds the first bottom for the SAME t1; no independent extreme-stack overlap is counted as interference.',
   'contact_classification':'Pin head atZ14 and first tail washer atZ-12 are retained intended contacts; all intersection triangles must lie exactly in the declared plane, never accepted from near-zero volume.',
  },
  'empty_channel_only':{
   'label':'Unoccupied side corridor requirement, NOT an E-clip or actual tool model',
   'local_box_mm':{'X':[-60,-4.2],'Y':[-12,12],'Z':[-18.1,-15.7]},
   'clear_box_dimensions_mm':[55.8,24,2.4],
   'approach':'from-localX toward the shaft; the box deliberately stops atX-4.2 outside the max shaft',
   'q0_groove_near_wall_Z_mm':[-16.1,-16],'q0_groove_far_wall_Z_mm':[-17.1,-16.9],
   'meaning':'Box is clear of preassembly, seated pin and thickest tail stack. It is an available approach region only, not a proven minimum-size maximum-opening channel.',
   'not_proved':'The final radial interaction insideX>-4.2, NETW7 elastic opening/tilt, actual ring containment, holder jaw/recess/body thickness, hand force and removal. Published free-ring D is not treated as an installed swept envelope.',
  },
  'nominal_analytic_clearances_mm':clearances,'probes':probes,
  'remaining_inputs':['Hhead/Ntail/head-root full profile acceptance, actual washer OD/flatness, as-printed bore alignment and shape','Actual installed E-clip inside declared R10 and axial space, insertion deformation, compatible tool and retention capacity','Friction, loaded return, wear and first physical assembly'],
  'adopted':False,'manufacturing_release':False,'physical_acceptance':False,
 }
 (folder/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (OUT/'latest.json').write_text(json.dumps({'directory':rel(folder),'report_sha256':sha(folder/'report.json')},indent=2)+'\n')
 print(json.dumps({'status':result['status'],'directory':rel(folder),'checks':checks,'clearances':clearances},indent=2),flush=True)
if __name__=='__main__':main()
