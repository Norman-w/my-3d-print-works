#!/usr/bin/env python3
"""Review a one-piece crosshead root against the existing electric assembly.

This is geometric evidence only: it does not release the output pin, printed
slot bearing, motor connector or the endpoint-compliance design.
"""

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
CAD = ROOT / "cad/electric-output-crosshead-screen.scad"
OUT = ROOT / "output/electric-output-crosshead-screen"
SCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
SIDE = ROOT / "output/electric-end-switch-side-cap/review.json"
BRIDGE = ROOT / "output/electric-rocker-bridge-screen/review.json"
FORK = ROOT / "output/electric-rocker-clamped-fork-screen/review.json"
POSES = tuple(i / 20 for i in range(21))
CLEAR_PROBES = (
    "crosshead-fixed", "crosshead-hardware", "crosshead-switch",
    "crosshead-motor", "crosshead-bracket", "crosshead-fasteners",
    "crosshead-rocker", "crosshead-other-moving",
)
CONTROL_PROBES = ("root-carriage-control", "slot-pin-control")


def digest(path: Path) -> str:
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


def command(part: str, dest: Path, *, t: float = 0, probe: str = "",
            camera: str = "34,47,25,67,0,143,220") -> subprocess.CompletedProcess[str]:
    dest.unlink(missing_ok=True)
    cmd = [str(SCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'oc_part="{part}"', "-D", f"oc_t={t}",
           "-D", f"rb_t={t}", "-D", f"cf_t={t}",
           "-D", "rb_plane_y=65", "-D", "rb_motor_y=63",
           "-D", "pm_pivot_y=65"]
    if probe:
        cmd += ["-D", f'oc_probe="{probe}"']
    if dest.suffix == ".png":
        cmd += ["--render", "--imgsize=1400,1000",
                f"--camera={camera}"]
    cmd += ["-o", str(dest), str(CAD)]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          timeout=180)


def mesh_info(path: Path) -> dict:
    run = subprocess.run(["python3", str(INSPECT), str(path), "--json",
                          "--require-watertight"], cwd=ROOT,
                         capture_output=True, text=True, timeout=30)
    if run.returncode:
        return {"error": (run.stdout + run.stderr)[-900:]}
    row = json.loads(run.stdout)
    return {"watertight": row["watertightByEdgeTopology"],
            "triangle_count": row["triangleCount"],
            "connected_components": ascii_mesh_components(path),
            "volume_mm3": round(row["volume"], 4),
            "bounds_mm": row["bounds"], "sha256": digest(path)}


def run_probe(item: tuple[str, float]) -> tuple[str, dict]:
    kind, t = item
    dest = OUT / "probes" / f"{kind}-t{t:.2f}.stl"
    run = command("probe", dest, t=t, probe=kind)
    log = run.stdout + run.stderr
    key = f"{kind}-t{t:.2f}"
    if run.returncode == 1 and "Current top level object is empty" in log \
            and "WARNING:" not in log and "ERROR:" not in log:
        return key, {"occupied": False, "volume_mm3": 0}
    if run.returncode or "WARNING:" in log or "ERROR:" in log \
            or not dest.is_file():
        return key, {"error": log[-900:]}
    info = mesh_info(dest)
    return key, {"occupied": info.get("volume_mm3", 0) > 1e-6,
                 "volume_mm3": info.get("volume_mm3", 0),
                 "error": info.get("error")}


def main() -> int:
    side = json.loads(SIDE.read_text())
    bridge = json.loads(BRIDGE.read_text())
    fork = json.loads(FORK.read_text())
    if side["status"] != "SIDE_BOLTED_ENDPOINT_CAP_GEOMETRY_PASS_UNRELEASED" \
            or bridge["status"] != "OUTPUT_BRIDGE_LAYOUT_SCREEN_ONLY" \
            or fork["status"] != "SPLIT_CLAMP_FORK_STATIC_SCREEN_ONLY":
        raise RuntimeError("Predecessor CAD candidate state changed")
    text = CAD.read_text()
    for literal in ("oc_outer_y0 = 50;", "oc_root_x0 = 48;",
                    "oc_root_y0 = 48;", "oc_root_y1 = 55;",
                    "oc_pin_d = 7;", "oc_wall = 3;"):
        if literal not in text:
            raise RuntimeError(f"Review contract changed: {literal}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probes").mkdir(exist_ok=True)
    tracked = source_closure(CAD) | {Path(__file__).resolve(),
        ROOT / "scripts/review_electric_rocker_clamped_fork_screen.py"}
    before = {str(path.relative_to(ROOT)): digest(path) for path in sorted(tracked)}
    parts = {}
    failures = []
    for part in ("crosshead", "carriage"):
        path = OUT / f"{part}.stl"
        run = command(part, path)
        log = run.stdout + run.stderr
        parts[part] = mesh_info(path) if not run.returncode \
            and "WARNING:" not in log and "ERROR:" not in log and path.exists() \
            else {"error": log[-900:]}
        if parts[part].get("error") or not parts[part].get("watertight") \
                or parts[part].get("connected_components") != 1:
            failures.append(f"mesh-{part}")
    cases = [(name, t) for t in POSES for name in CLEAR_PROBES]
    controls = [(name, t) for t in (0, .25, .5, .75, 1)
                for name in CONTROL_PROBES]
    with ThreadPoolExecutor(max_workers=4) as pool:
        clear = dict(pool.map(run_probe, cases))
        positive = dict(pool.map(run_probe, controls))
    failures += [key for key, row in clear.items()
                 if row.get("error") or row.get("occupied")]
    failures += [key for key, row in positive.items()
                 if row.get("error") or not row.get("occupied")]
    images = {}
    views = (("home", "context", 0, "34,47,25,67,0,143,220"),
             ("mid", "context", .5, "34,47,25,67,0,143,220"),
             ("full", "context", 1, "34,47,25,67,0,143,220"),
             ("crosshead-front", "crosshead", 0, "58,55,15,90,0,0,100"),
             ("crosshead-top", "crosshead", 0, "58,55,15,0,0,0,100"),
             ("crosshead-iso", "crosshead", 0, "58,55,15,60,0,35,100"))
    for label, part, t, camera in views:
        path = OUT / f"{label}.png"
        run = command(part, path, t=t, camera=camera)
        log = run.stdout + run.stderr
        raw = path.read_bytes() if path.exists() else b""
        images[label] = ({"file": str(path.relative_to(ROOT)),
                          "sha256": digest(path)}
                         if not run.returncode and "WARNING:" not in log
                         and "ERROR:" not in log and raw[:8] == b"\x89PNG\r\n\x1a\n"
                         and struct.unpack(">II", raw[16:24]) == (1400, 1000)
                         else {"error": log[-900:]})
        if images[label].get("error"):
            failures.append(f"image-{label}")
    after = {str(path.relative_to(ROOT)): digest(path) for path in sorted(tracked)}
    if before != after:
        failures.append("source-changed-during-review")
    report = {
        "status": "OUTPUT_CROSSHEAD_GEOMETRY_SCREEN_ONLY" if not failures else "OUTPUT_CROSSHEAD_SCREEN_FAILED",
        "source_sha256": before,
        "predecessor_sha256": {"side": digest(SIDE),
                               "bridge": digest(BRIDGE), "fork": digest(FORK)},
        "parameters_mm": {
            "rocker_input_radius": 75, "rocker_output_radius": 50,
            "rocker_plane_y": 65, "motor_proxy_axis_xy": [85, 63],
            "slot_pin_diameter": 7, "radial_clearance": .4,
            "minimum_slot_side_and_vertical_wall": 3,
            "crosshead_y": [50, 61.5], "root_xyz": [[48, 56.5], [48, 55], [8.1, 21.9]],
            "existing_upper_carriage_bridge_overlap_xyz": [[48, 52], [48, 54], [10, 16]],
            "output_pin_proxy_y": [53, 67],
            "output_pin_to_slot_engagement_y": [53, 61.5],
            "pin_has_dedicated_axial_retention": False,
        },
        "pose_count": len(POSES), "clear_probe_count": len(clear),
        "positive_control_count": len(positive),
        "parts": parts, "clear_probes": clear, "positive_controls": positive,
        "images": images, "replaces_existing_moving_frame": True,
        "promoted_to_selected_parts": False,
        "print_or_strength_release": False,
        "physical_acceptance": False, "failures": failures,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Output crosshead screen: {report['status']}, "
          f"{len(clear)} clear probes, {len(positive)} positive controls, "
          f"failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
