#!/usr/bin/env python3
"""Bound ONE common-frame yaw component; no CAD or full-domain certification."""
from pathlib import Path
from fractions import Fraction as F
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'analysis'))
from frame_y_guide_bound import upper as up

def q(x): return F(str(x))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def conv(x):
    if isinstance(x, F): return float(x)
    if isinstance(x, dict): return {k: conv(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [conv(v) for v in x]
    return x

paths = {
    'phase': 'output/current-joint-tolerance/common-phase-registration/report.json',
    'cam': 'output/current-joint-tolerance/common-cam-intersection/report.json',
    'joint': 'output/current-joint-tolerance/report.json',
    'axial': 'output/current-joint-tolerance/half-shell-axial-coupling/report.json',
}
r = {k: json.loads((ROOT / p).read_text()) for k, p in paths.items()}
# The phase audit already distinguishes the three changed, excluded historical
# scene/input/route dependencies. Check its CURRENT identities, not old hashes.
files = {ROOT / p for p in r['phase']['source_hashes']}
for p, h in r['phase']['source_hashes'].items():
    assert sha(ROOT / p) == h, p
files |= {ROOT / p for p in paths.values()} | {Path(__file__)}
before = {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)}

ax = r['axial']['numeric']
mc = r['joint']['mount_registration']['cases'][1]
fr = r['cam']['finite_frame_proof']['rows']
assert mc['label'].startswith('current32gon')
for side in ['right', 'left']:
    assert fr[side]['inverse_translation_Y_interval_mm'] == [0, .1]
    assert min(fr[side]['finite_margins_mm'].values()) > 0
Cm = q(mc['relative_hole_center_distance_upper_mm'])
k = q(mc['support_rotation_chord_upper'])
c = q(ax['seam_locator_disc_radius_upper_mm'])
sA = q(ax['sin_alpha_upper'])
cA = q(ax['cos_alpha_lower'])
assert k < F('.02') and sA < F('.002') and cA > F('.999')
M = {key: q(value) for key, value in fr['right']['matrix_abs_upper'].items()}
assert M['xy'] == q(fr['left']['matrix_abs_upper']['xy'])
assert M['xz'] == q(fr['left']['matrix_abs_upper']['xz'])
assert M['zy'] == q(fr['left']['matrix_abs_upper']['zy'])

# hYZ=(22,-15); the SAME two-hole transform interpolates at a=30/61.
# e_i=(1-a)d_minus+a*d_plus has norm <=Cm.  The remaining arm is 36 eY.
a = F(30, 61)
assert 0 < a < 1
assert (1-a)*F(-45)+a*F(16) == -15
cosP_lower = 1-k*k/2
# In N (the H angle bisector), mount-Y arm DIFFERENCE is
# 36[cos(alpha+psi_plus)-cos(-alpha+psi_minus)]; cos(alpha) cancels.
# Both arguments lie in [-(P+A), P+A], so its range width, not twice
# an independently absolute arm displacement, is sufficient.
mount_Y = up(36*(1-cosP_lower*cA+k*sA))
mount_Z = up(72*(k+sA*k*k/2))
# R(-alpha)(R(2alpha)-I)(h-p0)=2sin(alpha)J(-18,44).
rot_Y = up(mount_Y+88*sA)
rot_Z = up(mount_Z+36*sA)
# The three residual disks are projected ONCE on the same n=R_C eY.
disk = up(2*Cm+c)
nZ = up(q(ax['axis_projection_sin_beta_upper'])+M['zy'])
normal_registration = up(disk+rot_Y+nZ*rot_Z)
new_xy = up((F('.1')+normal_registration)/112)
new_common_yx = up(new_xy+M['xz']*nZ)
new_own_yx = up(new_xy+M['xz']*M['zy'])
assert 0 < new_xy < M['xy']

report = {
    'status': 'CONDITIONAL_COMMON_FRAME_YAW_STRICTLY_TIGHTENED_ONLY',
    'source_hashes': before,
    'historical_transfer': {
        'current_identity_audit': paths['phase'],
        'historical_source_audit_reused': r['phase']['historical_source_audit'],
        'scope': 'Only unchanged finite feeder guides, seated Rx registration, seam, and their algebraic outer bounds; changed input, cable route and scene export are not revalidated.'},
    'coordinate_contract': {
        'common_axes': 'N: X unchanged; YZ axes bisect the SAME half-shell relative Rx angle theta=2alpha.',
        'reference_points_nominal': {'right': [56,22,-15], 'left': [-56,22,-15]},
        'mirror': 'J=diag(-1,1,1); only X is mirrored, never Y.',
        'Q_right': 'S_R^T R_C',
        'Q_left': 'J S_L^T R_C J',
        'dprime_right': 'R_C^T [C(h_R)-S_R(h_R)]',
        'dprime_left': 'J R_C^T [C(h_L)-S_L(h_L)]',
        'n': 'R_C eY; dprime_Y=n dot [C(h)-S(h)] on BOTH sides.',
        'Qxy_sign': 'Q_right,xy=R_C,xy; Q_left,xy=-R_C,xy; their absolute values agree.'},
    'exact_identities': [
        'delta_i(h)=e_i+36(R(psi_i)-I)eY, e_i=(31/61)d_i_minus+(30/61)d_i_plus, norm(e_i)<=Cm.',
        'S_R(h_R)-S_L(h_L)=112eX+r in N.',
        'n dot [C(h_R)-C(h_L)]=112(R_CeY) dot (R_CeX)=0.',
        '112 R_C,xy=-(dprime_R,Y-dprime_L,Y)-n dot r.',
        'dprime_R,Y and dprime_L,Y are each in [0,.1]; therefore their signed difference is in [-.1,.1].',
        'r=E+r_rot, norm(E)<=2Cm+c; E=R(alpha)e_R-R(-alpha)e_L+R(-alpha)d0.',
        'r_rot,Y=36[cos(alpha+psi_R)-cos(-alpha+psi_L)]-88sin(alpha).',
        'r_rot,Z=36[sin(alpha+psi_R)-sin(-alpha+psi_L)-2sin(alpha)]-36sin(alpha).',
        'R_C,yx=R_C,xz R_C,zy-R_C,xy R_C,zz (proper-rotation cofactor).'],
    'numeric': {
        'mount_Cm_mm': Cm, 'mount_rotation_chord_upper': k,
        'seam_locator_disk_c_mm': c, 'sin_alpha_upper': sA,
        'cos_alpha_lower': cA, 'interpolation_a': a,
        'mount_arm_difference_Y_abs_upper_mm': mount_Y,
        'mount_arm_difference_Z_abs_upper_mm': mount_Z,
        'combined_three_disk_projection_upper_mm': disk,
        'registration_rotation_Y_abs_upper_mm': rot_Y,
        'registration_rotation_Z_abs_upper_mm': rot_Z,
        'common_normal_Z_abs_upper': nZ,
        'same_normal_registration_abs_upper_mm': normal_registration,
        'guide_inverse_Y_signed_difference_abs_upper_mm': F('.1'),
        'old_shared_Qxy_abs_upper': M['xy'],
        'new_shared_Qxy_abs_upper': new_xy,
        'new_common_N_RCyx_abs_upper': new_common_yx,
        'new_each_support_Qyx_abs_upper': new_own_yx,
        'old_shared_Qxz_abs_upper_reused': M['xz'],
        'old_each_Qzy_abs_upper_reused': M['zy'],
    },
    'proof_conditions': [
        'Both shell split planes and support mount planes remain seated; registration is Rx plus YZ translation only.',
        'The SAME two-hole mounting transform is retained at each support; hZ=-15 lies between -45 and16.',
        'Both rails are parts of ONE rigid common C, separated by112eX; independent cam transforms are not allowed.',
        'Effective guide gap remains the conditional .1mm nominal setting with existing finite-patch membership and normal branch.',
        'Old guide matrix bounds supply only the prior finite outer set; the new yaw result is not fed back to prove its own premises.',
        'The disk/arm bounds are outer support-function bounds, not jointly attainable worst-case poses.'
    ],
    'source_lines': [
        {'path':'cad/feeder-frame-y-guide.scad','lines':[54,64,75,77],'purpose':'same Y datum and X-only side mirror'},
        {'path':'cad/feeder-supports.scad','lines':[83,193,194],'purpose':'whole mirrored supports and one carriage with two rails'},
        {'path':'output/current-joint-tolerance/common-cam-intersection/review.py','lines':[48,52,67,93,102],'purpose':'shared components, finite Y rays, positive finite margins and both inverse Y intervals'},
        {'path':'output/current-joint-tolerance/review.py','lines':[42,50,118],'purpose':'two mounting-hole disks and SAME-transform interpolation'},
        {'path':'output/current-joint-tolerance/half-shell-axial-coupling/review.py','lines':[48,55,69],'purpose':'common H angle bisector and support-to-N roll bound'},
    ],
    'not_certified': [
        'Full joint Bx, cam endpoint fit, loaded contact, physical guide gaps/form error, cable lost motion or final stop setting.',
        'No new CAD collision, native mesh, slice, force or physical assembly acceptance.'
    ],
    'current_common_Bx_certified': False,
    'full_D02_closed': False,
    'manufacturing_release': False,
    'physical_acceptance': False,
    'numerical_method': 'Exact Fraction algebra with outward 1e-12 upper rounding; no optimizer or pose sample is used as proof.',
}
report['all_sources_stable'] = all(sha(ROOT/p)==h for p,h in before.items())
assert report['all_sources_stable']
(OUT/'report.json').write_text(json.dumps(conv(report),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(conv({'status':report['status'],'numeric':report['numeric']}),ensure_ascii=False,indent=2))
