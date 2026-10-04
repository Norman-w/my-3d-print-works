#!/usr/bin/env python3
"""Check nominal empty corridors for a future motor/rocker interface.

The probes contain no real actuator envelope, joint, bracket or fastener.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electric-drive-route-audit.scad"
OUT = ROOT / "output/electric-drive-route"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def source_tree(path: Path, found: set[Path] | None = None) -> set[Path]:
    found = found if found is not None else set()
    path = path.resolve()
    if path in found:
        return found
    found.add(path)
    for name in re.findall(r"\b(?:use|include)\s*<([^>]+)>", path.read_text()):
        source_tree(path.parent / name, found)
    return found


def run(row: tuple[str, str, float, bool]) -> tuple[str, dict]:
    region, target, position, expected_occupied = row
    tag = f"{region}-{target}-t{position:.2f}"
    destination = OUT / f"{tag}.stl"
    destination.unlink(missing_ok=True)
    command = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
               "-D", f'dr_region="{region}"', "-D", f'dr_target="{target}"',
               "-D", f"dr_t={position}", "-o", str(destination), str(CAD)]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=120)
    log = result.stdout + result.stderr
    if (result.returncode == 1 and "Current top level object is empty" in log
            and "WARNING:" not in log and "ERROR:" not in log):
        return tag, {"empty": True, "expected_occupied": expected_occupied,
                     "passed": not expected_occupied}
    if result.returncode or "WARNING:" in log or "ERROR:" in log:
        return tag, {"error": log[-1200:], "passed": False}
    inspected = subprocess.run([sys.executable, str(INSPECT), str(destination),
                                "--json", "--require-watertight"], cwd=ROOT,
                               text=True, capture_output=True)
    if inspected.returncode:
        return tag, {"error": inspected.stdout[-1200:] + inspected.stderr[-1200:],
                     "passed": False}
    mesh = json.loads(inspected.stdout)
    volume = mesh["volume"]
    zero_thickness_sheet = abs(volume) < 1e-9 and min(mesh["bounds"]["size"]) < 1e-9
    if abs(volume) < 1e-9 and not zero_thickness_sheet:
        return tag, {"error": "zero volume with nonplanar extent",
                     "mesh": mesh, "passed": False}
    occupied = volume > 1e-9
    return tag, {"empty": not occupied, "sheet_only": zero_thickness_sheet,
                 "volume_mm3": volume, "bounds": mesh["bounds"],
                 "expected_occupied": expected_occupied,
                 "passed": occupied == expected_occupied,
                 "stl_sha256": sha(destination), "bytes": destination.stat().st_size}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for position in (0, .25, .5, .75, 1):
        rows.extend((region, target, position, False)
                    for region in ("right-drive-plane", "right-riser", "pivot-crossbar")
                    for target in ("fixed", "moving", "hardware"))
        rows.append(("anchor-patch", "moving", position, False))
    rows.extend(("anchor-patch", target, 0, True) for target in ("fixed", "hardware"))
    before = {str(path.relative_to(ROOT)): sha(path)
              for path in sorted(source_tree(CAD) | {Path(__file__).resolve()})}
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = dict(pool.map(run, rows))
    after = {str(path.relative_to(ROOT)): sha(path)
             for path in sorted(source_tree(CAD) | {Path(__file__).resolve()})}
    failures = [tag for tag, row in results.items() if not row["passed"]]
    if before != after:
        failures.append("source changed during probe")
    report = {
        "status": "NOMINAL_ROUTE_CORRIDOR_PASS_NOT_A_MOUNT" if not failures else "FAIL",
        "source_sha256": before, "probes": results, "probe_count": len(rows),
        "failures": failures,
        "regions_mm": {
            "right-drive-plane": [[20, 120], [58, 70], [-80, 60]],
            "right-riser": [[72, 82], [30, 70], [-35, 45]],
            "pivot-crossbar": [[18, 78], [60, 66], [20, 26]],
            "anchor-patch": [[60, 67], [24, 30], [-32, 3]],
        },
        "real_motor_envelope_placed": False,
        "pivot_load_path_designed": False,
        "carriage_connection_designed": False,
        "full_continuous_sweep_proven": False,
        "motor_mount_designed": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"drive route: {'PASS' if not failures else 'FAIL'}; {len(rows)} probes")
    for failure in failures:
        print("  " + failure)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
