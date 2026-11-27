#!/usr/bin/env python3
"""Full nominal screw-shaft and nut insertion volumes in the existing candidate 3.

Read-only native artifacts. Width-plus-parser-error path envelopes; no hole
enlargement or tolerance waiver. Separates removable supports from model paths.
"""
from pathlib import Path
import collections, hashlib, importlib.util, json, math, sys
import numpy as np
from shapely.geometry import Point, Polygon, LineString

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
FOLDER = BASE / 'runs/20260927T110450585847Z/inlet-rear-rear-key-ends-down-supported'
sys.path[:0] = [str(ROOT / 'analysis'), str(ROOT / 'scripts')]
import cable_input_slice_review as g
sp = importlib.util.spec_from_file_location('archive', ROOT / 'output/current-manufacturing/feeder-reuse/review.py')
archive = importlib.util.module_from_spec(sp); sp.loader.exec_module(archive)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    inv = json.loads((FOLDER / 'invocation.json').read_text())
    models, project, code_hash, units = archive.archive_models(FOLDER / 'slice-review.3mf')
    assert len(models) == 1 and units == 'millimeter' and code_hash == sha(FOLDER / 'plate_1.gcode')
    M = np.array(next(iter(models.values()))['mapping']['current_cad_to_gcode_command'])
    assert np.allclose(M[:3, 1], [0, 0, 1], atol=1e-12)
    # A circumscribed polygon contains the entire circular shaft, not an
    # undersized inscribed circle. Source nut is the actual AF7 hex envelope.
    features = []
    for x in [-10.5, 10.5]:
        features.append((f'M2.5-shaft-X{x:g}', x, -142, -53.8, -42, 'round', 2.5))
    for x in [-43, 43]:
        features.append((f'M4-shaft-X{x:g}', x, -112, -12.02, -1.2, 'round', 4.0))
        features.append((f'M4-nut-axial-insertion-X{x:g}', x, -112, -12.02, -8.4, 'hex', 7.0))
    prepared = []
    for name, x, z, y0, y1, shape, size in features:
        q = g.affine(np.array([[x, y0, z], [x, y1, z]]), M)
        if shape == 'round':
            profile = Point(q[0, :2]).buffer(size / 2 / math.cos(math.pi / 256), quad_segs=64)
        else:
            radius = size / 2 / math.cos(math.pi / 6)
            local = np.array([[x + radius * math.cos(math.radians(30 + k * 60)), y0,
                               z - radius * math.sin(math.radians(30 + k * 60))] for k in range(6)])
            profile = Polygon(g.affine(local, M)[:, :2])
        prepared.append(dict(name=name, profile=profile, z0=q[:, 2].min(), z1=q[:, 2].max(),
                             cad_axis_interval=[y0, y1], nominal_size=size, shape=shape,
                             model_hits=[], support_hits=[], model_records_tested=0, support_records_tested=0))
    for r in g.extrusion_paths((FOLDER / 'plate_1.gcode').open()):
        if r.feature in g.IGNORED | {'Flush', 'Undefined', ''}: continue
        low = float(r.points[:, 2].min() - r.height)
        high = float(r.points[:, 2].max())
        active = [f for f in prepared if min(high, f['z1']) > max(low, f['z0'])]
        if not active: continue
        bead = LineString(r.points[:, :2]).buffer((r.width / 2 + .002) / math.cos(math.pi / 128), quad_segs=32)
        kind = 'support' if r.feature.startswith('Support') else 'model'
        for f in active:
            f[kind + '_records_tested'] += 1
            hit = bead.intersection(f['profile'])
            if not hit.is_empty:
                f[kind + '_hits'].append(dict(line=r.line, feature=r.feature, print_top=high, print_bottom=low,
                     positive_axial_overlap_mm=min(high, f['z1']) - max(low, f['z0']),
                     projected_hit_area_mm2=hit.area, projected_hit_bounds=list(hit.bounds)))
    rows = []
    for f in prepared:
        f.pop('profile'); rows.append(f)
    inputs = [FOLDER / n for n in ['invocation.json', 'slice-review.3mf', 'plate_1.gcode']]
    inputs += [ROOT / inv['input']['file'], ROOT / 'cad/inlet-retention-final.scad', ROOT / 'analysis/cable_input_slice_review.py', Path(__file__)]
    before = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    result = dict(status='NOMINAL_FULL_HARDWARE_VOLUMES_CLEAR_OF_MODEL' if all(not f['model_hits'] for f in rows) else 'NOMINAL_HARDWARE_MODEL_CONTACT_REQUIRES_REVIEW',
                  features=rows, source_and_artifact_sha256=before, cad_to_gcode=M.tolist(),
                  method='Actual commanded path-width envelopes and each record full height. Strictly positive axial overlap tested; exact endpoint face contact excluded only by the positive-volume interval definition. Round test profiles circumscribe full shaft diameter; AF7 nut is nominal hex, swept from open pocket to bearing face.',
                  limits=['These are nominal metal envelopes, not supplier tolerances or actual printed dimensions.', 'Support hits are retained and require support removal before fasteners enter.', 'Does not prove screw-head access, tightening torque, printed thread strength, or surface quality.'],
                  manufacturing_release=False, physical_acceptance=False, sent_to_printer=False)
    assert all(sha(ROOT / p) == h for p, h in before.items())
    (FOLDER / 'hardware-volume-review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'features': [{k: f[k] if k not in ['model_hits', 'support_hits'] else len(f[k]) for k in ['name', 'model_hits', 'support_hits']} for f in rows]}, ensure_ascii=False))


if __name__ == '__main__': main()
