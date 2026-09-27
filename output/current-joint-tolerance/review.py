#!/usr/bin/env python3
"""Finite D02 joint-domain audit. No CAD generation, optimization or release.

This bounds selected real constraints and preserves the unsolved common-domain
conditions. It never substitutes independently attainable/free maxima for an
assembly witness. Only writes this directory.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,math,re,sys
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'analysis'))
import frame_y_guide_bound as fy
import final_gate_error_bound as fg
GRID=10**12
up=fy.upper;down=fy.lower;sqrtlo=fy.sqrt_lower;sqrthi=fy.sqrt_upper

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def lit(name,key):
 p=ROOT/'cad'/name;m=re.findall(r'^\s*'+re.escape(key)+r'\s*=\s*([-+\d.]+)\s*;',p.read_text(),re.M);assert len(m)==1,(name,key);return F(m[0])
def evidence(name,needle):
 p=ROOT/name;rows=p.read_text().splitlines();hits=[{'path':name,'line':i+1,'text':s}for i,s in enumerate(rows)if needle in s];assert hits,(name,needle);return hits

def atan_interval(x,terms=100):
 # Alternating arctan series; endpoints bracket exact arctan for0<x<1.
 a=sum(((-1)**k)*x**(2*k+1)/F(2*k+1)for k in range(terms));b=a+((-1)**terms)*x**(2*terms+1)/F(2*terms+1)
 return min(a,b),max(a,b)
a,b=atan_interval(F(1,5));c,d=atan_interval(F(1,239));PIlo=16*a-4*d;PIhi=16*b-4*c
assert F('3.1415926535897932384626433832795028841971693')<PIlo<PIhi<F('3.1415926535897932384626433832795028841971695')

def cos_pi_lower(n):
 x=PIhi/n
 # Monotone cos on this positive domain and alternating negative-last bound.
 return down(1-x*x/2+x**4/24-x**6/720)
def f(v):return float(v)
def floats(d):
 if isinstance(d,F):return f(d)
 if isinstance(d,dict):return{k:floats(v)for k,v in d.items()}
 if isinstance(d,(tuple,list)):return[floats(v)for v in d]
 return d

# Source extraction: nut pocket reaches2*eps farther inward than its nominal end.
mountX=lit('feeder-supports.scad','support_mount_x');mountTh=lit('feeder-supports.scad','support_mount_thickness');bodyX=lit('feeder-body.scad','body_side_mount_x');eps=lit('feeder-body.scad','body_eps');nutD=lit('parameters.scad','nut_depth');holeR=lit('parameters.scad','fastener_d')/2
assert mountX==bodyX==F('35.5') and mountTh==8 and holeR==F('1.7')
bodyRoundEnd=bodyX-nutD-eps;bridge=mountX-bodyRoundEnd
assert bodyRoundEnd==F('32.88') and bridge==F('2.62')
mountSpan=F(61);p,dep=fg.parameters();assert p['v_half_span']==1.375

def mount_case(rmin,label):
 e=up(holeR-rmin);slope=up(2*e/mountTh);C=up(2*e+bridge*slope);chord=up(2*C/mountSpan)
 tip=up(C+14*chord);pinwindow=up(C+F('21.25')*chord)
 return {'label':label,'pin_section_inscribed_radius_lower_mm':rmin,'radial_room_upper_mm':e,'bolt_axis_transverse_slope_upper':slope,'relative_hole_center_distance_upper_mm':C,'support_rotation_chord_upper':chord,'support_about_X_angle_upper_deg_diagnostic':math.degrees(2*math.asin(f(C/mountSpan))),
 'support_tip_registration_norm_upper_mm':tip,'support_front_window_registration_norm_upper_mm':pinwindow,'tip_bound_z_scope':[-28.5,0],
 'remaining_Bz1_after_registration_and_nominal_round_pin_window_ONLY_mm':down(1-tip-F('.25')),
 'not_a_feasible_extreme_or_collision':True}
mount=[mount_case(F('1.5'),'ideal round D3 reference, axis tilt retained'),mount_case(down(F('1.5')*cos_pi_lower(32)),'current32gon shank guaranteed disk outer bound')]
# Exact source annulus is interrupted by the hex nut pocket. Without independent
# normal-axis proof, the C=0.4 disk is not a universal result of these two bores.

# Round-plus-capsule seam constraints at the SAME X0 interface: no axial bridge.
seamY=[F(40),F(-40)];seamZ=[F(-59),F(3)];L2=(seamY[1]-seamY[0])**2+(seamZ[1]-seamZ[0])**2;Llo=sqrtlo(L2)
seam_rows=[]
for label,rmin in [('ideal roundD3',F('1.5')),('current72gon pin guaranteed disk',down(F('1.5')*cos_pi_lower(72)))]:
 cs=up(F('1.55')+F('1.6')-2*rmin);sinA=up(2*cs/Llo);cosA=sqrtlo(1-sinA*sinA);chord=sqrthi(2*(1-cosA));points=[]
 for z in [F(0),F('-28.5')]:
  # p=(0,z), first round reference a=(40,-59).
  dy=F(-40);dz=z+59;norm=up(cs+chord*sqrthi(dy*dy+dz*dz))
  points.append({'tip_nominal_yz_mm':[0,z],'displacement_norm_upper_mm':norm,'component_y_upper_mm':up(cs+(1-cosA)*abs(dy)+sinA*abs(dz)),'component_z_upper_mm':up(cs+sinA*abs(dy)+(1-cosA)*abs(dz))})
 seam_rows.append({'label':label,'per_locator_transverse_center_room_upper_mm':cs,'sin_relative_roll_upper':sinA,'relative_roll_angle_upper_deg_diagnostic':math.degrees(math.asin(f(sinA))),'rotation_chord_upper':chord,'gate_datum_bounds':points})

# Whole cam graph contribution, retaining the existing physical circular-shaft
# reference separately from the literal display-mesh inscribed disk.
m=F('0.625');fac=sqrthi(1+m*m);invfac=down(1/fac);coshalf=sqrtlo((1+invfac)/2)
slots=[]
for label,rmin in [('ideal circularD4 reference',F(2)),('current32gon D4 mesh guaranteed disk',down(2*cos_pi_lower(32)))]:
 S=up((F('2.25')-rmin*coshalf)*fac);W=up(F('2.25')-rmin);intr=up(S+m*W)
 slots.append({'label':label,'whole_graph_slot_bound_upper_mm':S,'fixed_window_half_room_upper_mm':W,'intrinsic_radial_sum_upper_mm':intr,'remaining_Bx1_for_all_other_joint_terms_lower_mm':down(1-intr)})

# Finite V face domain and correlated shape allocation, not independent dx/dz.
vtable=[]
for E in [F(0),F('.05'),F('.1'),F('.15'),F('.2')]:
 root2=sqrthi(F(2));v=up(root2*E);dxrange=[-v,v];remain=down(slots[0]['remaining_Bx1_for_all_other_joint_terms_lower_mm']-v)
 vtable.append({'face_normal_error_E_mm_NOT_measurement':E,'radius_error_reference':0,'center_norm_and_abs_component_bound_mm':v,'mixed_projection_x_plus_mz_bound_mm':v,'work_compensation_reserve_lower_mm':down(F('.3')-v),'remaining_Bx1_for_all_pose_radius_form_load_terms_lower_mm':remain,'scope':'parallel axis and ideal face normals; both finite contacts maintained; other joint terms NOT set to zero'})
frame=fy.bound(.1,.1,36.58)
# Explicit finite contact material regions from current wrapper source. These are
# material patches; transformed overlap must be checked, not infinite planes.
patches={
 'frame_X_fixed_datum':{'x':54,'y':[21,24],'z':[-35,5]},
 'frame_X_gib_parallel_common_Z_stations':[-33.35,3.35],
 'frame_Y_fixed_lower_bands':{'y':20,'x':[53.5,58.5],'z':[[-33.5,-27.5],[-2.5,3.5]]},
 'frame_Y_moving_gib_teeth':{'x':[54.2,57.8],'z':[[-33.5,-27.5],[-2.5,3.5]],'axial_and_X_float':[-.2,.2]},
 'frame_Y_common_Z_stations_parallel_only':[-33.29,3.29],
 'carrier_front_intact_safe_local_patch':{'x':[13,28],'y':4.5,'abs_z':[3.1,3.9]},
 'carrier_front_fixed_flat_land':{'x':[44.3,57.3],'y':4.5,'abs_z':[2.5,4.1]},
 'carrier_rear_adjustable_land':{'x':[43.8,57.8],'y_at_display':-4.6,'abs_z':[2.1,4.1]},
 'carrier_top_bottom_guide':{'z_half':4.2,'moving_carrier_z_half':4,'source_x_domain':[35.5,58]},
 'V_face_cylinder_contact_Y_span':[1.75,4.5],
 'body_outer_rod_bearing_material_X_span':[31.5,33.5],
 'body_outer_rod_bearing_note':'The cylinder cutter runs23.5..33.5 but body seat material only31.5..33.5. The open cam carrier/body rectangular cut starts33.5. The inner guide is no longer engaged by the rod at open gate; do not assume a full10mm bearing for all stroke.'}
# Source lines retained, not descriptions inferred from stale renderings.
needles=[('cad/feeder-body.scad','body_side_mount_x-nut_depth/2'),('cad/feeder-body.scad','nut_depth+2*body_eps'),('cad/feeder-body.scad','side==1?31.5:-body_side_mount_x'),('cad/feeder-body.scad','side==1?33.5:-60'),('cad/feeder-supports.scad','support_mount_thickness ='),('cad/feeder-supports.scad','support_x_hole(support_mount_y'),('cad/feeder-supports.scad','cylinder(h=length,d=d,$fn=32)'),('cad/feeder-seam-candidate.scad','if(positive && index==1)'),('cad/feeder-seam-candidate.scad','seam_slot_unit'),('cad/feeder-seam-candidate.scad','fn=72'),('cad/feeder-pin-seat-revision.scad','ps_lip_half_z'),('cad/feeder-pin-seat-revision.scad','ps_v_void'),('cad/feeder-frame-y-guide.scad','yg_tooth_x'),('cad/feeder-frame-y-guide.scad','rotate([yg_pitch,0,0])'),('cad/feeder-guide-revision.scad','revision_datum_lead'),('cad/cam-study.scad','cam_follower_offset ='),('cad/cam-study.scad','cam_pin_shoulder_start_y ='),('cad/feeder-hardware-clearance.scad','hc_x_cylinder(47.05,-14,z,45,7+2*hc_head_clearance)'),('cad/launcher-final-assembly.scad','hc_support_clearance(1)yg_right_support()'),('cad/cable-output-interface.scad','union(){feeder_carriage(0);co_lug_blank();}')]
lines=[x for name,needle in needles for x in evidence(name,needle)]
files={ROOT/k for k in dep}|{ROOT/n for n,_ in needles}|{ROOT/'analysis/frame_y_guide_bound.py',ROOT/'analysis/final_gate_error_bound.py',ROOT/'output/current-assembly-budget/report.json',ROOT/'output/current-assembly-budget/README.md',Path(__file__)}
def include_graph(path):
 path=path.resolve()
 if path in scene_seen:return
 scene_seen.add(path);files.add(path)
 for name in re.findall(r'\b(?:include|use)\s*<([^>]+)>',path.read_text()):include_graph(path.parent/name)
scene_seen=set();include_graph(ROOT/'cad/cable-scene-export.scad')
before={str(q.relative_to(ROOT)):sha(q)for q in sorted(files)}
rep={'status':'D02_JOINT_RELATIONS_AND_CONTINUOUS_OUTER_BOUNDS_DEFINED_FULL_ASSEMBLY_NOT_CERTIFIED','task_id':'D02','completion':'PARTIAL_CONSERVATIVE_SUBDOMAIN_RESULTS; joint domain elimination remains open','scope':'Finite algebraic audit only; no CAD change, optimization, source/STL export, slicer or full collision run. Conditional contact branch, nominal digital geometry; actual form/load unknowns explicit.',
 'source_hashes':before,'evidence_lines':lines,'sources_stable':all(sha(ROOT/k)==v for k,v in before.items()),
 'joint_domain':{'name':'D02','variables':{'B_negative':'fixed reference body half','B_positive':'one shared seam rigid transform','S_left/S_right':'one rigid support transform per body half','C(u)':'ONE common cam transform for all four pins and both rails','K_i(u)':'one carrier transform for each finger','P_i(u)':'same shoulder-axis line in its V/window/cam constraints','G_j':'one transform for each actual finite gib; effective gaps and differential pitch explicit'},
 'common_transform_identities':['C_in_support_s = inverse(S_s) * inverse(B_s) * C','K_in_support_i = inverse(S_s) * inverse(B_s) * K_i','P_in_V_i = inverse(K_i) * P_i','P_in_cam_i = inverse(C) * P_i','P_in_fixed_window_i = inverse(S_s) * inverse(B_s) * P_i'],
 'constraints':['Both body split datum faces and support mounting datum faces remain seated in the declared normal branch; if form error permits pitch/yaw, additional angular envelopes are required.','Each physical mounting bolt is ONE line/cylinder through both actual finite bore regions; do not choose unrelated centres at separated X stations.','Each seam pin is ONE cross-section at common X0: d0 in disk(c), d1 in rotated longitudinal capsule([-.5,.5]e)+disk(c).','Finite frame X/Y bands must contain the transformed contact points. Parallel display gap .1 does not establish differential-gib coverage or positive gap under load.','Each actual carrier Y/Z patch must intersect its finite host land, including V-ear removals. No point may be constrained by an infinite continuation of absent material.','The SAME P_i lies inside the fixed window, actual cam slot, and retained cylinder contact domain of both V faces; shoulder remains seated and sample plane is within cylinder/cam material.','Both V contacts retain positive normal load; 2D necessary P-Fx>|Fz| is not a substitute for full moment/axial/contact feasibility.','All four followers share C(u) continuously for0<=u<=20; the inequalities and outer bounds are not independent attainable pose extrema.'],
 'not_yet_eliminated':['common two-support registration versus frame finite contact domains','four carrier rotations after finite Y-land clipping and V-ear cuts','differential gib pitch versus true finite pad coverage','finite pin engagement, all-slot endpoint phase, and loaded V contact continuation']},
 'finite_material_patches':patches,
 'mount_registration':{'mount_centres_YZ':[[-14,-45],[-14,16]],'span_mm':mountSpan,'body_nominal_round_bore_ends_at_X_mm':bodyRoundEnd,'support_round_bore_X_mm':[mountX,mountX+mountTh],'axial_bridge_mm':bridge,'formulas':['delta=R_hole-r_pin_inscribed; bolt_slope<=2*delta/L_support','C_mount<=delta_body+delta_support+axial_bridge*2*delta_support/L_support','d_minus=T_s(p_minus)-p_minus and d_plus=T_s(p_plus)-p_plus lie in discs C_mount for SAME T_s','2*sin(abs(theta_support)/2)<=2*C_mount/61 on seated normal branch','for z in[-45,16]: delta(y,z)=(1-a)*d_minus+a*d_plus+(R-I)*(y+14,0), a=(z+45)/61','therefore ||delta(y,z)||<=C_mount+abs(y+14)*2*C_mount/61'],
 'cases':mount,'assumptions':['Existing cylindrical shank remains engaged across the bore sample planes and is straight. Thread cylinder is a nominal envelope, not a thread-load model.','Datum faces retain parallel X normals; additional seat form/pitch/yaw is not assigned zero for real hardware.','Extra nut contacts and body-rod guidance may shrink these domains. Their omission makes an OUTER set, not a feasible witness.'],'parameter_extension':'delta_body=.2+eta_body+rho_bolt; delta_support=.2+eta_support+rho_bolt for physical circular reference; C adds (2.62+eta_axial)*2*delta_support/(8-eta_span). Unknown eta values remain supplied inputs.'},
 'seam_registration':{'locator_YZ':[[40,-59],[-40,3]],'span_squared_mm2':L2,'slot_half_longitudinal_run_mm':.5,'formulas':['At common X0, d0 in disk(c); d1 in R[-.5,.5]e + disk(c), with SAME R,t.','Project d1-d0=(R-I)L*e onto R*n: L*abs(sin(theta))<=2*c. The .5 longitudinal slot does not add .5 transverse error.','delta(p)=d0+(R-I)*(p-p0); norm<=c+2*sin(theta_max/2)*||p-p0||.'],'cases':seam_rows,'normal_branch_required':True},
 'whole_graph_reference':slots,
 'cam_endpoint_fit':{'ideal_circular_pin_sufficient_combined_centre_radius_lower_mm':down(F('2.25')*cos_pi_lower(32)-2),'joint_error_vector':'e_end = fixed-world-Y section(P_i) - transformed rounded track endpoint(C), expressed in the SAME host frame. Registration common to P_i and C cancels; it must not be added twice.','sufficient_form_tilt_condition':'norm(e_end)+radius_error+2*(sec(beta_world)-1)+inward_cam_form_error < 0.239165635009 (nominal32gon slot inner disk reference). Actual r_max should replace2 in the tilt term.','current_joint_e_end_upper_mm':None,'certified':False,'interpretation':'Cannot compare an independent0.531 mount-radius bound directly to this0.239 fit radius as though it were an attainable relative endpoint error; P_i and C are coupled by rails/window/V seats.'},
 'finite_V':{'mid_Y_mm':3.125,'half_span_mm':1.375,'joint_parallel_face_domain':'abs(dx-sqrt(2)*dr)+abs(dz)<=sqrt(2)*E; block_dx=dx+dr must lie[-.5,.3].','exact_correlated_support_function':'BEFORE clipping by block_dx in[-.5,.3], for any w=(wx,wz): max_abs(w.delta)=sqrt(2)*E*max(abs(wx),abs(wz))+sqrt(2)*rho*abs(wx). AFTER clipping it remains an upper bound, not necessarily the exact attained support of the joint domain.','working_guarantee_for_symmetric_errors':'sqrt(2)*E+(1+sqrt(2))*rho<=.3; does not prove preload.','finite_contact_extension':'Bv=[sqrt(2)*(E+rho+1.375*tan(beta)+(2+rho)*(sec(beta)-1))+epsilon*sqrt(2)*2]/(1-epsilon), epsilon=2*sqrt(2)*sin(alpha/2)<1. Contacts may occur at distinct Y; beta/alpha and retained contact not supplied.','shape_load_reserve_equation':'Let Jx be the supremum of all NON-V pose/registration/loaded terms over this SAME D02 domain. Circular-reference Bx bound: intrinsic(.rho,slot/window form)+Jx+Bv<=1. At zero radius/slot/window form, Bv+Jx<=0.457543440238. No assumption Jx=0 is made.','explicit_E_reserve':'E <= (1-epsilon)*(1-intrinsic-Jx)/sqrt(2)-rho-1.375*tan(beta)-(2+rho)*(sec(beta)-1)-2*epsilon; also apply the working compensation inequality. Negative RHS means this sufficient budget cannot certify its input domain, not a collision.','sensitivity_rows':vtable},
 'frame_contact_comparison_ONLY':{'actual_parallel_display_box':frame,'use_guard':'Only when both supports define the common frame and actual finite band membership holds. Do not add free registration extremes to this matrix result and call it jointly reachable.','contact_phase_formula':'with a single correctly registered fixed datum: phase_z <=59|Rzx|+25|Rzy|+h(1-Rzz), h5 at rest/h55 at full. For different supports and seam registration the SAME transforms must enter stop planes; a new numeric H_min is not established here.'},
 'finite_conclusion':{'new_feasible_collision_witness':None,'complete_current_Bx_Bz1_certificate':False,'reason':'Current nominal source supplies a nonzero correlated registration outer set, not exact zero datums. The computed support-registration outer budget already cannot certify Bz<=1 after the nominal fixed-window term. Finite carrier/body/rail constraints may tighten it, so this is failure of this OUTER certificate, not physical failure.','actionable_remaining_requirements':['Use actual or certified effective registration bounds (or eliminate the common constraints tighter), not default0.4 or zero.','Supply retained finite-V form/angle/radius/contact/load limits and solve remaining common pose terms before allocating the positive radial remainder.','For D03 retain phi_rest,phi_full,H_min as parameterized common-domain bounds; the old .229 values are only their stated parallel-registration comparison.']},
 'numerical_method':'Exact Fraction arithmetic and outward1e-12 rounding. pi bracket from alternating Machin arctan series; inscribed-radius cos bounded by alternating Taylor truncation. Angles in degrees are display diagnostics; certificate uses rational chord/sine bounds. No sampled optimizer extrema.',
 'manufacturing_release':False,'actual_measured_inputs':False,'physical_acceptance':False}
(OUT/'report.json').write_text(json.dumps(floats(rep),ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'mount_cases':floats(mount),'seam_cases':floats(seam_rows),'slots':floats(slots)},ensure_ascii=False))
