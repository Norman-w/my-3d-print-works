#!/usr/bin/env python3
"""Export only Ø41 v5 geometry. Never slice, print, or touch another revision."""
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
OUT_DEFAULT = ROOT/"output/fan-tee-narrow-nozzles-v5-20261007"
SKILL_DEFAULT = ROOT.parent/"AISkillsCrossLanguageCodeStandards/skills/openscad-stl-print"
SOURCE_NAMES = ["fan-tee-narrow-v5.scad", "fan-tee-v5-parameters.scad", "fan-tee-v5-thread.scad"]
PRINT_IDS = ["mother", "nozzle15", "nozzle20", "nozzle25", "nozzle30"]
TARGETS = {part: f"stl/fan-tee-v5-{part}-clean.stl" for part in PRINT_IDS}
TARGETS.update({part: f"review/{part}.stl" for part in [
    "review-lugs", "review-shell", "review-lug-roots", "review-male-ridge",
    "review-female-groove", "mother-section", "core-section"]})


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skill-dir", type=Path, default=SKILL_DEFAULT)
    ap.add_argument("--openscad", default="/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
    ap.add_argument("--baseline-package", type=Path, help="Optional initial read-only v4 evidence capture; never a default runtime dependency")
    a = ap.parse_args(); out = a.out.resolve()
    for folder in ["source", "stl", "review", "render", "verification/logs", "verification/reference"]:
        (out/folder).mkdir(parents=True, exist_ok=True)
    for name in SOURCE_NAMES:
        shutil.copy2(ROOT/"cad"/name, out/"source"/name)
    if a.baseline_package:
        baseline = json.loads((a.baseline_package/"verification/parameters.json").read_text())
        dump(out/"verification/v4-baseline.json", {
            "historical_package": str(a.baseline_package.resolve()), "runtime_dependency": False,
            "parameters": baseline,
            "mother_stl_sha256": sha(a.baseline_package/"stl/fan-tee-v4-connector-clean.stl"),
            "source_sha256": {p.name: sha(p) for p in (a.baseline_package/"source").glob("*.scad")},
        })
        old_core = a.baseline_package/"verification/reference/printed-core36.stl"
        if old_core.exists():
            shutil.copy2(old_core, out/"verification/reference/legacy-core36.stl")
            dump(out/"verification/reference/legacy-core36.json", {
                "sha256": sha(old_core), "local_helix_anchor_z": 5.44,
                "phase_at_seated_z_deg": 129.6, "old_length_mm": 45,
                "print_target": False, "purpose": "Thread-only legacy test; short length is not full v5 functional compatibility",
            })
    source = out/"source/fan-tee-narrow-v5.scad"
    echo = out/"verification/logs/parameters.echo"
    subprocess.run([a.openscad, "--hardwarnings", "-D", 'part="contract"',
                    "-o", str(echo), str(source)], check=True, capture_output=True, text=True)
    match = re.search(r"ECHO: v5_parameters = (\[.*\])", echo.read_text())
    if not match:
        raise ValueError("No evaluated OpenSCAD parameter contract")
    dump(out/"verification/parameters.json", dict(json.loads(match.group(1))))
    inspect_script = a.skill_dir/"scripts/inspect_stl.py"

    def export(item: tuple[str, str]) -> dict:
        part, rel = item; path = out/rel
        cmd = [a.openscad, "--backend", "Manifold", "--hardwarnings", "--export-format", "binstl",
               "-D", f'part="{part}"', "-o", str(path), str(source)]
        run = subprocess.run(cmd, capture_output=True, text=True)
        (out/f"verification/logs/{part}.log").write_text(run.stdout+run.stderr)
        if run.returncode:
            raise RuntimeError(f"{part}: {run.stderr}")
        test = subprocess.run([sys.executable, str(inspect_script), str(path),
                               "--require-watertight", "--json"], capture_output=True, text=True)
        if test.returncode:
            raise RuntimeError(f"{part}: {test.stdout} {test.stderr}")
        report = json.loads(test.stdout)
        dump(out/f"verification/topology-{part}.json", report)
        print(part, "closed topology PASS", sha(path), flush=True)
        return {"part_id": part, "file": rel, "sha256": sha(path),
                "print_target": part in PRINT_IDS, "quantity": 1 if part in PRINT_IDS else 0,
                "topology": report}

    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(export, TARGETS.items()))
    dump(out/"verification/export.json", {
        "status": "EXPORTED_GEOMETRY_NOT_SLICE_APPROVAL",
        "source_sha256": {n: sha(out/"source"/n) for n in SOURCE_NAMES},
        "files": rows, "embedded_supports": False,
        "skill_commit_requested": "77f77fd",
        "skill_files_read_sha256": {str(p.relative_to(a.skill_dir)): sha(p) for p in [
            a.skill_dir/"SKILL.md", a.skill_dir/"references/helical-thread-workflow.md",
            a.skill_dir/"references/printability-checklist.md", a.skill_dir/"references/socket-bayonet-fit.md"]},
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
