#!/usr/bin/env python3
"""Validate the source-level support pocket overrun; never repair STL triangles.

All generated files stay in output/support-export-fix. Exact decimal-rational
triangle area is checked separately from welded edge and single-cycle links.
CGAL reimport is a real intersection, not an import-only passthrough.
"""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import math
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/support-export-fix'
EXE = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
OLD_HASH = '848a9a02b33a66c4f0c798a4f4e382fbb867495fe074bc5e8ac5fb3735b4e40e'
FIXED_HASH = 'c95d3897032e549abeb42f416e6472b46e32f74863cc93dd3da68ad39193cc21'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def closure():
    result = set()
    pending = [ROOT / 'cad/feeder-cam-guide-revision.scad']
    while pending:
        p = pending.pop().resolve()
        if p in result:
            continue
        result.add(p)
        pending.extend(p.parent / name for name in re.findall(
            r'\b(?:include|use)\s*<([^>]+)>', p.read_text()))
    return sorted(result)


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def mesh(path):
    text = path.read_text()
    vertices = re.findall(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)', text)
    assert vertices and len(vertices) % 3 == 0
    raw = [[tuple(Fraction(c) for c in v) for v in vertices[i:i+3]]
           for i in range(0, len(vertices), 3)]
    triangles = [[tuple(float(c) for c in v) for v in t] for t in raw]
    zero = [i for i, (a, b, c) in enumerate(raw)
            if cross(sub(b, a), sub(c, a)) == (0, 0, 0)]
    # Welding tolerances are reported. Exact zero area is checked BEFORE this.
    edges = Counter()
    orient = Counter()
    links = defaultdict(lambda: defaultdict(Counter))
    face_neighbours = defaultdict(set)
    owners = {}
    for i, tri in enumerate(triangles):
        keys = [tuple(round(c / 1e-6) for c in v) for v in tri]
        for k, a in enumerate(keys):
            b, c = keys[(k+1) % 3], keys[(k+2) % 3]
            links[a][b][c] += 1
            links[a][c][b] += 1
            edge = tuple(sorted((a, b)))
            edges[edge] += 1
            orient[edge] += 1 if (a, b) == edge else -1
            if edge in owners:
                j = owners[edge]
                face_neighbours[i].add(j)
                face_neighbours[j].add(i)
            else:
                owners[edge] = i
    bad_links = []
    for point, graph in links.items():
        seen, pending = set(), [next(iter(graph))]
        while pending:
            v = pending.pop()
            if v in seen:
                continue
            seen.add(v)
            pending.extend(graph[v])
        if len(seen) != len(graph) or any(sum(v.values()) != 2 for v in graph.values()):
            bad_links.append([c*1e-6 for c in point])
    seen, components = set(), 0
    for i in range(len(triangles)):
        if i in seen:
            continue
        components += 1
        pending = [i]
        while pending:
            j = pending.pop()
            if j in seen:
                continue
            seen.add(j)
            pending.extend(face_neighbours[j])
    flat = [p for tri in triangles for p in tri]
    areas = [math.sqrt(dot(n, n))/2 for a, b, c in triangles
             for n in [cross(sub(b, a), sub(c, a))]]
    volume = sum(dot(a, cross(b, c))/6 for a, b, c in triangles)
    bounds = [[min(v[k] for v in flat), max(v[k] for v in flat)] for k in range(3)]
    r = {'sha256': digest(path), 'triangle_count': len(triangles),
         'zero_area_face_indices_0_based': zero,
         'area_method': 'Exact Fraction of ASCII decimal coordinates; cross=(0,0,0)',
         'minimum_area_mm2': min(areas), 'area_mm2': sum(areas),
         'signed_volume_mm3': volume, 'bounds_mm': bounds,
         'size_mm': [b-a for a, b in bounds], 'weld_tolerance_mm': 1e-6,
         'boundary_edges': sum(n == 1 for n in edges.values()),
         'nonmanifold_edges': sum(n != 2 for n in edges.values()),
         'inconsistent_edges': sum(orient[e] != 0 for e in edges),
         'non_single_cycle_vertex_links': bad_links, 'components': components}
    r['passed'] = not zero and not bad_links and components == 1 and volume > 0 and not any(
        r[k] for k in ['boundary_edges', 'nonmanifold_edges', 'inconsistent_edges'])
    return r


def run(name, source, suffix='.stl', extra=(), allow_empty=False):
    target = OUT / (name + suffix)
    target.unlink(missing_ok=True)
    cmd = [EXE, '--hardwarnings', '--backend', 'CGAL', '-o', str(target)]
    if suffix == '.stl':
        cmd += ['--export-format', 'asciistl']
    cmd += list(extra) + [str(source)]
    p = subprocess.run(cmd, cwd=OUT, capture_output=True, text=True, timeout=240)
    log = p.stdout + p.stderr
    (OUT / (name + '.log')).write_text(log)
    empty = 'Current top level object is empty' in log
    errors = bool(re.search(r'WARNING:|ERROR:|CGAL error|assertion violation', log))
    success = not errors and ((p.returncode == 0 and target.exists() and target.stat().st_size > 0)
                              or (allow_empty and empty and not target.exists()))
    result = {'name': name, 'command': cmd, 'returncode': p.returncode,
              'warnings_or_errors': errors, 'empty': empty,
              'file': str(target.relative_to(ROOT)) if target.exists() else None,
              'passed': success}
    if success and target.exists() and suffix == '.stl':
        result['mesh'] = mesh(target)
    return result


def entry(tree, side):
    return (f'use <{tree}/feeder-cam-guide-revision.scad>\n'
            f'use <{tree}/feeder-guide-revision.scad>\n'
            f'use <{tree}/feeder-supports.scad>\n'
            + ('cg_right_support();\n' if side == 'right' else
               'union(){mirror([1,0,0])revision_side_support_local();feeder_spring_fixed_interface();}\n'))


def scoped_source(tree, side):
    # OpenSCAD disallows use inside modules. Expand the actual include chain;
    # its use-only modules belong to display/probes and are not called here.
    # Keep all included definitions/parameters unchanged, in an isolated scope.
    def expand(path):
        text = path.read_text()
        text = re.sub(r'\buse\s*<[^>]+>\s*;?', '', text)
        return re.sub(r'\binclude\s*<([^>]+)>',
                      lambda m: expand(path.parent / m.group(1)), text)
    return ('cg_library_mode=true;\n' + expand(OUT / tree / 'feeder-cam-guide-revision.scad')
            + ('\ncg_right_support();\n' if side == 'right' else
               '\nunion(){mirror([1,0,0])revision_side_support_local();feeder_spring_fixed_interface();}\n'))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source_paths = closure()
    before = {str(p.relative_to(ROOT)): digest(p) for p in source_paths}
    assert before['cad/feeder-guide-revision.scad'] == FIXED_HASH
    old_source = OUT / 'before/feeder-guide-revision.scad'
    assert digest(old_source) == OLD_HASH
    # Complete private snapshots give reproducible controls without changing CAD.
    for kind in ['fixed-source', 'unfixed-source']:
        tree = OUT / kind
        tree.mkdir(exist_ok=True)
        for source in source_paths:
            shutil.copy2(source, tree / source.name)
        if kind == 'unfixed-source':
            shutil.copy2(old_source, tree / old_source.name)
    jobs = []
    for side in ['right', 'left']:
        for version, tree in [('fixed', 'fixed-source'), ('unfixed', 'unfixed-source')]:
            name = f'{side}-support' if version == 'fixed' else f'unfixed-{side}-support'
            scad = OUT / (name + '.scad')
            scad.write_text(entry(tree, side))
            jobs.append((name, scad))
    with ThreadPoolExecutor(max_workers=2) as pool:
        exports = list(pool.map(lambda args: run(*args), jobs))
    # Deliberate old source stays a genuine failing export, not deleted bad faces.
    reimports = []
    for row in exports:
        if not row['passed']:
            continue
        name = row['name'] + '-boolean-reimport'
        scad = OUT / (name + '.scad')
        scad.write_text('intersection(){import("' + row['name'] + '.stl");'
                        'cube([1000,1000,1000],center=true);}\n')
        r = run(name, scad)
        control = row['name'].startswith('unfixed-')
        r['expected_failure_control'] = control
        r['expected_result_observed'] = not r['passed'] if control else (
            r['passed'] and r.get('mesh', {}).get('passed', False))
        if r['passed'] and not control:
            r['volume_difference_mm3'] = abs(r['mesh']['signed_volume_mm3'] - row['mesh']['signed_volume_mm3'])
            r['expected_result_observed'] &= r['volume_difference_mm3'] < 1e-4
        reimports.append(r)
    # Nested library scopes keep old and new module definitions separate.
    deltas = []
    for side in ['right', 'left']:
        scopes = ('module old(){' + scoped_source('unfixed-source', side) + '}\n'
                  'module revised(){' + scoped_source('fixed-source', side) + '}\n')
        for kind, body in [('removed', 'difference(){old();revised();}'),
                           ('added', 'difference(){revised();old();}'),
                           ('outside-band', 'difference(){difference(){old();revised();}'
                            + ('union(){' if side == 'right' else 'mirror([1,0,0])union(){')
                            + 'for(g=[0,-28.5])translate([57.999,-14.001,g-4.301])cube([.022,9.322,8.602]);}}')]:
            name = f'{side}-{kind}'
            scad = OUT / (name + '.scad')
            scad.write_text(scopes + body + '\n')
            r = run(name, scad, allow_empty=kind != 'removed')
            r['expected_empty'] = kind != 'removed'
            r['expected_result_observed'] = r['passed'] and (r['empty'] if kind != 'removed' else
                bool(r.get('mesh')) and r['mesh']['signed_volume_mm3'] > 0)
            deltas.append(r)
    # Removed-only material inside the proved end band cannot add a motion or
    # tool obstruction; datum/ear working faces lie strictly outside that band.
    # Keep two small positive stop checks rather than repeat unrelated full
    # assembly CGAL sweeps (which include intentional planar contacts).
    probes = []
    for kind in ['overtravel', 'overtravel_back']:
        scad = OUT / ('guide-' + kind + '.scad')
        scad.write_text('revision_library_mode=true;\n'
                        'include <fixed-source/feeder-guide-revision.scad>\n'
                        f'revision_probe="{kind}";\nrevision_probe_geometry();\n')
        r = run('guide-' + kind, scad, allow_empty=True)
        want_solid = kind.startswith('overtravel')
        r['expected_overlap_control'] = want_solid
        r['expected_result_observed'] = r['passed'] and (bool(r.get('mesh')) and
            abs(r['mesh']['signed_volume_mm3']) > 1e-5 if want_solid else r['empty'])
        probes.append(r)
    previews = []
    for side in ['right', 'left']:
        for view, camera in [('iso', '54,3,-15,65,0,35,210'),
                             ('front', '54,3,-15,90,0,0,210'),
                             ('top', '54,3,-15,0,0,0,210')]:
            if side == 'left':
                camera = camera.replace('54,', '-54,', 1)
            previews.append(run(f'{side}-{view}', OUT / f'{side}-support.scad', '.png',
                ['--imgsize=1100,900', '--viewall', f'--camera={camera}']))
    after = {str(p.relative_to(ROOT)): digest(p) for p in source_paths}
    fixed = [x for x in exports if not x['name'].startswith('unfixed')]
    controls = [x for x in exports if x['name'].startswith('unfixed')]
    passed = before == after and len(fixed) == 2 and all(
        x['passed'] and x.get('mesh', {}).get('passed') for x in fixed)
    passed &= len(controls) == 2 and all(x['passed'] and not x['mesh']['passed'] for x in controls)
    passed &= len(reimports) == 4 and all(x['expected_result_observed'] for x in reimports)
    passed &= all(x['expected_result_observed'] for x in deltas + probes)
    passed &= all(x['passed'] for x in previews)
    outcomes = ([x['passed'] and x.get('mesh', {}).get('passed', False) for x in fixed]
        + [x['passed'] and not x['mesh']['passed'] for x in controls]
        + [x['expected_result_observed'] for x in reimports + deltas + probes]
        + [x['passed'] for x in previews])
    report = {'status': 'SUPPORT_SOURCE_EXPORT_FIX_PASS' if passed else 'FAIL_OR_STALE',
        'case_count': len(outcomes), 'pass_count': sum(outcomes),
        'source_sha256': before, 'sources_stable': before == after,
        'analysis_sha256': digest(Path(__file__)), 'old_guide_sha256': OLD_HASH,
        'fixed_guide_sha256': FIXED_HASH, 'exports': exports, 'boolean_reimports': reimports,
        'source_deltas': deltas, 'functional_probes': probes, 'previews': previews,
        'contract': {'units': 'mm', 'process': 'FDM, X1C, 0.4 nozzle, PETG',
            'cutter_outer_x_before_nominal': 58, 'cutter_outer_x_after_nominal': 58.02,
            'working_datum_y_unchanged': 4.5, 'datum_x_interval_unchanged': [43.8, 57.8],
            'datum_z_bands_unchanged': [[-4.1,-2.5],[2.5,4.1]],
            'rod_holes_and_fasteners': 'No source edit',
            'mechanical_effect': 'Only .02 mm end-band material removed; no new material.'},
        'limits': ['Exact zero-area and welded edge/link checks are not a universal self-intersection proof.',
            'Real CGAL Boolean reimport and targeted source-difference checks pass only when reported.',
            'Not print, fit, preload, strength, sealing, dynamics or total-error acceptance.']}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(report['status'], 'sources_stable', report['sources_stable'])
    for row in exports + reimports + deltas + probes + previews:
        print(row['name'], row.get('expected_result_observed', row['passed']),
              row.get('mesh', {}).get('zero_area_face_indices_0_based', []))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
