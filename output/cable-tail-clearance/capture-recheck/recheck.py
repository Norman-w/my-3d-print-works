#!/usr/bin/env python3
"""Narrow independent recheck of capture after the wire slot reaches the ear base."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OLD = ROOT / 'output/cable-output-interface/washer-retention-revision'
CAD = ROOT / 'cad/cable-output-interface.scad'
EXE = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
EXPECTED = '0b8ca954ddfc6df2b9495e5dd4b61eaffe845e28eaa0b5bbff3b2b5599ed17dc'
INSPECT = Path('/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
spec = importlib.util.spec_from_file_location('inspector', INSPECT)
mesh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mesh)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    seen = {Path(__file__).resolve(), INSPECT.resolve()}
    pending = [CAD]
    while pending:
        p = pending.pop().resolve()
        if p in seen:
            continue
        seen.add(p)
        pending += [p.parent / name for name in re.findall(
            r'\b(?:include|use)\s*<([^>]+)>', p.read_text())]
    return {str(p): sha(p) for p in sorted(seen)}


def execute(scad, positive):
    target = scad.with_suffix('.stl')
    if target.exists() or scad.with_suffix('.log').exists():
        raise RuntimeError('Refusing to overwrite evidence: ' + str(scad))
    cmd = [EXE, '--hardwarnings', '--backend', 'Manifold',
           '--export-format', 'asciistl', '-o', str(target), str(scad)]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    log = result.stdout + result.stderr
    scad.with_suffix('.log').write_text(log)
    empty = not target.exists() and 'Current top level object is empty' in log
    execution_ok = ('WARNING:' not in log and 'ERROR:' not in log and
                    ((result.returncode == 0 and target.exists()) or empty))
    info = mesh.inspect(target, 1e-6) if target.exists() else None
    solid = bool(info and info['volume'] > 0 and
                 all(x > 0 for x in info['bounds']['size']))
    row = {'name': scad.stem, 'command': cmd, 'returncode': result.returncode,
           'expected': 'positive solid overlap' if positive else 'empty difference',
           'execution_ok': execution_ok, 'empty': empty, 'mesh': info,
           'scad_sha256': sha(scad), 'stl_sha256': sha(target) if target.exists() else None,
           'passed': execution_ok and (solid if positive else empty)}
    print(row['name'], row['passed'], None if not info else info['volume'], flush=True)
    return row


if (OUT/'report.json').exists():
    raise RuntimeError('Existing report; not overwriting')
if sha(CAD) != EXPECTED:
    raise RuntimeError('Output source does not match the assigned frozen revision')
before = sources()
version = subprocess.run([EXE, '--version'], text=True, capture_output=True)
legacy = json.loads((OLD/'capture-checks.json').read_text())
legacy_files = sorted(OLD.glob('*capture-positive.scad')) + sorted(OLD.glob('washer-tilt-3deg-*.scad'))
rows = []
for original in legacy_files:
    copied = OUT/original.name
    shutil.copyfile(original, copied)
    row = execute(copied, True)
    row['identical_probe_source'] = sha(copied) == sha(original)
    row['legacy_probe_source'] = str(original.relative_to(ROOT))
    row['legacy_scad_sha256'] = sha(original)
    previous = next(x for x in legacy['results'] if x['name'] == row['name'])
    row['legacy_volume_mm3'] = previous['mesh']['volume']
    rows.append(row)

# Positive-sized continuous bars that must be entirely inside the *cut* ear.
# They lie outside the slot or behind it and avoid screw/nut/counterbore regions.
bars = {
    'left-side-continuous-rib': [-65.4, -64.3, 31.0, 38.8, 7.1, 31.9],
    'right-side-continuous-rib': [-54.3, -52.8, 31.2, 34.2, 7.1, 31.9],
    'rear-connecting-web': [-65.4, -47.1, 31.0, 31.5, 10.2, 15.8],
}
for name, box in bars.items():
    scad = OUT/(name+'.scad')
    scad.write_text('use <'+str(CAD)+'>\n' +
        'difference(){co_box('+','.join(str(x) for x in box)+');co_new_lug();}\n')
    row = execute(scad, False)
    row['witness_box'] = box
    row['witness_volume_mm3'] = math.prod(box[i+1]-box[i] for i in [0,2,4])
    rows.append(row)

r = 8.64/2
float_bound = 0.6
slot_half = 2.2/2
span = 2*math.sqrt(r*r-(slot_half+float_bound)**2)
block = math.degrees(math.asin(1/math.hypot(span,.7))-math.atan2(.7,span))
after = sources()
report = {
    'status': 'NOMINAL_CAPTURE_RECHECK_PASS' if before == after and all(x['passed'] for x in rows) else 'FAIL_OR_STALE',
    'timestamp_utc': datetime.now(timezone.utc).isoformat(),
    'source_sha256': before, 'source_sha256_after': after, 'sources_stable': before == after,
    'assigned_output_sha256': EXPECTED,
    'openscad_version': (version.stdout+version.stderr).strip(),
    'legacy_report': str((OLD/'capture-checks.json').relative_to(ROOT)),
    'legacy_report_sha256': sha(OLD/'capture-checks.json'),
    'results': rows,
    'continuous_tilt_reasoning': {
        'slot_width_unchanged_mm': 2.2, 'outside_slot_required_x_offset_mm': slot_half+float_bound,
        'minimum_washer_od_mm': 8.64, 'minimum_washer_thickness_mm': .7,
        'seat_depth_mm': 1.0, 'planar_seat_float_bound_mm': .58,
        'float_bound_through_3deg_mm': 4.9-4.32*math.cos(math.radians(3)),
        'conservative_float_used_mm': float_bound,
        'outside_slot_effective_span_mm': span, 'blocking_angle_degrees': block,
        'reason': 'Extending the slot downwards changes its Z termination, not the X strip. The old proof deliberately chooses an opposed outer-edge point pair outside that full strip. Unchanged cover opening and rear bore do not remove those points.',
        'bottom_wall_change': 'The old 2.8 mm seat-to-ear-bottom dimension is no longer a continuous floor across the wire slot. Retained material exists outside that strip and in the rear connecting web; bars are checked against co_new_lug after all cuts.',
    },
    'scope': 'Five original capture positive controls, eight original 3-degree tilt probes, and three new finite solid rib witnesses only; no whole-system rerun.',
    'limitations': ['Rigid nominal geometry; not PETG strength, thin-section stress, physical fit, screw retention, cable clamp strength, or service life.',
                   'The eight tilt samples alone are not a continuous proof; the unchanged outside-slot support-point argument supplies the stated conditional bound.',
                   'Positive-control intersection topology is recorded and is not a printed-part mesh acceptance test.'],
    'manufacturing_release': False, 'physical_acceptance': False,
}
(OUT/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(report['status'], 'sources_stable', report['sources_stable'], flush=True)
