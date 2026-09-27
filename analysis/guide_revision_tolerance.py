#!/usr/bin/env python3
"""Find and CSG-check bounded rigid poses of the revised guide.

A feasible pose gives a LOWER bound on worst play, never an upper bound.
The deliberately restrictive carrier surrogate and six ramp searches cannot
certify the complete stroke, the other followers, or manufacturing tolerances.
Run with FreeCAD's bundled Python (numpy/scipy); add --verify-csg for solids.
"""
from pathlib import Path
import hashlib
import itertools
import json
import subprocess
import sys

import numpy as np
import feeder_tolerance as base
from feeder_integration import classify

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/guide-revision/tolerance'
SCAD = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'


class RevisedModel(base.ClearanceModel):
    def __init__(self, p, revision, u):
        super().__init__(p, u)
        self.revision = revision
        self.edges = [(a, b) for a, b in itertools.combinations(range(8), 2)
                      if sum(self.vertices[a] != self.vertices[b]) == 1]

    def constraints(self, q, grouped=False):
        groups = super().constraints(q, True)
        tip, carrier, _, _ = self.transform(q)
        vertices = tip + self.vertices @ carrier.T
        x0, x1 = self.revision['revision_x0'], self.revision['revision_x1']
        clipped = [v for v in vertices if x0 <= v[0] <= x1]
        for a, b in self.edges:
            first, second = vertices[a], vertices[b]
            for x in (x0, x1):
                dx = second[0] - first[0]
                if abs(dx) > 1e-12:
                    fraction = (x - first[0]) / dx
                    if 0 <= fraction <= 1:
                        clipped.append(first + fraction * (second - first))
        if not clipped:
            raise ValueError('Carrier no longer overlaps the declared guide slab')
        ys = np.asarray(clipped)[:, 1]
        # These limits apply to the ENTIRE clipped carrier, including its
        # empty mid-band and datum lead-ins. This is stricter than actual CAD;
        # useful only for finding feasible witnesses, not proving maxima.
        groups['restrictive_front_slab'] = [float(min(
            self.revision['revision_datum_y'] - ys))]
        rear = self.revision['revision_front_retracted'] + self.revision['revision_setting']
        groups['restrictive_rear_slab'] = [float(min(ys - rear))]
        # The base model uses a cap constraint beyond x=23.5 and two rod-plane
        # constraints inside. Taking the minimum preserves both requirements
        # while keeping SLSQP's constraint-vector length constant.
        groups['inner_guide_cap_or_rod'] = [min(groups['inner_guide_cap_or_rod'])]
        return groups if grouped else np.concatenate(list(groups.values()))


def transform_matrix(rotation, translation):
    result = np.eye(4)
    result[:3, :3], result[:3, 3] = rotation, translation
    return result.tolist()


def verify(model, q, name):
    tip, carrier, frame, offset = model.transform(q)
    frame_matrix = transform_matrix(frame, model.center + offset - frame @ model.center)
    carrier_matrix = transform_matrix(carrier, tip)
    pin_shift = [model.p['cam_follower_offset'] + q[6], 0, q[7]]
    nut_shift = [pin_shift[0], -model.p['cam_carrier_width']/2 + .2, q[7]]
    src = '''revision_library_mode=true;
include <../../../cad/feeder-guide-revision.scad>
probe_kind="fixed";
t=__T__;
module moving_frame(){multmatrix(__FRAME__) feeder_carriage(t);}
module moved_carrier(){multmatrix(__CARRIER__) cam_finger_local();}
module moved_pin(){multmatrix(__CARRIER__) translate(__PIN__) cam_pin_local();}
module moved_nut(){multmatrix(__CARRIER__) translate(__NUT__)
 rotate([-90,0,0]) difference(){cylinder(h=2.4,d=5.5/cos(30),$fn=6);
 translate([0,0,-.02]) cylinder(h=2.44,d=3,$fn=32);}}
module followers(){moved_carrier();moved_pin();moved_nut();
 for(side=[-1,1],rear=[false,true])if(!(side==1&&!rear)){
 cam_finger(side,rear,t);cam_pin(side,rear,t,0);cam_follower_nut(side,rear,t);}}
module fixed(){feeder_body_full();revision_fixed();revision_gibs();
 feeder_cap_hardware();feeder_mount_hardware();
 for(side=[-1,1],g=[0,-gate_spacing])scale([side,1,1])revision_hardware_local(g);}
if(probe_kind=="fixed")intersection(){fixed();union(){moving_frame();followers();}}
else if(probe_kind=="cam")intersection(){moving_frame();followers();}
else if(probe_kind=="seat")intersection(){moved_carrier();union(){moved_pin();moved_nut();}}
else if(probe_kind=="control")intersection(){revision_fixed();revision_gibs(revision_travel+.1);}
else assert(false,"unknown probe");
'''
    for token, value in [('T', model.u/model.p['cam_stroke']), ('FRAME', frame_matrix),
                         ('CARRIER', carrier_matrix), ('PIN', pin_shift), ('NUT', nut_shift)]:
        src = src.replace('__'+token+'__', json.dumps(value))
    path = OUT / f'{name}.scad'
    path.write_text(src)
    rows = []
    for kind in ['fixed', 'cam', 'seat', 'control']:
        target = OUT / f'{name}-{kind}.stl'
        target.unlink(missing_ok=True)
        result = subprocess.run([SCAD, '--hardwarnings', '--backend', 'Manifold',
            '--export-format', 'asciistl', '-D', f'probe_kind="{kind}"',
            '-o', str(target), str(path)], cwd=ROOT, capture_output=True, text=True)
        log = result.stdout + result.stderr
        (OUT / f'{name}-{kind}.log').write_text(log)
        if 'WARNING:' in log or 'ERROR:' in log:
            raise RuntimeError(log)
        if target.exists():
            row = classify(target)
        elif 'Current top level object is empty' in log:
            row = {'triangle_count': 0, 'components': [], 'has_solid_or_unclassified_overlap': False}
        else:
            raise RuntimeError(log)
        row.update(name=kind, expected_overlap=kind == 'control')
        rows.append(row)
    margin = float(min(model.constraints(q)))
    accepted = margin >= -1e-9 and all(
        row['has_solid_or_unclassified_overlap'] == row['expected_overlap'] for row in rows)
    return {'name': name, 'stroke_mm': model.u, 'variables': q.tolist(),
            'tip_offset_xyz_mm': q[:3].tolist(), 'analytic_minimum_margin_mm': margin,
            'pose_csg_verified': bool(accepted), 'probes': rows,
            'source': {'path': str(path.relative_to(ROOT)),
                       'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p, sources = base.load()
    revision_source = ROOT / 'cad/feeder-guide-revision.scad'
    sources[str(revision_source.relative_to(ROOT))] = revision_source.read_text()
    sources['analysis/feeder_tolerance.py'] = (ROOT/'analysis/feeder_tolerance.py').read_text()
    sources['analysis/guide_revision_tolerance.py'] = Path(__file__).read_text()
    rev = {key: base.literal(revision_source.read_text(), key) for key in (
        'revision_x0', 'revision_x1', 'revision_datum_y', 'revision_front_retracted',
        'revision_setting', 'revision_bias_y')}
    assert rev['revision_bias_y'] == 0, 'Review pose references for a biased follower'
    hashes = {name: hashlib.sha256(content.encode()).hexdigest() for name, content in sources.items()}
    rows, candidates = [], []
    for u in [14., 17., 19.]:
        model = RevisedModel(p, rev, u)
        for sign in [1, -1]:
            result = model.solve(np.zeros(13), sign)
            margin = float(min(model.constraints(result.x)))
            row = {'stroke_mm': u, 'direction': sign, 'solver_success': bool(result.success),
                   'tip_x_offset_mm': float(result.x[0]), 'minimum_margin_mm': margin,
                   'variables': result.x.tolist()}
            rows.append(row)
            if result.success and margin >= -1e-7:
                candidates.append((model, result.x))
    witnesses = []
    if '--verify-csg' in sys.argv:
        for sign, name in [(1, 'outward'), (-1, 'inward')]:
            model, q = max(candidates, key=lambda candidate: sign*candidate[1][0])
            q = q*.995
            # Scaling a rotation toward zero need not move its extrema inward
            # from an asymmetric slab. Explicitly move 0.0002mm off its front
            # datum and recheck ALL analytic constraints and actual solids.
            # A previous attempt without this shift had negative analytic
            # margins and was rejected, despite near-planar mesh contacts.
            q[1] -= .0002
            witnesses.append(verify(model, q, name))
    stable = all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest
                 for name, digest in hashes.items())
    verified = [abs(w['tip_offset_xyz_mm'][0]) for w in witnesses if w['pose_csg_verified']]
    report = {
        'status': 'BOUNDED_RIGID_POSES_VERIFIED_NOT_GLOBAL_BOUND' if stable and len(verified) == 2
                  else 'BOUNDED_SEARCH_ONLY_OR_CSG_REJECTED',
        'source_sha256': hashes, 'sources_stable': stable, 'revision_parameters': rev,
        'local_searches': rows, 'csg_witnesses': witnesses,
        'worst_play_lower_bound_mm': max(verified) if verified else None,
        'certified_worst_play_upper_bound_mm': None,
        'largest_possible_remaining_1mm_budget_mm': 1-max(verified) if verified else None,
        'manufacturing_release': False, 'physical_acceptance': 'OPEN',
        'limits': [
            'Only the +X front follower at three interior points of its linear ramp is optimized.',
            'The whole-box baseline and full-height narrow slab are restrictive feasibility surrogates; they exclude real possible poses.',
            'A local optimizer maximum and absence of a new >1mm witness never prove the global bound is below 1mm.',
            'CSG checks every fixed solid and all four followers at each recorded pose; it does not prove a continuous reachable loaded path.',
            'Printed errors, seam alignment, deformation, friction, wear and spring loads are not included.',
            'Remaining budget is only an upper limit on room left by an existing pose, not a validated manufacturing allowance.',
            'Offsets refer to the front +X fingertip X component, not radial-distance change or a three-dimensional norm.',
            'The optimized follower nut seats at carrier-local Y=-4.3; the other three use the original display placements.',
        ]}
    artifacts = [path for path in OUT.iterdir() if path.suffix in ('.scad', '.log', '.stl')]
    report['source_and_artifact_sha256'] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts}
    (OUT/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(report['status'])
    print(json.dumps({key: report[key] for key in (
        'worst_play_lower_bound_mm', 'largest_possible_remaining_1mm_budget_mm')}, indent=2))
    return 0 if stable and len(verified) == 2 else 1


if __name__ == '__main__':
    sys.exit(main())
