#!/usr/bin/env python3
"""Slice the current cable candidates offline, preserving source and transform evidence.

Run with FreeCAD's bundled Python (numpy). This writes review artifacts only;
it never connects to a printer or modifies CAD/shared Bambu profiles.
"""
from pathlib import Path
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import math
import re
import shutil
import struct
import subprocess
import traceback
import zipfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'output/print-review/config'
DEFAULT_REPORT = ROOT / 'output/cable-scene-export/20260927T071458613482Z/report.json'
BAMBU = Path('/Applications/BambuStudio.app/Contents/MacOS/BambuStudio')
FIELDS = ['machine_start_gcode', 'machine_end_gcode', 'time_lapse_gcode',
          'change_filament_gcode', 'layer_change_gcode']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def rot(axis, degrees):
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    if axis == 'x': return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == 'y': return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


N = (0.263804000343, -0.964576305641)
PLAN = {
    'cable-input-cover': ('ci_cover', rot('x', -90), False, .1, 'Y-; 0.1 mm layers for 4.3/4.5 mm seating datums'),
    'cable-output-cap': ('co_cap', rot('x', -90), False, .1, 'Y-; 0.1 mm layers for 3.3 mm bearing datum'),
    'cable-route-cap': ('crr_cap', np.array([[0, 0, 1], [-N[1], N[0], 0], [-N[0], -N[1], 0]]), False, .2, 'N-'),
    'cable-route-lower': ('crr_lower', rot('x', 180), False, .2, 'Z-'),
    'cable-input-lever': ('ci_lever', rot('x', 90), False, .2, 'Y+; initial no-support diagnostic'),
    'cable-input-body': ('ci_body', rot('x', 90), True, .2, 'Y+; external tree support candidate'),
    'frame': ('co_frame', rot('x', 90), True, .2, 'Y+'),
    'beam-grip': ('co_beam', rot('z', 62) @ rot('x', 90) @ rot('z', -2.5), True, .2, 'B1'),
    'cable-route-base': ('crr_base', rot('y', -90), True, .2, 'X+'),
}
DIAGNOSTIC_PLAN = {
    'cable-input-terminal-cap': ('cil_terminal_cap', rot('x', -90), False, .1,
                               'Y-; split terminal-cap diagnostic only'),
}


def read_stl(path):
    b = Path(path).read_bytes()
    n = struct.unpack_from('<I', b, 80)[0] if len(b) >= 84 else 0
    if len(b) == 84 + n * 50:
        dtype = np.dtype([('normal', '<f4', 3), ('vertices', '<f4', (3, 3)), ('attr', '<u2')])
        return np.frombuffer(b, dtype=dtype, offset=84)['vertices'].astype(float)
    return np.array(re.findall(rb'vertex\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)\s+([-+eE.0-9]+)', b), float).reshape(-1, 3, 3)


def write_stl(path, t):
    # Keep ASCII double precision: Float32 STL can collapse micron-sized facets
    # in an otherwise valid CAD Boolean mesh. No welding or deletion is applied.
    normals = np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    assert (lengths > 0).all(), 'Degenerate transformed triangle'
    normals /= lengths[:, None]
    with Path(path).open('w') as out:
        out.write('solid oriented_cable_review_mm\n')
        for normal, tri in zip(normals, t):
            out.write(' facet normal ' + ' '.join(format(v, '.17g') for v in normal) + '\n  outer loop\n')
            for point in tri:
                out.write('   vertex ' + ' '.join(format(v, '.17g') for v in point) + '\n')
            out.write('  endloop\n endfacet\n')
        out.write('endsolid oriented_cable_review_mm\n')


def current_sources(expected):
    return {p: sha(ROOT / p) for p in expected}


def run_one(part, export, report_path, out, shared, support_mode='plan', layer_override=None):
    selector, R, supported, layer, description = {**PLAN, **DIAGNOSTIC_PLAN}[part]
    if layer_override is not None:
        layer = layer_override
        description += '; diagnostic layer override=' + str(layer)
    if support_mode != 'plan':
        supported = support_mode == 'on'
        description += '; diagnostic support override=' + support_mode
    row = next(v for v in export['parts'] if v['id'] == 'feeder/' + part)
    selector = row.get('selector', selector)
    assert sha(ROOT / row['file']) == row['sha256']
    assert current_sources(export['source_sha256']) == export['source_sha256']
    assert np.allclose(R.T @ R, np.eye(3), atol=1e-10) and abs(np.linalg.det(R)-1) < 1e-10
    folder = out / part
    folder.mkdir()
    original = read_stl(ROOT / row['file'])
    transformed = original @ R.T
    lo, hi = transformed.min(axis=(0, 1)), transformed.max(axis=(0, 1))
    shift = -(lo + hi) / 2
    shift[2] = -lo[2]
    transformed += shift
    affine = np.eye(4)
    affine[:3, :3], affine[:3, 3] = R, shift
    oriented = folder / 'oriented.stl'
    write_stl(oriented, transformed)
    reread = read_stl(oriented)
    max_error = float(np.max(np.abs(reread - transformed)))
    assert max_error < 1e-12, 'ASCII reorientation lost excessive coordinate precision'
    assert np.all(np.linalg.norm(np.cross(reread[:, 1]-reread[:, 0], reread[:, 2]-reread[:, 0]), axis=1) > 0)
    for name in ['machine', 'filament']:
        shutil.copy2(CONFIG / (name + '.json'), folder / (name + '.json'))
    process = json.loads((CONFIG / 'process.json').read_text())
    process.update(enable_support='1' if supported else '0', support_type='tree(auto)',
                   support_on_build_plate_only='1', layer_height=str(layer),
                   initial_layer_print_height=str(layer), brim_type='outer_only', brim_width='5')
    dump(folder / 'process.json', process)
    cmd = [str(BAMBU), '--datadir', str(folder/'app-data'), '--load-settings',
           str(folder/'machine.json')+';'+str(folder/'process.json'), '--load-filaments',
           str(folder/'filament.json'), '--orient', '0', '--arrange', '1', '--ensure-on-bed',
           '--slice', '0', '--export-3mf', 'slice-review.3mf', '--outputdir', str(folder), str(oriented)]
    inv = {
        'part': part, 'selector': selector, 'command': cmd, 'orientation': description,
        'cad_to_oriented': affine.tolist(),
        'input': {k: row[k] for k in ['id', 'file', 'sha256']},
        'oriented': {'file': str(oriented), 'sha256': sha(oriented)},
        'oriented_bounds_mm': [reread.min(axis=(0, 1)).tolist(), reread.max(axis=(0, 1)).tolist()],
        'stl_encoding': 'ASCII 17 significant digits', 'roundtrip_max_vertex_error_mm': max_error,
        'triangle_count_preserved': len(original) == len(reread),
        'export_report': str(report_path), 'export_report_sha256': sha(report_path),
        'export_status': export['status'],
        'diagnostic_candidate': export.get('diagnostic_candidate'),
        'source_sha256_at_start': export['source_sha256'], 'shared_profile_sha256': shared,
        'local_profile_sha256': {n: sha(folder/(n+'.json')) for n in shared},
        'assumptions': {'machine': 'X1C 0.4 confirmed', 'material': 'Generic PETG; brand unconfirmed',
                        'plate': 'Textured PEI analysis assumption; only PEI confirmed',
                        'layer_height_mm': layer, 'walls': 4, 'infill_percent': 25,
                        'support': 'tree(auto), build plate only' if supported else 'disabled',
                        'brim_mm': 5},
        'sent_to_printer': False, 'manufacturing_release': False, 'physical_acceptance': False,
    }
    dump(folder/'invocation.json', inv)
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (folder/'bambu-cli.log').write_text(result.stdout + result.stderr)
    inv['return_code'] = result.returncode
    if (folder/'result.json').exists(): inv['native_result'] = json.loads((folder/'result.json').read_text())
    inv['input_and_cad_stable'] = (sha(ROOT/row['file']) == row['sha256'] and
                                 current_sources(export['source_sha256']) == export['source_sha256'])
    inv['shared_profiles_untouched'] = all(sha(CONFIG/(n+'.json')) == h for n, h in shared.items())
    inv['artifact_sha256'] = {n: sha(folder/n) for n in ['plate_1.gcode', 'slice-review.3mf'] if (folder/n).exists()}
    if (folder/'plate_1.gcode').exists():
        g = (folder/'plate_1.gcode').read_text()
        first = g.index('; CHANGE_LAYER')
        heats = re.findall(r'^M10[49]\b[^\n;]*?\bS([-+\d.]+)', g[:first], re.M)
        inv['last_temperature_before_first_layer_c'] = float(heats[-1]) if heats else None
    if (folder/'slice-review.3mf').exists():
        with zipfile.ZipFile(folder/'slice-review.3mf') as z:
            if 'Metadata/plate_1.png' in z.namelist():
                (folder/'plate-preview.png').write_bytes(z.read('Metadata/plate_1.png'))
    native = inv.get('native_result', {})
    inv['status'] = 'SLICE_GENERATED_REVIEW_REQUIRED' if (result.returncode == 0 and
        native.get('return_code') == 0 and len(inv['artifact_sha256']) == 2 and
        inv['input_and_cad_stable'] and inv['shared_profiles_untouched']) else 'SLICE_FAILED_OR_STALE'
    dump(folder/'invocation.json', inv)
    brief = {'part': part, 'status': inv['status'], 'folder': str(folder),
             'warnings': [p.get('warning_message') for p in native.get('sliced_plates', [])]}
    print(json.dumps(brief, ensure_ascii=False), flush=True)
    return brief


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--export-report', type=Path, default=DEFAULT_REPORT)
    parser.add_argument('--parts', nargs='+', choices=[*PLAN, *DIAGNOSTIC_PLAN], default=list(PLAN))
    parser.add_argument('--workers', type=int, choices=[1, 2], default=2)
    parser.add_argument('--support', choices=['plan', 'on', 'off'], default='plan')
    parser.add_argument('--layer-height', type=float, choices=[.1, .2],
                        help='Explicit diagnostic layer height; leaves the named plan unchanged')
    parser.add_argument('--allow-diagnostic-candidate', action='store_true',
                        help='Accept an explicitly labeled candidate export; does not change the current inventory')
    args = parser.parse_args()
    report_path = args.export_report.resolve()
    export = json.loads(report_path.read_text())
    diagnostic = export['status'] == 'DIAGNOSTIC_CANDIDATE_EXPORT'
    assert export['status'] == 'CURRENT_SCENE_EXPORT_PASS' or (diagnostic and args.allow_diagnostic_candidate)
    assert not any(p in DIAGNOSTIC_PLAN for p in args.parts) or diagnostic
    assert current_sources(export['source_sha256']) == export['source_sha256']
    official = BAMBU.parent.parent / 'Resources/profiles/BBL/machine'
    machine = json.loads((CONFIG/'machine.json').read_text())
    assert all(machine[f] == json.loads((official/f'Bambu Lab X1 Carbon 0.4 nozzle template {f}.json').read_text())[f] for f in FIELDS)
    shared = {n: sha(CONFIG/(n+'.json')) for n in ['machine', 'process', 'filament']}
    out = ROOT/'output/print-review/current-cable'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    dump(out/'snapshot.json', {'export_report': str(report_path), 'export_report_sha256': sha(report_path),
                             'source_sha256': export['source_sha256'], 'shared_profiles': shared,
                             'parts': args.parts, 'runner_sha256': sha(__file__), 'bambu_binary_sha256': sha(BAMBU)})
    print('OUTPUT=' + str(out), flush=True)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(run_one, p, export, report_path, out, shared, args.support, args.layer_height): p for p in args.parts}
        for task in concurrent.futures.as_completed(jobs):
            try: results.append(task.result())
            except Exception as exc:
                row = {'part': jobs[task], 'status': 'EXECUTION_ERROR', 'error': repr(exc), 'traceback': traceback.format_exc()}
                results.append(row)
                print(json.dumps(row), flush=True)
            dump(out/'progress.json', results)
    stable = current_sources(export['source_sha256']) == export['source_sha256']
    report = {'status': 'OFFLINE_SLICES_GENERATED_REVIEW_REQUIRED' if stable and all(r['status'] == 'SLICE_GENERATED_REVIEW_REQUIRED' for r in results) else 'SLICE_BATCH_INCOMPLETE',
              'source_stable': stable, 'parts': results, 'scope': 'Native slice generation only; support removal, toolpath features, strength and physical fit need separate evidence.',
              'diagnostic_candidate': export.get('diagnostic_candidate'),
              'manufacturing_release': False, 'physical_acceptance': False, 'sent_to_printer': False}
    dump(out/'report.json', report)
    print(json.dumps({'status': report['status'], 'report': str(out/'report.json')}), flush=True)


if __name__ == '__main__':
    main()
