#!/usr/bin/env python3
"""Same pin/V/nut/window correlation. Writes only this new bounded evidence stage."""
from pathlib import Path
from fractions import Fraction as F
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'analysis'))
from frame_y_guide_bound import upper as up, lower as down, sqrt_lower as sl, sqrt_upper as su

def q(v): return F(str(v))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads((ROOT / p).read_text())
def conv(v):
    if isinstance(v, F): return float(v)
    if isinstance(v, dict): return {k:conv(x) for k,x in v.items()}
    if isinstance(v, (list,tuple)): return [conv(x) for x in v]
    return v

paths = {
    'phase':'output/current-joint-tolerance/common-phase-registration/report.json',
    'cam':'output/current-joint-tolerance/common-cam-intersection/report.json',
    'pin':'output/current-joint-tolerance/common-radial-closure/report.json',
    'carrier':'output/current-joint-tolerance/carrier-body-coupling/report.json',
}
reports = {k:read(p) for k,p in paths.items()}
phase = reports['phase']
assert phase['status'] == 'CONDITIONAL_COMMON_REFERENCE_PHASE_FINITE_BOUND_NOT_FULL_BX'
# The phase report separately audited the three input/route/export changes;
# here bind its exact currently reviewed dependency set, without rewriting the
# original historical common-cam/pin/carrier reports or pretending they reran.
for p,h in phase['source_hashes'].items():
    assert sha(ROOT/p)==h, ('source changed since local scope audit',p)
files = {ROOT/p for p in phase['source_hashes']} | {ROOT/p for p in paths.values()} | {Path(__file__)}
before = {str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}

cam = reports['cam']; pin = reports['pin']; carrier = reports['carrier']['new_result']
ra={k:q(v) for k,v in carrier['matrix_abs_upper'].items()}
rd={k:q(v) for k,v in carrier['matrix_diagonal_lower'].items()}
pn=pin['new_numeric']
w=q(pn['slope_norm_upper']);wp=q(pn['positive_q_norm_upper']);wn=q(pn['negative_q_norm_upper'])
rho=q(pn['rho_from_32gon_mm']);h=F('1.375');ym=F('3.125');radius=F(2)
assert radius/2==1
ywlo,ywhi=map(q,cam['fixed_window']['carrier_y_at_axis_crossing_mm'])
zeta=q(cam['fixed_window']['zeta_abs_upper_mm'])
s2lo,s2hi=sl(F(2)),su(F(2))
m=F('.625')
results={}
for side in ['right','left']:
    frame=cam['finite_frame_proof']['rows'][side]
    M={k:q(v) for k,v in frame['matrix_abs_upper'].items()}
    Qxxlo=q(frame['matrix_diagonal_lower'][0])
    yi=cam['same_pin_midplane_intersections'][side]
    ylo,yhi=map(q,yi['axis_y_star_interval_mm'])
    assert ylo>ywhi and ywlo>F('4.5')
    delta=up(yhi-ywlo)
    b=up(M['zx']+m)  # b_actual=Qzx+kQzz; covers both k signs without fixing Q.
    bt=up(b*delta)
    # A=Qxx(Rxx,Rxz); alpha=N*A, with N the two orthonormal V normals.
    amin=down((Qxxlo*rd['Rxx']-ra['Rxz'])/s2hi)
    amax=up((1+ra['Rxz'])/s2lo)
    assert amin>0
    Di=up((1+ra['Rzx'])/s2lo)
    # beta_i-h*alpha_i >= this positive bound. All y/Delta/Q/R values
    # belong to one declared domain; discarded correlations only enlarge it.
    drop_lhs=down((ylo-F('4.5'))*amin-bt*Di)
    drop_rhs=up(amax*radius*w/2)
    assert drop_lhs>drop_rhs>0
    Pp=up(yhi-F('1.75'));Pn=up(yhi-F('4.5'))
    row_cross=up(ra['Rxy']*ra['Rzy'])
    # Exact R row orthogonality: A.D=-Qxx*Rxy*Rzy,
    # ||A||²=Qxx²(1-Rxy²), ||D||²=1-Rzy².
    # Norm is taken AFTER combining the two same-pin sections.
    def combo_norm(P): return su(P*P+bt*bt+2*P*bt*row_cross)
    np=combo_norm(Pp);nn=combo_norm(Pn)
    pos=up(np*wp+amax*radius*wp*wp/2)
    # sum alpha_i=sqrt2*A_x <=sqrt2; shared nut constraint bounds q_minus.
    neg=up(nn*wn+s2hi*rho)
    mixed=max(pos,neg)
    independent=up(q(yi['axis_delta_at_max_y_star_norm_upper_mm'])+bt*w)
    assert mixed<independent
    base={
        'carrier_X_diagonal':up(20*(1-rd['Rxx'])),
        'carrier_Y_to_X':up(yhi*ra['Rxy']),
        'same_window_zeta':up(b*zeta),
        'carrier_Y_to_Z_between_sections':up(bt*ra['Rzy']),
    }
    group=up(sum(base.values())+mixed)
    previous=cam['radial_elimination']['rows'][side]
    oldterms={k:q(v) for k,v in previous['same_joint_identity_terms_upper_mm'].items()}
    oldgroup=up(oldterms['same_carrier_pin_X_offset']+oldterms['same_window_to_midplane_Z'])
    assert group<oldgroup
    # Only substitute G inside the original exact numerator; the eta term,
    # common phase, registration and all other terms are untouched.
    num=sum(v for k,v in oldterms.items() if k not in ['same_carrier_pin_X_offset','same_window_to_midplane_Z'])+group
    S=q(cam['radial_elimination']['S32_upper_mm'])
    extra=up(S*(1/Qxxlo-Qxxlo))
    j0=up(num/Qxxlo+extra)
    oldj=q(previous['J_common_outer_at_Lambda_zero_mm'])
    limit=q(cam['radial_elimination']['original_J_required_upper_mm'])
    assert j0<oldj and j0>limit
    results[side]={
        'actual_cam_carrier_y_interval_mm':[ylo,yhi],
        'actual_window_carrier_y_interval_mm':[ywlo,ywhi],
        'same_pin_delta_y_upper_mm':delta,'abs_Qzx_plus_kQzz_upper':b,
        'V_projection_alpha_interval':[amin,amax],
        'negative_q_drop_lhs_lower_mm':drop_lhs,
        'negative_q_drop_rhs_upper_mm':drop_rhs,
        'negative_q_drop_margin_lower_mm':down(drop_lhs-drop_rhs),
        'combined_positive_coefficient_norm_upper_mm':np,
        'combined_negative_coefficient_norm_upper_mm':nn,
        'same_pin_positive_projection_upper_mm':pos,
        'same_pin_negative_projection_magnitude_upper_mm':neg,
        'same_pin_abs_projection_upper_mm':mixed,
        'independent_norm_reference_for_same_pin_expression_mm':independent,
        'same_expression_improvement_lower_mm':down(independent-mixed),
        'remaining_group_terms_upper_mm':base,
        'combined_G_numerator_abs_upper_mm':group,
        'old_two_term_G_numerator_abs_upper_mm':oldgroup,
        'G_numerator_improvement_lower_mm':down(oldgroup-group),
        'J0_after_only_this_valid_substitution_upper_mm':j0,
        'old_J0_upper_mm':oldj,
        'same_original_J_budget_mm':limit,
        'phase_gain_unchanged':q(previous['phase_residual_gain_upper']),
        'this_outer_certifies_J_even_at_Lambda_zero':False,
    }

# Rational regressions test the algebra on arbitrary transformations; they do
# not search feasible mechanisms or replace the universal inequalities above.
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def add(a,b):return [x+y for x,y in zip(a,b)]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def mul(a,k):return [x*k for x in a]
def mv(A,x):return [dot(row,x) for row in A]
def tr(A):return [list(x) for x in zip(*A)]
def mm(A,B):return [[dot(r,c) for c in tr(B)] for r in A]
def rot(axis,t):
    c=(1-t*t)/(1+t*t);s=2*t/(1+t*t)
    if axis==0:return [[F(1),F(0),F(0)],[F(0),c,-s],[F(0),s,c]]
    if axis==1:return [[c,F(0),s],[F(0),F(1),F(0)],[-s,F(0),c]]
    return [[c,-s,F(0)],[s,c,F(0)],[F(0),F(0),F(1)]]
tests=[]
for index,k in enumerate([F('-.625'),F(0),F('.625')]):
    R=mm(rot(1,F(1,80)),rot(2,F(-1,100)))
    Q=mm(rot(0,F(-1,600)),rot(2,F(1,150)))
    yM=F('10.7');yW=F('7.1');D=yM-yW
    ww=[F('-.009'),F('.017')];d0=[F('.025'),F('-.008')]
    dM=add(d0,mul(ww,yM-ym));dW=add(d0,mul(ww,yW-ym))
    g=F('-28.5');zz=F('.08');pW=[F(42),F(7),g+zz]
    pM=add(pW,mul(mv(R,[ww[0],F(1),ww[1]]),D))
    tipX=pW[0]-20*R[0][0]-yW*R[0][1]-R[0][0]*dW[0]-R[0][2]*dW[1]
    bx=pM[0]-tipX;b=Q[2][0]+k*Q[2][2]
    A=[Q[0][0]*R[0][0],Q[0][0]*R[0][2]]
    DD=[R[2][0],R[2][2]]
    B=add(mul(A,yM-ym),mul(DD,b*D))
    lhs=Q[0][0]*(bx-20)+b*(pM[2]-g)
    rhs=Q[0][0]*(20*(R[0][0]-1)+yM*R[0][1])+b*zz+b*D*R[2][1]+dot(A,d0)+dot(B,ww)
    assert lhs==rhs
    assert dot(A,DD)==-Q[0][0]*R[0][1]*R[2][1]
    # Norm identity for each plus/minus h shift precedes outward enclosure.
    for P in [yM-F('1.75'),yM-F('4.5')]:
        v=add(mul(A,P),mul(DD,b*D))
        norm2=P*P*Q[0][0]**2*(1-R[0][1]**2)+(b*D)**2*(1-R[2][1]**2)-2*P*b*D*Q[0][0]*R[0][1]*R[2][1]
        assert dot(v,v)==norm2
    tests.append(dict(case=index,cam_secant_slope=k,exact_combined_G=True,exact_row_orthogonality=True,
                      exact_coefficient_norm=True,not_a_feasible_assembly_pose=True))

result={
    'status':'STRICTLY_TIGHTER_SAME_PIN_WINDOW_COMBINATION_NOT_FULL_BX',
    'source_hashes':before,
    'inherited_identity_scope':{
        'bridge_report':paths['phase'],
        'unchanged_inherited_sources':47,'explicitly_scoped_historical_changes':3,
        'meaning':'Uses the prior explicit local-source scope audit; does not restamp stale full-system reports as current. All 52 files bound by that stage still match.'},
    'exact_local_combination':{
        'symbols':'R maps carrier to its support; Q maps common cam to the same support. yM is the actual carrier coordinate where SAME pin meets actual cam localY10.5 plane; yW is its coordinate at fixed supportY7. Delta=yM-yW>0; delta(y)=delta0+(y-3.125)w.',
        'b':'b=Qzx+kQzz; k front in[0,.625], rear in[-.625,0], from the SAME two phases. This proof covers both signs without selecting an independent k for each algebraic term.',
        'same_line':'pM-pW=Delta*R*(wx,1,wz), pW.z=g+zeta',
        'G':'G=Qxx*(bX-20)+b*(pM.z-g), bX=pM.x-Ttip.x',
        'decomposition':'G=Qxx*[20(Rxx-1)+yM*Rxy]+b*zeta+b*Delta*Rzy+A dot delta0+B dot w',
        'A':'A=Qxx*(Rxx,Rxz)',
        'B':'B=(yM-3.125)*A+b*Delta*(Rzx,Rzz)',
        'in_common_cam_numerator':'The old exact radial numerator contains -G. This combined bound replaces exactly same_carrier_pin_X_offset + same_window_to_midplane_Z before dividing by Qxx. Other terms are untouched.'},
    'correlated_V_nut_proof':{
        'basis':'n1=(1,-1)/sqrt2,n2=(1,1)/sqrt2; qi=ni dot w; alpha_i=ni dot A>0; beta_i=ni dot B.',
        'inherited_same_nut':'deltaN=delta0-(3.125-YN)w, with ONE retained nut/V/pin. Reuse the proved q_plus norm<=wp and q_minus norm<=wn, not two independently fitted pin lines.',
        'upper':'ni dot delta0<=h|qi|+(Rmax/2)qi². If beta_i-h*alpha_i>=(Rmax/2)*alpha_i*wbar, negative qi cannot increase A.delta0+B.w. Positive projection<=||h*alpha+beta||*wp+(Rmax/2)*alpha_max*wp².',
        'lower':'ni dot delta0>=-rho-h*qi. Since beta_i-h*alpha_i>=0, negative projection magnitude<=||beta-h*alpha||*wn+rho*sum(alpha_i).',
        'orthogonality':'For D=(Rzx,Rzz), A.D=-Qxx*Rxy*Rzy, ||A||²=Qxx²(1-Rxy²), ||D||²=1-Rzy². Thus for P=yM-1.75 or yM-4.5: ||P*A+b*Delta*D||²=P²Qxx²(1-Rxy²)+(b*Delta)²(1-Rzy²)-2P*b*Delta*Qxx*Rxy*Rzy.',
        'enclosure':'Take the norm only after the SAME two-section vectors combine. The monotone outer Pmax²+tmax²+2Pmax*tmax*|Rxy Rzy| remains universal without claiming endpoint poses attainable.',
        'what_was_not_done':'No independent extreme chosen for delta_x, delta_z, slope, or the two section locations; remaining Q/R/registration correlations are still not fully eliminated.'},
    'rows':results,
    'algebra_regressions':tests,
    'domain_conditions':[
        'Exactly the inherited nominal rigid, seated nut, coaxial nominal threaded/shoulder axis, retained finite V contacts and finite full-shoulder coverage. Real thread play, shape, preload, load deformation and loss of contact are not assigned zero manufacturing errors.',
        'The actual cam and fixed-window intersection ranges are inherited, not replaced by yM=10.5 or yW=7 in carrier coordinates. They belong to the same pin line and carrier transform.',
        'Carrier/body and frame finite-contact normal branches, support/half-shell registration and Xtip20..27 guard are inherited. The radial guard still must be closed by a full same-domain Bx proof.',
        'Same C/H/S/K/P and common phase for all four fingers. This local bound covers either front/rear k sign, but does not optimize independent favourable phases.',
    ],
    'scope_of_improvement':{
        'new_local_bound':True,'same_y_star_or_phase_reproof':False,
        'full_J_claim':False,'Bx1_claim':False,'actual_failure_witness':None,
        'warning':'The substituted J outer is smaller but still too large even with zero phase residual. This is failure to certify by this outer bound, not proof of physical failure. Do not add its reduction to another incompatible error-domain budget.'},
    'remaining':'Common Q/R/window/registration/four-pin and phase correlations, loaded contact, actual tolerances and calibrated stop/return data remain open. No further optimization in this stage.',
    'full_D02_closed':False,'current_common_Bx_certified':False,
    'manufacturing_release':False,'physical_acceptance':False,
    'numerical_method':'Exact Fraction algebra; directed1e-12 enclosures and positive guard; rational identity regressions, not sampled extrema.',
    'all_sources_stable':all(sha(ROOT/p)==digest for p,digest in before.items()),
}
assert result['all_sources_stable']
(OUT/'report.json').write_text(json.dumps(conv(result),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(conv({'status':result['status'],'source_count':len(before),'rows':results,
                       'all_sources_stable':result['all_sources_stable']}),ensure_ascii=False,indent=2))
