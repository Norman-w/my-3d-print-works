#!/usr/bin/env python3
"""Bind the unchanged inlet STL to reviewed candidate 3. No slicing or printing.

Selection means a bounded digital evidence binding, as for the other instances.
Strict historical contact checks remain unchanged; physical gates remain open.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FOLDER = ROOT / 'output/current-inlet-process-revision/runs/20260927T110450585847Z/inlet-rear-rear-key-ends-down-supported'
EVIDENCE = {}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p): return str(Path(p).resolve().relative_to(ROOT))
def bind(p, expected=None):
    p = Path(p); p = p if p.is_absolute() else ROOT / p
    h = sha(p)
    assert expected is None or h == expected, (rel(p), 'stale evidence')
    assert rel(p) not in EVIDENCE or EVIDENCE[rel(p)] == h
    EVIDENCE[rel(p)] = h
    return h
def read(p):
    p = Path(p); p = p if p.is_absolute() else ROOT / p
    bind(p); return json.loads(p.read_text())


def main():
    names = ['current-review.json', 'key-bed-start-review.json', 'underlay-review.json',
             'hardware-volume-review.json', 'whole-support-sweep/report.json',
             'hit-localization.json', 'initial-compatibility-origin.json']
    reports = {n: read(FOLDER / n) for n in names}
    for report in reports.values():
        for field in ['source_and_artifact_sha256', 'source_hashes', 'source_and_artifact_hashes_before', 'artifacts', 'source_sha256_at_slice']:
            for p, h in report.get(field, {}).items(): bind(p, h)
    inv = read(FOLDER / 'invocation.json')
    for p, h in inv['source_sha256_at_start'].items(): bind(p, h)
    source = ROOT / inv['input']['file']; bind(source, inv['input']['sha256'])
    generic = reports['current-review.json']
    assert all(generic['checks'].values()) and generic['sources_and_artifacts_stable']
    assert len(generic['instances']) == 1 and generic['instances'][0]['identity_pass']
    assert [p['feature'] for p in generic['pending_review']] == ['whole_external_tree']
    keys = reports['key-bed-start-review.json']
    assert keys['gcode_equals_archive'] and len(keys['four_actual_mesh_bed_components']) == 4
    underlay = reports['underlay-review.json']
    assert underlay['actual_support_object_xy_distance'] == .35
    assert len(underlay['four_keys_actual_first_layer']) == 4 and len(underlay['surfaces']) == 3
    hardware = reports['hardware-volume-review.json']
    assert hardware['status'] == 'NOMINAL_FULL_HARDWARE_VOLUMES_CLEAR_OF_MODEL'
    assert len(hardware['features']) == 6 and all(not x['model_hits'] for x in hardware['features'])
    local = reports['hit-localization.json']
    assert local['summary']['slabs_with_obstacle_below_starting_support_bottom'] == 0
    origin = reports['initial-compatibility-origin.json']
    assert origin['archive_evidence']['embedded_gcode_equals_external']
    assert origin['tri90']['actual_positive_volume_pair_count'] == 0
    assert len(origin['five_boundary_hits']) == 5
    assert all(x['original_strict_model_hit_retained'] for x in origin['five_boundary_hits'])
    for name in ['key-bed-start-review.md', 'underlay-review.md', 'hardware-volume-review.md',
                 'hit-localization.md', 'initial-compatibility-origin.md']:
        bind(FOLDER / name)
    for name in ['machine.json', 'process.json', 'filament.json', 'slice-review.3mf', 'plate_1.gcode']:
        bind(FOLDER / name)
    bind(__file__)
    limitations = [
        'This selection binds digital evidence; it is not manufacturing or physical acceptance.',
        'Original strict zero-contact failures remain. Commanded-plane boundary contact is not positive clearance; source-curve/printed-step differences are explicitly classified.',
        'M4 shoulder first paths have only small partial edge backing; anchor has an identified 4.60631 mm straight unsupported segment with pre-existing projection anchors. PETG bridge quality and strength remain unmeasured.',
        'Supports occupy shaft and nut paths and must be removed before hardware insertion. Detachment force, grip, debris, damage, adhesion and real dimensions remain unverified.',
        'After bed removal and support separation, nominal removal is opposite growth (-CAD Y); the complete path analysis found no lower obstacle. No force or one-piece physical extraction guarantee.',
        'Generic PETG and Textured PEI are analysis assumptions; user confirmed PETG and PEI only.',
    ]
    item = dict(instance_id='feeder/inlet-rear', current_stl_sha256=sha(source),
                slice_folder=rel(FOLDER), selected_3mf=rel(FOLDER / 'slice-review.3mf'),
                selected_3mf_sha256=sha(FOLDER / 'slice-review.3mf'),
                gcode=rel(FOLDER / 'plate_1.gcode'), gcode_sha256=sha(FOLDER / 'plate_1.gcode'),
                plate_quantity=1, identity_status='CURRENT_STL_ACTUAL_3MF_FACE_BIJECTION',
                process_status='BOUNDED_INLET_PROCESS_EVIDENCE_BOUND_PHYSICAL_OPEN',
                needs_reslice=False, pending_review=False,
                reason='Candidate 3: own key growth, chronological underside paths, full nominal hardware volumes and complete support-path contact classification bound. Physical/process-quality limits retained.',
                manufacturing_release=False, physical_acceptance=False, sent_to_printer=False)
    report = dict(status='CURRENT_INLET_PROCESS_BINDING_COMPLETE_WITH_EXPLICIT_LIMITS',
                  created_utc=datetime.now(timezone.utc).isoformat(), items=[item],
                  evidence_sha256=EVIDENCE, source_and_artifacts_stable=True,
                  original_pending_feature=generic['pending_review'][0],
                  resolution='Original generic local-pick limitation is supplemented by complete actual-support projection/record-height localization and contact-origin audit. No strict historical result is rewritten.',
                  scope='One unchanged normal model and one plate; bounded digital manufacturing binding only.',
                  limitations=limitations, manufacturing_release=False, physical_acceptance=False, sent_to_printer=False)
    assert all(sha(ROOT / p) == h for p, h in EVIDENCE.items())
    (OUT / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'evidence_files': len(EVIDENCE), 'instance': item['instance_id'], 'manufacturing_release': False}, ensure_ascii=False))


if __name__ == '__main__': main()
