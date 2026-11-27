#!/usr/bin/env python3
"""Finite split-guide barrier proof for a normally parked rigid two-ball state.

No CAD change, optimizer, sampling substitute, slicing, or physical release.
Only this directory is written. All scalar bounds are rounded outward.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'analysis'))
from frame_y_guide_bound import upper as up,lower as down,sqrt_lower as sl,sqrt_upper as su

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def q(x):return F(str(x))
def conv(x):
 if isinstance(x,F):return float(x)
 if isinstance(x,dict):return{k:conv(v)for k,v in x.items()}
 if isinstance(x,(list,tuple)):return[conv(v)for v in x]
 return x
def lit(p,k):
 m=re.findall(r'^\s*'+re.escape(k)+r'\s*=\s*([-+\d.]+)\s*;', (ROOT/p).read_text(),re.M)
 assert len(m)==1,(p,k)
 return F(m[0])

axial_path='output/current-joint-tolerance/half-shell-axial-coupling/report.json'
axial=json.loads((ROOT/axial_path).read_text());a=axial['numeric']
carrier_path='output/current-joint-tolerance/carrier-body-coupling/report.json'
carrier=json.loads((ROOT/carrier_path).read_text());cr=carrier['new_result'];rm=cr['matrix_abs_upper'];rd=cr['matrix_diagonal_lower']
files={ROOT/p for p in axial['source_hashes']}|{ROOT/axial_path,ROOT/carrier_path,Path(__file__)}
for p,h in axial['source_hashes'].items():assert sha(ROOT/p)==h,p
before={str(p.relative_to(ROOT)):sha(p)for p in sorted(files)}
assert lit('cad/parameters.scad','guide_id')==F('42.5')
assert lit('cad/parameters.scad','guide_od')==47
assert lit('cad/parameters.scad','guide_start_z')==-80 and lit('cad/parameters.scad','guide_length')==104
assert lit('cad/parameters.scad','finger_tip_radius')==F('2.5')
assert lit('cad/parameters.scad','ball_min_d')==40 and lit('cad/parameters.scad','ball_max_d')==41
assert lit('cad/parameters.scad','guide_clearance_budget')==F('.25')
assert lit('cad/parameters.scad','radial_print_clearance')==F('.25')
assert re.search(r'^\s*\$fn\s*=\s*72\s*;', (ROOT/'cad/parameters.scad').read_text(),re.M)

c=q(a['seam_locator_disc_radius_upper_mm']);ca=q(a['cos_alpha_lower']);sa=q(a['sin_alpha_upper']);ta=q(a['tan_alpha_upper']);AA=q(a['same_A_abs_upper_mm']);Llo=sl(F(10244))
Bz=q(a['rear_tip_abs_Z_about_nominal_minus28_5_upper_mm'])
Rmin=F(20);Rmax=F('20.5');tipR=F('2.5');holeR=F('2.75')
# A simple explicit upperpi is sufficient for these small-angle Taylor bounds.
piHi=F('3.14159265359')
u=piHi/72;co72=down(1-u*u/2+u**4/24-u**6/720)
outer_in=down(F('23.5')*co72)

def b_bound(zeta_lo,zeta_hi):
 """Support bound after eliminating the SAMEH's slotlambda. Not free offsets."""
 assert zeta_lo<0<zeta_hi
 beta_lo=down((zeta_lo/ca+59)/62);beta_hi=up((zeta_hi/ca+59)/62)
 rows=[]
 # Norm of an affine vector is convex in beta forfixedt and in t forfixedbeta;
 # |beta|sqrt(1+t²) is likewise separatelyconvex. Rectangle corners suffice.
 for beta in [beta_lo,beta_hi]:
  for t in [-ta,ta]:
   v=up(c/(2*Llo)*(su((-80-62*beta*t)**2+(62*(1-beta))**2)+62*abs(beta)*su(1+t*t)))
   rows.append({'beta':beta,'tan_alpha':t,'b_abs_upper_mm':v})
 return max(x['b_abs_upper_mm']for x in rows),{'beta_interval':[beta_lo,beta_hi],'analytic_convex_corner_bounds':rows}

def circle_E(Astar,hstar,R):
 assert 0<hstar<R<Astar
 # Use the positive rationalized expression. E increases in A,h and fallsinR;
 # numerator exact, denominator rounded down gives the upper bound.
 den=sl(Astar*Astar-hstar*hstar)+sl(R*R-hstar*hstar)
 return up((Astar*Astar-R*R)/den)

def barrier_case(label,zlo,zhi,innerA):
 b,proof=b_bound(zlo,zhi)
 Astar=up(innerA/ca+b);hstar=up(holeR/ca+b)
 local_outer=up(Astar+b)
 # localZ=zeta/cosalpha +/- A/cosalpha +/-sinalpha(y +/-b).
 dz=up(AA/ca+sa*(Astar+b))
 zlocal=[down(zlo/ca-dz),up(zhi/ca+dz)]
 assert -80<zlocal[0]<zlocal[1]<24
 assert local_outer<outer_in
 E=circle_E(Astar,hstar,Rmin)
 assert E<Astar-hstar # strictinterior: cannot first leave circle through a gap
 return{'label':label,'held_ball_centre_common_Z_interval_mm':[zlo,zhi],'inner_radius_upper_mm':innerA,'hole_radius_upper_mm':holeR,'half_axis_separation_half_bound_mm':b,'b_support_proof':proof,
 'barrier_circle_radius_mm':Astar,'all_holes_enclosing_Y_half_band_mm':hstar,'actual_wall_local_radial_upper_mm':local_outer,'outer_wall_guaranteed_inscribed_radius_lower_mm':outer_in,'outer_wall_reserve_lower_mm':down(outer_in-local_outer),
 'all_barrier_points_local_Z_interval_mm':zlocal,'finite_cylinder_Z_reserves_mm':[down(zlocal[0]+80),down(24-zlocal[1])],
 'sphere_radius_interval_mm':[Rmin,Rmax],'ball_centre_transverse_norm_upper_mm':E,
 'radius_specific_analytic_values':[{'ball_radius_mm':R,'centre_norm_upper_mm':circle_E(Astar,hstar,R)}for R in [Rmin,F('20.25'),Rmax]],
 'bound_formula_for_each_R':'E(R)=[Astar²−R²]/[sqrt(Astar²−hstar²)+sqrt(R²−hstar²)]',
 'source_realization_note':'Barrier is a necessary wall constraint, not a reachable offset or a manufactured clearance measurement.'}

# Firstderive finitecentredomain fromcontactwith ANY actual printedfinger point.
# This avoids presuming the old E or ideal spherical-tip contact.
vxlo=q(rd['Rxx']);vz=q(a['projected_rod_slope_abs_upper'])
vy=q(cr['rod_axis_to_support_X_tan_upper'])
local_y_to_common_z=up(q(rm['Rzy'])+q(a['axis_projection_sin_beta_upper']))
carrier_z=up(28*vz+F('4.5')*local_y_to_common_z+4)
rod_z=up(14*vz+tipR)
Pz=max(tipR,carrier_z,rod_z)
first_broad=[-up(Bz+Pz+Rmax),up(Bz+Pz)]
both_broad=[-up(Bz+Pz+3*Rmax),first_broad[1]]
boot=barrier_case('bootstrap_full_finger_contact_budgeted_radius',*both_broad,F('21.5'))
E0=boot['ball_centre_transverse_norm_upper_mm']

# Ruleoutcarriercontact usinga realX bound, then ruleoutrodinteriorcontact.
carrier_xlo=down(20+13*vxlo-F('4.5')*q(rm['Rxy'])-4*q(rm['Rxz']))
ball_xhi=up(E0+Rmax)
carrier_clear=down(carrier_xlo-ball_xhi);assert carrier_clear>0
# Ownfront-holepoint half-axis displacement at zeta0 has |Y|=|b(0)|;
# use the larger fullworkingb plus bisectorshift as a safe outer bound.
tipY=up(q(cr['tip_transverse_YZ_norm_upper_mm_CURRENT_nominal_mesh'])+boot['half_axis_separation_half_bound_mm']+AA*ta)
zdist=up(max(abs(first_broad[0]),abs(first_broad[1]))+Bz)
ydist=up(E0+tipY)
rod_projection=up((E0-20)*vxlo+ydist*vy+zdist*vz)
assert rod_projection<0
# For constantrod cross-sectionlocalX0..14, negativeaxis projection means the
# nearestcross-section is atlocalX0. Contactthus liesinside the radius2.5
# sphere/root-cap envelope, evenifthe32gonroot is not inside the40gonhead.
first_refined=[-up(Bz+tipR+Rmax),up(Bz+tipR)]
both_refined=[-up(Bz+tipR+3*Rmax),first_refined[1]]
nominal=barrier_case('current_nominal_inner_radius',*both_refined,F('21.25'))
budget=barrier_case('conditional_inner_radius_plus_point25',*both_refined,F('21.5'))

needles=[('cad/feeder-body.scad','body_tube(guide_start_z,guide_length,guide_od,guide_id)'),('cad/feeder-body.scad','cylinder(h=120,r=finger_tip_radius+radial_print_clearance)'),('cad/feeder-body.scad','body_port(z,a)'),('cad/feeder-body.scad','side==1?33.5:-60'),('cad/feeder-body.scad','side==1?23.5:-33.5'),('cad/feeder-seam-candidate.scad','positive?0:-100'),('cad/feeder-seam-candidate.scad','seam_reservoir_segment(s,a[0],a[1],a[2],a[3])'),('cad/feeder-support-harness.scad','sh_y_cyl(x,z,-55,22,4.5)'),('cad/feeder-integrated-candidate.scad','if(!positive) seam_reservoir_cuts()'),('cad/cam-study.scad','cylinder(h=cam_carrier_inner_offset+1'),('cad/cam-study.scad','cube([cam_carrier_length,cam_carrier_width,cam_carrier_axial])'),('cad/feeder-pin-seat-revision.scad','module ps_carrier_local()')]
evidence=[]
for path,needle in needles:
 rows=[{'path':path,'line':i+1,'text':line}for i,line in enumerate((ROOT/path).read_text().splitlines())if needle in line]
 assert rows,(path,needle)
 evidence.extend(rows)

report={'status':'FINITE_SPLIT_GUIDE_BALL_CENTRE_OUTER_BOUND_FOR_NORMAL_PARKED_PAIR_CONDITIONAL_DOMAIN',
 'source_hashes':before,'source_evidence':evidence,'parent_axial_report_sha256':sha(ROOT/axial_path),
 'coordinates':'Same H and true near-nominal bisectorN fromhalf-shell-axial-coupling. WorldX is unchanged byRx(theta); commontransversecoordinate isy along eyM and axialcoordinatezeta along ezM.',
 'same_H_relations':[
  'Let b(zeta)=ay0−tan(alpha)zeta whereay0=eyM.t/2. At commonaxialzeta the two actual guide axes are y=+/-b; theirlocalcross-sections obey x²+cos²(alpha)(y−/+b)²=innerR², restrictedto respectiveX halfspaces.',
  'Usingq0,q1 fromthe same locator transform: q1−q0=2Lsin(alpha)n; beta=(zeta/cos(alpha)+59)/62; 2b=(1−beta)q0_y+beta q1_y.',
  'Eliminate SAMEslotlambda: lambda cos(alpha)=(q0−v1).e. In2b, the q0 coefficient is(e_y+beta*tan(alpha)n_y)e+(1−beta)n_y n; the v1 coefficient is−beta*tan(alpha)n_y e+beta n_y n.',
  '|b|<=c/(2L)*[sqrt((-80−62beta*tan(alpha))²+(62(1−beta))²)+62|beta|sec(alpha)]. This is a support-function outer bound aftercorrelated elimination, not addition ofindependent locator displacements.',
  'The bound is convex inbeta withtanalpha fixed and convex intanalpha withbeta fixed. Four rectanglecorners enclose the whole continuous axial/angle domain; they are not sampled physical poses or achievable maxima.',
 ],
 'continuous_wall_barrier_proof':[
  'For any sameH pose and any centreplanein the stated finiteinterval, useuniform bbar>=|b(zeta)| andcosalpha>=camin. LetAstar=Amax/camin+bbar andhstar=hmax/camin+bbar.',
  'At everypoint on commoncirclex²+y²=Astar², localradius sqrt(x²+cos²alpha(y−/+b)²)>=cosalpha(Astar−|b|)>=Amax. It isoutside eitherhalf actualinnercutter, onthe correct X half.',
  'The same localradius<=Astar+bbar, strictlybelow the actualouterpolygon guaranteed inscribed radius23.5cos(pi/72). Thus thepointis within guidewall thickness. LocalZformula andreported interval keep all suchpoints strictlywithin realcylinderZ[-80,24], awayfromtaperports.',
  'If |y|>=hstar then |localY|=cosalpha|y−/+b|>=hmax. BothroundX fingerholes arethereforeexcluded, regardless oftheirlocalZ centres or half-shell axialshift. Theirunion neverextendsoutside thisenlargedY band.',
  'The seatedX0 halfspace seam haszero Xgap. Both reconstructed annularbands include the seam boundary; all othercurrent cutters areoutside thisrealinner-guide material region. A gasket/openXseam isNOTcovered.',
  'Consequently actualsolid providesallcirclearcs outside |y|<hstar at the ball-equatorial plane. A rigidball cuts thisplane in a radiusR disc. Inthenormal interior component the surviving arcs force e<=sqrt(Astar²−hstar²)−sqrt(R²−hstar²).',
  'All-direction proof: letgamma=asin(hstar/Astar). For centreazimuththeta nearanX opening, boundary distanceusesdelta=max(0,gamma−|theta|), so e<=Astar cosdelta−sqrt(R²−Astar²sin²delta). It increases withdelta forAstar>R; maximumatdelta=gamma. Elseanintactradialarc givesAstar−R. This rederives the circle-rim lemma for a NEWmaterialbarrier, ratherthan reusing oldphysicalcoaxialE.',
  'Theboundisstrictlyinside the bootstrapinterior circle. A continuousnormallyinserted ball cannotfirst leave thiscomponent within thecertified axialrange withoutpenetrating one ofthesurviving arcs. Arbitraryoutsideballs/endescapeareexcluded.',
 ],
 'parked_state_and_refinement':{'state_conditions':['One rigidball is stationary against an actualfrontfinger; itscentre is upstream of the supportingcontactpoint incommonaxialcoordinate. A secondrigidball is upstream and touches it. Thisis the intended staticparked-pair state, not a claim about arriving or flyingballs.','Bothradii lie20..20.5 as CADdesigninputs, not measured40+size. Bothballs belong to normalinteriorguidecomponent; sourcecut and seatedseam assumptions hold.','Inheritedcarrier/axialnormalbranch, tipX20..27, parallelgib andrigidshape assumptions remainconditions; Bx itselfisnotderived.'],
 'full_finger_outer_geometry':{'sphere_radius':tipR,'rod_local_X':[0,14],'carrier_local_box':[[13,28],[-4.5,4.5],[-4,4]],'carrier_local_Y_to_common_Z_component_abs_upper':local_y_to_common_z,'whole_finger_axial_extent_about_tip_upper_mm':Pz},
 'bootstrap_first_ball_Z_interval_mm':first_broad,'bootstrap_both_Z_interval_mm':both_broad,'bootstrap_barrier':boot,
 'contact_refinement':{'carrier_world_abs_X_lower_mm':carrier_xlo,'ball_world_abs_X_upper_mm':ball_xhi,'carrier_ball_X_separation_lower_mm':carrier_clear,'front_tip_abs_Y_bound_mm':tipY,'ball_minus_tip_dot_outward_rod_axis_upper_mm':rod_projection,'interpretation':'Carrier cannotcontactthisball. Negativeaxisprojection makesconstantrodsectiondistance strictlyincrease forlocalX>0, so anyfirstnonpenetrating rod/head contactis in the tip/rootcap radius2.5 envelope. Thisdoesnotassumethe32gonrodroot iscontainedinthe40gonhead.'},
 'refined_first_ball_Z_interval_mm':first_refined,'refined_both_Z_interval_mm':both_refined,'derivation':'Ifallcontactpoints lie |zeta|<=Bz+Pz and upstreamcontact holds, firstcentre in[-Bz−Pz−Rmax,Bz+Pz]; touchingsecondadds atmost2Rmaxupstream. StartwithwholefingerPz, deriveE0, excludeothercontacts, thenusePz=2.5. Two finiteanalytical passes, no optimizer or infiniteiteration.'},
 'final_cases':[nominal,budget],
 'wall_cut_audit':['body_inner_guide radialholes aretheonlyguidecuts in theverifiedinteriorZ range; taperbody_ports occuroutside[-80,24].','body_side_cuts rectangularcarrieropening begins|X|33.5 andshortbearingcutterbegins|X|23.5, beyondthestatedbarrierradialrange.','splitfasteners andseamlocatorcuts liearound|Y|40, outsideguide. Reservoirgrooves inthiscylindricalZsegment areatmeanbodyradius33.5, not innerguideR21.25.','ic_host onlyunionsoutlet/harness additions before sh_host_cuts andseamreservoir recuts; sh cutters haveY<=-33. Allareoutsidethebarrierlocalradius<22.0 region. Addedmaterial mayonlyrestrictballspace further.'],
 'parameter_limits':{'nominal_hole_radius_not_measured':holeR,'actual_ball_radius_values':None,'actual_guide_inner_outer_form_bounds':None,'actual_seam_gap_or_form':None,'budget_case_warning':'Amax21.5 is guide_clearance_budget input; it is valid only if an actual fullwall remains outto the reportedradius andholesremain insidehmax2.75. The sourceouterpolygon providesnominalmaterial, not an asprinted guarantee.'},
 'not_closed':['FourfingerBy andradialBx, Vpreload/loadedshape, commoncamendpoint phase, andactualmaterials arestilloutside thisball-only bound.','No dynamicarrival/airflow/friction/ballcompression or exactone-release claim. The held-state assumptions are explicit.','These circlesenclosefeasiblecentres; everypointinthecircle neednotbe attainable, andfailedtests over thiscirclewouldnotprovea realcollision.','No claim a physicalball followsN or thateitherhalf iscoaxialwiththeother. OldEmax1.513367 isNOT used.'],
 'finite_conditional_ball_centre_domain_closed':True,'full_D02_closed':False,'static_two_ball_function_recertified':False,'manufacturing_release':False,'physical_acceptance':False,
 'all_sources_stable':all(sha(ROOT/p)==h for p,h in before.items())}
assert report['all_sources_stable']
(OUT/'report.json').write_text(json.dumps(conv(report),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(conv({'bootstrap_Z':both_broad,'refined_Z':both_refined,'carrier_clearance':carrier_clear,'rod_projection':rod_projection,'final_cases':[{k:v for k,v in case.items()if k not in ['b_support_proof']}for case in [nominal,budget]]}),ensure_ascii=False,indent=2))
