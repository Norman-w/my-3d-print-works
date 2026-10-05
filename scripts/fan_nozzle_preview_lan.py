#!/usr/bin/env python3
"""Serve the unified fan-nozzle assembly preview on the local LAN."""

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
PREVIEW = ROOT / "output/fan-nozzle-preview"
STATE = ROOT / "output/preview-service"
SERVER = ROOT / "scripts/launcher_preview_server.py"
LABEL = "local.norman.fan-nozzle-preview"
DOMAIN = f"gui/{os.getuid()}"
TARGET = f"{DOMAIN}/{LABEL}"
PORT = 8899


def registered():
    return subprocess.run(
        ["launchctl", "print", TARGET], capture_output=True
    ).returncode == 0


def health():
    required = ("index.html", "app.mjs", "manifest.json", "manifest-fan41-direct.json")
    for name in required:
        with urlopen(f"http://127.0.0.1:{PORT}/{name}", timeout=2) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status} for {name}")
    with urlopen(f"http://127.0.0.1:{PORT}/manifest.json", timeout=2) as response:
        manifest = json.load(response)
    variants = manifest.get("variantCatalog", {}).get("variants", [])
    if {item.get("id") for item in variants} != {"fan76-tube", "fan41-direct"}:
        raise RuntimeError("Unified fan variant catalog is incomplete")
    return len(variants)


def print_status(count):
    print(f"Running, {count} fan schemes; bound to 0.0.0.0:{PORT}")
    print(f"Local: http://127.0.0.1:{PORT}/")
    for interface in ("en0", "en1"):
        ip = subprocess.run(
            ["ipconfig", "getifaddr", interface], capture_output=True, text=True
        )
        if ip.returncode == 0 and ip.stdout.strip():
            print(f"LAN ({interface}): http://{ip.stdout.strip()}:{PORT}/")
    print("Managed for this login session; run start again after reboot/logout.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "stop"))
    args = parser.parse_args()

    if args.action == "stop":
        if registered():
            subprocess.run(["launchctl", "bootout", TARGET], check=True)
        print("Fan-nozzle preview service stopped.")
        return

    if args.action == "start" and not registered():
        for path in (PREVIEW / "index.html", PREVIEW / "manifest.json", SERVER):
            if not path.is_file():
                raise FileNotFoundError(path)
        listener = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{PORT}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
        )
        if listener.returncode == 0:
            raise RuntimeError(
                f"Port {PORT} is occupied; existing process was left untouched.\n"
                f"{listener.stdout}"
            )
        STATE.mkdir(parents=True, exist_ok=True)
        plist = STATE / f"{LABEL}.plist"
        plist.write_bytes(
            plistlib.dumps(
                {
                    "Label": LABEL,
                    "ProgramArguments": [
                        sys.executable,
                        str(SERVER),
                        "--directory",
                        str(PREVIEW),
                        "--host",
                        "0.0.0.0",
                        "--port",
                        str(PORT),
                    ],
                    "WorkingDirectory": str(PREVIEW),
                    "RunAtLoad": True,
                    "KeepAlive": True,
                    "ThrottleInterval": 5,
                    "StandardOutPath": str(STATE / "fan-nozzle-stdout.log"),
                    "StandardErrorPath": str(STATE / "fan-nozzle-stderr.log"),
                    "EnvironmentVariables": {"PYTHONUNBUFFERED": "1"},
                }
            )
        )
        subprocess.run(["launchctl", "bootstrap", DOMAIN, str(plist)], check=True)

    if not registered():
        raise RuntimeError("Fan-nozzle preview service is not running")

    for attempt in range(20):
        try:
            count = health()
            break
        except Exception:
            if attempt == 19:
                raise
            time.sleep(0.25)
    print_status(count)


if __name__ == "__main__":
    main()
