#!/usr/bin/env python3
"""Finite common cam / same carrier-pin intersection; conditional nominal domain.
Only writes this new evidence directory. No CAD mutation or sampled optimizer.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,math,sys

ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'analysis'))
from frame_y_guide_bound import upper as up,lower as down,sqrt_lower as sl,sqrt_upper as su
def q(x): return F(str(x))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def convert(x):
 if isinstance(x,F): return float(x)
 if isinstance(x,dict): return {k:convert(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)): return [convert(v) for v in x]
 return x

paths={k:ROOT/('output/current-joint-tolerance/'+v+'/report.json') for k,v in {
 'pin':'common-radial-closure','carrier':'carrier-body-coupling',
 'frame':'frame-finite-contact','gate':'gate-ball-joint-review'}.items()}
reports={k:json.loads(p.read_text()) for k,p in paths.items()}
files={Path(__file__),*paths.values()}
for report in reports.values():
 for p,h in report.get('source_hashes',report.get('source_sha256',{})).items():
  assert sha(ROOT/p)==h,p
  files.add(ROOT/p)
hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}
evidence=[]
for name,needles in {
 'cad/feeder-frame-y-guide.scad':['yg_face=24.1','yg_pitch=0','yg_bands=','yg_tooth_x=','yg_pocket_clear=.2'],
 'cad/feeder-cam-guide-revision.scad':['cg_setting=.9','ONE X master','cg_contact_y0=21','cg_end_recess=.4'],
 'cad/feeder-supports.scad':['support_radial_y1 = 7.25','support_rail_x0 = 54','support_rail_x1 = 58','support_rail_y0 = 20','support_rail_y1 = 24','Open-ended front window','support_radial_x1-(finger_closed_center_r+cam_follower_offset)'],
}.items():
 lines=(ROOT/name).read_text().splitlines()
 for needle in needles:
  hits=[{'path':name,'line':i+1,'text':v} for i,v in enumerate(lines) if needle in v]
  assert hits,(name,needle)
  evidence.extend(hits)
pn=reports['pin']['new_numeric']; Rn=reports['carrier']['new_result']
ra={k:q(v) for k,v in Rn['matrix_abs_upper'].items()}
rd={k:q(v) for k,v in Rn['matrix_diagonal_lower'].items()}
cy=q(Rn['carrier_reference_abs_Y_upper_mm']);cz=q(Rn['carrier_reference_abs_Z_upper_mm'])
w=q(pn['slope_norm_upper']);rhoN=up(su(2)*q(pn['rho_from_32gon_mm']))
def delta(y): return up((y-F('1.75'))*w+w*w+rhoN)

# Both actual guide systems are used in their OWN seated support frame.
# Support-to-half and half-to-half rotations are about the same X direction.
# Thus |Qxy|, |Qxz| and Qxx agree between the two canonical mirrored frames.
# Four actual Y-ray stations per side lie in the tooth, including +/- .2 float.
gy=F('.1');gx=F('.1');Lx=F('36.7');Ly=F('36.58');spanX=F(3)
a=up(gy/spanX);c=up(gy/Ly);bx_right=up(gx/Lx)
def matrix(zx, shared_xz=None):
 zz=sl(1-zx*zx-c*c)
 yz=up(zx*a+c)
 yx=up((yz*zx+a)/zz)
 xz=up(yx*c+zx) if shared_xz is None else shared_xz
 xx=sl(1-yx*yx-zx*zx);yy=sl(1-a*a-c*c)
 return dict(xy=a,xz=xz,yx=yx,yz=yz,zx=zx,zy=c,xx=xx,yy=yy,zz=zz)
right=matrix(bx_right)
# Cofactors: |Qzx_left| <= |Qxy Qyz|+|Qxz Qyy|;
# |Qyz_left| <= |Qzx_left Qxy|+|Qxx Qzy_left|.
bx_left=up((right['xz']+a*c)/(1-a*a))
left=matrix(bx_left,right['xz']);left['xx']=right['xx']

def finite_frame(M,side):
 dx=F('.1') if side=='right' else F('.2')
 dy=gy
 # Centred coordinates h=(56,22,-15); Q maps local to own support.
 # The same inverse translation d'=Q^T d is bounded by real X/Y rays.
 phase=up(3*(M['zx']+M['zy']))
 dzp_lo=-up((phase+M['zx']*dx+M['zy']*dy)/M['zz'])
 dzp_hi=up((20+phase+M['zx']*dx+M['zy']*dy)/M['zz'])
 dzp=max(-dzp_lo,dzp_hi)
 y_ray_x_error=up(F('1.5')*(1-M['xx'])+F('2.1')*M['yx']+F('18.29')*M['zx']+dx)
 x_ray_y_abs=up(F('2.2')*M['xy']+F('18.35')*M['zy']+dy)
 rail_z_lo=-up(F('2.2')*M['xz']+F('2.1')*M['yz']+F('18.35')+dzp_hi)
 rail_z_hi=up(F('2.2')*M['xz']+F('2.1')*M['yz']+F('18.35')-dzp_lo)
 world_dx=up(dx+M['xy']*dy+M['xz']*dzp)
 world_dy=up(M['yx']*dx+dy+M['yz']*dzp)
 stop_x_error=up(3*(1-M['xx'])+3*M['xy']+40*M['xz']+world_dx)
 stop_y_error=up(3*M['yx']+3*(1-M['yy'])+40*M['yz']+world_dy)
 margins={
  'Y_ray_to_rail_X_edge':down(F('.5')-y_ray_x_error),
  'X_ray_to_rail_Y_edge':down(2-x_ray_y_abs),
  'rail_Z_lower_end':down(rail_z_lo+F('49.5')),
  'rail_Z_upper_end':down(31-rail_z_hi),
  'stop_X_strip':down(F('.8')-stop_x_error),
  'stop_outer_Y_strip':down(F('1.5')-stop_y_error),
  'stop_internal_window_Y':down(F('.8')-stop_y_error),
 }
 assert min(margins.values())>0,margins
 # Use stronger elementary bound cos3deg <= 1-(pi/60)^2/2+(pi/60)^4/24.
 pi_lo=F('3.141592653589793238462643383279')
 angle=pi_lo/60; cos3_upper=1-angle*angle/2+angle**4/24
 assert M['xx']+M['yy']+M['zz']>1+2*cos3_upper
 return {'side':side,'matrix_abs_upper':{k:M[k] for k in ('xy','xz','yx','yz','zx','zy')},
  'matrix_diagonal_lower':[M['xx'],M['yy'],M['zz']],
  'axis_angle_deg_diagnostic':math.degrees(math.acos(float((M['xx']+M['yy']+M['zz']-1)/2))),
  'inverse_translation_X_interval_mm':[0,dx] if side=='right' else [-dx,dx],
  'inverse_translation_Y_interval_mm':[0,dy],
  'inverse_translation_Z_interval_mm':[dzp_lo,dzp_hi],
  'translation_Z_interval_mm':[-phase,20+phase],
  'finite_margins_mm':margins,'finite_rail_local_Z_centered_interval_mm':[rail_z_lo,rail_z_hi],
  'stop_XY_error_upper_mm':[stop_x_error,stop_y_error]}
fr={s:finite_frame(M,s) for s,M in [('right',right),('left',left)]}

def intersect(M):
 # v=R^T Q e_y in carrier coordinates; use the SAME w/line, not free lambda.
 vx=up(M['xy']+ra['Ryx']+M['zy']*ra['Rzx'])
 vz=up(M['xy']*ra['Rxz']+ra['Ryz']+M['zy'])
 vp=su(vx*vx+vz*vz)
 vy=down(M['yy']*rd['Ryy']-M['xy']*ra['Rxy']-M['zy']*ra['Rzy'])
 den=down(vy-vp*w)
 assert den>0
 # Evaluate plane residual at y=10.5, then solve its one affine root.
 # 3|Qxy|+36.58|Qzy|<=gy: one joint budget, not two free angular extremes.
 ax=up(16+20*(1-rd['Rxx'])+F('10.5')*ra['Rxy'])
 az=up(15+cz+F('1.5')*ra['Rzx']+F('10.5')*ra['Rzy'])
 joint_angle_term=up(gy*max(ax/spanX,az/Ly))
 yterm=up(cy+F('1.5')*ra['Ryx']+F('10.5')*(1-rd['Ryy']))
 residual=up(joint_angle_term+F('11.5')*(1-M['yy'])+gy+yterm+vp*delta(F('10.5')))
 shift=up(residual/den)
 ylo=down(F('10.5')-shift);yhi=up(F('10.5')+shift)
 # For the actual oblique cam mid-plane, not only its axis centre:
 # support vector eY-v/(v.d) is perpendicular to d=(wx,1,wz).
 section_offset=up(2*vp*su(1+w*w)/den)
 slab_lo=down(ylo-section_offset);slab_hi=up(yhi+section_offset)
 pinlo,pinhi=map(q,pn['full_shoulder_cross_section_Y_interval_mm'])
 margins=[down(slab_lo-pinlo),down(pinhi-slab_hi)]
 assert min(margins)>0
 # Support-Y interval of the SAME intersection; dxy is a correlated set,
 # its norm outer bound is used only for a universal enclosure.
 dmax=delta(yhi)
 py_error=up(cy+F('1.5')*ra['Ryx']+yhi*(1-rd['Ryy'])+su(ra['Ryx']**2+ra['Ryz']**2)*dmax)
 pylo=down(ylo-py_error);pyhi=up(yhi+py_error)
 bxerr=up(20*(1-rd['Rxx'])+yhi*ra['Rxy']+su(1+ra['Rxz']**2)*dmax)
 return {'axis_y_star_interval_mm':[ylo,yhi], 'whole_midplane_pin_section_carrier_Y_interval_mm':[slab_lo,slab_hi],
  'full_shoulder_reserve_mm':margins,'root_denominator_lower':den,'root_residual_at_nominal_Y10_5_abs_upper_mm':residual,
  'joint_frame_Y_normal_contribution_upper_mm':joint_angle_term,'v_XZ_norm_upper':vp,
  'carrier_Y_excursion_of_oblique_cross_section_upper_mm':section_offset,
  'same_intersection_support_Y_interval_mm':[pylo,pyhi],
  'axis_to_tip_X_offset_minus20_abs_outer_mm':bxerr,
  'axis_delta_at_max_y_star_norm_upper_mm':dmax}
intersections={s:intersect(M) for s,M in [('right',right),('left',left)]}

# Fixed support window: actual Y=7 plane, not a window point independent of pin.
rperp=su(ra['Ryx']**2+ra['Ryz']**2)
wd=down(rd['Ryy']-rperp*w)
wr=up(cy+F('1.5')*ra['Ryx']+7*(1-rd['Ryy'])+rperp*delta(F(7)))
wlo=down(7-wr/wd);whi=up(7+wr/wd)
wsection=up(2*rperp*su(1+w*w)/wd)
assert wlo-wsection>q(pn['full_shoulder_cross_section_Y_interval_mm'][0])
assert whi+wsection<q(pn['full_shoulder_cross_section_Y_interval_mm'][1])
sx=up((ra['Rxy']+w*su(1+ra['Rxz']**2))/wd)
sz=up((ra['Rzy']+w*su(ra['Rzx']**2+1))/wd)
window_r=q(reports['pin']['finite_contact_backsubstitution']['guaranteed_pin_inner_radius_mm'])
zeta=up(F('2.25')-window_r)
wxerr=up(20*(1-rd['Rxx'])+whi*ra['Rxy']+su(1+ra['Rxz']**2)*delta(whi))
window_axis_X=[down(40-wxerr),up(47+wxerr)]
witness_X_offset=up(window_r*sx*sz)
window_X_margins=[down(window_axis_X[0]-witness_X_offset-F('38.75')),down(58-window_axis_X[1]-witness_X_offset)]
assert min(window_X_margins)>0

# Exact inverse-X radial identity; combine the same pin/window phase first.
# The outer row is a sufficient inequality, NOT an attainable failure witness.
m=F('.625');S=q(reports['gate']['exact_radial_residual_contract']['S32_upper_mm']) if 'S32_upper_mm' in reports['gate']['exact_radial_residual_contract'] else q('0.397123268976')
budget=q(reports['gate']['exact_radial_residual_contract']['J_common_required_upper_mm'])
def radial(M,s):
 i=intersections[s];pylo,pyhi=i['same_intersection_support_Y_interval_mm'];
 yr=max(abs(pylo-22),abs(pyhi-22)); yw=max(abs(pylo-7),abs(pyhi-7))
 Xdiff=up(16+i['axis_to_tip_X_offset_minus20_abs_outer_mm'])
 # Exact signed coefficients: (Qzx+kQzz)*[zeta+sz*(pMY-7)] and
 # (Qyx+kQyz)*(pMY-22), k has the gate-specific sign and |k|<=m.
 terms={
 'finite_X_datum':F('.1') if s=='right' else F('.2'),
 'same_carrier_pin_X_offset':i['axis_to_tip_X_offset_minus20_abs_outer_mm'],
 'frame_XX_scale':up((1-M['xx'])*15),
 'combined_frame_Y_coefficient':up((M['yx']+m*M['yz'])*yr),
 'gate_reference_frame_Z':up(M['zx']*15+m*15*(1-M['zz'])),
 'same_window_to_midplane_Z':up((M['zx']+m)*(zeta+sz*yw)),
 'frame_inverse_Z_X_coefficient':up(m*M['xz']*Xdiff),
 }
 numerator=sum(terms.values())
 # Original forward identity uses Qxx*eta, not eta/Qxx. Keep that difference.
 extra=up(S*(1/M['xx']-M['xx']))
 j0=up(numerator/M['xx']+extra);gain=up(m/M['xx'])
 return {'same_joint_identity_terms_upper_mm':terms,
  'J_common_outer_at_Lambda_zero_mm':j0,'phase_residual_gain_upper':gain,
  'sufficient_conditional_inequality':'J_i <= J0_i + phase_gain_i * Lambda_i, where Lambda_i bounds |dprime_i.z-u| in the SAME C/S/u joint domain.',
  'remaining_J_budget_after_this_outer_mm':down(budget-j0),
  'this_outer_certifies_original_J_budget_even_at_Lambda_zero':j0<=budget,
  'unknown_Lambda_i_mm':None,'actual_feasible_failure_witness':None}
radials={s:radial(M,s) for s,M in [('right',right),('left',left)]}

def dot(a,b):return sum(x*y for x,y in zip(a,b))
def add(a,b):return [x+y for x,y in zip(a,b)]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def mv(A,x):return [dot(row,x) for row in A]
def tr(A):return [list(x) for x in zip(*A)]
def mm(A,B):return [[dot(row,col) for col in tr(B)] for row in A]
def rot(axis,t):
 co=(1-t*t)/(1+t*t);si=2*t/(1+t*t)
 if axis==0:return [[F(1),F(0),F(0)],[F(0),co,-si],[F(0),si,co]]
 if axis==1:return [[co,F(0),si],[F(0),F(1),F(0)],[-si,F(0),co]]
 return [[co,-si,F(0)],[si,co,F(0)],[F(0),F(0),F(1)]]
def gate_radius(rear,u):
 clamp=lambda x:min(F(1),max(F(0),x))
 return 26-5*clamp(u/8) if rear else 21+5*clamp((u-12)/8)
algebra_tests=[]
for rear,u,vphase in [(True,F(4),F('4.3')),(False,F(15),F('14.7')),(False,F(8),F(9))]:
 # Arbitrary rational rigid transforms test only exact algebra, not feasibility.
 Q=mm(rot(2,F(1,90)),rot(0,F(-1,600)))
 R=mm(rot(1,F(-1,100)),rot(2,F(1,120)))
 cen=[F(56),F(22),F(-15)];ym=F('3.125');ystar=F('10.3');g=F('-28.5') if rear else F(0)
 wc=[F('.01'),F('-.012')];delta0=[F('.02'),F('-.01')]
 dstar=[delta0[j]+(ystar-ym)*wc[j] for j in range(2)]
 tipx=gate_radius(rear,u)+F('.2')
 carrier_c=[tipx+F('21.5')*R[0][0],F('.03'),g-F('.04')]
 p=add(carrier_c,mv(R,[F('-1.5')+dstar[0],ystar,dstar[1]]))
 eta=F('.1');camq=[gate_radius(rear,vphase)+20+eta,F('10.5'),g-vphase]
 d=sub(sub(p,cen),mv(Q,sub(camq,cen)));dp=mv(tr(Q),d)
 axis=mv(R,[wc[0],F(1),wc[1]])
 n=[row[1] for row in Q]
 pym=add(carrier_c,mv(R,[F('-1.5')+delta0[0],ym,delta0[1]]))
 root=ym+(F('-11.5')+dp[1]-dot(n,sub(pym,cen)))/dot(n,axis)
 assert root==ystar
 pw=add(p,[a*(7-p[1])/axis[1] for a in axis]);zeta_test=pw[2]-g
 sztest=axis[2]/axis[1];lam=dp[2]-u;k=(gate_radius(rear,vphase)-gate_radius(rear,u))/(vphase-u)
 bx=p[0]-tipx;DX=p[0]-56;DYr=p[1]-22;DYw=p[1]-7
 phase_formula=lam+(g+15)*(1-Q[2][2])-Q[0][2]*DX-Q[1][2]*DYr-Q[2][2]*(zeta_test+sztest*DYw)
 numerator=eta+dp[0]-Q[0][0]*(bx-20)+(1-Q[0][0])*(gate_radius(rear,u)-36)-(Q[1][0]+k*Q[1][2])*DYr-Q[2][0]*(g+15)+k*(g+15)*(1-Q[2][2])-(Q[2][0]+k*Q[2][2])*(zeta_test+sztest*DYw)-k*Q[0][2]*DX+k*lam
 assert phase_formula==vphase-u
 assert numerator==Q[0][0]*(tipx-gate_radius(rear,u))
 algebra_tests.append({'rear':rear,'u':u,'v':vphase,'root_error_exact':0,'phase_identity_error_exact':0,'radial_identity_error_exact':0})

result={
 'status':'REAL_OBLIQUE_CAM_MIDPLANE_FINITE_PIN_COVERAGE_PROVED_ON_DECLARED_NOMINAL_BRANCH_COMMON_RADIAL_NOT_CERTIFIED',
 'source_hashes':hashes,
 'source_evidence':evidence,
 'new_result':'Both independent support coordinates can be used without asserting a shared support datum. Actual same-pin cam-midplane roots and their entire oblique cross-sections lie within the finite shoulder. Common radial residual remains unclosed.',
 'coordinates':{
  'support':'Each seated half/support has common X normal; each canonical side mirrors X. All half/support relative registration rotations are about X, not set to zero.',
  'frame':'C_i(q)=h+d_i+Q_i(q-h), h=(56,22,-15); dprime_i=Q_i^T d_i. All C_i derive from ONE physical cam C and the corresponding actual support transforms.',
  'carrier':'p_i(y) = (Xtip+21.5Rxx,cY,g+cZ)+R[-1.5+delta_x(y),y,delta_z(y)]. delta(y)=delta0+(y-3.125)w is the SAME nut/V-constrained pin.',
  'normal':'n=Q_i e_y; v=R_i^T n; d_pin=(wx,1,wz).',
  'root':'y*=3.125 + [-11.5 + dprime_i.y - n dot(p_i(3.125)-h)]/[n dot(R_i d_pin)]. Equivalently n dot(p_i(y*)-h)-dprime_i.y=-11.5.',
 },
 'domain_conditions':[
  'Existing carrier radial guard Xtip in[20,27], seated common-X mounting normals, rigid nominal parts, parallel carrier gib setting.9 and the inherited normal contact branch. This remains conditional until Bx closes the guard.',
  'Both Y frame gibs parallel, effective gap<=.1; right X-master gap<=.1; left original total X gap .4. These are source nominal comparison inputs, NOT measured FDM accuracy or a proof about arbitrarily tilted gibs.',
  'From the nominal installed continuous branch, frame/support rotations stay initially below3deg and real station/stop material is covered. Strict finite reentry and trace bounds prevent a first exit while the stated contacts remain retained.',
  'All nominal nut/V seated-contact requirements from common-radial-closure; actual thread play/form/preload/deformation remain unknown.',
 ],
 'finite_frame_proof':{
  'Y_stations_support_X':[54.5,57.5],'Y_stations_support_Z':[-33.29,3.29],
  'Y_tooth_float_included_mm':.2,'fixed_Y_station_X_reserve_mm':.1,'fixed_Y_station_Z_reserve_mm':.01,
  'necessary_joint_Y_inequality':'4+3|Qxy|+36.58|Qzy| <= 4.1 Qyy for EACH side, at four finite stations.',
  'right_master_X_inequality':'4+36.7|Qzx_right| <= 4.1 Qxx_right; X rays at supportY22,Z[-33.35,3.35].',
  'same_X_normal_coupling':'Because all support transforms are Rx plus YZ translation, |Qxy|, |Qxz| and Qxx are shared. Qzx_left <= (Qxz_right_bound + |Qxy| |Qzy_left|)/(1-|Qxy|^2), by two cofactor identities. No alignment of the independent support origins/rolls is assumed.',
  'inverse_translation_intervals':'Real X/Y plane inequalities eliminate dprime.x/y. In centred h coordinates, right dprime.x in[0,.1], left in[-.2,.2], both dprime.y in[0,.1].',
  'stops':'Real local stop-face corners (relative h) X/Y=+/-3,Z20/-40 imply d.z in[-3(|Qzx|+|Qzy|),20+3(|Qzx|+|Qzy|)]. Same derived transforms put all selected corners back in real stop strips and outside internal windows.',
  'moving_rail_Z_relative_h':[-49.5,31],
  'rows':fr,
 },
 'same_pin_midplane_intersections':intersections,
 'fixed_window':{'support_Y':7,'carrier_y_at_axis_crossing_mm':[wlo,whi],
  'whole_window_cross_section_carrier_Y_mm':[down(wlo-wsection),up(whi+wsection)],
  'axis_X_interval_mm':window_axis_X,'window_Z_wall_support_witness_X_margins_mm':window_X_margins,
  'same_axis_support_slopes_upper':{'sx':sx,'sz':sz},'zeta_abs_upper_mm':zeta,
  'same_line_identity':'pM.z = g + zeta + sz_signed*(pM.y-7). zeta is the SAME pin intersection with the finite fixed window, not an independent phase assigned to the cam.',
  'material':'Y7 lies within the fixed support material toY7.25; window walls at g+/-2.25 retain support points within X[38.75,58]. Actual oblique shoulder section and finite X margins were checked.',
 },
 'radial_elimination':{
  'definitions':'bX=pM.x-Ttip.x; DeltaX=pM.x-56; DeltaYr=pM.y-22; DeltaYw=pM.y-7; v=g-qz; k=(r(v)-r(u))/(v-u), k=0 when v=u; front k in[0,.625], rear k in[-.625,0]. lambda_i=dprime_i.z-u.',
  'same_phase':'v-u=lambda_i+(g+15)(1-Qzz)-Qxz*DeltaX-Qyz*DeltaYr-Qzz*(zeta+sz_signed*DeltaYw).',
  'exact_radial_numerator':'Qxx*(Ttip.x-r(u))=eta+dprime.x-Qxx*(bX-20)+(1-Qxx)*(r(u)-36)-(Qyx+k*Qyz)*DeltaYr-Qzx*(g+15)+k*(g+15)*(1-Qzz)-(Qzx+k*Qzz)*(zeta+sz_signed*DeltaYw)-k*Qxz*DeltaX+k*lambda_i.',
  'original_residual':'J_signed=(1/Qxx-Qxx)*eta+the_above_numerator_without_eta/Qxx, preserving original Bx<=S32+J_common convention.',
  'S32_upper_mm':S,'original_J_required_upper_mm':budget,
  'rows':radials,
  'interpretation':'The coupled identities eliminate frame X translation and carrier Z drift before taking any norm outer bound. The remaining conservative outer is NOT claimed attainable; its exceeding the budget is failure to certify, not a physical collision or a valid defect witness.',
 },
 'minimal_remaining_obstruction':[
  'The phase lambda_i=dprime_i.z-u must be obtained from the SAME calibrated common output coordinate and independent support registration/zero-stop poses. Hard stops bound travel, not an exact identity dprime_i.z=u for both supports.',
  'Even lambda=0 does not make this sufficient outer pass: matrix/line boxes lose correlations between R, w, deltaN, the finite window and all four common cam contacts. A sharper elimination must keep those signed constraints together; the failed outer does not prove a remaining free mode is physically reachable.',
  'Actual effective gaps, gib tilt/form, threaded coaxiality and retained V contact under load are still unset inputs, not silently zero manufacturing tolerances.',
 ],
 'J_common_proved_upper_mm':None,'current_common_Bx_certified':False,'actual_feasible_failure_witness':None,
 'full_D02_closed':False,'manufacturing_release':False,'physical_acceptance':False,
 'numerical_method':'Fraction and directed1e-12 rounding; algebraic same-line/plane elimination, finite contact reentry and affine-root denominator certificate. No sampled optimizer.',
 'exact_rational_algebra_checks':{'purpose':'Sign/centering regression for the displayed identities on three arbitrary rigid transformations. Not feasible assembly poses, not an extrema search, and not the continuous proof.','cases':algebra_tests},
 'review_notes':['An initial in-progress human-readable root string incorrectly retained10.5 rather than-11.5 after centeringhY22; corrected before freezing. The actual residual/root calculation always used the centred11.5 offset and numeric results did not change. No prior frozen report was overwritten.','Requested independent peer review was not completed within this bounded task because the peer was assigned a separate root priority. This report does not claim an independent signoff.'],
 'source_stable':all(sha(ROOT/p)==h for p,h in hashes.items()),
}
assert result['source_stable']
OUT.mkdir(exist_ok=True,parents=True)
(OUT/'report.json').write_text(json.dumps(convert(result),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(convert({'frame':fr,'midplane':intersections,'window':result['fixed_window'],'radial':radials}),ensure_ascii=False,indent=2))
