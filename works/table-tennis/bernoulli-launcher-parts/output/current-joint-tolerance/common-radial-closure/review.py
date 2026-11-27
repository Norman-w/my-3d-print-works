#!/usr/bin/env python3
"""Finite follower-nut / same-pin / V-seat coupling; no CAD mutation.

The numerical rows describe the nominal rigid, seated, retained-contact branch.
Actual fastener/form/preload data are deliberately not invented.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,math,re,sys

ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'analysis'))
from frame_y_guide_bound import upper as up,lower as down,sqrt_lower as sl,sqrt_upper as su
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
q=lambda x:F(str(x))
def conv(v):
 if isinstance(v,F):return float(v)
 if isinstance(v,dict):return{k:conv(x)for k,x in v.items()}
 if isinstance(v,(tuple,list)):return[conv(x)for x in v]
 return v
def ev(path,needle):
 rows=(ROOT/path).read_text().splitlines();r=[{'path':path,'line':i+1,'text':s}for i,s in enumerate(rows)if needle in s];assert r,(path,needle);return r

gatepath=ROOT/'output/current-joint-tolerance/gate-ball-joint-review/report.json'
jointpath=ROOT/'output/current-joint-tolerance/report.json'
gate=json.loads(gatepath.read_text());joint=json.loads(jointpath.read_text())
files={ROOT/p for p in gate['source_hashes']}|{gatepath,jointpath,Path(__file__)}
for p,h in gate['source_hashes'].items():assert sha(ROOT/p)==h,p
evidence=[]
for path,needle in [
 ('cad/cam-study.scad','cam_pin_start_y = -5.25'),
 ('cad/cam-study.scad','cam_pin_shoulder_start_y = 1.75'),
 ('cad/cam-study.scad','cam_pin_shoulder_end_y = 13.75'),
 ('cad/cam-study.scad','cam_carrier_width = 9'),
 ('cad/cam-study.scad','cylinder(h=nut_depth+cam_eps,'),
 ('cad/cam-study.scad','d=nut_af/cos(30),$fn=6'),
 ('cad/cam-study.scad','cylinder(h=2.4,d=5.5/cos(30),$fn=6)'),
 ('cad/cam-study.scad','-cam_carrier_width/2+0.1'),
 ('cad/feeder-pin-seat-revision.scad','translate([0,.1,0])cam_follower_nut'),
 ('cad/feeder-pin-seat-revision.scad','ps_v_z=2.4'),
 ('cad/feeder-pin-seat-revision.scad','ps_v_void()'),
 ('cad/feeder-pin-seat-revision.scad','ps_nose_y0=ps_seat_y0+.2'),
 ('cad/feeder-pin-seat-revision.scad','ps_adjust_retracted=.3'),
 ('cad/feeder-pin-seat-revision.scad','ps_jack_y=1.5'),
 ('cad/parameters.scad','nut_af = 5.8'),
 ('cad/parameters.scad','nut_depth = 2.6')]:
 evidence.extend(ev(path,needle));files.add(ROOT/path)
before={str(p.relative_to(ROOT)):sha(p)for p in sorted(files)}

sqrt2lo,sqrt2hi=sl(F(2)),su(F(2));sqrt3lo=sl(F(3))
pin_R=F(2);pin_rmin=down(F('2.25')-q(joint['whole_graph_reference'][1]['fixed_window_half_room_upper_mm']))
rho=up(pin_R-pin_rmin)
nut_rin=F('2.75');nut_rout=up(F('5.5')/sqrt3lo)
hole_apothem=F('2.9');cn=up(2*(hole_apothem-nut_rin)/sqrt3lo)
nut_half=F('1.2');roof=F('-1.9');seat=F('1.75');y0=seat;y1=F('4.5');ym=(y0+y1)/2;h=(y1-y0)/2
yn_upper=roof-nut_half # roof nonpenetration actually makes this stricter at tilt
Dmin=ym-yn_upper;A=Dmin-h;B=Dmin+h
guard=F('.09');ay_guard=down(1/su(1+guard*guard));sin_guard=up(guard/sl(1+guard*guard))
yn_lower=down(roof-nut_half-nut_rout*sin_guard)
center_guard=up(cn+(y1-yn_lower)*guard)
support_component_upper=up(pin_rmin*(1/sqrt2lo+guard*guard))
support_x_lower=down(pin_rmin*(1/sqrt2hi-guard*guard)/su(1+guard*guard))
apex_lo=down(20-2*sqrt2hi);apex_hi=up(20-2*sqrt2lo)
face_end_lo=down(apex_lo+F('2.4'))
witness_xlo=down(20-center_guard-support_component_upper)
witness_xhi=up(20+center_guard-support_x_lower)
witness_zabs=up(center_guard+support_component_upper)
finite_margins={'to_V_apex_x_lower':down(witness_xlo-apex_hi),'to_V_face_outer_x_end_lower':down(face_end_lo-witness_xhi),'to_V_face_Z_edge_lower':down(F('2.4')-witness_zabs)}
assert min(finite_margins.values())>0,finite_margins

# Nut centre plane is a real finite hex pocket section. Even the tilted
# guaranteed nut outer circle fits within the nut's 2.4 mm axial extent.
nut_disc_axial_projection=up(nut_rin*sin_guard)
assert nut_disc_axial_projection<nut_half
assert yn_lower>F('-4.5') and yn_upper<roof
roof_outer_extent=up(nut_rout+cn+nut_half*sin_guard)
roof_inner_rim=down(nut_rin*ay_guard-cn-nut_half*sin_guard)
assert roof_outer_extent<4 and roof_inner_rim>F('1.7')
assert nut_rin>=nut_half*sin_guard # stronger than needed: 1-cosβ<=sin²β
guard_full_ylo=up(seat+2*pin_R*sin_guard)
guard_full_yhi=down(seat+12*ay_guard-2*pin_R*sin_guard)
assert guard_full_ylo<y1<guard_full_yhi

rhoN=up(sqrt2hi*rho)
def small_root(b):
 # A*t - R*t²/2 <= b. On 0..guard its lhs is increasing.
 # The smaller positive root, rationalized and outward rounded.
 return up(2*b/(A+sl(A*A-2*pin_R*b)))
w=small_root(cn+rhoN);wp=small_root(cn);wn=up((cn+rhoN)/B)
assert A-pin_R*guard>0 and w<guard
assert A*guard-pin_R*guard*guard/2>cn+rhoN
ay=down(1/su(1+w*w));sb=up(w/sl(1+w*w))
full_ylo=up(seat+2*pin_R*sb)
full_yhi=down(seat+12*ay-2*pin_R*sb)
assert full_ylo<y1<full_yhi
nut_ylo_final=down(roof-nut_half-nut_rout*sb)
thread_near=down(seat-pin_R*sb-yn_upper-nut_half)
thread_far=up((seat+pin_R*sb-nut_ylo_final)/ay+nut_half)
assert thread_near>0 and thread_far<7

ymcam=F('10.5');C=ymcam-ym;m=F('.625');coef=su(1+m*m)
assert C-h>=pin_R*guard/2 # negative q cannot increase the positive projection
positive=up(coef*((C+h)*wp+pin_R*wp*wp/2))
negative=up(coef*((C-h)*wn+rhoN))
mixed=max(positive,negative)
delta_mid=up(h*w+pin_R*w*w/2+rhoN)
delta_cam=up((C+h)*w+pin_R*w*w/2+rhoN)
delta_far=up((13-ym+h)*w+pin_R*w*w/2+rhoN)
assert mixed<q(gate['exact_radial_residual_contract']['J_common_required_upper_mm'])
report={'status':'NEW_FINITE_NUT_V_PIN_BOUND_IN_SEATED_CONTACT_BRANCH_COMMON_RADIAL_CERTIFICATE_REMAINS_OPEN',
 'source_hashes':before,'evidence_lines':evidence,
 'scope':'Same finite pin, nut pocket and V faces in actual carrier-local coordinates. Nominal rigid CAD and maintained contact branch. Not an actual threaded-fit/metrology/preload certificate or full C/H/K/P elimination.',
 'new_actual_constraint':{'nut_AF':5.5,'pocket_AF':5.8,'nut_axial_length':2.4,'nut_pocket_material_Y':[-4.5,-1.9],'nominal_nut_Y':[-4.3,-1.9],
  'nut_axis_centre_hex_apothem_mm':hole_apothem-nut_rin,'nut_axis_centre_disc_upper_mm':cn,
  'meaning':'At the same installed nut mid-plane, its guaranteed R2.75 outer circle must fit the real AF5.8 hex pocket. The pin axis is the same coaxial threaded-axis line in the nominal fastener model. Nut rotation around its own axis is not set to zero.'},
 'joint_variables':{'w':'same pin/carrier-local slope (dx/dY,dz/dY)','q_i':'n_i dot w, n1=(1,-1)/sqrt2,n2=(1,1)/sqrt2; orthonormal pair','delta0':'same pin centre minus (20,0) at carrier Y3.125','deltaN':'same pin centre at installed nut centre Y_N','identity':'deltaN=delta0-(3.125-Y_N)w; deltaXZ(y*)=delta0+(y*-3.125)w',
  'cam_intersection_identity':'C(qcam)=T_i+O_i[20+delta_x(y*), y*, delta_z(y*)]. y* and qcam are the SAME intersection with the real cam section; do not replace y* by10.5 under arbitrary C/K pose.'},
 'branch_requirements':['Nut axis and shoulder axis are coaxial in the nominal fastener model; real thread play/coaxiality is not supplied.','Follower nut front annulus is seated on its real +Y pocket roof at Y−1.9; shoulder end has at least one contact with its real seat Y1.75. Entire faces need not be assumed fully flush.','Both finite V planes retain at least one actual pin contact; their contacts may occur at different Y and at finite end edges. Full-length generatrix contact is NOT assumed.','From the nominal installed branch, contacts remain retained and rigid solids do not interpenetrate. Nut backing out or V unloading leaves this proof domain.','Current nominal six-sided nut and 32-sided shoulder shapes are used only as outer/inner bounding shapes; no as-purchased tolerances inferred.'],
 'finite_contact_backsubstitution':{
  'bootstrap_slope_guard':guard,'nut_midY_interval_mm':[yn_lower,yn_upper],'nut_disc_axial_projection_upper_mm':nut_disc_axial_projection,'nut_half_length_mm':nut_half,
  'nut_roof_outer_radius_enclosure_upper_mm':roof_outer_extent,'nut_roof_inner_rim_radius_lower_mm':roof_inner_rim,'roof_material_test':'outer<4mm carrier half-Z; inner>1.7mm M3 passage; M2 cut starts4.8mm from axis, beyond this ring.',
  'upper_V_section_Y':y1,'upper_V_axis_centre_offset_guard_upper_mm':center_guard,'guaranteed_pin_inner_radius_mm':pin_rmin,
  'full_shoulder_Y_interval_at_bootstrap_guard_mm':[guard_full_ylo,guard_full_yhi],
  'V_support_witness_X_interval_mm':[witness_xlo,witness_xhi],'V_support_witness_absZ_upper_mm':witness_zabs,'finite_face_margins_mm':finite_margins,
  'proof':'At the upper section limit Y→4.5 from below, inscribed-cylinder support points fall strictly inside the two real diagonal face spans; lower-end cap truncation is allowed. Nut and shoulder finite caps remain covered. Derived slope <.09 prevents a first exit from this finite domain.'},
 'inequalities':{
  'contact_upper':'n_i.delta0 <= h|q_i| + e_i; e_i=Rmax(sqrt(1+q_i²)-1)<=Rmax*q_i²/2. This follows from an actual contact somewhere in the finite Y1.75..4.5 span; no same-Y contact assumption.',
  'upper_nonpenetration':'n_i.delta0+h q_i >= -rho, rho=2-r_pin_min, from a real inscribed-cylinder point at the finite upper face limit.',
  'nut':'||deltaN||<=cN and D=3.125-Y_N>=6.225; SAME delta0,q,D.',
  'global_slope':'(Dmin-h)||w|| <= cN+sqrt2*rho+(Rmax/2)||w||². On0..guard, monotonic lhs gives its small-root upper bound.',
  'positive_q_norm':'||q_plus|| <= smallroot(cN); the negative-q components do not consume an independent second nut-centre budget.',
  'negative_q_norm':'||q_minus|| <= (cN+sqrt2*rho)/(Dmin+h).',
  'negative_q_dropped_from_positive_projection':'For carrier-local Y10.5, C-h=6 >= Rmax*guard/2=.09. Hence e_i <= (Rmax*guard/2)|q_i| cannot offset the negative linear contribution when q_i<0. Both (1,+/-.625) have nonnegative coefficients in the two V-normal basis directions.',
  'common_domain_handling':'These are necessary consequences of the SAME nut centre and pin line. Their safe norm outer bounds are not claimed simultaneously attained, and no physical failure is inferred from a loose bound.'},
 'new_numeric':{'Dmin_mm':Dmin,'A_Dmin_minus_h_mm':A,'rho_from_32gon_mm':rho,'slope_norm_upper':w,'angle_deg_diagnostic':math.degrees(math.atan(float(w))),
  'positive_q_norm_upper':wp,'negative_q_norm_upper':wn,'V_mid_axis_offset_norm_upper_mm':delta_mid,
  'full_shoulder_cross_section_Y_interval_mm':[full_ylo,full_yhi],'nominal_far_cam_face_Y13_reserve_lower_mm':down(full_yhi-13),
  'nominal_thread_axis_interval_covering_entire_nut_mm':[thread_near,thread_far],'thread_length_mm':7,'thread_back_end_reserve_lower_mm':down(7-thread_far),
  'axis_offset_norm_at_carrier_Y10_5_upper_mm':delta_cam,'axis_offset_norm_at_carrier_Y13_upper_mm':delta_far},
 'radial_projection_bookkeeping':{'nominal_aligned_cam_mid_Y':ymcam,'cam_slope_abs':m,'positive_dx_plus_or_minus_mdz_upper_mm':positive,'negative_magnitude_upper_mm':negative,'mixed_abs_upper_mm':mixed,
  'remaining_from_old_J_budget_IF_projection_decomposition_proved_mm':down(q(gate['exact_radial_residual_contract']['J_common_required_upper_mm'])-mixed),
  'guard':'The .372... mixed bound is in carrier-local X/Z at Y10.5 with coefficient(1,±.625). It is NOT automatically the entire finite-pin term in an arbitrarily transformed common cam. Use the exact C/K identity and actual y* before subtracting it from J_common.',
  'general_y_bound':'For y*>=4.5 within the proven full-cylinder interval: ||deltaXZ(y*)|| <= (y*−1.75)wbar +Rmax*wbar²/2+sqrt2*rho. Use this vector set with the same O_i/C, not an independent phase shift.'},
 'unclosed_actual_inputs':{'thread_axis_radial_play_and_coaxiality':None,'nut_and_pocket_actual_AF_profile':None,'shoulder_actual_radius_form_and_end_faces':None,'V_face_form_and_angle':None,'retained_contact_load_preload_creep':None,
  'joint_common_cam_intersection_y_star_interval':None,'joint_common_frame_phase_and_registration_residual':None},
 'mechanical_interpretation':{'current_pin_is_not_geometrically_free':'The real captive nut supplies a lower radial registration section; it must not be omitted and then replaced by an invented long V bearing.',
  'what_does_not_lock_contact':'The sliding block ear and compensation stops retain the block, but do not by themselves prove a positive V preload under the cam wrench. The single M2 adjuster acts atY1.5 while pin-contact nose startsY1.95; block moment/pose cannot be replaced by a prescribed zero tilt.',
  'minimal_next_action':'First include this same-nut bound and the finite shoulder slab in the common C/K intersection calculation. This is a tighter nominal constraint, not a reason to change the existing holes merely because an older loose bound failed.',
  'optional_design_if_retention_or_tolerance_cannot_be_bounded':'A lockable longer M2 adjuster with an exterior jam nut can retain screw position, after local tool/clearance review; it does not certify preload or remove pin tilt. To remove reliance on a threaded nut as a radial datum, replace the carrier pin location with a positively retained metal round-journal/bushing support over a declared finite span; this requires the corresponding longer journal/seat and real host clearance review, not simply shrinking a PETG hole or calling the existing2.75mm V infinitely long.'},
 'current_common_Bx_certified':False,'J_common_proved_upper_mm':None,'actual_feasible_failure_witness':None,'manufacturing_release':False,'physical_acceptance':False,
 'numerical_method':'Fraction arithmetic, directed1e−12 rounding and conservative square-root bounds. No sampling optimizer; branch guard and finite-domain margins verified analytically.',
 'sources_stable':all(sha(ROOT/p)==v for p,v in before.items())}
assert report['sources_stable']
OUT.mkdir(exist_ok=True,parents=True);(OUT/'report.json').write_text(json.dumps(conv(report),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(conv({'new_numeric':report['new_numeric'],'radial_projection_bookkeeping':report['radial_projection_bookkeeping'],'finite_margins':finite_margins}),ensure_ascii=False,indent=2))
