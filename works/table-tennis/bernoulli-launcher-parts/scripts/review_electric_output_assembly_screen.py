#!/usr/bin/env python3
"""Check cap/tool paths and a rocker axial insertion route in nominal CAD."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electric-output-assembly-screen.scad"
OUT = ROOT / "output/electric-output-crosshead-screen"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
OFFSETS = (0, 2.5, 5, 7.5, 10, 15, 20)


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def source_closure(path: Path, found: set[Path] | None = None) -> set[Path]:
    found = found if found is not None else set()
    path = path.resolve()
    if path in found:
        return found
    found.add(path)
    for name in re.findall(r"\b(?:use|include)\s*<([^>]+)>", path.read_text()):
        source_closure(path.parent / name, found)
    return found


def probe(case: tuple[str, float, float, float]) -> tuple[str, dict]:
    kind, stroke, cap_progress, offset = case
    name = f"{kind}-t{stroke:g}-s{cap_progress:g}-dy{offset:g}"
    path = OUT / "assembly-probes" / f"{name}.stl"
    path.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'oa_probe="{kind}"', "-D", f"oc_t={stroke}",
           "-D", f"rb_t={stroke}", "-D", f"cf_t={stroke}",
           "-D", "rb_plane_y=65", "-D", "rb_motor_y=63",
           "-D", "pm_pivot_y=65", "-D", f"oa_cap_progress={cap_progress}",
           "-D", f"oa_rocker_y_offset={offset}",
           "-o", str(path), str(CAD)]
    run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                         timeout=120)
    log = run.stdout + run.stderr
    if (run.returncode == 1 and "Current top level object is empty" in log
            and "WARNING:" not in log and "ERROR:" not in log):
        return name, {"occupied": False, "volume_mm3": 0}
    if run.returncode or "WARNING:" in log or "ERROR:" in log or not path.is_file():
        return name, {"error": log[-1000:]}
    inspected = subprocess.run(["python3", str(INSPECT), str(path), "--json"],
                               cwd=ROOT, text=True, capture_output=True,
                               timeout=30)
    if inspected.returncode:
        return name, {"error": (inspected.stdout + inspected.stderr)[-1000:]}
    volume = json.loads(inspected.stdout)["volume"]
    return name, {"occupied": volume > 1e-6,
                  "volume_mm3": round(volume, 6)}


def main() -> int:
    predecessor = OUT / "review.json"
    side = ROOT / "output/electric-end-switch-side-cap/review.json"
    fork = ROOT / "output/electric-rocker-clamped-fork-screen/review.json"
    for path, status in (
        (predecessor, "OUTPUT_CROSSHEAD_GEOMETRY_SCREEN_ONLY"),
        (side, "SIDE_BOLTED_ENDPOINT_CAP_GEOMETRY_PASS_UNRELEASED"),
        (fork, "SPLIT_CLAMP_FORK_STATIC_SCREEN_ONLY"),
    ):
        if json.loads(path.read_text())["status"] != status:
            raise RuntimeError(f"Predecessor changed: {path}")
    source_files = source_closure(CAD) | {Path(__file__).resolve()}
    sources = {str(path.relative_to(ROOT)): sha(path) for path in sorted(source_files)}
    (OUT / "assembly-probes").mkdir(parents=True, exist_ok=True)
    cases = [("cap-crosshead", t, s, 0)
             for t in (0, .5, 1) for s in (0, .25, .5, .75, 1)]
    cases += [("switch-tool-crosshead", t, 0, 0) for t in (0, .5, 1)]
    cases += [(kind, 0, 0, offset)
              for kind in ("rocker-crosshead-axial", "rocker-fork-axial")
              for offset in OFFSETS]
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = dict(pool.map(probe, cases))
    clear = {name: row for name, row in rows.items()
             if not name.startswith("rocker-fork-axial")}
    fork_rows = {name: row for name, row in rows.items()
                 if name.startswith("rocker-fork-axial")}
    blocked_offsets = [offset for offset in OFFSETS
                       if fork_rows[f"rocker-fork-axial-t0-s0-dy{offset:g}"].get("occupied")]
    failures = [name for name, row in rows.items() if row.get("error")]
    failures += [name for name, row in clear.items() if row.get("occupied")]
    failures += ["no-axial-fork-obstruction"] if not blocked_offsets else []
    failures += ["assembled-rocker-fork-collision"] if fork_rows[
        "rocker-fork-axial-t0-s0-dy0"].get("occupied") else []
    failures += ["initial-axial-position-collides"] if fork_rows[
        "rocker-fork-axial-t0-s0-dy20"].get("occupied") else []
    current_sources = {str(path.relative_to(ROOT)): sha(path)
                       for path in sorted(source_files)}
    if sources != current_sources:
        failures.append("source-changed-during-review")
    report = {
        "status": "SERVICE_PATH_PARTIAL_AXIAL_INSERTION_BLOCKED" if not failures
                  else "SERVICE_PATH_SCREEN_FAILED",
        "source_sha256": sources,
        "predecessor_sha256": {str(path.relative_to(ROOT)): sha(path)
                               for path in (predecessor, side, fork)},
        "scope": "nominal geometry only; detached right cap, screwdriver axes, +Y rocker insertion with fixed fork",
        "cases": rows,
        "nominal_cap_removal_vs_new_crosshead_clear": not any(
            row.get("occupied") or row.get("error") for name, row in rows.items()
            if name.startswith("cap-crosshead")),
        "nominal_switch_tool_vs_new_crosshead_clear": not any(
            row.get("occupied") or row.get("error") for name, row in rows.items()
            if name.startswith("switch-tool-crosshead")),
        "nominal_rocker_pin_axial_path_into_slot_clear_without_fork": not any(
            row.get("occupied") or row.get("error") for name, row in rows.items()
            if name.startswith("rocker-crosshead-axial")),
        "rocker_with_fixed_fork_axial_blocked_y_offset_mm": blocked_offsets,
        "complete_rocker_assembly_path_proven": False,
        "real_fastener_and_motor_assembly_proven": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "assembly-review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Output assembly path: {report['status']}; "
          f"fixed-fork axial blockage at {blocked_offsets} mm; "
          f"failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
