#!/usr/bin/env python3
"""One common half-shell transform, physical guide-axis datum, conditional Z bound.

No pose grid or optimizer; no CAD changes or exports. Writes this directory only.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,math,re,sys

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'analysis'))
from frame_y_guide_bound import upper as up,lower as down,sqrt_lower as sl,sqrt_upper as su

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(rel):return json.loads((ROOT/rel).read_text())
def q(v):return F(str(v))
def scalar(file,key):
 rows=re.findall(r'^\s*'+re.escape(key)+r'\s*=\s*([-+\d.]+)\s*;', (ROOT/'cad'/file).read_text(),re.M)
 assert len(rows)==1,(file,key)
 return F(rows[0])
def conv(v):
 if isinstance(v,F):return float(v)
 if isinstance(v,dict):return{k:conv(x)for k,x in v.items()}
 if isinstance(v,(tuple,list)):return[conv(x)for x in v]
 return v

paths={
 'joint':'output/current-joint-tolerance/report.json',
 'carrier':'output/current-joint-tolerance/carrier-body-coupling/report.json',
 'frame':'output/current-joint-tolerance/frame-finite-contact/report.json',
}
joint=read(paths['joint']);carrier=read(paths['carrier']);frame=read(paths['frame'])
assert not carrier['full_D02_closed'] and not frame['whole_D02_domain_certified']
files={ROOT/p for p in carrier['source_hashes']}|{ROOT/p for p in paths.values()}|{Path(__file__)}
for p,h in carrier['source_hashes'].items():assert sha(ROOT/p)==h,p
for p,h in frame['source_sha256'].items():assert sha(ROOT/p)==h,p
files|={ROOT/p for p in frame['source_sha256']}
before={str(p.relative_to(ROOT)):sha(p)for p in sorted(files)}

assert scalar('parameters.scad','gate_spacing')==F('28.5')
assert scalar('parameters.scad','guide_id')==F('42.5')
assert scalar('parameters.scad','guide_start_z')==F(-80)
assert scalar('parameters.scad','guide_length')==F(104)
seam=(ROOT/'cad/feeder-seam-candidate.scad').read_text()
assert 'seam_locator_y = [40,-40]' in seam and 'seam_locator_z = [-59,3]' in seam
assert 'positive?0:-100' in seam and 'if(positive && index==1)' in seam

# e=(p1-p0)/L=(-80,62)/L; n=J e=(-62,-80)/L.
L2=F(10244);Llo=sl(L2)
seam_case=joint['seam_registration']['cases'][1]
c=q(seam_case['per_locator_transverse_center_room_upper_mm'])
sin_theta=up(2*c/Llo)
cos_theta=sl(1-sin_theta*sin_theta)
sin_alpha=su((1-cos_theta)/2)
cos_alpha=sl((1+cos_theta)/2)
tan_alpha=up(sin_alpha/cos_alpha)

# Exact common-H elimination precedes the disc support-function outer bound.
# q1-q0=2L sin(alpha)n, q1=lambda R(alpha)e+v1.
# lambda cos(alpha)=(q0-v1).e; A=(q0_z+q1_z)/4.
# Both gates haveY0, so the SAME A is present at both of them.
A=up(c/(4*Llo)*(su((124+80*tan_alpha)**2+6400)+80*su(1+tan_alpha*tan_alpha)))
lambda_bound=up(2*c/cos_alpha)
assert lambda_bound<F('.5')

# Tighten the body-local transverse-norm result to this common axial direction.
# The same rod axis is S_i R_i e_x; support/body roll psi is constrained by
# the two mounting axes, while half-shell roll is the same theta as above.
mc=q(joint['mount_registration']['cases'][1]['support_rotation_chord_upper'])
nr=carrier['new_result'];r=nr['matrix_abs_upper'];diag=nr['matrix_diagonal_lower']
beta_sin=up(mc+sin_alpha) # |sin(psi +/- alpha)| <= chord(psi)+sin|alpha|
tau_z=up((q(r['Rzx'])+beta_sin*q(r['Ryx']))/q(diag['Rxx']))
cb=q(nr['body_bore_radial_axis_room_upper_mm'])
D=F('31.6')-20
local_axial=up(cb+D*tau_z)
Bfront=up(local_axial+A)
spacing_contraction=up(F('28.5')*(1-cos_alpha))
Brear=up(Bfront+spacing_contraction)
assert Brear<1
axis_shift=up(A*tan_alpha)
guide_intersect_shift=up(A/cos_alpha)
remaining=down(1-Brear)

# A counterexample only to a UNIQUE ball-centre line: an aligned bore and a
# ball centre atY0 orY.5 both fit nominalR21.25, ballR20, atZ-14 (away from holes).
ball_witness={'scope':'Guide-only nominal rigid-sphere fit, not full mechanism or release witness',
 'half_shell_transform':'identity','ball_radius_mm':20,'centres_CAD':[[0,0,-14],[0,.5,-14]],
 'radial_ball_extent_mm':[20,20.5],'nominal_inner_guide_radius_mm':21.25,
 'axial_ball_extent_mm':[-34,6],'finite_cylindrical_guide_mm':[-80,24],
 'assertion':'Both entire spheres fit the uncut ideal enclosing guide bore; current inscribed polygon must additionally containR20.5. This proves the source defines a guide datum, not a unique ball-centre trajectory.'}
# Actual body bore uses OpenSCAD cylinder faceting, defaultfn96 fromparameters.
params=(ROOT/'cad/parameters.scad').read_text()
fn=re.findall(r'^\s*\$fn\s*=\s*(\d+)\s*;',params,re.M)
if fn:
 n=int(fn[0]);assert n>=32
 # Even inscribed32gonR21.25 is >20.5; outward cos lower below is rational.
 x=F('3.14159265359')/32
 cos32=down(1-x*x/2+x**4/24-x**6/720)
 inner=down(F('21.25')*cos32);assert inner>F('20.5')
 ball_witness['guaranteed_inscribed32gon_radius_lower_mm']=inner
 ball_witness['source_default_fn']=n
else:
 ball_witness['actual_mesh_fit_not_claimed_without_resolution']='No literalfn found; the nonuniqueness statement is ideal-source geometry only.'

needles=[('cad/feeder-body.scad','body_tube(guide_start_z,guide_length,guide_od,guide_id)'),('cad/feeder-body.scad','for(z=body_side_seat_z)'),('cad/feeder-body.scad','cylinder(h=120,r=finger_tip_radius+radial_print_clearance)'),('cad/feeder-seam-candidate.scad','seam_locator_y ='),('cad/feeder-seam-candidate.scad','seam_locator_z ='),('cad/feeder-seam-candidate.scad','if(positive && index==1)'),('cad/feeder-seam-candidate.scad','seam_halfspace(positive)'),('cad/parameters.scad','guide_start_z ='),('cad/parameters.scad','guide_length =')]
evidence=[]
for p,s in needles:
 hits=[{'path':p,'line':i+1,'text':line}for i,line in enumerate((ROOT/p).read_text().splitlines())if s in line]
 assert hits,(p,s)
 evidence.extend(hits)

report={
 'status':'COMMON_HALF_SHELL_AXIAL_BOUND_CONDITIONAL_NORMAL_SUBDOMAIN_NOT_FULL_D02',
 'source_hashes':before,'source_evidence':evidence,
 'reference_geometry':{
  'H':'Positive half is H(p)=Rx(theta)p+t relative to negative half; common seatedX0 plane. One theta,t applies to both gates, both locator axes and the positive inner guide.',
  'guide_axes':'Gminus(z)=(0,0,z); Gplus(z)=H(Gminus(z)), localz in[-80,24]. Nominal boreR21.25; actual guide is two finite half-cylinders with radial side openings.',
  'mu':'alpha=theta/2; ezM=Rx(alpha)ez; eyM=Rx(alpha)ey; M(z)=(Gminus(z)+Gplus(z))/2.',
  'A':'A=ezM dot(Gplus(z)-Gminus(z))/2 is independent ofz, because both gate axes and both guide axes have localY0.',
  'true_near_nominal_angle_bisector':'N(zeta)=M(0)+tan(alpha)*A*eyM+zeta*ezM. Same-z midpoint lineM(z) is parallel but is generally NOT the exact equidistant bisector. Transverse correction does not alter axial projections.',
  'gate_midpoints':'M(0) andM(-Lgate) have axial coordinates0 and-Lgate*cos(alpha); actual gate pairs straddle those planes by the SAME +/-A.',
  'ball_centre_not_forced_to_datum':True,
 },
 'common_variables_and_relations':[
  'p0=(40,-59),p1=(-40,3), L=sqrt10244, e=(-80,62)/L,n=Je. d_j=H(p_j)-p_j inYZ.',
  'At common seamX0: ||d0||<=c; d1=lambda*Rx(theta)e+v, ||v||<=c, |lambda|<=.5; oneH, not independent locator extrema.',
  'Rotate allYZ vectors by-alpha: q0=R(-alpha)d0, q1=R(-alpha)d1, v1=R(-alpha)v. Thenq1-q0=2L*sin(alpha)*n andq1=lambda*R(alpha)e+v1.',
  'The sameH giveslambda*cos(alpha)=(q0-v1).e. The slot longitudinal parameter is eliminated; its.5 travel is not added toZ.',
  'For localY0: A=(q0_z+q1_z)/4. Letk=e_z+tan(alpha)n_z; then4A=(ez+k*e).q0+(ez-k*e).v1.',
  'Taking the support of the two necessary discs AFTER this elimination gives |A|<=c/4*(sqrt((2e_z+tan(alpha)n_z)^2+n_z^2)+|n_z|sec(alpha)). A uniform angle bound usesabs(tan(alpha)); omittedtheta consistency only enlarges the set, so this is an outer bound, not an attained extremum.',
  'Each tip isTi,minus=p_g+e_i orTi,plus=H(p_g+e_i), with the SAME carrier/rodK_i and supportS_i as its finite guide and bearing constraints. Common-axis deviations are-A+ezM.e_i and+A+ezM.R(theta)e_i.',
  'Local rod slope in that axial projection is bounded bytauZ=(|Rzx|+sinBetaBound*|Ryx|)/Rxx, |sinBeta|<=mountRotationChord+sin|alpha|. This rotates one actual axis; it does not add a mounting-translation norm.',
  'At actual bearingX31.6, projectedaxis residual has magnitude<=cb. Tip axial residual isthat-(31.6-tipX)*projectedaxisSlope. Thus|tipZ-about-its-own-half-gate|<=cb+11.6tauZ on the inheritedtipX20..27 subdomain.',
  'Combine these projected linear forms with their sharedalpha envelope, preserving +/-A and its equality for both gate heights. Conservative scalar support islocalAxial+A. It is not oldseamNorm+oldmountNorm+guidePlay.',
 ],
 'numeric':{'seam_locator_disc_radius_upper_mm':c,'sin_theta_upper':sin_theta,'sin_alpha_upper':sin_alpha,'cos_alpha_lower':cos_alpha,'tan_alpha_upper':tan_alpha,'slot_lambda_abs_upper_from_common_H_mm':lambda_bound,'same_A_abs_upper_mm':A,'true_bisector_transverse_shift_from_midpoint_line_upper_mm':axis_shift,'finite_axis_intersection_local_z_shift_upper_mm':guide_intersect_shift,'support_rotation_chord_upper':mc,'axis_projection_sin_beta_upper':beta_sin,'projected_rod_slope_abs_upper':tau_z,'own_half_tip_axial_upper_mm':local_axial,'front_tip_abs_Z_about_common_datum_upper_mm':Bfront,'rear_tip_abs_Z_about_nominal_minus28_5_upper_mm':Brear,'projected_gate_spacing_lower_mm':down(F('28.5')*cos_alpha),'gate_spacing_contraction_upper_mm':spacing_contraction,'remaining_to_Bz1_lower_mm':remaining},
 'shared_cancellation':{'same_side_front_minus_rear':'A cancels exactly. The projected nominal separation isLgate*cos(alpha), plus the difference of that same-side carrier errors.','opposite_side_front_minus_rear':'The shared seam term is+/-2A, not two freely chosen per-gate seam errors.','common_global_drift':'Any whole-assembly rigid transformation movesN, gates and ball guide together; it cancels from all expressed relations.'},
 'finite_guide_interpretation':{'axis_domain_local_z_mm':[-80,24],'gate_axis_common_station_local_z_ranges':[[down(-guide_intersect_shift),up(guide_intersect_shift)],[down(F('-28.5')-guide_intersect_shift),up(F('-28.5')+guide_intersect_shift)]],'physical_wall_limit':'The datum comes from the real finite inner guide, not a display line. A cylinder-axis datum does not imply full cylindrical wall at radial side holes, nor that spheres follow the bisector exactly.','nonunique_ball_centre_witness':ball_witness},
 'necessary_remaining_conditions':['All carrier-body subdomain premises remain conditions, especiallytipX20..27, normal seatedX mounting planes, currentparallelgib and retained engagement. RadialBx is NOT proved here.','Full actual fabrication/form/load terms and differentialgib poses are not assigned zero by this digital nominal result. Their values remainunknown.','The two half-guides are not coaxial unlessH isidentity up to axialtranslation. ExistingfullcoaxialEmax andBy assumptions cannot be reused verbatim: need ball-centre envelope in the finite, split, rotated, side-opened lumen, at the actual parked-ball axial domain.','The half-axisbisector is a geometricdatum, not a measured gravity/airflow direction or unique ballcentreline. Dynamic/one-ball release is not certified.','Frame-finite-contact remains a separate sharedparallelhost comparison; this report doesnot use it as proof of true independentlyregisteredleft/right supports.'],
 'shape_load_budget':{'actual_inputs':None,'conditional_remaining_scalar_mm':remaining,'warning':'This remainder is not freely spendable across changes that invalidate the inherited finitecontact/normal-plane/engagement proof. Such changes must enter the same projected formulas before recomputing.'},
 'full_D02_closed':False,'radial_Bx_certified':False,'conditional_nominal_axial_Bz1_certified_on_declared_subdomain':True,'static_two_ball_function_recertified':False,'manufacturing_release':False,'physical_acceptance':False,
 'all_sources_stable':all(sha(ROOT/p)==h for p,h in before.items()),
}
assert report['all_sources_stable']
(OUT/'report.json').write_text(json.dumps(conv(report),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(conv(report['numeric']),ensure_ascii=False,indent=2))
