#!/usr/bin/env python3
"""Check fixed nominal cable route against declared service access envelopes.

This is an added-obstacle check. Existing tool-to-host clearance, tool purchase,
disconnected-cable motion, and physical serviceability remain separate evidence.
"""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import ast
import hashlib
import json
import re
import subprocess
from feeder_integration import classify

ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT/'cad/cable-service-review.scad'
EXE = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'


def hashes():
    paths = {Path(__file__).resolve(), ROOT/'analysis/feeder_integration.py'}
    pending = [CAD]
    while pending:
        p = pending.pop().resolve()
        if p in paths:
            continue
        paths.add(p)
        pending.extend(p.parent/name for name in
                       re.findall(r'\b(?:include|use)\s*<([^>]+)>', p.read_text()))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def execute(out, name, definitions, suffix='stl'):
    target = out/(name+'.'+suffix)
    cmd = [EXE, '--hardwarnings', '--backend', 'Manifold']
    if suffix == 'stl':
        cmd += ['--export-format', 'asciistl']
    for key, value in definitions.items():
        cmd += ['-D', key+'='+json.dumps(value)]
    cmd += ['-o', str(target), str(CAD)]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    log = result.stdout+result.stderr
    (out/(name+'.log')).write_text(log)
    empty = 'Current top level object is empty' in log and not target.exists()
    ok = not ('WARNING:' in log or 'ERROR:' in log) and (
        result.returncode == 0 or empty) and (target.exists() or empty)
    return {'name': name, 'command': cmd, 'returncode': result.returncode,
            'execution_ok': ok, 'empty': empty,
            'file': str(target.relative_to(ROOT)) if target.exists() else None}


def main():
    out = ROOT/'output/cable-service-review'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    before = hashes()
    row = execute(out, 'contract', {'csr_part': 'contract'}, 'echo')
    if not row['execution_ok'] or not row['file']:
        raise RuntimeError('Service contract export failed; see '+str(out))
    raw = (ROOT/row['file']).read_text()
    line = next(s for s in raw.splitlines() if s.startswith('ECHO: "CSR_CONTRACT", '))
    value = line.split('ECHO: "CSR_CONTRACT", ', 1)[1]
    for old, new in [('undef', 'None'), ('true', 'True'), ('false', 'False')]:
        value = re.sub(r'\b'+old+r'\b', new, value)
    contract = dict(ast.literal_eval(value))

    def probe(job):
        kind, fault = job
        name = kind+('-positive-control' if fault else '')
        result = execute(out, name, {'csr_part': 'probe', 'csr_kind': kind, 'csr_fault': fault})
        info = classify(ROOT/result['file']) if result['file'] else {
            'has_solid_or_unclassified_overlap': False, 'components': []}
        result.update(classification=info, expected_overlap=fault,
                      passed=result['execution_ok'] and info['has_solid_or_unclassified_overlap'] == fault)
        print(name, result['passed'], flush=True)
        return result

    jobs = [(kind, False) for kind in contract['kinds']]+[(contract['kinds'][0], True)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(probe, jobs))
    stable = before == hashes()
    passed = stable and all(r['passed'] for r in results)
    report = {
        'status': 'NOMINAL_SERVICE_ROUTE_PASS' if passed else 'FAIL_OR_STALE',
        'sources_stable': stable, 'source_sha256': before,
        'contract': contract, 'results': results,
        'scope': 'Nominal fixed complete sheath plus 1 mm clearance against named service envelopes. '
                 'Continuous conservative Z sweeps where declared; follower tools sampled at 21 poses.',
        'preconditions': {
            'output-cap-removal': 'Remove cap screws before sliding cap +Y.',
            'output-washer-removal': 'Cap removed; washer not retained after this step.',
            'output-terminal-removal': 'Release clamp and withdraw core from closed cross-hole first; '
                                       'terminal cannot slide sideways through a stationary core.',
            'input-module-removal': 'NOT TESTED against a fixed route: disconnect output core and ferrule, '
                                    'open intermediate route retainers, then remove input module.',
            'input-cover-removal': 'NOT TESTED in installed host: remove input module to bench first.'},
        'unverified': ['unlisted service envelopes', 'actual tool choice and full wrench rotation',
                       'tool-to-existing-host clearance beyond separate local reports',
                       'flexible cable deformation during disconnection', 'physical route retention',
                       'real external blower/tee/hand/backpack', 'manufacturing and loaded performance'],
        'manufacturing_release': False, 'physical_acceptance': False}
    path = out/'report.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(report['status'], path, flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
