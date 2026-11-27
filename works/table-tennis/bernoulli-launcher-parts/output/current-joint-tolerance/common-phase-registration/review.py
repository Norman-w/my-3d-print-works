#!/usr/bin/env python3
"""Conditional common output phase bound. No CAD/slice work; this directory only."""
from pathlib import Path
from fractions import Fraction as F
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'analysis'))
from frame_y_guide_bound import upper as up, lower as down, sqrt_lower as sl, sqrt_upper as su


def q(x): return F(str(x))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads((ROOT / p).read_text())
def conv(x):
    if isinstance(x, F): return float(x)
    if isinstance(x, dict): return {k: conv(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [conv(v) for v in x]
    return x


paths = {
    'cam': 'output/current-joint-tolerance/common-cam-intersection/report.json',
    'axial': 'output/current-joint-tolerance/half-shell-axial-coupling/report.json',
    'joint': 'output/current-joint-tolerance/report.json',
}
reports = {k: read(p) for k, p in paths.items()}
# Only these explicitly identified historical dependencies changed. All other
# inherited files must still match. None of these three supplies the local
# feeder guide/stop/seam/support constraints reused by this proof.
drift_contract = {
    'cad/cable-housing-route.scad': (
        '5f7aa2f1c5ee59f0b90833ea8b9265c1fe96cf00420faf6991872c87085897f1',
        'b5b335abe0b6fa4790c1331ad849c36827c2ef39711eaaf60e655ebd0d82cfaa',
        'Input endpoint shift and 3 mm route extension; not a source of the feeder rigid contact domain. Cable loads and takeup-to-output loss remain outside this proof.'),
    'cad/cable-scene-export.scad': (
        'c756235f815ba7c62d484792856654d950e87943733e75fa86eefdc4c08229c4',
        'f13b272bed1b9f0928d75f0897615c898d85ba1b986a73872cce2c736be0b42b',
        'Scene selectors/display export changed; none defines the reused physical stop/guide/seam/support dimensions.'),
    'cad/cable-trigger-input.scad': (
        'e243be6b39956ae2ac28bda58c8f3d92bcf4e9a04b28818d8b37d65dea276d07',
        'cf2dc90ecea43e0bb5bf3b6fe68f9cf7adb8d47145b4b15577e5dd40f1679d8d',
        'Input axis/position adoption; this report has no trigger-angle, input-stop, input-bearing or force term. It does not revalidate combined assembly or imported historical source identity.'),
}
inherited = reports['cam']['source_hashes']
audit = []
seen_drift = set()
for name, historical in inherited.items():
    current = sha(ROOT / name)
    if current != historical:
        assert name in drift_contract, ('unreviewed drift', name)
        old, new, reason = drift_contract[name]
        assert (historical, current) == (old, new), ('unexpected revision', name)
        seen_drift.add(name)
        status = 'HISTORICAL_HASH_CHANGED_EXCLUDED_FROM_LOCAL_CONSTRAINTS'
    else:
        reason = 'Exact inherited bytes unchanged.'
        status = 'INHERITED_BYTES_MATCH'
    audit.append(dict(path=name, historical_sha256=historical,
                      current_sha256=current, status=status, reason=reason))
assert seen_drift == set(drift_contract)
files = {ROOT / p for p in inherited} | {ROOT / p for p in paths.values()} | {
    Path(__file__), ROOT / 'cad/cable-output-interface.scad',
    ROOT / 'analysis/frame_y_guide_bound.py',
}
before = {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)}

evidence = []
for name, needles in {
    'cad/cable-output-interface.scad': [
        'co_box(-65.5,-49,28,co_cap_y,co_lug_bottom,32)',
        'union(){feeder_carriage(0);co_lug_blank();}',
        'co_cap_screws=[-62.5,-51]', 'co_cap_screw_z=26',
        'co_x=-58', 'co_y=35.5', 'co_z=15'],
    'cad/feeder-supports.scad': [
        'support_rail_x0 = 54', 'support_rail_x1 = 58',
        'support_rail_y0 = 20', 'support_rail_y1 = 24',
        'support_guide_z0 = -35', 'support_guide_z1 = 5',
        'support_stop_x0 = support_rail_x0-1',
        'support_stop_x1 = support_rail_x1+1',
        'support_stop_y0 = support_rail_y0-1',
        'support_stop_y1 = support_rail_y1+1',
        'support_guide_z0-cam_stroke-support_stop_thickness',
        'support_guide_z1])'],
}.items():
    lines = (ROOT / name).read_text().splitlines()
    for needle in needles:
        hits = [dict(path=name, line=i + 1, text=s) for i, s in enumerate(lines) if needle in s]
        assert hits, (name, needle)
        evidence.extend(hits)

cam = reports['cam']
ax = reports['axial']['numeric']
mount = reports['joint']['mount_registration']['cases'][1]
assert mount['label'].startswith('current32gon')
beta = q(ax['axis_projection_sin_beta_upper'])
nzlo = sl(1 - beta * beta)
cm = q(mount['relative_hole_center_distance_upper_mm'])
chord = q(mount['support_rotation_chord_upper'])
# hYZ=(22,-15) lies between both real mount axes Z=-45,16. The same
# mounting rigid transform gives this existing interpolated norm enclosure.
mount_h = up(cm + 36 * chord)
# H at the SAME hYZ, based on the actual round locator p0=(40,-59).
# ||H(h)-h|| <= ||H(p0)-p0|| + ||RH-I||*||h-p0||.
seam_h = up(q(ax['seam_locator_disc_radius_upper_mm'])
            + 2 * q(ax['sin_alpha_upper']) * su(F(18**2 + 44**2)))
host_pair = up(2 * mount_h + seam_h)
reference = [F('-65.5'), F(28), F(32)]
h = [F(56), F(22), F(-15)]

frames = {}
for side, row in cam['finite_frame_proof']['rows'].items():
    M = {k: q(v) for k, v in row['matrix_abs_upper'].items()}
    M.update(dict(zip(['xx', 'yy', 'zz'], map(q, row['matrix_diagonal_lower']))))
    dp = [max(abs(q(v)) for v in row[f'inverse_translation_{axis}_interval_mm']) for axis in 'XYZ']
    world = [up(dp[0] + M['xy'] * dp[1] + M['xz'] * dp[2]),
             up(M['yx'] * dp[0] + dp[1] + M['yz'] * dp[2]),
             max(abs(q(v)) for v in row['translation_Z_interval_mm'])]
    # n_i is the fixed support's expression of eZ_N. n_x=0,
    # |n_y|<=beta, n_z>=nzlo. v=Q^T n in the moving frame.
    vx = up(beta * M['yx'] + M['zx'])
    vy = up(beta + M['zy'])
    vzlo = down(nzlo * M['zz'] - beta * M['yz'])
    assert vzlo > 0
    # n_i does NOT vary between C and C0; cancel that static rotation before
    # bounding delta-v. Diagonal differences use [lower,1], not twice 1.
    dv = [up(2 * vx), up(beta * (1 - M['yy']) + 2 * M['zy']),
          up(2 * beta * M['yz'] + (1 - M['zz']))]
    zero_z = up(20 * (1 - M['zz']) + 3 * (M['zx'] + M['zy']))
    zero_projection = up(zero_z + beta * world[1])
    ai = [reference[0] if side == 'right' else -reference[0], *reference[1:]]
    arm = [abs(x-y) for x, y in zip(ai, h)]
    correction = up((1 - vzlo) * dp[2] + vx * dp[0] + vy * dp[1])
    rotation = up(sum(x*y for x, y in zip(dv, arm)))
    frames[side] = dict(matrix=M, inverse_translation_abs_upper_mm=dp,
                       support_translation_abs_upper_mm=world,
                       v_abs_xy_upper=[vx, vy], v_z_lower=vzlo,
                       same_support_delta_v_abs_upper=dv,
                       reference_local=ai, reference_arm_abs_mm=arm,
                       active_zero_support_dz_upper_mm=zero_z,
                       active_zero_N_projection_upper_mm=zero_projection,
                       current_dprime_projection_correction_upper_mm=correction,
                       reference_rotation_difference_upper_mm=rotation)

scenarios = []
for active in ['right', 'left']:
    rows = {}
    for side in ['right', 'left']:
        f = frames[side]
        # SAME common frame: its h_right-h_left is 112 eX. The two support
        # registration transforms are bounded but never set identical.
        cross = F(0) if side == active else up(112 * frames[active]['v_abs_xy_upper'][0] + host_pair)
        zero_projection = up(frames[active]['active_zero_N_projection_upper_mm'] + cross)
        lam = up(zero_projection + f['current_dprime_projection_correction_upper_mm']
                 + f['reference_rotation_difference_upper_mm'])
        rows[side] = dict(zero_N_projection_abs_upper_mm=zero_projection,
                          common_frame_cross_support_term_upper_mm=cross,
                          Lambda_phase_upper_mm=lam)
    scenarios.append(dict(one_zero_contact_side=active, rows=rows))
overall = {s: max(x['rows'][s]['Lambda_phase_upper_mm'] for x in scenarios) for s in frames}

# Exact rational tests: algebra only, no claim these arbitrary orientations
# satisfy all of the physical joint-domain contacts.
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def add(a, b): return [x+y for x, y in zip(a, b)]
def sub(a, b): return [x-y for x, y in zip(a, b)]
def mv(A, x): return [dot(r, x) for r in A]
def tr(A): return [list(x) for x in zip(*A)]
def mm(A, B): return [[dot(r, c) for c in tr(B)] for r in A]
def rot(axis, t):
    c=(1-t*t)/(1+t*t); s=2*t/(1+t*t)
    if axis == 0: return [[F(1),F(0),F(0)],[F(0),c,-s],[F(0),s,c]]
    if axis == 1: return [[c,F(0),s],[F(0),F(1),F(0)],[-s,F(0),c]]
    return [[c,-s,F(0)],[s,c,F(0)],[F(0),F(0),F(1)]]
tests=[]
for k in [1,2,3]:
    Q=mm(rot(2,F(k,100)),rot(0,F(-k,600)))
    Q0=mm(rot(1,F(-k,700)),rot(2,F(k,150)))
    n=mv(rot(0,F(k,500)),[F(0),F(0),F(1)])
    dp=[F(k,70),F(k,80),F(5+k)]; dp0=[F(k,75),F(k,85),F(k,100)]
    A=[reference[j]-h[j] for j in range(3)]
    v=mv(tr(Q),n);v0=mv(tr(Q0),n)
    u=dot(n,sub(mv(Q,add(dp,A)),mv(Q0,add(dp0,A))))
    lhs=dp[2]-u
    rhs=(1-v[2])*dp[2]-v[0]*dp[0]-v[1]*dp[1]+dot(v0,dp0)-dot(sub(v,v0),A)
    assert lhs==rhs
    # The minimum of the four transformed lower-face corners is exactly 5.
    dz0=20*(1-Q0[2][2])+3*(abs(Q0[2][0])+abs(Q0[2][1]))
    minimum=min(-15+dz0+dot(Q0[2],[F(x),F(y),F(20)]) for x in [-3,3] for y in [-3,3])
    assert minimum==5
    tests.append(dict(case=k, phase_identity_exact=True, zero_face_corner_identity_exact=True,
                      not_a_feasible_assembly_sample=True))
# A narrow subdomain witness: aligned frames; one support's origin is -.4Z.
# One common C0 then contacts only the right zero face; the left gap is .4.
# This proves ONLY that the phase convention must retain support registration.
toy = dict(common_frame_z0_mm=0, support_z0_mm={'right':0,'left':-.4},
           zero_gaps_mm={'right':0,'left':.4}, lambda_phase_mm={'right':0,'left':.4},
           full_four_pin_domain_feasibility_claimed=False)

result = {
    'status':'CONDITIONAL_COMMON_REFERENCE_PHASE_FINITE_BOUND_NOT_FULL_BX',
    'source_hashes':before, 'historical_source_audit':audit, 'source_evidence':evidence,
    'reference':{
        'a_CAD_mm':reference,
        'feature':'Integral output lug left/front/top corner; intersection of X=-65.5, Y=28, Z=32 planes of co_frame, not removable cap, screw, wire nipple, or trigger.',
        'definition':'u_N=eZ_N dot [C(a)-C0(a)], fixed N axis from the same installed half-shell bisector. Track the same corner (or fit its three local planes) relative to a fixed datum aligned with that axis.',
        'physical_alignment_measured':False,
        'zero':'C0 is the same installed common frame at at least ONE actual return zero-stop contact. It is not a fresh independent support registration or an asserted simultaneous two-sided contact.',
        'limitations':'No new marker or CAD geometry added. Real corner form, axis registration, reading errors, and reachability of this zero pose remain unmeasured; returning under spring force is not proved.'},
    'exact_bridge':{
        'coordinates':'Each canonical mirrored side has h=(56,22,-15), Ci(q)=h+di+Qi(q-h), di=Qi*dprime_i. Both Ci and Ci0 come from the SAME global C/C0 and fixed H/S_i. ai is the same physical a in each cam-local mirrored coordinate convention.',
        'normal':'ni=rotation(Sglobal_i)^T*eZ_N; ni.x=0. H/S_i are unchanged from C0 to C. v_i=Qi^T ni, v_i0=Qi0^T ni.',
        'u':'u_N=ni dot {Qi[dprime_i+ai-h]-Qi0[dprime_i0+ai-h]}',
        'lambda':'lambda_phase_i=dprime_i.z-u_N=(1-v_i.z)dprime_i.z-v_i.x*dprime_i.x-v_i.y*dprime_i.y+v_i0 dot dprime_i0-(v_i-v_i0) dot (ai-h)',
        'zero_contact':'For active side j, d_j0.z=20(1-Q_j0.zz)+3(|Q_j0.zx|+|Q_j0.zy|). Only at least one side j is required. The minimising return-stop-face corner lies in material by the inherited finite stop-strip proof.',
        'same_frame_between_sides':'|ni dot di0-nj dot dj0| <=112*|eZ_N dot R_C0 eX| + 2*mount_h + seam_h; |eZ_N dot R_C0 eX| <= beta*|Q_j0.yx|+|Q_j0.zx|. No independent favourable C assigned per side.',
        'symbol_warning':'lambda_phase is NOT the finite-pin longitudinal lambda used in gate-ball-joint-review. This report does not assume nominal source translate([0,0,u]) for the actual contact domain.'},
    'numeric':{'support_axis_sin_beta_upper':beta,'support_axis_cos_beta_lower':nzlo,
               'mount_h_norm_upper_mm':mount_h,'same_H_at_h_norm_upper_mm':seam_h,
               'pair_support_h_registration_norm_upper_mm':host_pair,
               'frames':frames,'single_active_zero_scenarios':scenarios,
               'all_active_side_Lambda_phase_upper_mm':overall},
    'domain_conditions':[
        'Exactly the inherited conditional rigid normal contact domain of common-cam-intersection: seated common-X mounting normals; parallel effective Y gaps<=.1, right X gap<=.1, left total X gap .4; retained finite guide, pin/nut/V and body contacts; tip radial guard20..27 remains conditional.',
        'One fixed physical installation H/S_i for the entire C0-to-C path. Actual differential-gib setting, shape, thread clearance, load deformation and contact loss are not assigned zero manufacturing tolerances.',
        'C0 reaches at least one existing return stop face without a different obstruction defining its rest pose. Both C0 and C remain on the inherited finite normal branch. This is a declared zero-datum premise, not proof of loaded return or global path existence.',
        'The stated bounds are universal outer bounds on that domain, not attained extrema. They may be reduced by other common contacts. No failed inequality is a realizable mechanical defect witness.',
        'For subsequent gate comparison restrict the same u_N to[0,20]; this result alone does not certify that all actual travel spans exactly that interval.'
    ],
    'relation_to_stop_and_cable':{
        'functional_phase_alignment':'The conditional gate radius laws can now be stated relative to this explicit u_N by retaining lambda_phase. Neither lambda_phase nor its bound is zero.',
        'input_take_up':'Input core takeup is not automatically u_N when the frame tilts. Net loss ell must use this same output reference and include any core-length/projection/clamp takeup difference once only.',
        'actual_F_H_ell_e':None,'phase_reference_alignment_certified':False,
        'conditional_gate_threshold_18_596709_is_current_actual_F':False,
        'reason':'Bx<=1, an actual calibrated zero/reference, and compatible earliest hard stop remain unproved. Do not append Lambda to F as a separately attainable phase error or count it twice with J/ell.'},
    'checks':{'exact_rational_algebra':tests,'single_side_zero_convention_control':toy,
              'no_midplane_or_fixed_window_reproof':True,'no_CAD_export_or_slice':True},
    'remaining':[
        'This finite Lambda removes an unbounded/undefined notation gap but does not close J_common. The prior J outer already exceeded the .602876731024 budget even at Lambda=0.',
        'A future Bx proof must retain the same signed Q/R/w/deltaN/window/four-cam constraints and this bridge. It must close the radial20..27 guard without circular use.',
        'Physical datum alignment, as-built form/gaps, retained contact under load, actual cable lost motion and spring return still require supplier/assembly evidence.'
    ],
    'full_D02_closed':False,'current_common_Bx_certified':False,
    'manufacturing_release':False,'physical_acceptance':False,
    'numerical_method':'Exact Fraction algebra with directed 1e-12 bounds; imported unchanged finite contact enclosures. No pose sample maxima or free per-side phase matching.',
    'all_sources_stable':all(sha(ROOT/p)==digest for p,digest in before.items()),
}
assert result['all_sources_stable']
(OUT/'report.json').write_text(json.dumps(conv(result),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(conv({'status':result['status'],'source_count':len(before),
                       'inherited_unchanged':sum(x['status']=='INHERITED_BYTES_MATCH' for x in audit),
                       'explicit_historical_drift':len(seen_drift),
                       'registration':host_pair,'Lambda':overall,
                       'scenarios':scenarios,'all_sources_stable':result['all_sources_stable']}),ensure_ascii=False,indent=2))
