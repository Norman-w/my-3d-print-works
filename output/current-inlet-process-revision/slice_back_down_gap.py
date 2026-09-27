#!/usr/bin/env python3
"""Same rear-key-down native candidate, one change: tree XY clearance .6 mm.

No geometric edit, no shared-preset mutation and no printer connection. The
original slice helper records the exact overridden local process hash before
launching Bambu Studio. Wider XY clearance is a hypothesis, not a release.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OLD = ROOT / 'output/current-manufacturing/feeder-new/runs/20260927T094300899015Z/inlet-rear-anchor-z-down-supported'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
dump = lambda p, d: Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')


def main():
    spec = importlib.util.spec_from_file_location('base', ROOT / 'scripts/review_final_feeder_slice.py')
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    old = json.loads((OLD / 'invocation.json').read_text())
    source = ROOT / old['inputs'][0]['file']
    assert sha(source) == '146bcf746c8f1a52825c68675ad1844d8ed4de079c75c3885504240121e3069a'
    run = OUT / 'runs' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True)
    base.OUT = run
    base.PLAN['inlet-rear'] = (
        ['--rotate-x', '90'], True, 'rear-key-ends-down-xy060',
        'Rear key ends down, growth +CAD Y; original .2 mm layer and Z gaps; only tree XY gap .35 to .6 mm.')
    original_dump = base.dump

    def dump_local_process(path, value):
        if Path(path).name == 'process.json':
            assert str(value['support_object_xy_distance']) == '0.35'
            value = {**value, 'support_object_xy_distance': '0.6'}
        original_dump(path, value)

    base.dump = dump_local_process
    snapshot = {
        'groups': {'inlet-rear': old['inputs']},
        'source_sha256': {**old['source_sha256_at_start'], str(Path(__file__).relative_to(ROOT)): sha(__file__)},
        'shared_profile_sha256': old['shared_profile_sha256'],
        'hypothesis': 'Single process-field change relative to rear-key-down candidate: support_object_xy_distance 0.35 -> 0.6. Recheck both extraction and underside first paths.',
    }
    assert all(sha(ROOT / p) == h for p, h in snapshot['source_sha256'].items())
    assert all(sha(base.CONFIG / (n + '.json')) == h for n, h in snapshot['shared_profile_sha256'].items())
    dump(run / 'input-snapshot.json', snapshot)
    print(str(run), flush=True)
    folder = base.slice_family('inlet-rear', snapshot)
    inv = json.loads((folder / 'invocation.json').read_text())
    actual = json.loads((folder / 'process.json').read_text())
    original = json.loads((OLD / 'process.json').read_text())
    delta = {k: [original.get(k), actual.get(k)] for k in original.keys() | actual.keys() if original.get(k) != actual.get(k)}
    assert delta == {'support_object_xy_distance': ['0.35', '0.6']}, delta
    status = 'NATIVE_XY_GAP_CANDIDATE_REVIEW_REQUIRED' if inv['return_code'] == inv.get('native_result', {}).get('return_code') == 0 else 'NATIVE_SLICE_FAILED'
    result = dict(folder=str(folder.relative_to(ROOT)), status=status, mechanical_geometry_changed=False, process_delta=delta)
    dump(run / 'process-delta.json', result)
    dump(OUT / 'back-down-gap-latest.json', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
