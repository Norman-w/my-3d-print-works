#!/usr/bin/env python3
"""Rebuild the five clean FAN76 v1 meshes from the independent SCAD snapshot.

No mesh surgery, slicer invocation, printer connection, or Git mutation.
"""
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
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/fan76-direct-longtravel-v1-20261007"
SKILL = ROOT.parent / "AISkillsCrossLanguageCodeStandards/skills/openscad-stl-print"
SOURCES = ["fan76-direct-v1.scad", "fan76-direct-v1-parameters.scad", "fan76-direct-v1-thread.scad"]
PARTS = ["body", "core15", "core20", "core25", "core30"]
REVIEWS = ["review-fan-envelope", "review-male-ridge", "review-female-groove"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--openscad", default="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
    ap.add_argument("--part", choices=PARTS + REVIEWS, action="append")
    a = ap.parse_args()
    for folder in ["source", "stl", "review", "render", "verification/logs"]:
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    for name in SOURCES:
        shutil.copy2(ROOT / "cad" / name, OUT / "source" / name)
    source = OUT / "source" / SOURCES[0]
    echo = OUT / "verification/logs/contract.echo"
    cmd = [a.openscad, "--hardwarnings", "-D", 'part="contract"', "-o", str(echo), str(source)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    match = re.search(r"ECHO: fan76_contract = (\[.*\])", echo.read_text())
    if not match:
        raise ValueError("OpenSCAD did not emit the evaluated mechanical contract")
    parameters = dict(json.loads(match.group(1)))
    dump(OUT / "verification/parameters.json", parameters)
    inspect_script = SKILL / "scripts/inspect_stl.py"

    def export(part: str) -> dict:
        folder = "stl" if part in PARTS else "review"
        name = f"fan76-direct-v1-{part}-clean.stl" if part in PARTS else f"{part}.stl"
        target = OUT / folder / name
        with tempfile.TemporaryDirectory(prefix=f"export-{part}-", dir=OUT / "verification") as temp:
            mesh = Path(temp) / name
            command = [a.openscad, "--backend", "Manifold", "--hardwarnings", "--export-format", "binstl",
                       "-D", f'part="{part}"', "-o", str(mesh), str(source)]
            run = subprocess.run(command, capture_output=True, text=True)
            (OUT / f"verification/logs/export-{part}.log").write_text(run.stdout + run.stderr)
            if run.returncode or not mesh.exists():
                raise RuntimeError(f"{part} export failed: {run.stderr}")
            test_command = [sys.executable, str(inspect_script), str(mesh), "--require-watertight", "--json"]
            checked = subprocess.run(test_command, capture_output=True, text=True)
            report = json.loads(checked.stdout)
            report["export_returncode"] = run.returncode
            report["inspect_returncode"] = checked.returncode
            report["file"] = str(target.relative_to(OUT))
            report["path"] = str(target)
            dump(OUT / f"verification/topology-{part}.json", report)
            if checked.returncode:
                raise RuntimeError(f"{part} topology failed: {checked.stdout} {checked.stderr}")
            shutil.copy2(mesh, target)
        print(f"{part}: binary STL / canonical closed-topology PASS / {sha(target)}", flush=True)
        return {"part_id": part, "file": str(target.relative_to(OUT)), "sha256": sha(target),
                "source_module": "f76_body" if part == "body" else "f76_core" if part in PARTS else part,
                "quantity": 1 if part in PARTS else 0, "print_target": part in PARTS,
                "material": "PETG candidate; actual filament not yet selected",
                "print_rotation_deg": [0, 0, 0], "topology": report}

    targets = a.part or PARTS + REVIEWS
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(export, targets))
    # Partial rebuilds update existing records without pretending to validate them.
    old = OUT / "verification/export.json"
    if a.part and old.exists():
        original = json.loads(old.read_text())["files"]
        rows = [r for r in original if r["part_id"] not in targets] + rows
    provenance = {
        "schema_version": "fan76-direct-cad-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "units": "mm", "openscad_version": subprocess.run([a.openscad, "--version"], capture_output=True, text=True).stderr.strip(),
        "status": "GEOMETRY_EXPORTED_VALIDATION_PENDING", "embedded_supports": False,
        "source_sha256": {n: sha(OUT / "source" / n) for n in SOURCES},
        "skill_files_sha256": {str(p.relative_to(SKILL)): sha(p) for p in [
            SKILL / "SKILL.md", SKILL / "references/helical-thread-workflow.md",
            SKILL / "references/printability-checklist.md", SKILL / "references/socket-bayonet-fit.md",
            SKILL / "references/versioned-print-package.md", SKILL / "references/mechanical-design-patterns.md",
            SKILL / "examples/helical-thread-profile.scad"]},
        "files": rows,
    }
    dump(old, provenance)
    if not a.part:
        dump(OUT / "manifest.json", {**provenance, "mechanical_contract": parameters,
             "printer_target": {"model": "X1C", "bed_mm": [256, 256], "max_z_mm": 256, "preferred_part_height_max": 245},
             "sliced": False, "three_mf": None, "physical_fit_verified": False})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
