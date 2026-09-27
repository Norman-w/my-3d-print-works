#!/usr/bin/env python3
"""Verify the exact published candidate through this Mac's LAN interface."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from urllib.parse import quote
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'output/revision-review'


def main():
    ip = subprocess.check_output(['ipconfig', 'getifaddr', 'en0'], text=True).strip()
    base = f'http://{ip}:8877/'
    client = build_opener(ProxyHandler({}))
    def fetch(name):
        with client.open(base + quote(name, safe='/'), timeout=30) as response:
            return response.read(), dict(response.headers)
    manifest = json.loads((PUBLIC / 'manifest.json').read_text())
    evidence = json.loads((PUBLIC / 'evidence.json').read_text())
    api = json.loads(fetch('api/parts')[0])
    assert api['parts'] == manifest['parts'], 'Live API differs from published manifest'
    names = {'index.html', 'models.html', 'app.js', 'manifest.json',
             'evidence.json', 'printed-parts.csv'}
    if (PUBLIC/'revision-status.json').exists():
        revision=json.loads((PUBLIC/'revision-status.json').read_text())
        assert revision['printed_instances']==evidence['printed_instances']
        names.add('revision-status.json')
    names.update(row['file'] for row in evidence['assets'])
    if (PUBLIC/'motion-manifest.json').exists():
        motion=json.loads((PUBLIC/'motion-manifest.json').read_text())
        names.update(['motion-manifest.json','feeder-motion.html','feeder-motion.mjs','feeder-motion-kinematics.mjs'])
        for part in motion['parts']:
            assert sha256((PUBLIC/part['file']).read_bytes()).hexdigest()==part['sha256']
            names.add(part['file'])
        for path,expected in motion['web_sources'].items():
            assert sha256((PUBLIC/Path(path).name).read_bytes()).hexdigest()==expected
        for part in motion.get('assembly_catalog',[]):
            assert sha256((PUBLIC/part['file']).read_bytes()).hexdigest()==part['sha256']
            names.add(part['file'])
            for piece in part.get('subparts',[]):
                assert sha256((PUBLIC/piece['file']).read_bytes()).hexdigest()==piece['sha256']
                names.add(piece['file'])
    rows = []
    for name in sorted(names):
        expected = (PUBLIC / name).read_bytes()
        actual, headers = fetch(name)
        assert actual == expected, name
        assert 'no-store' in headers.get('Cache-Control', ''), name + ' is cacheable'
        rows.append({'file': name, 'bytes': len(actual), 'sha256': sha256(actual).hexdigest(),
                     'cache_control': headers.get('Cache-Control')})
    listener = subprocess.check_output(
        ['lsof', '-nP', '-iTCP:8877', '-sTCP:LISTEN'], text=True)
    pid = listener.splitlines()[1].split()[1]
    cwd = subprocess.check_output(['lsof', '-a', '-p', pid, '-d', 'cwd', '-Fn'], text=True)
    assert f'n{PUBLIC}\n' in cwd, cwd
    result = {'status': 'PUBLISHED_LAN_BYTES_AND_API_MATCH',
              'verified_at_utc': datetime.now(timezone.utc).isoformat(),
              'base_url': base,
              'verified_from': 'same Mac via LAN IPv4; second device untested',
              'listener': listener, 'process_cwd': cwd,
              'part_count': api['count'],
              'printed_instances': evidence['printed_instances'],
              'groups': api['groups'], 'files': rows,
              'manufacturing_release': False, 'physical_acceptance': False}
    target = ROOT / 'output/preview-service/lan-verification.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f'Verified {len(rows)} files and {api["count"]} entries at {base}')


if __name__ == '__main__':
    main()
