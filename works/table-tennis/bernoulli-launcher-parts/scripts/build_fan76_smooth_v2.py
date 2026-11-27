#!/usr/bin/env python3
"""New Ø76 shell + byte-identical Ø41 v5 cores; never slice/send/alter old releases."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from fan76_smooth_release import smooth_release

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/fan76-smooth-v2-20261008"
CORES = ROOT / "output/fan-tee-narrow-nozzles-v5-20261007"
SKILL = Path("/Users/norman/.codex/skills/openscad-stl-print")
SOURCE = "fan76-smooth-v2.scad"
SOURCES = [SOURCE, "fan-tee-v5-parameters.scad", "fan-tee-v5-thread.scad", "fan-tee-narrow-v5.scad"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def build(openscad, revision=2):
    release = smooth_release(revision)
    OUT, SOURCE, SOURCES = release.out, release.source, release.sources
    for name in ["source", "stl", "review", "render", "verification/logs"]:
        (OUT / name).mkdir(parents=True, exist_ok=True)
    original = json.loads((CORES / "verification/export.json").read_text())
    for name in SOURCES:
        source = ROOT / "cad" / name
        if name != SOURCE:
            if sha(source) != original["source_sha256"][name]:
                raise ValueError(f"Do not change the frozen compatible core source: {name}")
        shutil.copy2(source, OUT / "source" / name)
    contract = OUT / "verification/logs/contract.echo"
    subprocess.run([openscad, "--hardwarnings", "-D", 'part="contract"', "-o", str(contract),
                    str(OUT / "source" / SOURCE)], check=True, capture_output=True, text=True)
    match = re.search(r"ECHO: fan76_smooth_contract = (\[.*\])", contract.read_text())
    if not match:
        raise ValueError(f"Missing evaluated v{revision} contract")
    p = dict(json.loads(match.group(1)))
    dump(OUT / "verification/parameters.json", p)
    if revision >= 4:
        sample_echo = OUT / "verification/logs/profile-samples.echo"
        subprocess.run([openscad, "--hardwarnings", "-D", 'part="profile-samples"', "-o", str(sample_echo),
                        str(OUT / "source" / SOURCE)], check=True, capture_output=True, text=True)
        samples = re.search(r"ECHO: fan76_profile_samples = (\[.*\])", sample_echo.read_text())
        if not samples:
            raise ValueError("Missing evaluated wall/profile samples")
        dump(OUT / "verification/profile-samples.json", json.loads(samples.group(1)))

    def export(part):
        folder = "stl" if part == "body" else "review"
        name = f"{release.stem}-body-clean.stl" if part == "body" else f"{part}.stl"
        target = OUT / folder / name
        command = [openscad, "--backend", "Manifold", "--hardwarnings", "--export-format", "binstl",
                   "-D", f'part="{part}"', "-o", str(target), str(OUT / "source" / SOURCE)]
        run = subprocess.run(command, capture_output=True, text=True)
        (OUT / f"verification/logs/{part}.log").write_text(run.stdout + run.stderr)
        if run.returncode:
            raise RuntimeError(run.stderr)
        report = subprocess.run([sys.executable, str(SKILL / "scripts/inspect_stl.py"), str(target),
                                 "--require-watertight", "--json"], capture_output=True, text=True)
        topology = json.loads(report.stdout)
        dump(OUT / f"verification/topology-{part}.json", topology)
        if report.returncode:
            raise ValueError(f"Final STL topology failed: {topology}")
        print(f"{part}: exported and closed topology PASS", flush=True)
        return {"part_id": part, "file": str(target.relative_to(OUT)), "sha256": sha(target),
                "print_target": part == "body", "source": SOURCE, "source_selector": f'part="{part}"',
                "units": "mm", "topology": topology}

    with ThreadPoolExecutor(max_workers=2) as pool:
        files = list(pool.map(export, ["body", "review-fan-envelope", "review-female-groove"]))
    for diameter in p["outlet_ids"]:
        source = CORES / f"stl/fan-tee-v5-nozzle{diameter}-clean.stl"
        recorded = next(r for r in original["files"] if r["file"] == str(source.relative_to(CORES)))
        if sha(source) != recorded["sha256"]:
            raise ValueError(f"Original compatible core STL changed: {source}")
        target = OUT / "stl" / source.name
        shutil.copy2(source, target)
        assert source.read_bytes() == target.read_bytes()
        files.append({"part_id": f"core{diameter}", "file": str(target.relative_to(OUT)),
                      "sha256": sha(target), "print_target": True, "units": "mm",
                      "source": "fan-tee-narrow-v5.scad", "source_selector": f'part="nozzle{diameter}"',
                      "copied_from": str(source.relative_to(ROOT)), "unchanged_bytes": True})
        print(f"core{diameter}: exact frozen Ø41 STL copy PASS", flush=True)
    report = {"schema_version": release.stem, "generated_utc": datetime.now(timezone.utc).isoformat(),
              "units": "mm", "source_sha256": {name: sha(OUT / "source" / name) for name in SOURCES},
              "files": files, "mechanical_contract": p, "embedded_supports": False,
              "status": "CAD_REVIEW_NOT_SLICED", "sliced": False, "physical_fit_verified": False,
              "flow_performance_verified": False}
    dump(OUT / "verification/export.json", report)
    dump(OUT / "manifest.json", report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", default="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
    parser.add_argument("--revision", type=int, choices=[2, 3, 4, 5], default=2)
    args = parser.parse_args()
    build(args.openscad, args.revision)


if __name__ == "__main__":
    main()
