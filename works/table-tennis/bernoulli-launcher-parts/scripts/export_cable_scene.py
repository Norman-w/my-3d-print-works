#!/usr/bin/env python3
"""Export an explicit current scene inventory, retaining per-instance evidence.

Assembly coordinates and source dependencies are preserved. This is neither a
print arrangement nor a manufacturing release. Historical exports are untouched.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / 'docs/cable-assembly-inventory.json'
EXE = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
INSPECTOR = Path('/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py')
sys.path.insert(0, str(ROOT / 'analysis'))
from exact_mesh import exact_area_and_links
from feeder_integration import classify

spec = importlib.util.spec_from_file_location('scene_mesh_inspector', INSPECTOR)
mesh_inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mesh_inspector)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources(inventory):
    paths = {Path(__file__).resolve(), INVENTORY,
             ROOT / 'analysis/exact_mesh.py', ROOT / 'analysis/feeder_integration.py'}
    pending = [ROOT / row['source'] for row in inventory['parts']]
    while pending:
        path = pending.pop().resolve()
        path.relative_to(ROOT)
        if path in paths:
            continue
        paths.add(path)
        pending.extend(path.parent / dep for dep in re.findall(
            r'\b(?:use|include)\s*<([^>]+)>', path.read_text()))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}


def run(command, log_path):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    log = result.stdout + result.stderr
    log_path.write_text(log)
    return {'command': command, 'returncode': result.returncode,
            'log': str(log_path.relative_to(ROOT)),
            'execution_ok': result.returncode == 0 and 'WARNING:' not in log and 'ERROR:' not in log}


def export_fixed_components(row, output, name, target):
    """Compose display triangles, preserving the separately verified CGAL pin.

    This is an assembly display, never a fused/printable solid. Verify the exact
    parent composition so a future hardware addition cannot silently disappear.
    """
    assert row['id'] == 'feeder/cable-input-hardware-fixed' and row['role'] == 'purchased'
    source = ROOT / 'cad/cable-trigger-input.scad'
    compact = re.sub(r'\s+', '', re.sub(r'//[^\n]*|/\*[\s\S]*?\*/', '', source.read_text()))
    required = [
        'module ci_local_fixed_axis_hardware(){ci_local_axis_pin();ci_local_tail_washers();ci_local_thrust_washers();}',
        'module ci_local_fixed_hardware(delta=ci_delta){ci_local_fixed_axis_hardware();ci_local_other_fixed_hardware(delta);}',
        'module ci_fixed_hardware(delta=ci_delta){ci_mount_hardware_cad();ci_to_cad()ci_local_fixed_hardware(delta);}',
    ]
    assert all(re.sub(r'\s+', '', s) in compact for s in required), 'Fixed hardware composition changed: audit display partition'
    recipes = [
        ('pin', 'CGAL', 'ci_axis_pin();'),
        ('other', 'Manifold', 'ci_mount_hardware_cad();ci_to_cad(){ci_local_other_fixed_hardware();ci_local_tail_washers();ci_local_thrust_washers();}'),
    ]
    pieces, facets = [], []
    for label, backend, expression in recipes:
        wrapper = output / (name + '-' + label + '.scad')
        wrapper.write_text('use <' + str(source) + '>\n$fn=72;\n' + expression + '\n')
        file = wrapper.with_suffix('.stl')
        item = run([EXE, '--hardwarnings', '--backend', backend, '--export-format', 'asciistl',
                    '-o', str(file), str(wrapper)], wrapper.with_suffix('.log'))
        item.update(label=label, backend=backend, wrapper=str(wrapper.relative_to(ROOT)), wrapper_sha256=sha(wrapper))
        if item['execution_ok'] and file.exists():
            item.update(file=str(file.relative_to(ROOT)), sha256=sha(file), mesh=mesh_inspector.inspect(file, 1e-6))
            if label == 'pin':
                m = item['mesh']
                item['execution_ok'] = m['watertightByEdgeTopology'] and m['degenerateTriangleCount'] == 0
            chunks = re.findall(r'\bfacet normal\b[\s\S]*?\bendfacet\b', file.read_text())
            assert len(chunks) == item['mesh']['triangleCount']
            facets.extend(chunks)
        pieces.append(item)
    ok = all(p['execution_ok'] for p in pieces)
    if ok:
        target.write_text('solid fixed_hardware_display\n' + '\n'.join(facets) + '\nendsolid fixed_hardware_display\n')
    return {'execution_ok':ok, 'components_export':pieces,
            'display_composition':'Triangle concatenation of separate source parts; no Boolean fusion or printable-solid claim.'}


def export(row, output):
    name = row['id'].replace('/', '__')
    target = output / (name + '.stl')
    command = [EXE, '--hardwarnings', '--backend', row.get('backend', 'Manifold'),
               '--export-format', 'asciistl']
    for key, value in row['definitions'].items():
        command.extend(['-D', key + '=' + json.dumps(value)])
    command.extend(['-o', str(target), str(ROOT / row['source'])])
    if row.get('export_mode') == 'separate-axis-pin-display-merge':
        result = {**row, **export_fixed_components(row, output, name, target), 'passed':False}
    else:
        result = {**row, **run(command, output / (name + '.log')), 'passed': False}
    if target.exists() and target.stat().st_size:
        result.update(file=str(target.relative_to(ROOT)), sha256=sha(target), bytes=target.stat().st_size)
        try:
            result['mesh'] = mesh_inspector.inspect(target, 1e-6)
            if row['role'] == 'printed':
                result['topology'] = exact_area_and_links(target)
                result['components'] = len(classify(target)['components'])
                wrapper = output / (name + '-reimport.scad')
                wrapper.write_text('intersection(){import(' + json.dumps(target.name) +
                                   ');cube([10000,10000,10000],center=true);}\n')
                reimported = output / (name + '-reimport.stl')
                result['boolean_reimport'] = run(
                    [EXE, '--hardwarnings', '--backend', 'CGAL', '--export-format', 'asciistl',
                     '-o', str(reimported), str(wrapper)], output / (name + '-reimport.log'))
                result['passed'] = bool(result['execution_ok'] and
                    result['mesh']['watertightByEdgeTopology'] and result['components'] == 1 and
                    not result['topology']['exact_zero_area_face_indices'] and
                    not result['topology']['non_ring_vertex_links'] and
                    result['boolean_reimport']['execution_ok'] and reimported.exists())
            else:
                result['passed'] = result['execution_ok'] and result['mesh']['triangleCount'] > 0
                result['display_only'] = 'Reference assembly may contain multiple touching bodies; no printable-solid claim.'
        except Exception as error:
            result['inspection_error'] = str(error)
    print(row['id'], result['passed'], flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    inventory = json.loads(INVENTORY.read_text())
    rows = inventory['parts']
    ids = [row['id'] for row in rows]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[a-z0-9-]+/[a-z0-9-]+', i) for i in ids):
        raise ValueError('Inventory ids must be unique safe group/id names')
    if any(row['role'] not in ('printed', 'purchased', 'reference') for row in rows):
        raise ValueError('Unknown inventory role')
    output = ROOT / 'output/cable-scene-export' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True)
    before = sources(inventory)
    (output / 'inventory.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    with ThreadPoolExecutor(max_workers=max(1, min(4, args.workers))) as pool:
        results = list(pool.map(lambda row: export(row, output), rows))
    stable = before == sources(inventory)
    passed = stable and all(row['passed'] for row in results)
    report = {'status': 'CURRENT_SCENE_EXPORT_PASS' if passed else 'FAIL_OR_STALE',
              'source_sha256': before, 'external_inspector': {'path': str(INSPECTOR), 'sha256': sha(INSPECTOR)},
              'sources_stable': stable, 'inventory_sha256': before[str(INVENTORY.relative_to(ROOT))],
              'parts': results, 'printed_instances': sum(row['role'] == 'printed' for row in rows),
              'scope': 'Listed current-source assembly instances. Printed meshes checked for edge topology, exact area, vertex links, connectivity and CGAL reimport. No full-assembly collision, slicing or load claim.',
              'manufacturing_release': False, 'physical_acceptance': False}
    target = output / 'report.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(report['status'], target, flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
