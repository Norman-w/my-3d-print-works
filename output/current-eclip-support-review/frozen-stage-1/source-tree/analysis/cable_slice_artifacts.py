#!/usr/bin/env python3
"""Verify offline slice provenance and actual 3MF mesh, not just slicer repair flags."""
from pathlib import Path
import argparse
import collections
import hashlib
import importlib.util
import json
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cable_slicer', ROOT/'scripts/review_cable_slice.py')
slicer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(slicer)
NS = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
PRODUCTION = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path, data): Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')


def normalization_review(source, vertices, faces):
    """Account for every source face after slicer vertex precision conversion.

    This is separate from strict identity. A face-count failure stays a failure;
    an explicit contraction proof can explain a numerical conversion without
    pretending that the slicer preserved all source triangles.
    """
    distance, mapped = cKDTree(vertices).query(source.reshape(-1, 3))
    mapped = mapped.reshape(-1, 3)
    canonical = lambda t: min(tuple(t), tuple(np.roll(t, 1)), tuple(np.roll(t, 2)))
    collapsed = [i for i, t in enumerate(mapped) if len(set(t)) < 3]
    expected = collections.Counter(canonical(t) for t in mapped if len(set(t)) == 3)
    actual = collections.Counter(canonical(t) for t in faces)
    edges, directed = collections.Counter(), collections.Counter()
    links = collections.defaultdict(lambda: collections.defaultdict(set))
    adjacency = collections.defaultdict(set)
    for face in faces:
        for i in range(3):
            a, b, c = map(int, [face[i], face[(i+1)%3], face[(i+2)%3]])
            edges[tuple(sorted((a, b)))] += 1
            directed[a, b] += 1
            links[a][b].add(c); links[a][c].add(b)
            adjacency[a].add(b); adjacency[b].add(a)
    faults = []
    for vertex, graph in links.items():
        seen, todo = set(), [next(iter(graph))]
        while todo:
            p = todo.pop()
            if p in seen: continue
            seen.add(p); todo.extend(graph[p]-seen)
        if len(seen) != len(graph) or any(len(v) != 2 for v in graph.values()): faults.append(vertex)
    seen, components = set(), 0
    for start in adjacency:
        if start in seen: continue
        components += 1; todo = [start]
        while todo:
            p = todo.pop()
            if p in seen: continue
            seen.add(p); todo.extend(adjacency[p]-seen)
    winding = sum(not (directed[a, b] == directed[b, a] == 1) for a, b in edges)
    non_two = sum(count != 2 for count in edges.values())
    volume = lambda t: float(np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2])).sum()/6)
    passed = expected == actual and not faults and not non_two and not winding and components == 1 and max(distance) < .00001
    return {
        'status': 'BOUNDED_VERTEX_CONTRACTION_VERIFIED' if passed else 'NORMALIZATION_NOT_VERIFIED',
        'method': 'Map each source triangle corner to an actual 3MF vertex. Require exact oriented-face multiset equality after recording the collapsed source faces. Verify final edge/vertex manifold, winding and connectivity. Corresponding triangle points move no more than the maximum corner displacement by barycentric interpolation. This explains numerical conversion, not byte or face-count identity.',
        'source_triangles': len(source), 'actual_3mf_triangles': len(faces),
        'collapsed_source_triangle_indices': collapsed,
        'maximum_corner_displacement_mm': float(max(distance)),
        'surviving_oriented_faces_exactly_match': expected == actual,
        'unexpected_actual_faces': sum((actual-expected).values()),
        'missing_surviving_faces': sum((expected-actual).values()),
        'non_two_incidence_edges': non_two, 'vertex_link_faults': faults,
        'orientation_faults': winding, 'components': components,
        'volume_source_mm3': volume(source), 'volume_actual_3mf_mm3': volume(vertices[faces]),
        'manufacturing_release': False, 'physical_acceptance': False,
    }


def check(folder):
    inv = json.loads((folder/'invocation.json').read_text())
    original = slicer.read_stl(ROOT/inv['input']['file'])
    oriented = slicer.read_stl(folder/'oriented.stl')
    M = np.array(inv['cad_to_oriented'])
    predicted = original @ M[:3, :3].T + M[:3, 3]
    checks = {
        'original_stl_matches_export': sha(ROOT/inv['input']['file']) == inv['input']['sha256'],
        'oriented_stl_matches_invocation': sha(folder/'oriented.stl') == inv['oriented']['sha256'],
        'source_files_still_match': all(sha(ROOT/p) == h for p, h in inv['source_sha256_at_start'].items()),
        'profiles_match_slice_start': all(sha(folder/(n+'.json')) == h for n, h in inv['local_profile_sha256'].items()),
        'artifacts_match_invocation': all(sha(folder/n) == h for n, h in inv['artifact_sha256'].items()),
        'one_to_one_rigid_reorientation': bool(original.shape == oriented.shape and np.max(np.abs(predicted-oriented)) < .00002),
        'no_scale_or_reflection': bool(np.allclose(M[:3, :3].T@M[:3, :3], np.eye(3), atol=1e-10) and abs(np.linalg.det(M[:3, :3])-1) < 1e-10),
    }
    with zipfile.ZipFile(folder/'slice-review.3mf') as z:
        main = ET.fromstring(z.read('3D/3dmodel.model'))
        settings = ET.fromstring(z.read('Metadata/model_settings.config'))
        objects = main.findall('./m:resources/m:object', NS)
        build = main.findall('./m:build/m:item', NS)
        parts = settings.findall('./object/part')
        checks['single_model_instance'] = len(objects) == len(build) == len(parts) == 1
        if not checks['single_model_instance']: raise ValueError('Unexpected multi-object slice')
        component = objects[0].find('./m:components/m:component', NS)
        meta = {m.attrib.get('key'): m.attrib.get('value') for m in parts[0].findall('./metadata')}
        offset = np.array([float(meta['source_offset_'+a]) for a in 'xyz'])
        mesh_path = component.attrib[PRODUCTION+'path'].lstrip('/')
        mesh = ET.fromstring(z.read(mesh_path))
        vertices = np.array([[float(v.attrib[a]) for a in 'xyz'] for v in mesh.findall('.//m:vertex', NS)])
        indices = np.array([[int(v.attrib[a]) for a in ['v1', 'v2', 'v3']] for v in mesh.findall('.//m:triangle', NS)])
        imported = vertices[indices] + offset
        repairs = parts[0].find('./mesh_stat').attrib
        nearest_to_import = float(cKDTree(imported.reshape(-1, 3)).query(oriented.reshape(-1, 3))[0].max())
        nearest_to_input = float(cKDTree(oriented.reshape(-1, 3)).query(imported.reshape(-1, 3))[0].max())
        areas = np.linalg.norm(np.cross(imported[:, 1]-imported[:, 0], imported[:, 2]-imported[:, 0]), axis=1)/2
        checks.update({
            'actual_3mf_triangle_count_preserved': len(indices) == len(oriented),
            'reported_3mf_triangle_count_matches_actual': int(repairs['face_count']) == len(indices),
            'no_reported_mesh_repairs': all(int(repairs.get(k, 0)) == 0 for k in ['edges_fixed', 'degenerate_facets', 'facets_removed', 'facets_reversed', 'backwards_edges']),
            'actual_3mf_has_no_zero_area_facets': bool((areas > 0).all()),
            'actual_3mf_vertices_match_input_within_0_0001mm': max(nearest_to_import, nearest_to_input) < .0001,
            'archived_gcode_equals_external_gcode': hashlib.sha256(z.read('Metadata/plate_1.gcode')).hexdigest() == sha(folder/'plate_1.gcode'),
            '3mf_units_mm': main.attrib.get('unit') == 'millimeter',
        })
        project = json.loads(z.read('Metadata/project_settings.config'))
    normalization = None
    if len(indices) != len(oriented):
        normalization = normalization_review(oriented, vertices+offset, indices)
        normalization.update(input_stl_sha256=sha(folder/'oriented.stl'),
                             slice_3mf_sha256=sha(folder/'slice-review.3mf'), auditor_sha256=sha(__file__))
        dump(folder/'float-normalization-review.json', normalization)
    native = inv['native_result']
    checks['native_slice_success'] = inv['return_code'] == native['return_code'] == 0
    warnings = [p.get('warning_message', '') for p in native['sliced_plates']]
    checks['native_warnings_empty'] = not any(warnings)
    expected = {'wall_loops': '4', 'sparse_infill_density': '25%', 'layer_height': str(inv['assumptions']['layer_height_mm'])}
    checks['resolved_process_matches_intent'] = all(str(project.get(k)) == v for k, v in expected.items())
    checks['resolved_machine_X1C_04'] = project.get('printer_model') == 'Bambu Lab X1 Carbon' and project.get('nozzle_diameter') == ['0.4']
    checks['resolved_filament_PETG'] = project.get('filament_type') == ['PETG']
    checks['first_model_layer_nozzle_255C'] = inv['last_temperature_before_first_layer_c'] == 255
    result = {
        'status': 'SLICE_ARTIFACT_IDENTITY_PASS' if all(checks.values()) else 'SLICE_ARTIFACT_REVIEW_FLAGGED',
        'part': inv['part'], 'folder': str(folder.relative_to(ROOT)), 'checks': checks,
        'warnings': warnings, 'source_triangle_count': len(original), 'oriented_triangle_count': len(oriented),
        'actual_3mf_triangle_count': len(indices), 'mesh_stat': repairs,
        'bidirectional_vertex_distance_mm': [nearest_to_import, nearest_to_input],
        'actual_3mf_min_triangle_area_mm2': float(areas.min()),
        'explicit_numerical_normalization': normalization,
        'slice_invocation_sha256': sha(folder/'invocation.json'),
        'artifact_sha256': inv['artifact_sha256'], 'auditor_sha256': sha(__file__),
        'scope': 'Source/profile/rigid transform/actual archived mesh and G-code identity only. No support removal, strength, fit or physical print acceptance.',
        'manufacturing_release': False, 'physical_acceptance': False, 'sent_to_printer': False,
    }
    dump(folder/'artifact-review.json', result)
    print(json.dumps({'part': result['part'], 'status': result['status'], 'failed': [k for k, v in checks.items() if not v]}, ensure_ascii=False), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folders', nargs='+', type=Path)
    args = parser.parse_args()
    for folder in args.folders: check(folder.resolve())
