#!/usr/bin/env python3
"""Bounded STL review of the final negative-half reservoir subtraction.

Run with FreeCAD's Python (numpy/shapely/matplotlib); --export performs only
offline OpenSCAD exports. It neither slices nor sends a print job.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import math
import os
import re
import shutil
import subprocess

import numpy as np
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from feeder_body_geometry import read_mesh, mesh_topology, Sections

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/outlet-groove-fix'
CAD = ROOT / 'cad/feeder-integrated-candidate.scad'
EXE = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, v):
    p.write_text(json.dumps(v, indent=2, ensure_ascii=False) + '\n')


def dependencies():
    found = {}; pending = [CAD]
    while pending:
        p = pending.pop().resolve()
        key = str(p.relative_to(ROOT))
        if key in found:
            continue
        found[key] = sha(p)
        pending += [p.parent / d for d in re.findall(r'\b(?:use|include)\s*<([^>]+)>', p.read_text())]
    return dict(sorted(found.items()))


def module(text, name='ic_host_half'):
    start = re.search(r'\bmodule\s+' + name + r'\s*\(', text).start()
    brace = text.index('{', start); depth = 1; end = brace + 1
    while depth:
        if text[end] == '{': depth += 1
        elif text[end] == '}': depth -= 1
        end += 1
    return text[start:end]


def normalized(text):
    return re.sub(r'\s+', '', re.sub(r'//[^\n]*', '', text))


def run(name, code, backend='Manifold'):
    src = OUT / (name + '.scad'); target = OUT / (name + '.stl')
    src.write_text(code + '\n'); target.unlink(missing_ok=True)
    cmd = [EXE, '--hardwarnings', '--backend', backend, '--export-format', 'asciistl', '-o', str(target), str(src)]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    log = result.stdout + result.stderr
    (OUT / (name + '.log')).write_text(log)
    empty = 'Current top level object is empty' in log and not target.exists()
    passed = ('WARNING:' not in log and 'ERROR:' not in log and
              (result.returncode == 0 and target.exists() or result.returncode == 1 and empty))
    record = {'name': name, 'command': cmd, 'return_code': result.returncode,
              'recognized_empty_result': empty, 'execution_ok': passed,
              'stl_sha256': sha(target) if target.exists() else None}
    if not passed:
        raise RuntimeError(json.dumps(record) + '\n' + log)
    print(name, 'EMPTY' if empty else target.stat().st_size, flush=True)
    return record


def exports():
    identity = dependencies()
    for path in identity:
        target = OUT / 'snapshot' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, target)
    if any(sha(OUT / 'snapshot' / p) != h for p, h in identity.items()):
        raise RuntimeError('Dependency snapshot changed while copying')
    dump(OUT / 'snapshot-manifest.json', identity)
    # OpenSCAD special variables such as $fn are dynamically inherited. A
    # library-only wrapper would silently drop the host's 72-facet setting.
    use = 'include <snapshot/cad/parameters.scad>\nuse <snapshot/cad/feeder-integrated-candidate.scad>\n'
    jobs = [run('negative-half', use + 'ic_host_half(false);'),
            run('positive-half', use + 'ic_host_half(true);'),
            run('reservoir-cutters', 'use <snapshot/cad/feeder-seam-candidate.scad>\nseam_reservoir_cuts();')]
    old = 'import("before/negative-half.stl");'
    new = 'import("negative-half.stl");'
    cuts = 'import("reservoir-cutters.stl");'
    # Actual imported-STL booleans independently test nominal material change
    # and a nonempty old-part control. CGAL's exact imported old-minus-new
    # result warned about non-manifold remnants and is preserved as rejected
    # evidence. These Manifold results are explicitly numerical mesh checks.
    for name, code in [
        ('removed-material', 'difference(){' + old + new + '}'),
        ('unexpected-added-material', 'difference(){' + new + old + '}'),
        ('removal-outside-original-cutters', 'difference(){difference(){' + old + new + '}' + cuts + '}'),
        ('new-material-inside-original-cutters', 'intersection(){' + new + cuts + '}'),
        ('old-refill-control', 'intersection(){' + old + cuts + '}')]:
        jobs.append(run(name, code, 'Manifold'))
    dump(OUT / 'export-invocations.json', jobs)


def plane_shape(t, axis, position):
    chosen = t[(abs(t[:, :, axis] - position) < 1e-6).all(axis=1)]
    keep = [i for i in range(3) if i != axis]
    shapes = [Polygon(v[:, keep]) for v in chosen]
    return unary_union([p for p in shapes if p.area > 1e-10])


def vertex_links(t):
    links = collections.defaultdict(lambda: collections.defaultdict(set))
    for tri in t:
        v = [tuple(np.round(p, 7)) for p in tri]
        for i in range(3):
            c, a, b = v[i], v[(i + 1) % 3], v[(i + 2) % 3]
            links[c][a].add(b); links[c][b].add(a)
    faults = []
    for vertex, g in links.items():
        seen = set(); fans = 0
        for v in g:
            if v in seen: continue
            fans += 1; pending = [v]
            while pending:
                q = pending.pop()
                if q not in seen:
                    seen.add(q); pending.extend(g[q] - seen)
        if fans != 1 or any(len(a) != 2 for a in g.values()):
            faults.append({'point': list(vertex), 'fans': fans,
                           'non_degree_two': sum(len(a) != 2 for a in g.values())})
    return {'weld_decimals': 7, 'faults': faults, 'vertices': len(links)}


def mesh_review(path):
    t, _ = read_mesh(path); info = mesh_topology(t); info['vertex_links'] = vertex_links(t)
    info['passed'] = (info['boundary_edges'] == info['nonmanifold_edges'] ==
                      info['inconsistently_oriented_two_face_edges'] ==
                      info['degenerate_triangles'] == 0 and
                      info['edge_connected_surface_components'] == 1 and
                      not info['vertex_links']['faults'])
    return t, info


def components(g):
    return list(g.geoms) if hasattr(g, 'geoms') else [g]


def boundary_sheet_certificate(t, reference, tolerance=1e-7):
    """Certify double-sided zero-thickness output on known cutter facets.

    Each complete triangle must lie in a reference facet plane AND within its
    projected polygon. Every occupied planar patch must have both orientations.
    Tiny signed volume alone is deliberately insufficient. Tolerance is a
    numerical mesh-comparison tolerance in mm, never a manufacturing budget.
    """
    groups = {}
    for v in reference:
        n = np.cross(v[1] - v[0], v[2] - v[0]); length = np.linalg.norm(n)
        if length < 1e-12: continue
        n /= length; drop = int(np.argmax(abs(n)))
        if n[drop] < 0: n = -n
        d = float(n @ v[0]); key = tuple(np.round([*n, d], 7))
        g = groups.setdefault(key, {'normal': n, 'offset': d, 'drop': drop,
                                    'reference': [], 'positive': [], 'negative': []})
        g['reference'].append(Polygon(np.delete(v, drop, axis=1)))
    groups = list(groups.values())
    for g in groups: g['shape'] = unary_union(g['reference'])
    normals = np.array([g['normal'] for g in groups]); offsets = np.array([g['offset'] for g in groups])
    unmatched = []; max_distance = 0.
    for i, v in enumerate(t):
        normal = np.cross(v[1] - v[0], v[2] - v[0])
        if np.linalg.norm(normal) < 1e-12:
            unmatched.append(i); continue
        distances = abs(v @ normals.T - offsets).max(axis=0)
        matched = False
        for j in np.where(distances <= tolerance)[0]:
            g = groups[j]; polygon = Polygon(np.delete(v, g['drop'], axis=1))
            if polygon.difference(g['shape'].buffer(tolerance)).area > tolerance**2:
                continue
            g['positive' if normal @ g['normal'] > 0 else 'negative'].append(polygon)
            max_distance = max(max_distance, float(distances[j])); matched = True; break
        if not matched: unmatched.append(i)
    unpaired = 0.; occupied_planes = 0
    for g in groups:
        if not g['positive'] and not g['negative']: continue
        occupied_planes += 1
        a, b = unary_union(g['positive']), unary_union(g['negative'])
        # Compare exact unions; area tolerance covers floating point edges.
        unpaired += a.symmetric_difference(b).area / abs(g['normal'][g['drop']])
    volume = abs(float(np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6))
    return {'triangles': len(t), 'reference': 'original reservoir cutter boundary',
            'coordinate_tolerance_mm': tolerance, 'unmatched_triangle_indices': unmatched,
            'maximum_matched_plane_distance_mm': max_distance, 'occupied_planes': occupied_planes,
            'opposite_orientation_symmetric_difference_area_mm2': unpaired,
            'absolute_signed_volume_mm3': volume,
            'certified_double_sided_boundary_only': not unmatched and unpaired < 1e-7 and volume < 1e-7}


def charts(old, new, floor_old, floor_new, capture):
    os.environ['MPLCONFIGDIR'] = str(OUT / 'matplotlib-config')
    os.environ['XDG_CACHE_HOME'] = str(OUT / 'cache')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Patch
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    def draw(ax, geom, color, alpha=1.):
        for p in components(geom):
            if p.geom_type != 'Polygon': continue
            ax.add_patch(Patch(p.exterior.coords, facecolor=color, edgecolor=color, alpha=alpha))
            for hole in p.interiors:
                ax.add_patch(Patch(hole.coords, facecolor='white', edgecolor=color))

    fig, axes = plt.subplots(1, 3, figsize=(14, 6), constrained_layout=True)
    for ax, sign in zip(axes[:2], [-1, 1]):
        roi = box(sign * 26.75 - .8, 44, sign * 26.75 + .8, 69)
        draw(ax, floor_new.intersection(roi), '#f1ac53')
        draw(ax, floor_old.intersection(roi), '#4b789c')
        ax.set(xlim=(sign * 26.75 - .8, sign * 26.75 + .8), ylim=(44, 69),
               xlabel='Assembly Y (mm)', ylabel='Assembly Z (mm)',
               title=f'X = -0.2 groove floor, side {sign:+d}\nBlue: before; orange: restored')
        ax.grid(alpha=.2)
    z, sec = Sections(new).at(46.137)
    draw(axes[2], sec, '#afbac5')
    axes[2].plot([-.2, 0, 0, -.2], [26.35, 26.35, 27.15, 27.15], color='#d95325')
    axes[2].axhline(28.5, color='green', linestyle='--', label='Capture lip inner radius')
    axes[2].set(xlim=(-.8, .2), ylim=(24.8, 29), xlabel='Assembly X (mm)', ylabel='Assembly Y (mm)',
                title=f'Actual STL section Z={z:g}\nGroove does not reach bore or capture land')
    axes[2].legend(fontsize=8); axes[2].grid(alpha=.2)
    fig.savefig(OUT / 'groove-sections.png', dpi=180); plt.close(fig)

    fig = plt.figure(figsize=(14, 6), constrained_layout=True)
    ax = fig.add_subplot(121, projection='3d')
    t = new[(new[:, :, 2].max(axis=1) >= 43.9) & (new[:, :, 2].min(axis=1) <= 69)]
    ax.add_collection3d(Poly3DCollection(t, facecolor='#93aabd', edgecolor='none', alpha=.9))
    ax.set(xlim=(-33, 1), ylim=(-32, 32), zlim=(43, 70), xlabel='X', ylabel='Y', zlabel='Z',
           title='Negative outlet: actual exported STL')
    ax.set_box_aspect((34, 64, 27)); ax.view_init(elev=25, azim=40)
    ax = fig.add_subplot(122)
    draw(ax, plane_shape(new, 2, 48), '#c8d3df')
    draw(ax, capture, '#568a64')
    ax.set(xlim=(-33, 1), ylim=(-33, 33), xlabel='Assembly X (mm)', ylabel='Assembly Y (mm)',
           title='Z=48 axial capture bearing surface\nGreen area is identical before / after')
    ax.set_aspect('equal'); ax.grid(alpha=.2)
    fig.savefig(OUT / 'outlet-working-surfaces.png', dpi=180); plt.close(fig)


def analyze():
    identity = json.loads((OUT / 'snapshot-manifest.json').read_text())
    manifest = json.loads((OUT / 'before/manifest.json').read_text())
    assert all(sha(ROOT / v['archived_as']) == v['sha256'] for v in manifest.values())
    assert all(sha(OUT / 'snapshot' / p) == h for p, h in identity.items())
    old, old_info = mesh_review(OUT / 'before/negative-half.stl')
    new, new_info = mesh_review(OUT / 'negative-half.stl')
    positive, pos_info = mesh_review(OUT / 'positive-half.stl')
    cutters, _ = read_mesh(OUT / 'reservoir-cutters.stl')
    before_module = module((OUT / 'before/feeder-integrated-candidate.scad').read_text())
    after_module = module((OUT / 'snapshot/cad/feeder-integrated-candidate.scad').read_text())
    change = 'if(!positive)seam_reservoir_cuts();'
    only_change = normalized(after_module).replace(change, '') == normalized(before_module)
    floor_old = plane_shape(old, 0, -.2); floor_new = plane_shape(new, 0, -.2)
    floor_expected = plane_shape(cutters, 0, -.2)
    rows = []
    for sign in [-1, 1]:
        cy = sign * 26.75; roi = box(cy - .6, 44, cy + .6, 69)
        a = floor_old.intersection(roi); b = floor_new.intersection(roi)
        expected = floor_expected.intersection(roi)
        refill = box(cy - .6, 45, cy + .6, 48)
        rows.append({'side': sign, 'before_bounds_YZ_mm': list(a.bounds),
                     'after_bounds_YZ_mm': list(b.bounds),
                     'before_floor_area_Z45_to_48_mm2': a.intersection(refill).area,
                     'after_floor_area_Z45_to_48_mm2': b.intersection(refill).area,
                     'after_total_floor_area_mm2': b.area,
                     'difference_from_original_cutter_floor_mm2': b.symmetric_difference(expected).area})
    circle = Point(0, 0).buffer(28.5, resolution=1024)
    faces = []; capture = None
    for axis, value, name in [(2, 44, 'flange_bottom'), (2, 48, 'flange_top'),
                              (1, -30, 'negative_Y_antirotation_flat'),
                              (1, 30, 'positive_Y_antirotation_flat')]:
        a, b = plane_shape(old, axis, value), plane_shape(new, axis, value)
        if axis == 2:
            a, b = a.difference(circle), b.difference(circle)
            if value == 48: capture = b
        else:
            roi = box(-40, 44, 0, 48); a, b = a.intersection(roi), b.intersection(roi)
        faces.append({'name': name, 'axis': axis, 'coordinate_mm': value,
                      'before_area_mm2': a.area, 'after_area_mm2': b.area,
                      'symmetric_difference_mm2': a.symmetric_difference(b).area,
                      'scope': 'r >= 28.5 axial capture land' if axis == 2 else 'Z44..48 flat'})
    # Model-space sampled sections are supporting illustrations only. The
    # imported-mesh Boolean differences below check the complete mesh input
    # with a numerical backend, rather than proving exact real-valued sets.
    sec_old, sec_new = Sections(old), Sections(new); sections = []
    for z in [44.137, 45.137, 45.537, 46.137, 47.937, 48.137, 60.137, 68.137]:
        zz, a = sec_old.at(z); _, b = sec_new.at(z)
        delta = a.difference(b)
        sections.append({'z_mm': zz, 'removed_area_mm2': delta.area,
                         'added_area_mm2': b.difference(a).area,
                         'removed_bounds_XY_mm': list(delta.bounds) if not delta.is_empty else []})
    invocations = json.loads((OUT / 'export-invocations.json').read_text())
    bools = {v['name']: v for v in invocations}
    removed, _ = read_mesh(OUT / 'removed-material.stl')
    control, _ = read_mesh(OUT / 'old-refill-control.stl')
    removed_info = mesh_topology(removed); control_info = mesh_topology(control)
    contacts = {}
    for name in ['unexpected-added-material', 'new-material-inside-original-cutters']:
        path = OUT / (name + '.stl')
        contacts[name] = (boundary_sheet_certificate(read_mesh(path)[0], cutters) if path.exists()
                          else {'certified_double_sided_boundary_only': True, 'recognized_empty_result': bools[name]['recognized_empty_result']})
    contacts['old_refill_positive_control'] = boundary_sheet_certificate(control, cutters)
    max_r = float(np.linalg.norm(removed[:, :, :2], axis=2).max())
    positive_equal = sha(OUT / 'positive-half.stl') == sha(OUT / 'before/positive-half.stl')
    # Triangle order can change without changing geometry. This fallback still
    # demands identical oriented triangles at the stated STL precision.
    def canonical(t):
        result = []
        for v in np.round(t, 7):
            i = min(range(3), key=lambda n: tuple(v[n]))
            result.append(tuple(np.roll(v, -i, axis=0).ravel()))
        return sorted(result)
    if not positive_equal:
        positive_equal = canonical(positive) == canonical(read_mesh(OUT / 'before/positive-half.stl')[0])
    stable = dependencies() == identity
    checks = {
        'ic_host_half_only_adds_negative_final_subtraction': only_change,
        'positive_half_unchanged_at_1e_7_mesh_precision': positive_equal,
        'negative_half_closed_connected_vertex_links': new_info['passed'],
        'positive_half_closed_connected_vertex_links': pos_info['passed'],
        'all_original_negative_floor_polygons_retained': floor_new.symmetric_difference(floor_expected).area < 1e-5,
        'both_Z45_68_outlet_floor_segments_restored': all(abs(r['after_bounds_YZ_mm'][1] - 45) < 1e-6 and abs(r['after_bounds_YZ_mm'][3] - 68) < 1e-6 for r in rows),
        'old_refill_counterexample_has_positive_volume': control_info['signed_volume_mm3'] > .9,
        'no_added_solid_material_with_boundary_sheets_classified': contacts['unexpected-added-material']['certified_double_sided_boundary_only'],
        'no_removed_material_outside_original_cutters': bools['removal-outside-original-cutters']['recognized_empty_result'],
        'new_cutter_intersection_only_paired_boundary_sheets': contacts['new-material-inside-original-cutters']['certified_double_sided_boundary_only'],
        'boundary_classifier_rejects_old_refill_control': not contacts['old_refill_positive_control']['certified_double_sided_boundary_only'],
        'capture_bearing_and_antirotation_surfaces_unchanged': all(r['after_area_mm2'] > 1 and r['symmetric_difference_mm2'] < 1e-5 for r in faces),
        'removed_region_clear_of_capture_land': max_r < 28.5,
        'snapshot_matches_current_recursive_sources': stable,
    }
    report = {'status': 'BOUNDED_OUTLET_GROOVE_REPAIR_PASS' if all(checks.values()) else 'FAIL_OR_SOURCE_MOVED',
              'checks': checks, 'source_sha256': identity, 'analysis_sha256': sha(Path(__file__)),
              'host_module_sha256': hashlib.sha256(after_module.encode()).hexdigest(),
              'before_manifest_sha256': sha(OUT / 'before/manifest.json'),
              'current_sources_sha256': dependencies(),
              'parts': {name: {'sha256': sha(OUT / (name + '.stl')), 'mesh': info} for name, info in [('negative-half', new_info), ('positive-half', pos_info)]},
              'outlet_floor_segments': rows, 'protected_working_surfaces': faces, 'sampled_sections': sections,
              'removed_material': {**removed_info, 'maximum_vertex_radius_mm': max_r,
                                   'radial_clearance_to_capture_land_mm': 28.5 - max_r,
                                   'clearance_to_antirotation_flats_mm': 30 - float(np.abs(removed[:, :, 1]).max())},
              'old_refill_failure_control': control_info,
              'boundary_contact_certificates': contacts,
              'all_floor_difference_from_original_cutters_mm2': floor_new.symmetric_difference(floor_expected).area,
              'method': ['Private recursive SCAD snapshot, actual half-shell exports; positive-half invariance.',
                         'Imported STL Manifold Boolean comparison over complete nominal meshes, not only sampled sections; this is not an exact-set proof.',
                         'Coplanar STL triangles unioned at X=-0.2 give the complete groove-floor footprint.',
                         'Nonempty contact output accepted only when every full triangle is on a known cutter facet, both oriented projected patch unions match, and signed volume is below 1e-7 mm3; old refill is a rejection control.',
                         'Capture land r>=28.5 and Y=+/-30 flats compared as full planar working faces.',
                         'Closed oriented edge topology plus every vertex link a connected degree-two cycle; no general triangle self-intersection proof.'],
              'rejected_checks': ['rejected-missing-resolution/reason.json', 'rejected-exact-import-difference/reason.json'],
              'limits': ['Geometric repair only: no strength, gasket adhesion, gas-tightness or physical assembly acceptance.',
                         'CGAL exact old-minus-new imported mesh comparison produced a non-manifold warning and was rejected; numerical Manifold mesh checks and complete planar face comparisons are reported separately.',
                         'Original 0.8 mm wide by 0.2 mm deep reservoir contract restored; this is not a compression gasket specification.',
                         'Existing negative-half slice predates this repair and is not accepted for the new geometry; root will re-slice after combined integration.',
                         'No new slicing, printer connection, or print submission.'],
              'resliced': False, 'sent_to_printer': False, 'manufacturing_release': False}
    charts(old, new, floor_old, floor_new, capture)
    report['images'] = {p.name: sha(p) for p in OUT.glob('*.png')}
    dump(OUT / 'report.json', report)
    print(json.dumps({'status': report['status'], 'checks': checks,
                      'outlet_floor_segments': rows, 'removed_volume_mm3': removed_info['signed_volume_mm3']}, indent=2))
    return 0 if all(checks.values()) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', action='store_true', help='Export current private source snapshot first')
    args = parser.parse_args(); OUT.mkdir(parents=True, exist_ok=True)
    if args.export: exports()
    return analyze()


if __name__ == '__main__':
    raise SystemExit(main())
