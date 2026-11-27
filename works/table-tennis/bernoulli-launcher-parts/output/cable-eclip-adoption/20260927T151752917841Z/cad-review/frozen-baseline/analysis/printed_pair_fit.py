#!/usr/bin/env python3
"""Check each printed STL pair at its exported assembly pose."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
from feeder_integration import classify

ROOT = Path(__file__).resolve().parents[1]
EXE = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', default='output/launcher-final/report.json')
    parser.add_argument('--out', default='output/printed-pair-fit')
    args = parser.parse_args()
    report_path = ROOT/args.report
    original = sha(report_path)
    inventory = json.loads(report_path.read_text())
    parts = [p for p in inventory['parts'] if p['role'] == 'printed']
    out = ROOT/args.out
    out.mkdir(parents=True, exist_ok=True)
    candidates, disjoint = [], []
    for a, b in itertools.combinations(parts, 2):
        for p in (a, b):
            assert sha(ROOT/p['file']) == p['sha256'], p['id']
        A, B = a['mesh']['bounds'], b['mesh']['bounds']
        # Strict separation only. Tangencies still get a real CSG check.
        overlap = [min(A['max'][k], B['max'][k])-max(A['min'][k], B['min'][k]) for k in range(3)]
        if min(overlap) < 0:
            disjoint.append([a['id'], b['id']])
        else:
            candidates.append((a, b))

    def check(pair):
        a, b = pair
        name = a['id']+'--'+b['id']
        source, target = out/(name+'.scad'), out/(name+'.stl')
        source.write_text('intersection(){\n'+''.join(
            'import('+json.dumps(str(ROOT/p['file']))+');\n' for p in pair)+'}\n')
        target.unlink(missing_ok=True)
        command = [EXE, '--hardwarnings', '--backend', 'Manifold', '--export-format', 'asciistl',
                   '-o', str(target), str(source)]
        proc = subprocess.run(command, capture_output=True, text=True)
        log = proc.stdout+proc.stderr
        (out/(name+'.log')).write_text(log)
        empty = 'Current top level object is empty' in log and not target.exists()
        ok = not any(x in log for x in ['ERROR:', 'WARNING:']) and (proc.returncode == 0 or empty)
        result = classify(target) if target.exists() else {'components': [], 'has_solid_or_unclassified_overlap': False}
        passed = ok and not result['has_solid_or_unclassified_overlap']
        print(name, passed, flush=True)
        return {'pair': [a['id'], b['id']], 'passed': passed, 'command': command,
                'returncode': proc.returncode, **result}

    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(check, candidates))
    stable = sha(report_path) == original and all(sha(ROOT/p['file']) == p['sha256'] for p in parts)
    passed = stable and all(row['passed'] for row in rows)
    result = {'status': 'PRINTED_PAIR_POSE_PASS' if passed else 'PRINTED_PAIR_POSE_FAIL_OR_STALE',
              'source_report': str(report_path.relative_to(ROOT)), 'source_report_sha256': original,
              'script_sha256': sha(Path(__file__)), 'source_stable': stable,
              'printed_instances': len(parts), 'strictly_separated_pairs': disjoint, 'checked_pairs': rows,
              'scope': 'Every unordered printed-STL pair at the exported pose only. No whole-motion, tolerance, hardware, or physical acceptance claim.',
              'physical_acceptance': False}
    (out/'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(result['status'], flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
