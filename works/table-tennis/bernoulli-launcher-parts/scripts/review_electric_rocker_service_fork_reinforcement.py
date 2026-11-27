#!/usr/bin/env python3
"""Screen a wider service-fork low beam without promoting it to the BOM."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from review_electric_rocker_service_fork_screen import inspect, source_closure


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electric-rocker-service-fork-reinforcement-screen.scad"
PRIOR = ROOT / "output/electric-rocker-service-fork-screen/review.json"
LOAD = ROOT / "output/electric-rocker-service-fork-screen/load-screen.json"
ORIGINAL = ROOT / "output/electric-rocker-service-fork-screen/base.stl"
OUT = ROOT / "output/electric-rocker-service-fork-reinforcement-screen"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
STROKES = tuple(n / 20 for n in range(21))
STATIC = ("added-fixed", "added-hardware", "added-motor",
          "added-rear", "anchor-channel")


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build(part: str, destination: Path, *, probe: str = "", t: float = 0) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'rf_part="{part}"', "-D", f'rf_probe="{probe}"',
           "-D", f"oc_t={t}"]
    if destination.suffix == ".png":
        cmd += ["--render", "--imgsize=1400,1000",
                "--camera=13,54,0,67,0,145,215"]
    cmd += ["-o", str(destination), str(CAD)]
    run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                         timeout=120)
    log = (run.stdout + run.stderr).strip()
    if run.returncode == 1 and log == "Current top level object is empty.":
        return {"occupied": False, "volume_mm3": 0}
    if run.returncode or "WARNING:" in log or "ERROR:" in log \
            or not destination.is_file():
        return {"error": log[-1000:] or "missing output"}
    if destination.suffix == ".png":
        data = destination.read_bytes()
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return {"error": "invalid PNG"}
        return {"file": str(destination.relative_to(ROOT)),
                "sha256": sha(destination), "bytes": len(data)}
    mesh = inspect(destination, watertight=part == "base")
    if mesh.get("error"):
        return mesh
    return {"occupied": mesh["volume_mm3"] > 1e-6, **mesh}


def probe(case: tuple[str, float]) -> tuple[str, dict]:
    name, t = case
    key = f"{name}-t{t:.2f}"
    return key, build("probe", OUT / "probes" / f"{key}.stl",
                      probe=name, t=t)


def main() -> int:
    prior = json.loads(PRIOR.read_text())
    load = json.loads(LOAD.read_text())
    if prior["status"] != "SERVICE_FORK_NOMINAL_ASSEMBLY_PATH_ONLY" \
            or load["status"] != "SERVICE_FORK_LOAD_PATH_UNRELEASED" \
            or prior["parts"]["base"]["sha256"] != sha(ORIGINAL) \
            or load["source_sha256"]["cad/electric-rocker-service-fork-screen.scad"] \
            != sha(ROOT / "cad/electric-rocker-service-fork-screen.scad"):
        raise RuntimeError("Original fork source or review changed")
    OUT.mkdir(parents=True, exist_ok=True)
    sources = source_closure(CAD) | {Path(__file__).resolve()}
    before = {str(path.relative_to(ROOT)): sha(path) for path in sorted(sources)}
    base = build("base", OUT / "base-reinforced-screen.stl")
    moving_controls = {
        f"t{t:.2f}": build("moving-control", OUT / f"moving-control-t{t:.2f}.stl", t=t)
        for t in (0.0, 1.0)
    }
    rows = [("added-moving", t) for t in STROKES]
    rows += [(name, 0) for name in STATIC]
    rows.append(("added-positive-control", 0))
    with ThreadPoolExecutor(max_workers=4) as pool:
        probes = dict(pool.map(probe, rows))
    context = build("context", OUT / "beam-extension-context.png")
    after = {str(path.relative_to(ROOT)): sha(path) for path in sorted(sources)}
    failures = []
    if before != after:
        failures.append("source changed during screen")
    if base.get("error") or not base.get("occupied") \
            or not base.get("watertight") \
            or base.get("connected_components") != 1 \
            or base.get("volume_mm3", 0) <= prior["parts"]["base"]["volume_mm3"]:
        failures.append("reinforced base mesh")
    if context.get("error"):
        failures.append("context image")
    phase_shift = None
    start, end = moving_controls["t0.00"], moving_controls["t1.00"]
    if any(row.get("error") or not row.get("occupied") for row in (start, end)):
        failures.append("moving phase controls")
    else:
        start_bounds, end_bounds = start["bounds_mm"], end["bounds_mm"]
        shifts = [end_bounds[edge][2] - start_bounds[edge][2]
                  for edge in ("min", "max")]
        phase_shift = [round(shift, 6) for shift in shifts]
        if any(abs(shift - 20.0) > 1e-6 for shift in shifts):
            failures.append("moving phase control shift")
    for key, row in probes.items():
        expected = key.startswith("added-positive-control")
        if row.get("error") or row.get("occupied") is not expected:
            failures.append(key)

    width_x = 7.0
    height_z = 11.0
    vertical_section = width_x * height_z**2 / 6
    side_section = height_z * width_x**2 / 6
    stress = []
    for case in load["seller_claim_static_idealization_only"]:
        moment = case["beam_vertical_bending_moment_nmm"]
        stress.append({
            "seller_claim_kgf": case["seller_claim_kgf"],
            "isolated_unperforated_beam_vertical_mpa": round(moment / vertical_section, 3),
            "isolated_unperforated_beam_side_mpa": round(moment / side_section, 3),
            "original_isolated_beam_vertical_mpa":
                case["isolated_beam_vertical_nominal_stress_mpa"],
            "original_isolated_beam_side_mpa":
                case["same_magnitude_x_side_load_sensitivity_mpa"],
        })
    report = {
        "status": "REINFORCED_BEAM_GEOMETRY_SCREEN_ONLY" if not failures else "FAIL",
        "source_sha256": before,
        "original_review_sha256": sha(PRIOR),
        "original_load_review_sha256": sha(LOAD),
        "original_base_sha256": sha(ORIGINAL),
        "reinforced_base": base,
        "moving_phase_control": {
            "endpoint_bounds_mm": {
                "t0.00": start.get("bounds_mm"), "t1.00": end.get("bounds_mm")
            },
            "min_max_z_shift_mm": phase_shift,
        },
        "context_image": context,
        "probes": probes,
        "failures": failures,
        "beam_cross_section_mm": {"width_x": width_x, "height_z": height_z},
        "straight_beam_only_stress_sensitivity": stress,
        "anchor_screw_channel_and_root_not_in_straight_beam_stress": True,
        "motor_force_and_side_load_measured": False,
        "print_orientation_and_layer_strength_verified": False,
        "structural_release": False,
        "manufacturing_release": False,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False,
                                               indent=2) + "\n")
    print(f"{report['status']}: {len(probes)} probes; {len(failures)} failures")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
