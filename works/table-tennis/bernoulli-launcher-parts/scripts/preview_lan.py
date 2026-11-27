#!/usr/bin/env python3
"""Run this project's existing preview under the current macOS login session."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / 'output/revision-review'
STATE = ROOT / 'output/preview-service'
SERVER = ROOT / 'scripts/launcher_preview_server.py'
LABEL = 'local.norman.bernoulli-preview'
DOMAIN = f'gui/{os.getuid()}'
TARGET = f'{DOMAIN}/{LABEL}'
PORT = 8877


def registered():
    return subprocess.run(['launchctl', 'print', TARGET], capture_output=True).returncode == 0


def health():
    with urlopen(f'http://127.0.0.1:{PORT}/api/parts', timeout=2) as response:
        payload = json.load(response)
    expected = json.loads((PREVIEW / 'manifest.json').read_text())
    if {p['id'] for p in payload['parts']} != {p['id'] for p in expected['parts']}:
        raise RuntimeError('Port is serving a different model listing')
    return payload['count']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'status', 'stop'))
    args = parser.parse_args()
    if args.action == 'stop':
        if registered():
            subprocess.run(['launchctl', 'bootout', TARGET], check=True)
        print('Preview service stopped.')
        return
    if args.action == 'start' and not registered():
        for path in (PREVIEW / 'index.html', PREVIEW / 'manifest.json', SERVER):
            if not path.is_file():
                raise FileNotFoundError(path)
        listener = subprocess.run(['lsof', '-nP', f'-iTCP:{PORT}', '-sTCP:LISTEN'], capture_output=True, text=True)
        if listener.returncode == 0:
            raise RuntimeError(f'Port {PORT} is occupied; existing process was left untouched.\n{listener.stdout}')
        STATE.mkdir(parents=True, exist_ok=True)
        plist = STATE / f'{LABEL}.plist'
        plist.write_bytes(plistlib.dumps({
            'Label': LABEL,
            'ProgramArguments': [sys.executable, str(SERVER), '--directory', str(PREVIEW),
                                 '--host', '0.0.0.0', '--port', str(PORT)],
            'WorkingDirectory': str(PREVIEW),
            'RunAtLoad': True,
            'KeepAlive': True,
            'ThrottleInterval': 5,
            'StandardOutPath': str(STATE / 'stdout.log'),
            'StandardErrorPath': str(STATE / 'stderr.log'),
            'EnvironmentVariables': {'PYTHONUNBUFFERED': '1'},
        }))
        subprocess.run(['launchctl', 'bootstrap', DOMAIN, str(plist)], check=True)
    if not registered():
        raise RuntimeError('Preview service is not running')
    for attempt in range(20):
        try:
            count = health()
            break
        except Exception:
            if attempt == 19:
                raise
            time.sleep(.25)
    print(f'Running, {count} parts; bound to 0.0.0.0:{PORT}')
    print(f'Local: http://127.0.0.1:{PORT}/')
    for interface in ('en0', 'en1'):
        ip = subprocess.run(['ipconfig', 'getifaddr', interface], capture_output=True, text=True)
        if ip.returncode == 0 and ip.stdout.strip():
            print(f'LAN ({interface}): http://{ip.stdout.strip()}:{PORT}/')
    print('Managed for this login session; run start again after reboot/logout.')


if __name__ == '__main__':
    main()
