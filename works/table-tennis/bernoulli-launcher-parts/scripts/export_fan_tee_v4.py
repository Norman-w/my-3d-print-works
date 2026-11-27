#!/usr/bin/env python3
"""Rebuild the standalone v4 connector and review meshes; no slicer/device actions.

Optional --reference-core freezes an explicitly supplied existing core mesh for
compatibility evidence. Subsequent runs only use the frozen local witness, so
retirement of earlier version directories cannot break v4.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "output/fan-tee-direct-print-v4-20261007"
SOURCE_NAMES = ["fan-tee-direct-v4.scad", "fan-tee-v4-parameters.scad", "fan-tee-v4-thread.scad"]
TARGETS = {
    "connector": "stl/fan-tee-v4-connector-clean.stl",
    "reference-core36": "verification/reference/baseline-anchored-core36.stl",
    "review-shell": "review/shell.stl",
    "review-lugs": "review/lugs.stl",
    "review-root-intersection": "review/lug-root-intersection.stl",
    "review-female-groove": "review/female-groove.stl",
    "connector-section": "review/connector-section.stl",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--openscad", default="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
    parser.add_argument("--skill-dir", type=Path, default=Path.home()/".codex/skills/openscad-stl-print")
    parser.add_argument("--reference-core", type=Path)
    parser.add_argument("--reference-sha256")
    args = parser.parse_args()
    out = args.out.resolve()
    for folder in ["source", "stl", "review", "verification/reference", "logs", "render"]:
        (out/folder).mkdir(parents=True, exist_ok=True)
    # Never touch print/ or verification/retirement.json: owned by main thread.
    for name in SOURCE_NAMES:
        source = ROOT/"cad"/name
        shutil.copy2(source, out/"source"/name)
        assert sha(source) == sha(out/"source"/name)
    if args.reference_core:
        ref_sha = sha(args.reference_core)
        if args.reference_sha256 and ref_sha != args.reference_sha256:
            raise ValueError("Existing core witness hash does not match the declared baseline")
        destination = out/"verification/reference/printed-core36.stl"
        if destination.exists() and sha(destination) != ref_sha:
            raise ValueError("Refusing to replace a different existing core witness")
        shutil.copy2(args.reference_core, destination)
        dump(out/"verification/reference/printed-core-provenance.json", {
            "historical_source_path": str(args.reference_core.resolve()),
            "source_path_is_runtime_dependency": False,
            "file": str(destination.relative_to(out)), "sha256": ref_sha,
            "role": "compatibility witness only; NOT a print target",
            "physical_identity_note": "Historical exported core36; physical part identity and fit still require confirmation",
        })
    source = out/"source/fan-tee-direct-v4.scad"
    echo_path = out/"logs/parameters.echo"
    subprocess.run([args.openscad, "--hardwarnings", "-D", 'part="contract"',
                    "-o", str(echo_path), str(source)], check=True, capture_output=True, text=True)
    match = re.search(r"ECHO: v4_parameters = (\[.*\])", echo_path.read_text())
    if not match:
        raise ValueError("OpenSCAD did not evaluate the parameter contract")
    dump(out/"verification/parameters.json", dict(json.loads(match.group(1))))
    inspect_script = args.skill_dir/"scripts/inspect_stl.py"

    def build(item: tuple[str, str]) -> dict:
        selector, relative = item
        destination = out/relative
        command = [args.openscad, "--backend", "Manifold", "--hardwarnings",
                   "--export-format", "binstl", "-D", f'part="{selector}"',
                   "-o", str(destination), str(source)]
        result = subprocess.run(command, capture_output=True, text=True)
        (out/"logs"/f"{selector}.log").write_text(result.stdout+result.stderr)
        if result.returncode:
            raise RuntimeError(f"{selector}: {result.stderr}")
        result = subprocess.run([sys.executable, str(inspect_script), str(destination),
                                 "--require-watertight", "--json"], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"{selector} topology: {result.stdout} {result.stderr}")
        report = json.loads(result.stdout)
        dump(out/"verification"/f"topology-{selector}.json", report)
        print(f"{selector}: export and closed-edge topology PASS", flush=True)
        return {"selector": selector, "file": relative, "sha256": sha(destination),
                "print_target": selector == "connector", "topology": report}

    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(build, TARGETS.items()))
    dump(out/"verification/export.json", {
        "status": "EXPORTED_NOT_SLICED", "units": "mm by source convention",
        "source_sha256": {name: sha(out/"source"/name) for name in SOURCE_NAMES},
        "openscad_version": subprocess.run([args.openscad, "--version"], capture_output=True, text=True).stderr.strip(),
        "files": records, "embedded_support_geometry": False,
        "physical_fit_verified": False, "sliced": False,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
