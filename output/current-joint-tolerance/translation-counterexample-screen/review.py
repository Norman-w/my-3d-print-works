#!/usr/bin/env python3
"""Read-only, translation-only four-follower failure screen; no feasible witness claimed."""
from pathlib import Path
from fractions import Fraction as F
import hashlib, json, sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'analysis'))
from frame_y_guide_bound import upper as up, lower as down, sqrt_lower as sl, sqrt_upper as su

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def q(x): return F(str(x))
def load(p): return json.loads((ROOT / p).read_text())
def conv(v):
    if isinstance(v, F): return float(v)
    if isinstance(v, dict): return {k: conv(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [conv(x) for x in v]
    return v

paths = {k: f'output/current-joint-tolerance/{p}' for k, p in {
    'phase': 'common-phase-registration/report.json',
    'cam': 'common-cam-intersection/report.json',
    'carrier': 'carrier-body-coupling/report.json',
    'ball': 'ball-center-coupling/report.json',
    'axial': 'half-shell-axial-coupling/report.json',
    'joint': 'report.json',
}.items()}
d = {k: load(p) for k, p in paths.items()}
for p, h in d['phase']['source_hashes'].items():
    assert sha(ROOT / p) == h, ('current phase-source drift', p)
files = {ROOT / p for p in d['phase']['source_hashes']} | {ROOT / p for p in paths.values()} | {Path(__file__)}
allowed = {row['path']: row for row in d['phase']['historical_source_audit']
           if row['status'] != 'INHERITED_BYTES_MATCH'}
historical_audit = []
for k in ['carrier', 'ball', 'axial', 'cam', 'joint']:
    for p, historical in d[k]['source_hashes'].items():
        current = sha(ROOT / p)
        files.add(ROOT / p)
        if current != historical:
            assert p in allowed, ('unreviewed upstream drift', k, p)
            row = allowed[p]
            assert historical == row['historical_sha256'] and current == row['current_sha256']
            historical_audit.append(dict(report=k, path=p, historical_sha256=historical,
                                         current_sha256=current, exclusion_reason=row['reason']))
before = {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)}

evidence = []
for p, needles in {
    'cad/cam-study.scad': ['cam_pin_shoulder_start_y = 1.75', 'cam_pin_shoulder_end_y = 13.75',
        'cam_plate_y = 8', 'cam_plate_thickness = 5', 'cam_carrier_axial = 8',
        'module cam_y_cylinder', 'cylinder(h=length,d=d,$fn=32)', 'function cam_gate_r'],
    'cad/feeder-supports.scad': ['support_guide_z0 = -35', 'support_guide_z1 = 5',
        'support_axial_clearance = 0.2', 'support_guide_z0-cam_stroke-support_stop_thickness',
        'support_guide_z1])'],
    'cad/feeder-guide-revision.scad': ['revision_setting=0.90', 'revision_datum_y=4.50'],
    'cad/feeder-frame-y-guide.scad': ['yg_face=24.1', 'yg_datum_y=support_rail_y0'],
    'cad/feeder-cam-guide-revision.scad': ['cg_setting=.9', 'cg_datum_x=support_rail_x0'],
    'cad/feeder-pin-seat-revision.scad': ['ps_v_half_angle=45', 'ps_v_apex=cam_follower_offset-ps_pin_r/sin(ps_v_half_angle)',
        'ps_seat_y0=cam_pin_shoulder_start_y', 'ps_seat_y1=cam_carrier_width/2'],
}.items():
    lines = (ROOT / p).read_text().splitlines()
    for needle in needles:
        hits = [dict(path=p, line=i+1, text=line) for i, line in enumerate(lines) if needle in line]
        assert hits, (p, needle)
        evidence.extend(hits)

cb = q(d['carrier']['new_result']['body_bore_radial_axis_room_upper_mm'])
c = q(d['axial']['numeric']['seam_locator_disc_radius_upper_mm'])
S = q(d['joint']['whole_graph_reference'][1]['whole_graph_slot_bound_upper_mm'])
E = q(d['ball']['final_cases'][-1]['ball_centre_transverse_norm_upper_mm'])
assert (cb, c, S, E) == tuple(map(F, ['.262038183323', '.152855335258', '.397123268976', '1.622943151079']))
m = F(5, 8); gapZ = F('.2'); frameX = F('.1')
b = up(cb+c/2)                 # same half offset about midpoint axis N
eps = up(S+frameX)             # radial error at each actual phase, NOT at u_N
spread = up(c+2*cb)            # all four actual tip Z offsets a_i
endpoint_loss = up(spread+gapZ)
v_end_lo = down(20-endpoint_loss)
r_front_end_lo = down(21+m*(v_end_lo-12)-eps)
ball_outer = up(F('20.5')+F('2.5')+E)  # deliberately loose maxR + maxE
release_margin = down(r_front_end_lo-ball_outer)
tip_radial = [down(21-eps), up(26+eps)]
assert 20 < tip_radial[0] and tip_radial[1] < 27
assert 12 < v_end_lo < 20 and endpoint_loss < 8

# Finite actual pin coverage: C_y-s_y in[0,.1], k_y-s_y in[-.1,0].
relative_y = [F(0), F('.2')]
pin_near = down(8+relative_y[0]-F('1.75'))
pin_far = down(F('13.75')-13-relative_y[1])
assert pin_near > 0 and pin_far > 0
# Pure translations give full rod cross-sections throughout the real 2 mm bore.
rod_reserves = [down(F('31.5')-tip_radial[1]), down(tip_radial[0]+14-F('33.5'))]
assert min(rod_reserves) > 0

Rlo=F(20); Rhi=F('20.5'); tmin=F('2.4845'); tmax=F('2.5')
Hmin = sl((Rlo+tmin)**2-(21+eps)**2-(E+b)**2)
Hmax = su((Rhi+tmax)**2-(21-eps-E)**2)  # whole R interval, no unproved endpoint monotonicity
Pmin = sl((2*Rlo)**2-(2*E)**2)
Llo = up(2*Hmax+2*b); Lhi = down(Hmin+Pmin-Hmax-2*b)
hold_r = down(sl((Rlo+tmin)**2-(E+b)**2-b*b)-eps)
rear_v = up((26-hold_r)/m); front_v = down(12+(hold_r-21)/m)
overlap = down(front_v-rear_v-spread)
plateau_overlap = down(12-8-spread)
assert Llo < F('28.5') < Lhi and hold_r > 21 and overlap > 0
# Endpoint inclusion: C0<=max(a)+.2; Cend>=min(a)+19.8.
window_after_start = down(rear_v-spread-gapZ)
window_before_end = down(20-gapZ-front_v-spread)
assert min(window_after_start, window_before_end) > 0

report = {
    'status': 'NO_COUNTEREXAMPLE_IN_DECLARED_TRANSLATION_SUBDOMAIN',
    'actual_failure_witness_found': False,
    'all_rotation_domain_searched': False,
    'full_D02_closed': False, 'manufacturing_release': False, 'physical_acceptance': False,
    'source_hashes': before, 'historical_source_audit': historical_audit, 'source_evidence': evidence,
    'method': 'Continuous necessary outer constraints and sufficient ball inequalities; exact Fractions with directed 1e-12 square-root/arithmetic bounds. No optimizer and no sampled pose is called feasible.',
    'subdomain': [
        'H is a pure YZ translation; split X=0 faces stay seated; two locator features share this H.',
        'Both supports, common C and four carriers undergo translations only; seated support X datum retained.',
        'Four pins retain their present nominal direction/roll, shoulder/nut axial seats and two V contacts. Pin tilt or roll is not included.',
        'Current parallel guide settings cg=.9, revision=.9, yg_face=24.1; finite contact branch retained.',
        'Every considered pose must satisfy actual mounting, carrier, bore, V, nut, window and closed-slot nonpenetration. Dropping some of those constraints enlarges the screening set, never supplies a feasible counterexample.',
        'Rigid geometry and inherited static two-ball/finite guide domain; R20..20.5, guide inner radius<=21.5, side hole radius<=2.75 are conditional bounds, not measurements.',
    ],
    'joint_equations': {
        'half_tip_support': 'h_negative=0,h_positive=t; ||t_YZ||<=c; a_i=h_side.Z+e_i.Z; ||e_i.YZ||<=cb; kappa_i=a_i-s_side in[-.2,.2]. Same s_side for its front/rear fingers.',
        'four_tip_positions': 'T_i=[side_i*(r_i(v_i)+side_i*C_x+eta_i),h_side.Y+e_i.Y,g_i+a_i], |eta_i|<=S; v_i=C_z-a_i; g_front=0,g_rear=-28.5.',
        'same_cam': 'C_x in[0,.1]; C_y-s_side.Y in[0,.1]; k_i.Y-s_side.Y in[-.1,0]; all four slots use the same C.',
        'zero_and_end': 'C0_z=max(s_negative.Z,s_positive.Z); Cend_z=20+min(s_negative.Z,s_positive.Z).',
        'endpoint_elimination': 'Cend_z-a_i=20+min_j(h_j.Z+e_j.Z-kappa_j)-(h_i.Z+e_i.Z)>=20-c-2cb-.2. This does not compare u_N with a nominal release threshold.',
        'normal_axis': 'For theta=0 the same bisector axis is Y=tY/2 with Z datum=tZ/2, hence each tip Y and gate-Z offset <=cb+c/2; ball center is not set to this axis.',
        'blocking_window': 'C_z lies between max(rear a_i)+rear_v and min(front a_i)+front_v; all four actual tips block at the common gate plane.',
        'monotone_sequence': 'v_i increases with the same C_z; rear gate only closes and front only opens. The positive common blocking interval prevents a two-open phase in this subdomain.',
    },
    'numeric': {
        'cb_mm': cb, 'c_mm': c, 'whole_slot_S_mm': S, 'actual_phase_radial_error_upper_mm': eps,
        'tip_Y_and_Z_about_N_upper_mm': b, 'all_four_a_i_spread_upper_mm': spread,
        'actual_phase_at_end_lower_mm': v_end_lo, 'actual_phase_at_start_upper_mm': endpoint_loss,
        'front_tip_radial_at_hard_end_lower_mm': r_front_end_lo,
        'rear_tip_radial_at_zero_stop_lower_mm': r_front_end_lo,
        'maxR_plus_maxE_plus_outer_tip_upper_mm': ball_outer,
        'front_open_and_rear_initial_open_radial_reserve_lower_mm': release_margin,
        'all_cycle_actual_tip_radial_interval_mm': tip_radial,
        'finite_pin_near_far_face_cover_reserve_lower_mm': [pin_near,pin_far],
        'finite_rod_bore_near_far_reserve_lower_mm': rod_reserves,
        'Hmin_lower_mm': Hmin, 'Hmax_upper_mm': Hmax, 'touching_ball_pitch_lower_mm': Pmin,
        'sufficient_gate_spacing_interval_mm': [Llo,Lhi], 'gate_spacing_mm': F('28.5'),
        'maximum_nominal_r_guaranteed_blocking_mm': hold_r,
        'rear_phase_required_for_blocking_mm': rear_v, 'front_phase_until_blocking_mm': front_v,
        'same_C_all_four_blocking_window_width_lower_mm': overlap,
        'same_C_both_closed_plateau_window_width_lower_mm': plateau_overlap,
        'blocking_window_after_start_before_end_reserves_lower_mm': [window_after_start,window_before_end],
    },
    'not_proved': [
        'Tilted H/support/carrier/frame/pin poses; full coupled phase and J_common remain unclosed.',
        'Ability to reach the hard stop without friction/jam or cable lost motion; no force or preload result.',
        'Actual material dimensions, print distortion, ball elasticity, dynamic airflow or real one-shot reliability.',
        'This is not an actual feasible adverse-pose witness and is not a complete all-assembly proof.',
    ],
}
after = {p:sha(ROOT/p) for p in before}
assert before == after
report['all_sources_stable'] = True
(OUT/'report.json').write_text(json.dumps(conv(report),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(conv({'status':report['status'],'numeric':report['numeric'],'source_count':len(before)}),ensure_ascii=False,indent=2))
