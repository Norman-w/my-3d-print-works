#!/usr/bin/env python3
"""Join independently reviewed current manufacturing bindings, without printing.

The manifest identifies every instance and selected plate; gaps remain explicit.
This is an evidence index, not a physical or manufacturing release operation.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/current-manufacturing'
EXPORT = ROOT / 'output/cable-scene-export/20260927T091627124663Z/report.json'
EVIDENCE = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    resolved = Path(path).resolve()
    return str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved)


def path(value):
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def read(p):
    p = path(p)
    data = p.read_bytes()
    record(p, hashlib.sha256(data).hexdigest())
    return json.loads(data)


def record(p, digest):
    name = rel(p)
    assert name not in EVIDENCE or EVIDENCE[name] == digest, f'Evidence changed mid-review: {name}'
    EVIDENCE[name] = digest


def verified(p, expected):
    p = path(p)
    actual = sha(p)
    assert actual == expected, f'Changed evidence: {p}'
    record(p, actual)


def main():
    inv = read('docs/cable-assembly-inventory.json')
    export = read(EXPORT)
    assert export['status'] == 'CURRENT_SCENE_EXPORT_PASS'
    for p, h in export['source_sha256'].items():
        verified(p, h)
    printed = {r['id']: r for r in export['parts'] if r['role'] == 'printed'}
    assert len(printed) == inv['counts']['printed'] == 56
    bindings = {}

    def add(rows, evidence, key='instance_id', replace=False):
        for r in rows:
            ident = r[key]
            assert ident in printed, f'Unknown instance: {ident}'
            assert replace or ident not in bindings, f'Duplicate instance: {ident}'
            assert r['current_stl_sha256'] == printed[ident]['sha256'], ident
            bindings[ident] = (r, evidence)

    feeder_path = 'output/current-manufacturing/feeder-reuse/report.json'
    feeder = read(feeder_path)
    assert feeder['sources_and_artifacts_stable']
    for p, h in feeder['source_and_artifact_sha256'].items():
        verified(p, h)
    add(feeder['mapping'], feeder_path)

    cable_path = 'output/current-manufacturing/cable-other-reuse/report.json'
    cable = read(cable_path)
    assert cable['status'] == 'CURRENT_SIX_SLICES_TRANSFERRED_WITH_EXPLICIT_LIMITS'
    for p, h in cable['evidence_sha256'].items():
        verified(p, h)
    add(cable['parts'], cable_path)

    input_path = 'output/current-manufacturing/input-process/manifest.json'
    inputs = read(input_path)
    input_check = read('output/current-manufacturing/input-process/report.json')
    assert input_check['status'] == 'CURRENT_INPUT_PROCESS_BINDING_CHECK_PASS'
    assert rel(path(input_check['manifest'])) == input_path
    verified(input_path, input_check['manifest_sha256'])
    for r in inputs['items']:
        for e in r['review_evidence']:
            verified(e['file'], e['sha256'])
    add(inputs['items'], input_path)

    spin_path = 'output/current-manufacturing/spin-reuse/report.json'
    spin = read(spin_path)
    assert spin['status'] == 'TEN_SPIN_SELECTED_SLICES_REUSABLE_DIGITAL_SCOPE_PHYSICAL_OPEN'
    assert spin['sources_stable']
    for p, h in spin['input_sha256'].items():
        verified(p, h)
    add(spin['rows'], spin_path)

    new_path = 'output/current-manufacturing/feeder-new/mapping.json'
    if path(new_path).exists():
        new = read(new_path)
        assert isinstance(new, list)
        assert len({r['instance_id'] for r in new}) == len(new)
        for r in new:
            assert bindings[r['instance_id']][0]['needs_reslice']
            assert type(r['needs_reslice']) is bool and type(r['pending_review']) is bool
            verified(r['report_file'], r['report_sha256'])
            report = read(r['report_file'])
            assert report['status'] == 'CURRENT_13_INSTANCE_OFFLINE_REVIEW_COMPLETE_WITH_EXPLICIT_LIMITS'
            matches = [x for x in report['mapping'] if x['instance_id'] == r['instance_id']]
            assert len(matches) == 1 and matches[0] == {k:v for k,v in r.items() if k not in ['report_file','report_sha256']}
            for p in report['plate_reports']:
                verified(p['path'], p['sha256'])
            verified(r['current_review'], r['current_review_sha256'])
            verified(r['selected_3mf'], r['selected_3mf_sha256'])
            verified(r['gcode'], r['gcode_sha256'])
        add(new, new_path, replace=True)

    assert set(bindings) == set(printed), 'Missing current instances'
    items = []
    plates = defaultdict(list)
    candidate_plates = defaultdict(list)
    for ident, source in printed.items():
        verified(source['file'], source['sha256'])
        r, evidence = bindings[ident]
        pending = bool(r.get('needs_reslice', False) or r.get('pending_review', False))
        folder = r.get('slice_folder', r.get('selected_slice'))
        selected = r.get('selected_3mf')
        artifacts = r.get('artifacts', {})
        if not selected and 'slice-review.3mf' in artifacts:
            selected = artifacts['slice-review.3mf']['file']
        if not selected and folder and not pending:
            selected = str(path(folder) / 'slice-review.3mf')
        # An outdated slice is evidence of the gap, never a selected plate.
        if r.get('needs_reslice', False):
            selected = None
        selected_hash = None
        gcode = None
        gcode_hash = None
        if selected:
            selected = rel(path(selected))
            selected_hash = sha(path(selected))
            expected = r.get('selected_3mf_sha256') or r.get('artifact_sha256', {}).get('slice-review.3mf')
            if expected:
                assert expected == selected_hash, ident
            if artifacts:
                for a in artifacts.values():
                    verified(a['file'], a['sha256'])
            gcode = r.get('gcode') or (str(path(folder) / 'plate_1.gcode') if folder else None)
            assert gcode, f'Missing G-code path: {ident}'
            gcode = rel(path(gcode))
            gcode_hash = sha(path(gcode))
            if r.get('gcode_sha256'):
                assert gcode_hash == r['gcode_sha256'], ident
            with zipfile.ZipFile(path(selected)) as archive:
                assert hashlib.sha256(archive.read('Metadata/plate_1.gcode')).hexdigest() == gcode_hash, ident
            record(path(gcode), gcode_hash)
            record(path(selected), selected_hash)
            (candidate_plates if pending else plates)[selected].append(ident)
        row = {
            'instance_id': ident, 'name': source['name'], 'quantity': 1,
            'material': 'Bambu TPU 95A HF' if ident == 'spin/pad' else 'PETG',
            'current_stl': source['file'], 'current_stl_sha256': source['sha256'],
            'binding_report': evidence, 'binding_report_sha256': EVIDENCE[evidence],
            'identity_status': r.get('identity_status', r.get('status')),
            'process_status': r.get('process_status', r.get('status')),
            'pending_review': pending, 'needs_reslice': bool(r.get('needs_reslice', False)),
            'selected_3mf': None if pending else selected,
            'selected_3mf_sha256': None if pending else selected_hash,
            'candidate_3mf': selected if pending else None,
            'candidate_3mf_sha256': selected_hash if pending else None,
            'gcode': gcode, 'gcode_sha256': gcode_hash,
            'plate_quantity': r.get('plate_quantity', r.get('quantity_in_selected_3mf', 1)),
            'reason': r.get('reason', 'Current input bound to frozen, reviewed process.'),
            'manufacturing_release': False, 'physical_acceptance': False,
        }
        items.append(row)
    by_id = {r['instance_id']: r for r in items}
    plate_rows = []
    for p, ids in plates.items():
        quantities = {by_id[i]['plate_quantity'] for i in ids}
        assert quantities == {len(ids)}, (p, ids, quantities)
        plate_rows.append({'file': p, 'sha256': EVIDENCE[p], 'instance_ids': ids,
                           'quantity': len(ids), 'print_plate_once_for_these_instances': True,
                           'pending_review': any(by_id[i]['pending_review'] for i in ids)})
    candidate_rows = []
    for p, ids in candidate_plates.items():
        assert {by_id[i]['plate_quantity'] for i in ids} == {len(ids)}, (p, ids)
        candidate_rows.append({'file': p, 'sha256': EVIDENCE[p], 'instance_ids': ids,
                               'quantity': len(ids), 'pending_review': True})
    record(__file__, sha(__file__))
    assert all(sha(path(p)) == h for p, h in EVIDENCE.items())
    counts = {'printed_instances': len(items), 'material_instances': dict(Counter(r['material'] for r in items)),
              'bound_instances': sum(bool(r['selected_3mf']) for r in items),
              'candidate_instances': sum(bool(r['candidate_3mf']) for r in items),
              'pending_instances': sum(r['pending_review'] for r in items),
              'needs_reslice_instances': sum(r['needs_reslice'] for r in items),
              'selected_plates': len(plate_rows), 'candidate_plates': len(candidate_rows)}
    d = {'schema_version': 1, 'status': 'CURRENT_MANUFACTURING_INDEX_WITH_OPEN_GATES',
         'created_utc': datetime.now(timezone.utc).isoformat(), 'counts': counts,
         'items': items, 'plates': plate_rows, 'candidate_plates': candidate_rows, 'evidence_sha256': EVIDENCE,
         'sources_and_artifacts_stable': True, 'manufacturing_release': False,
         'physical_acceptance': False, 'sent_to_printer': False,
         'scope': 'Current 56-instance evidence index. Consult each binding report for exact normal-mesh identity, actual process, support-cleaning scope and retained failures. A bound slice is not a physical or manufacturing release.',
         'assumptions': ['X1C, 0.4 mm nozzle; PETG brand unspecified; Textured PEI analysis assumption; TPU pad has its own Bambu TPU 95A HF profile.']}
    (OUT / 'manifest.json').write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
    keys = ['instance_id','name','quantity','material','current_stl','current_stl_sha256',
            'selected_3mf','candidate_3mf','plate_quantity','pending_review','needs_reslice','identity_status','process_status','binding_report']
    with (OUT / 'instances.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(items)
    print(json.dumps({'status': d['status'], 'counts': counts}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
