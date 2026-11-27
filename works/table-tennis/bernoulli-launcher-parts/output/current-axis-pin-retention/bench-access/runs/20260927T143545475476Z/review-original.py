#!/usr/bin/env python3
"""Bench insertion sweeps for frozen clevis-pin candidate, no CAD changes."""
from pathlib import Path
from datetime import datetime,timezone
from fractions import Fraction as F
from concurrent.futures import ThreadPoolExecutor
import importlib.util,hashlib,json,math,re,sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rel=lambda p:str(Path(p).relative_to(ROOT))
helperfile=ROOT/'output/current-axis-offset-candidate/host-review/review.py'
spec=importlib.util.spec_from_file_location('axis_host_helper',helperfile)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def main():
 latest=json.loads((OUT.parent/'latest.json').read_text());native=ROOT/latest['directory']/'report.json'
 assert sha(native)==latest['report_sha256']
 nr=json.loads(native.read_text());assert nr['status']=='CONDITIONAL_STANDARD_PIN_GEOMETRY_PASS'
 sources=dict(nr['source_sha256'])
 for p,h in sources.items():assert sha(ROOT/p)==h,p
 for p in [native,Path(__file__),OUT/'probes.scad',helperfile,OUT.parent/'feasibility/continuous-rotation.json']:
  sources[rel(p)]=sha(p)
 folder=OUT/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder.mkdir(parents=True)
 pre='$fn=72;\nuse <'+str(OUT/'probes.scad')+'>\nuse <'+str(OUT.parent/'candidate.scad')+'>\nuse <'+str(ROOT/'output/current-axis-retention-review/candidate.scad')+'>\nuse <'+str(ROOT/'cad/cable-trigger-input.scad')+'>\n'
 jobs=[
 ('main-pin-insertion-plastic','intersection(){bench_pin_insertion();pin_plastics();}',[14]),
 ('main-pin-insertion-rotor','intersection(){bench_pin_insertion();ar_rotor(0);}',[]),
 ('main-pin-insertion-fixed-and-wire','intersection(){bench_pin_insertion();union(){bench_fixed();ci_local_cable(0);}}',[]),
 ('tail-washer-insertion-plastic','intersection(){bench_tail_washer_sweep();pin_plastics();}',[-12]),
 ('tail-washer-insertion-rotor','intersection(){bench_tail_washer_sweep();ar_rotor(0);}',[]),
 ('tail-washer-insertion-fixed-and-wire','intersection(){bench_tail_washer_sweep();union(){bench_fixed();ci_local_cable(0);}}',[]),
 ('tail-washer-insertion-seated-pin','intersection(){bench_tail_washer_sweep();bench_pin_seated_outer();}',[]),
 ('cotter-straight-preassembly','intersection(){bench_cotter_straight_sweep();bench_preassembly();}',[]),
 ('cotter-straight-tail-washers','intersection(){bench_cotter_straight_sweep();bench_tail_washers_max_stack();}',[]),
 ('cotter-straight-min-hole','intersection(){bench_x_tube(-17);bench_min_hole_pin();}',[]),
 ('control-cotter-hole-missing','intersection(){bench_x_tube(-17);bench_pin_seated_outer();}',None),
 ]
 def run(job):
  name,code,planes=job;r=helper.run(pre+code+'\n',name,folder)
  if r['native_empty']:r['classification']='NATIVE_EMPTY'
  else:
   _,raw=helper.mesh(ROOT/r['file'])
   if planes is None:
    r['raw_geometry']=helper.classify(ROOT/r['file']);r['classification']='POSITIVE_CONTROL_SOLID_INTERSECTION'
   else:
    r['expected_contact_Z_planes_mm']=planes
    exact=bool(planes) and all(any(all(F(v[2])==z for v in raw[i:i+3]) for z in planes) for i in range(0,len(raw),3))
    r['classification']='EXACT_END_FACE_CONTACT' if exact else 'UNCLASSIFIED_INTERSECTION'
  print(name,r['classification'],flush=True);return r
 with ThreadPoolExecutor(max_workers=2) as pool:probes=list(pool.map(run,jobs))
 # Radii account for the explicit circumscribed sweep and inscribed CAD bores.
 co=math.cos(math.pi/72);k=1/co
 margins={
  'shaft_to_POM_min72gon_bore_radial_mm':4.1*co-7.95*k/2,
  'shaft_to_fixed_PETG_min72gon_bore_radial_mm':4.15*co-7.95*k/2,
  'root_to_cover_min72gon_relief_radial_mm':4.6*co-9*k/2,
  'washer_min72gon_ID_to_shaft_outer_radial_mm':4.2*co-7.95*k/2,
  'cotter_sweep_to_min72gon_crosshole_radial_mm':co-.9*k,
  'cotter_sweep_to_max_tail_stack_Z_mm':.5-.9*(k-1),
 }
 assert min(margins.values())>0
 checks={
  'all_ten_path_probes_clear_or_exact_final_contact':all(r['classification'] in ['NATIVE_EMPTY','EXACT_END_FACE_CONTACT'] for r in probes[:-1]),
  'closed_crosshole_positive_control_has_solid':any(c['volume_mm3']>.001 for c in probes[-1].get('raw_geometry',{}).get('components',[])),
  'analytic_coaxial_radial_and_tail_gaps_positive':min(margins.values())>0,
  'sources_stable':all(sha(ROOT/p)==h for p,h in sources.items()),
 }
 report={
  'status':'BENCH_COAXIAL_PIN_WASHER_AND_STRAIGHT_COTTER_PATHS_CONDITIONAL_PASS' if all(checks.values()) else 'REVIEW_REQUIRED',
  'source_sha256':sources,'checks':checks,'native_report':rel(native),'native_report_sha256':sha(native),
  'candidate':rel(OUT.parent/'candidate.scad'),'candidate_sha256':sha(OUT.parent/'candidate.scad'),
  'coordinate_basis':'Input local coordinates; explicit ci_origin=[75,-85,5] retained for CAD-to-local mounting geometry.',
  'bench_state':{
   'present':['pin_body','pin_cover with two M3 cover fasteners/nuts','ar_rotor(0): lever, POM hex bush, two INTERNAL thrust washers, terminal cap and moving hardware','other_fixed_metal(): M6 seat hardware and M3 stop/cover hardware, old central axis removed','internal ci_local_cable(0), terminal preinstalled before cover'],
   'absent':['all four shared long host M4 bolts/host nuts','main feeder host/beam','old shoulder axis/cup washer/central axis nut','external complete housing route; module not yet mounted','tail washers and cotter during main-pin insertion; cotter during tail-washer insertion'],
   'alignment':'Temporarily hold the bush/rotor and fixed apertures coaxial at u0. Head is held against cover Z14 during rear washer/cotter installation; no clamp torque is applied through PETG.',
  },
  'sequence':[
   {'id':'B1','action':'On bench insert captive cover nuts and preassemble lever/POM bush, two internal thrust washers, cable terminal/cap and cable route; close cover with its two M3 fasteners. Four host M4 bolts remain absent.'},
   {'id':'B2','action':'Main pin enters from +localZ and moves along -Z. Sweep parameter s60 to0; at s0 head underside sits onZ14. No rear washers/cotter are installed yet.'},
   {'id':'B3','action':'Hold head seated q0; slide first rear washer from -Z until its upper face reachesZ-12. Slide second from -Z until it meets the first. Each t in[1.4,1.8]; preserve matched stop positions.'},
   {'id':'B4','action':'With q0 maintained, align the transverse cross-hole with localX. Move undeformed cotter straight legs from -X toward+X through the hole. This certificate stops before forming/bending legs.'},
   {'id':'B5','action':'Only after a separately acceptable cotter eye/formed-leg retention state is established may the module be attached using the four shared M4 bolts. Full host/removal and plier-forming are not certified here.'},
  ],
  'continuous_sweeps':{
   'main_pin':{'translation_s_mm':[0,60],'travel_direction':'from+Z along-Z','seated_shaft_Z':[-21,14],'root_Z':[11.5,14],'head_Z':[14,17],
    'envelope':'Union of exact continuous Z sweeps of each conservative cylindrical primitive. Start shaft tailZ39 is beyond all preassembly material in the radial corridor. Root never enters below11.5, head never below14.'},
   'tail_washers':{'two_thicknesses_each_mm':[1.4,1.8],'all_straight_sweeps_enclosed_annulus_Z':[-75.6,-12],'OD_nominal_held_mm':15,'ID_min_mm':8.4,
    'first_final_Z':'[-12-t1,-12]','second_final_Z':'[-12-t1-t2,-12-t1]',
    'matched_contact':'For the same t1/t2, second upper face <= first lower face at every insertion time. Do not test all independent thickness extreme positions against each other and call the artificial overlap interference.',
    'no_cotter_yet':'Installing the cotter before the washers obstructs the intended annular threading route; sequence is mandatory.'},
   'cotter_straight':{'direction':'from-localX toward+localX','straight_diameter_max_mm':1.8,'swept_X_budget_mm':[-40,12],'hole_centre_Z_range_with_q0_mm':[-17.25,-17],
    'proof':'E30 and holeD[2,2.5] couple centreZ=14-30-holeD/2. For every holeD, the coaxial minimum round hole admits the rigid straight-leg section. Native minD2 case plus analytic radial containment proves the continuum; do not independently move the cross-hole and leg centre.',
    'nominal_length_budget':'A nominal16mm rigid segment can move from[-40,-24] to[-4,12], crossing the<=7.95mm main pin. Actual length/eye dimensions and both shorter/longer leg engagement are not certified by this segment proxy.',
    'physical_straight_diameter_top_Z_max_mm':-16.1,'max_washer_stack_bottom_Z_mm':-15.6},
  },
  'analytic_clearances_mm_display':margins,
  'probes':probes,
  'conditions_not_supplier_guarantees':['E=30 and L=35 kept exact; actual tolerances remain missing.','Head-root is accepted only within D9x2.5; supplier has not confirmed this profile.','Washer OD15 held nominal; actual OD/flatness/burr tolerances not supplied.','Coaxial straight insertion without axis tilt, eccentric bores or deformed parts. Physical fit and insertion force are unverified.'],
  'not_checked':['Cotter eye/full undeformed assembly sliding into place: supplier eye length tolerance and exact form are incomplete.','Bending both legs, plier jaw/body and hand access, extracting a bent cotter, or installed retention force.','A particular purchased plier, full host-mounted service path, real bore tolerances/burrs/roughness and loaded behaviour.','Whether a nominal16mm cotter gives the desired final free leg lengths after actual eye seating.'],
  'no_tool_certification':'No plier model is introduced or claimed to be purchased/usable. Straight-segment clearance is not full cotter/plier assembly clearance.',
  'adopted':False,'manufacturing_release':False,'physical_acceptance':False,
 }
 (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (OUT/'latest.json').write_text(json.dumps({'directory':rel(folder),'report_sha256':sha(folder/'report.json')},indent=2)+'\n')
 print(json.dumps({'status':report['status'],'directory':rel(folder),'checks':checks,'margins':margins},indent=2),flush=True)

if __name__=='__main__':main()
