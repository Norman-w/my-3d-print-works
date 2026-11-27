#!/usr/bin/env python3
"""Audit existing ASCII STL exports; never modify geometry or run OpenSCAD."""
from fractions import Fraction as F
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/integrated-review-parts'
VERTEX = re.compile(r'^\s*vertex\s+(\S+)\s+(\S+)\s+(\S+)\s*$', re.M)
KNOWN_RIGHT = '9647784b194f13aacf8b5150b2f16ec9909c09e95fc0867cc94bdbc01d03dedc'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cross(a, b, c):
    u = tuple(y-x for x, y in zip(a, b))
    v = tuple(y-x for x, y in zip(a, c))
    return (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2],
            u[0]*v[1]-u[1]*v[0])


def audit(row):
    path = ROOT / row['file']
    identity = digest(path)
    if identity != row['sha256']:
        raise RuntimeError(f'Stale STL identity: {path}')
    raw = path.read_text()
    text_vertices = VERTEX.findall(raw)
    if len(text_vertices) % 3 or len(text_vertices)//3 != raw.count('endfacet'):
        raise ValueError(f'Expected complete ASCII STL triangles: {path}')
    vertices = [tuple(F(value) for value in point) for point in text_vertices]
    triangles = [vertices[i:i+3] for i in range(0, len(vertices), 3)]
    bad = []
    for index, (a, b, c) in enumerate(triangles):
        if not any(cross(a, b, c)):
            bad.append({'triangle_index_zero_based': index,
                        'vertices_as_written': text_vertices[3*index:3*index+3]})
    result = {'id': row['id'], 'file': row['file'], 'sha256': identity,
              'triangle_count': len(triangles), 'zero_area_faces': bad,
              'zero_area_count': len(bad),
              'legacy_report_degenerate_count': row['mesh']['degenerateTriangleCount'],
              'known_coplanar_overlap_witness': None}
    if row['id'] == 'right-support' and identity == KNOWN_RIGHT:
        q = (F(58), F('-4.685'), F('4.24'))
        sub = lambda u, v: (u[1]-v[1], u[2]-v[2])
        det = lambda u, v: u[0]*v[1]-u[1]*v[0]
        inside = []
        normals = []
        for index in (2, 2685):
            a, b, c = triangles[index]
            if not a[0] == b[0] == c[0] == q[0]:
                raise AssertionError('Known coplanar witness changed')
            den = det(sub(b, a), sub(c, a))
            beta = det(sub(q, a), sub(c, a))/den
            gamma = det(sub(b, a), sub(q, a))/den
            bary = (1-beta-gamma, beta, gamma)
            if min(bary) <= 0:
                raise AssertionError('Known strict interior witness changed')
            inside.append({'triangle_index_zero_based': index,
                           'barycentric_exact': list(map(str, bary))})
            normals.append(cross(a, b, c)[0])
        assert normals[0]*normals[1] < 0
        result['known_coplanar_overlap_witness'] = {
            'point_mm': list(map(str, q)), 'opposite_normals': True,
            'strictly_inside_both': inside}
    result['no_defect_found_in_this_check'] = not bad and not result['known_coplanar_overlap_witness']
    return result


def main():
    report_path = OUT/'report.json'
    report = json.loads(report_path.read_text())
    source_hashes = report['source_sha256']
    if any(digest(ROOT/path) != value for path, value in source_hashes.items()):
        raise RuntimeError('Instance report source identity is stale')
    rows = [audit(row) for row in report['parts'] if row['role'] == 'printed']
    passed = all(row['no_defect_found_in_this_check'] for row in rows)
    result = {'status': 'NO_LISTED_DEFECT_FOUND' if passed else 'EXPORTED_MESH_DEFECT_CONFIRMED',
              'method': 'Exact rational cross products of decimal ASCII coordinates; plus one fixed strict coplanar-overlap witness.',
              'scope': 'All listed printed instances checked for exactly zero area. Near-zero area, arbitrary self-intersections and mechanical fitness are not certified.',
              'script_sha256': digest(Path(__file__)),
              'instance_report_sha256': digest(report_path),
              'source_sha256': source_hashes, 'parts': rows,
              'manufacturing_release': False}
    (OUT/'degeneracy-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(result['status'], len(rows), 'printed instances', flush=True)
    for row in rows:
        if not row['no_defect_found_in_this_check']:
            print(row['id'], row['zero_area_count'], 'zero-area faces; overlap:',
                  bool(row['known_coplanar_overlap_witness']), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
