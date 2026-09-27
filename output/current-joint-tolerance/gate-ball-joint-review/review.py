#!/usr/bin/env python3
"""Joint-condition gate screen using the current split-guide sphere bound.

Analytic sufficient inequalities. No optimizer, physical counterexample claim,
CAD mutation, slicing, or unmeasured print/load precision is introduced.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'analysis'))
from frame_y_guide_bound import upper as up,lower as down,sqrt_lower as sl,sqrt_upper as su

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def q(x):return F(str(x))
def conv(v):
 if isinstance(v,F):return float(v)
 if isinstance(v,dict):return{k:conv(x)for k,x in v.items()}
 if isinstance(v,(list,tuple)):return[conv(x)for x in v]
 return v
def read(p):return json.loads((ROOT/p).read_text())

paths={'ball':'output/current-joint-tolerance/ball-center-coupling/report.json',
 'axial':'output/current-joint-tolerance/half-shell-axial-coupling/report.json',
 'carrier':'output/current-joint-tolerance/carrier-body-coupling/report.json',
 'joint':'output/current-joint-tolerance/report.json',
 'assembly':'output/current-assembly-budget/report.json'}
b=read(paths['ball']);ax=read(paths['axial']);car=read(paths['carrier']);joint=read(paths['joint']);assembly=read(paths['assembly'])
files={ROOT/p for p in b['source_hashes']}|{ROOT/p for p in paths.values()}|{Path(__file__)}
for p,h in b['source_hashes'].items():assert sha(ROOT/p)==h,p
diag=assembly['gate_budget']['current_tip_mesh_diagnostic'];mesh=ROOT/diag['file'];assert sha(mesh)==diag['sha256'];files.add(mesh)
before={str(p.relative_to(ROOT)):sha(p)for p in sorted(files)}

a=ax['numeric'];c=q(a['seam_locator_disc_radius_upper_mm']);ta=q(a['tan_alpha_upper']);AA=q(a['same_A_abs_upper_mm']);Llo=sl(F(10244))
cr=car['new_result'];r=cr['matrix_abs_upper'];d=cr['matrix_diagonal_lower']
tau_y=up((q(r['Ryx'])+q(a['axis_projection_sin_beta_upper'])*q(r['Rzx']))/q(d['Rxx']))
own_y=up(q(cr['body_bore_radial_axis_room_upper_mm'])+F('11.6')*tau_y)
by_rows=[]
for z in [F(0),F('-28.5')]:
 beta=(z+59)/62
 vals=[up(c/(2*Llo)*(su((-80-62*beta*t)**2+(62*(1-beta))**2)+62*abs(beta)*su(1+t*t)))for t in [-ta,ta]]
 half=max(vals);By=up(own_y+half+AA*ta)
 by_rows.append({'gate_local_z_mm':z,'seam_half_lateral_term_upper_mm':half,'own_half_tip_Y_projection_upper_mm':own_y,'bisector_transverse_correction_upper_mm':up(AA*ta),'tip_abs_Y_about_common_axis_upper_mm':By})
By=max(x['tip_abs_Y_about_common_axis_upper_mm']for x in by_rows)
Bzf=q(a['front_tip_abs_Z_about_common_datum_upper_mm']);Bzr=q(a['rear_tip_abs_Z_about_nominal_minus28_5_upper_mm']);Zsum=up(Bzf+Bzr)

Rlo=F(20);Rhi=F('20.5');tmin=F('2.4845');tmax=F('2.5');closed=F(21);opened=F(26);spacing=F('28.5');m=F('.625');stroke=F(20);front_start=F(12)
assert q(diag['selected_conservative_reference_radius_mm'])==tmin
assert q(diag['minimum_facet_plane_distance_mm'])>tmin
assert joint['whole_graph_reference'][1]['label'].startswith('current32gon')

def E_interval(case,R):
 A=q(case['barrier_circle_radius_mm']);h=q(case['all_holes_enclosing_Y_half_band_mm']);num=A*A-R*R
 assert num>0 and R>h
 denlo=sl(A*A-h*h)+sl(R*R-h*h);denhi=su(A*A-h*h)+su(R*R-h*h)
 return down(num/denhi),up(num/denlo)

def evaluate(case,bx):
 Elo,E=E_interval(case,Rlo);EhiLo,Ehi=E_interval(case,Rhi);h=q(case['all_holes_enclosing_Y_half_band_mm'])
 # hmax² derivative /2 = R+tmax−(closed−bx−E(R))*R/sqrt(R²−h²).
 # Interval lower>0 proves max atRhi continuously, not a two-point guess.
 Qmax=up(closed-bx-EhiLo)
 hmax_derivative_half_lower=down(Rlo+tmax-Qmax*Rhi/sl(Rlo*Rlo-h*h))
 assert hmax_derivative_half_lower>0
 Hmin=sl((Rlo+tmin)**2-(closed+bx)**2-(E+By)**2)
 Hmax=su((Rhi+tmax)**2-(closed-bx-Ehi)**2)
 pitch=sl((2*Rlo)**2-(2*E)**2)
 interval=[up(2*Hmax+Zsum),down(Hmin+pitch-Hmax-Zsum)]
 lower_margin=down(spacing-interval[0]);upper_margin=down(interval[1]-spacing)
 # At the common gate plane two opposing tips may have different axial
 # offsets. Include the largest such offset in the blocking distance;
 # do not silently treat the two tip centres as one transverse plane.
 Bzmax=max(Bzf,Bzr)
 hold_threshold=down(sl((Rlo+tmin)**2-(E+By)**2-Bzmax*Bzmax)-bx)
 close_margin=down(hold_threshold-closed)
 release=up(front_start+(Rlo+tmax+E+bx-closed)/m)
 open_margin=down(opened-bx-(Rlo+tmax+E))
 overlap=[up((opened-hold_threshold)/m),down(front_start+(hold_threshold-closed)/m)]
 return{'ball_case':case['label'],'Bx_required_upper_mm':bx,'Bx_currently_certified':False,'By_proved_conditionally_upper_mm':By,'Bz_front_rear_mm':[Bzf,Bzr],
 'E_max_upper_mm':E,'E_at_Rhi_upper_mm':Ehi,'Hmin_lower_mm':Hmin,'Hmax_upper_mm':Hmax,'Hmax_squared_derivative_half_lower_over_R_domain':hmax_derivative_half_lower,'touching_ball_pitch_lower_mm':pitch,
 'allowed_nominal_spacing_open_interval_mm':interval,'current_spacing_mm':spacing,'spacing_sufficient_margins_lower_mm':[lower_margin,upper_margin],
 'closed_radial_margin_lower_mm':close_margin,'fully_open_radial_margin_lower_mm':open_margin,
 'release_requires_common_output_u_strictly_greater_mm':release,'conditional_full_stroke_release_reserve_lower_mm':down(stroke-release),'both_gates_guaranteed_blocking_u_interval_mm':overlap,
 'sufficient_static_geometry_if_all_joint_conditions_hold':min(lower_margin,upper_margin,close_margin,open_margin)>0 and overlap[0]<overlap[1],
 'interpretation':'PASS of a sufficient conditional outer domain, not proof ofBx or force retention. Loosebounds are safe here because every represented feasible statepasses; no impossible combination isdeclared a realfailure.'}

cases=[evaluate(case,F(1))for case in b['final_cases']]
assert all(x['sufficient_static_geometry_if_all_joint_conditions_hold']for x in cases)
worst=cases[-1]

# Extend the prior head/root-cap contact reduction to bothballs versusALLfour
# tips and everyradialinsertionpose in the inheritedX20..27 domain.
E=q(worst['E_max_upper_mm']);firstlast=[q(x)for x in b['parked_state_and_refinement']['refined_both_Z_interval_mm']]
tipZrange=[-spacing-Bzr,Bzf]
zsep=up(max(abs(z-tz)for z in firstlast for tz in tipZrange))
vX=q(d['Rxx']);vY=q(cr['rod_axis_to_support_X_tan_upper']);vZ=q(a['projected_rod_slope_abs_upper'])
projection=up((E-20)*vX+(E+By)*vY+zsep*vZ)
carrierX=down(20+13*vX-F('4.5')*q(r['Rxy'])-4*q(r['Rxz']))
carrier_gap=down(carrierX-E-Rhi)
assert projection<0 and carrier_gap>0

slot=joint['whole_graph_reference'][1]
S=q(slot['whole_graph_slot_bound_upper_mm']);W=q(slot['fixed_window_half_room_upper_mm']);mw=up(m*W)
Jlimit=down(1-S);splitlimit=down(1-S-mw)

report={'status':'JOINT_BY_AND_NEW_SPLIT_GUIDE_STATIC_GATE_SUFFICIENCY_DEFINED_BX_CERTIFICATE_STILL_OPEN',
 'source_hashes':before,'by_projection':{'same_axis_formula':'tauY=(|Ryx|+sinBetaBound|Rzx|)/Rxx; ownY<=cb+11.6tauY. This uses the SAME rodK_i through its bodybearing, not mounting translation added to its tip.',
 'half_shell_formula':'At gatezg, beta=(zg+59)/62. SameH gives gatehalf-axis lateralterm with the locator-eliminated supportfunction; realbisector correction is−A tanalpha. Combine signedterms before outerbounding; preserveoneH forbothgates.',
 'tauY_upper':tau_y,'rows':by_rows,'all_tip_By_upper_mm':By,'manufactured_By_certified':False},
 'common_joint_domain':{'variables':['one bodyrelativeH','one commoncamC(u) for allfourpins','onecarrierK_i pertip','one actual finitepinaxisP_i percarrier','finiteV contacts and rod/bodyengagement'],
 'radial_definition':'Bx=sup over SAME declaredD02,u∈[0,20],i of abs(s_i*ex·T_i−r_gate(i)(u)), whereT_i=K_i(0); r_front=21+5clamp((u−12)/8), r_rear=26−5clamp(u/8). u isONEregisteredoutputphase, not chosenindependentlyperpin.',
 'required_constraint_for_functional_rows':'Bx<=1 at allfourfingers and allcommonu. Then nominalr in21..26 implies tipX20..27 and closes that antecedent of the carrier/ball/By/Bz conditional results. It is a sufficient condition to prove, NOT a result of the currentCAD.',
 'constraints':['The sameP_i finite D4 section liesinside the actual closedcam track underC and is fullyengaged across the section being used.','The sameP_i is retained by both finiteV faces ofK_i and the fixedwindow transformedbythe actualsupport/bodypose.','The sameK_i satisfies itscarrierY/Z lands and real2mmrod bearing. The sameH registersguide, shellholes andtipbodyframes.','Allnonpenetration and positivemechanicalcapture survivea stalledrearball. Force/preload/loaddeformation conditionsare not supplied by geometry alone.'],
 'frame_parallel_comparison_not_promoted':True},
 'exact_radial_residual_contract':{
 'coordinates':'C(q)=Qc*q+Tc in commonNcoordinates, withcamlocalYsection yq=10.5. Letq=(s(r(v)+20)+eta,10.5,zq), v=zg−zq, |eta|<=S32 if the actualfinitepin section and track prerequisites hold. Track law isconstant-continued outsideendpoints only asanoutergraph.',
 'pin_carrier_identity':'Pq=T_i+Oi*(v0+delta_i)+lambda_i*ai; v0=(20,3.125,0), Oi isthecarrierorthogonallinearmapincluding itsleft/rightmirror. delta_i isactualV-midplaneaxisoffset; ai isthatSAMEpinaxis unitvector, lambda_i goesfromtheV-midplane pointtoactualcamsection. Finitecoverage mustbeproved.',
 'exact_error':'s*T_i.x−r(u) = s*Qc_xx*eta + J_signed; J_signed=(Qc_xx−1)*(r(v)+20)+(r(v)−r(u))+s*Qc_xy*10.5+s*Qc_xz*zq+s*Tc_x+20−s*(Oi*v0).x−s*(Oi*delta_i).x−s*lambda_i*ai.x.',
 'primary_sufficient_certificate':'Define J_common=sup_D02,u,i |J_signed| on the SAMEcoupled poses. ThenBx<=S32+J_common. No independentframe,carrier,V orseam extreme is asserted simultaneously attainable.',
 'slot_S32_upper_mm':S,'J_common_required_upper_mm':Jlimit,'J_common_currently_proved_upper_mm':None,
 'optional_window_bookkeeping':{'window_half_room32_mm':W,'m_times_W32_upper_mm':mw,'remaining_after_legitimate_separation_mm':splitlimit,'condition':'Onlyafter proving a decomposition ofJ_signed intoa fixedwindow termboundedbymW32 PLUSa remainingjointresidual maythissmallerbudgetbeused. Existingparallelframe comparisondoesNOTestablishthesplitfor independentlyregistered supports. Do not silently insertmW32 into currentJ.'},
 'ideal_round_metal_reference_only':joint['whole_graph_reference'][0],
 'unproved_minimum_items':['Commoncam displacement/phase inN underactualtwo-support registration andfinitebands.','Samefinitepin inclination/engagement and lambda betweenactualV andcamsections.','RetainedVaxis offset/form, preload underload, and nonrigidradialdeflection. No manufacturing precision assigned.']},
 'static_sufficient_geometry':{'design_radii_mm':[Rlo,Rhi],'tip_inner_outer_radii_mm':[tmin,tmax],'tip_inner_reference':diag,
 'formulae':['Hmin=sqrt((Rmin+tmin)^2−(closed+Bx)^2−(Emax+By)^2). Choose the neareropposedtip; E isthisnewsplit-guide bound.','Hmax=max_R sqrt((R+tmax)^2−(closed−Bx−E(R))^2). Positive derivative certificate placesmaximumatRmax.','Pmin=sqrt((2Rmin)^2−(2Emax)^2).','2Hmax+Bzf+Bzr < Lgate < Hmin+Pmin−Hmax−Bzf−Bzr.','sqrt((closed+Bx)^2+(Emax+By)^2+max(Bzf,Bzr)^2)<Rmin+tmin; opened−Bx>max_R(R+tmax+E(R)).','R+E(R) strictlydecreaseswithR forfixedAstar,hstar; therefore releaseworstcase isRmin.'],
 'rows':cases,
 'same_H_correlation_handling':'The H-derivedBy/Bz/E enclosures may contain unattainable combinations. All such outercombinationsPASS in theBx<=1 rows, which is a valid sufficient guarantee on the smallercommon domain. No failurewitness is claimed, and no sensitivityoutside inheritedX20..27 is used ascertification.',
 'whole_finger_extension':{'all_four_tip_and_two_ball_axis_projection_upper_mm':projection,'carrier_ball_X_clearance_lower_mm':carrier_gap,'meaning':'For allcovered insertionposes, carriers cannotreachballs andconstantoutwardrodinterior isfartherthanitsroot. A radius2.5 tip/rootenvelope suffices fornoncollision, while2.4845 exposedheadreference isusedfor guaranteedblocking.'},
 'phase_coverage':'Rear movesinwardu0..8 whilefront remainsnominallyclosed to12. Static insertion inequalitiesuseworstradial inwardextent, so bound everyintermediatepose in theBx/By/Bz envelopes, notonlytheendpoint. Frontrelease followsu12..20. This doesnotdescribe impact, ballarrival, or friction.'},
 'release_scope':'The open-gate inequality establishes radial clearance for the bounded parked-ball domain and crossing of the common front gate plane. The inherited E is proved on the stated finite axial domain; this report does not silently extend it to the entire downstream flight or outlet transition.',
 'current_conclusion':{'new_E_and_By_force_static_failure':False,'static_enough_condition_exists':True,'current_common_Bx_certified':False,'actual_mechanical_failure_witness':None,'reason':'WithBx<=1 and the declarednormalcontact/domainconditions, newE/By/Bz retainpositive staticmargins. Bx and retainedloadedcapture remainunproved, so fullmechanicalsuccess cannotbeclaimed either.'},
 'stop_contract_boundary':{'conditional_functional_release_u_upper_mm':worst['release_requires_common_output_u_strictly_greater_mm'],'actual_F_or_H_or_lost_motion':None,'warning':'This conditional18.596710 value isnotan asbuiltstopsetting or certifiedcurrentF; do not replaceactualnullinputs. It mayreplacetheoldcoaxialexampleonlywithalltheseconditionsstated.'},
 'full_D02_closed':False,'manufacturing_release':False,'physical_acceptance':False,'all_sources_stable':all(sha(ROOT/p)==h for p,h in before.items())}
assert report['all_sources_stable']
(OUT/'report.json').write_text(json.dumps(conv(report),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(conv({'By':by_rows,'budget_case':worst,'J_common_limit':Jlimit,'window_split_only_if_proved':splitlimit,'whole_finger_projection':projection,'carrier_gap':carrier_gap}),ensure_ascii=False,indent=2))
