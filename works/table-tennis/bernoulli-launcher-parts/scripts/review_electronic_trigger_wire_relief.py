#!/usr/bin/env python3
"""Review the selected trigger-backplate tie route and beam mesh."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import subprocess

from review_electric_rocker_clamped_fork_screen import ascii_mesh_components


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electronic-trigger-wire-relief-screen.scad"
TRIGGER = ROOT / "output/electronic-trigger-candidate/review.json"
INTEGRATION = ROOT / "output/electric-trigger-integration/review.json"
OUT = ROOT / "output/electronic-trigger-wire-relief"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
EMPTY = (
    "lead-beam", "lead-switch-body", "lead-other-fixed", "lead-other-moving",
    "tie-beam", "tie-switch-body", "tie-other-fixed", "tie-other-moving",
    "hole-switch-body", "hole-pivot", "beam-minus-original",
)
POSITIVE = ("hole-original-positive-control",
            "original-minus-beam-positive-control")
STROKES = (0, .5, 1)
ANGLES = (0, -4, -8)


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def source_closure(path: Path, found: set[Path] | None = None) -> set[Path]:
    found = found if found is not None else set()
    path = path.resolve()
    if path in found:
        return found
    found.add(path)
    for name in re.findall(r"\b(?:use|include)\s*<([^>]+)>", path.read_text()):
        source_closure(path.parent/name, found)
    return found


def command(part: str, target: Path, *, probe: str = "", angle: float = 0,
            stroke: float = 0, camera: str = "55,-52,-15,60,0,145,115") -> subprocess.CompletedProcess[str]:
    target.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'wr_part="{part}"', "-D", f"wr_angle={angle}",
           "-D", f"wr_feed_t={stroke}"]
    if probe:
        cmd += ["-D", f'wr_probe="{probe}"']
    if target.suffix == ".png":
        cmd += ["--render", "--imgsize=1400,1000", f"--camera={camera}"]
    cmd += ["-o", str(target), str(CAD)]
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                          timeout=120)


def inspect(path: Path, *, require_watertight: bool = False) -> dict:
    cmd = ["python3", str(INSPECT), str(path), "--json"]
    if require_watertight:
        cmd.append("--require-watertight")
    run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=60)
    if run.returncode:
        return {"error": (run.stdout+run.stderr)[-900:]}
    data = json.loads(run.stdout)
    result = {"volume_mm3": round(data["volume"], 6),
              "triangle_count": data["triangleCount"],
              "bounds_mm": data["bounds"]}
    if require_watertight:
        result.update(watertight=data["watertightByEdgeTopology"],
                      connected_components=ascii_mesh_components(path),
                      sha256=sha(path))
    return result


def run_probe(case: tuple[str, float, float]) -> tuple[str, dict]:
    kind, angle, stroke = case
    label = f"{kind}-a{angle:+g}-t{stroke:g}"
    path = OUT / "probes" / f"{label}.stl"
    run = command("probe", path, probe=kind, angle=angle, stroke=stroke)
    log = run.stdout+run.stderr
    if run.returncode == 1 and "Current top level object is empty" in log \
            and "WARNING:" not in log and "ERROR:" not in log:
        return label, {"occupied": False, "volume_mm3": 0}
    if run.returncode or "WARNING:" in log or "ERROR:" in log:
        return label, {"error": log[-900:]}
    row = inspect(path)
    row["occupied"] = row.get("volume_mm3", 0) > 1e-5
    return label, row


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probes").mkdir(exist_ok=True)
    trigger = json.loads(TRIGGER.read_text())
    integration = json.loads(INTEGRATION.read_text())
    if trigger["status"] != "TRIGGER_CANDIDATE_GEOMETRY_PASS_UNRELEASED" \
            or integration["status"] != "SELECTED_TRIGGER_GEOMETRY_PASS_UNRELEASED" \
            or integration["trigger_geometry_review_sha256"] != sha(TRIGGER):
        raise RuntimeError("Selected trigger review is stale or not passed")
    selected_cad = (ROOT / "cad/electronic-trigger-candidate.scad").read_text()
    screen_cad = CAD.read_text()
    for selected, screen in (
        (r"et_wire_tie_hole_x\s*=\s*\[42\.5,\s*48\.5\]",
         r"wr_hole_x\s*=\s*\[42\.5,\s*48\.5\]"),
        (r"et_wire_tie_hole_z\s*=\s*-13\.5", r"wr_hole_z\s*=\s*-13\.5"),
        (r"et_wire_tie_hole_d\s*=\s*3", r"wr_hole_d\s*=\s*3"),
    ):
        if not re.search(selected, selected_cad) or not re.search(screen, screen_cad):
            raise RuntimeError("Tie clearance proxy differs from selected beam holes")
    sources = source_closure(CAD) | {Path(__file__).resolve()}
    before = {str(p.relative_to(ROOT)): sha(p) for p in sorted(sources)}
    failures = []
    beam = OUT / "beam-candidate.stl"
    run = command("beam", beam)
    if run.returncode or "WARNING:" in run.stdout+run.stderr \
            or "ERROR:" in run.stdout+run.stderr:
        failures.append("beam-export-failed")
        part = {"error": (run.stdout+run.stderr)[-900:]}
    else:
        part = inspect(beam, require_watertight=True)
        if not part.get("watertight") or part.get("connected_components") != 1:
            failures.append("beam-not-one-closed-solid")
        if part.get("sha256") != trigger["parts"]["beam"]["sha256"]:
            failures.append("wire-relief-beam-differs-from-selected-trigger-beam")
    cases = [(kind, 0, 0) for kind in EMPTY if kind != "lead-other-moving"
             and kind != "tie-other-moving"]
    cases += [(kind, angle, stroke)
              for kind in ("lead-other-moving", "tie-other-moving")
              for angle in ANGLES for stroke in STROKES]
    controls = [(kind, 0, 0) for kind in POSITIVE]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = dict(pool.map(run_probe, cases+controls))
    for label, row in results.items():
        expected = any(label.startswith(kind+"-") for kind in POSITIVE)
        if row.get("error") or row.get("occupied") != expected:
            failures.append(f"{label}: occupancy differs")
    images = {}
    for label, angle, camera in (
        ("released", 0, "55,-52,-15,60,0,145,115"),
        ("pulled", -8, "55,-52,-15,60,0,145,115"),
        ("front", 0, "55,-52,-15,90,0,180,115"),
    ):
        path = OUT / f"{label}.png"
        rendered = command("context", path, angle=angle, camera=camera)
        data = path.read_bytes() if path.exists() else b""
        log = rendered.stdout+rendered.stderr
        if rendered.returncode or "WARNING:" in log or "ERROR:" in log \
                or data[:8] != b"\x89PNG\r\n\x1a\n" \
                or struct.unpack(">II", data[16:24]) != (1400, 1000):
            failures.append(f"render-{label}")
            images[label] = {"error": log[-900:]}
        else:
            images[label] = {"sha256": sha(path),
                             "file": str(path.relative_to(ROOT))}
    after = {str(p.relative_to(ROOT)): sha(p) for p in sorted(sources)}
    if before != after:
        failures.append("source-changed-during-review")
    report = {
        "status": "WIRE_RELIEF_NOMINAL_GEOMETRY_ONLY" if not failures else "FAIL",
        "source_sha256": before,
        "predecessor_sha256": {
            str(p.relative_to(ROOT)): sha(p) for p in (TRIGGER, INTEGRATION)},
        "part": part,
        "geometry_contract": {
            "units": "mm", "process": "X1C/0.4/PETG candidate",
            "tie_hole_centers_x_mm": [42.5, 48.5],
            "tie_hole_z_mm": -13.5, "tie_hole_nominal_d_mm": 3,
            "nominal_tie_width_mm": 2.5,
            "minimum_left_edge_wall_mm": 2,
            "minimum_between_holes_wall_mm": 3,
            "minimum_to_finger_window_mm": 3,
            "route_is_clearance_proxy_not_a_selected_wire": True,
            "tie_reference": "HellermannTyton T18R, 101.6 x 2.5 mm",
            "tie_catalog_url": "https://www.hellermanntyton.com/products/cable-ties-inside-serrated/t18r/111-01230",
            "tie_head_catalog_xyz_mm": [4.45, 3.7, 4.8],
            "tie_head_keepout_xyz_mm": [5.5, 4.7, 5.8],
        },
        "empty_probe_count": len(cases),
        "positive_control_count": len(controls),
        "probes": results, "images": images,
        "promoted_to_selected_beam": True,
        "actual_wire_sleeve_tie_and_solder_fit_verified": False,
        "manufacturing_release": False,
        "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False,
                                             indent=2) + "\n")
    print(report["status"], f"{len(cases)} clear + {len(controls)} controls; failures={len(failures)}")
    for failure in failures:
        print("  "+failure)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
