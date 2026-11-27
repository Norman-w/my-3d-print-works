#!/usr/bin/env python3
"""Compatibility entry: use the EXISTING shared 8877 /fan-nozzle/ service."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PORT = 8877

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "stop"))
    args = parser.parse_args()
    if args.action == "stop":
        parser.error("Shared service was NOT stopped. Manage it explicitly with scripts/preview_lan.py stop.")
    subprocess.run([sys.executable, str(ROOT / "scripts/preview_lan.py"), args.action], check=True)
    with urlopen(f"http://127.0.0.1:{PORT}/fan-nozzle/manifest.json", timeout=5) as response:
        manifest = json.load(response)
    ids = {v["id"] for v in manifest["variantCatalog"]["variants"]}
    if ids != {"fan76-direct", "fan41-direct"}:
        raise RuntimeError("Preview is stale; run scripts/publish_fan_nozzle_preview.py")
    print(f"Fan assembly: http://127.0.0.1:{PORT}/fan-nozzle/#fan76-direct")
    for interface in ("en0", "en1"):
        ip = subprocess.run(["ipconfig", "getifaddr", interface], capture_output=True, text=True)
        if ip.returncode == 0 and ip.stdout.strip():
            print(f"LAN: http://{ip.stdout.strip()}:{PORT}/fan-nozzle/#fan76-direct")

if __name__ == "__main__":
    main()
