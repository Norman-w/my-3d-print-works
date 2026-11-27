#!/usr/bin/env python3
"""Review nominal two-piece rocker fork and staged assembly access."""

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
CAD = ROOT / "cad/electric-rocker-service-fork-screen.scad"
OUT = ROOT / "output/electric-rocker-service-fork-screen"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
INSPECT = Path("/Users/norman/.codex/skills/openscad-stl-print/scripts/inspect_stl.py")
PREVIOUS = ROOT / "output/electric-output-crosshead-screen/assembly-review.json"
CROSSHEAD = ROOT / "output/electric-output-crosshead-screen/review.json"
FORK = ROOT / "output/electric-rocker-clamped-fork-screen/review.json"
STATIC = (
    "base-fixed", "base-carriage", "base-hardware", "base-motor",
    "base-bushing", "rear-fixed", "rear-carriage", "rear-hardware",
    "rear-motor", "rear-bushing", "base-rear", "m3-hardware-fixed",
    "anchor-original-minus-base", "anchor-base-minus-original",
    "m3-hardware-moving", "m3-hardware-rocker", "m3-hardware-base",
    "m3-hardware-rear", "m3-tools-fixed", "m3-tools-moving",
    "m3-tools-motor",
)
STROKES = (0, .25, .5, .75, 1)
OFFSETS = (0, 2.5, 5, 7.5, 10, 15, 20, 25)


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


def command(part: str, path: Path, *, probe: str = "", t: float = 0,
            rear: float = 0, rocker: float = 0, shaft: float = 0,
            nut: float = 0,
            camera: str = "48,53,10,65,0,145,260") -> subprocess.CompletedProcess[str]:
    path.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'sf_part="{part}"', "-D", f"sf_t={t}",
           "-D", f"oc_t={t}", "-D", f"rb_t={t}", "-D", f"cf_t={t}",
           "-D", "rb_plane_y=65", "-D", "rb_motor_y=63",
           "-D", "pm_pivot_y=65", "-D", f"sf_rear_offset_y={rear}",
           "-D", f"sf_rocker_offset_y={rocker}",
           "-D", f"sf_shaft_offset_y={shaft}",
           "-D", f"sf_nut_offset_y={nut}"]
    if probe:
        cmd += ["-D", f'sf_probe="{probe}"']
    if path.suffix == ".png":
        cmd += ["--render", "--imgsize=1400,1000", f"--camera={camera}"]
    cmd += ["-o", str(path), str(CAD)]
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                          timeout=180)


def inspect(path: Path, *, watertight: bool = False) -> dict:
    cmd = ["python3", str(INSPECT), str(path), "--json"]
    if watertight:
        cmd.append("--require-watertight")
    run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                         timeout=30)
    if run.returncode:
        return {"error": (run.stdout + run.stderr)[-900:]}
    row = json.loads(run.stdout)
    result = {"volume_mm3": round(row["volume"], 6),
              "bounds_mm": row["bounds"],
              "triangle_count": row["triangleCount"]}
    if watertight:
        result |= {"watertight": row["watertightByEdgeTopology"],
                   "connected_components": ascii_mesh_components(path),
                   "sha256": sha(path)}
    return result


def run_probe(case: tuple[str, float, float, float, float, float]) -> tuple[str, dict]:
    kind, t, rear, rocker, shaft, nut = case
    name = (f"{kind}-t{t:.2f}-rear{rear:g}-rocker{rocker:g}"
            f"-shaft{shaft:g}-nut{nut:g}")
    path = OUT / "probes" / f"{name}.stl"
    run = command("probe", path, probe=kind, t=t,
                  rear=rear, rocker=rocker, shaft=shaft, nut=nut)
    log = run.stdout + run.stderr
    if run.returncode == 1 and "Current top level object is empty" in log \
            and "WARNING:" not in log and "ERROR:" not in log:
        return name, {"occupied": False, "volume_mm3": 0}
    if run.returncode or "WARNING:" in log or "ERROR:" in log or not path.is_file():
        return name, {"error": log[-900:]}
    row = inspect(path)
    return name, {"occupied": row.get("volume_mm3", 0) > 1e-6,
                  "volume_mm3": row.get("volume_mm3", 0),
                  **({"error": row["error"]} if row.get("error") else {})}


def main() -> int:
    for path, status in (
        (PREVIOUS, "SERVICE_PATH_PARTIAL_AXIAL_INSERTION_BLOCKED"),
        (CROSSHEAD, "OUTPUT_CROSSHEAD_GEOMETRY_SCREEN_ONLY"),
        (FORK, "SPLIT_CLAMP_FORK_STATIC_SCREEN_ONLY"),
    ):
        if json.loads(path.read_text())["status"] != status:
            raise RuntimeError(f"Predecessor changed: {path}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probes").mkdir(exist_ok=True)
    sources = source_closure(CAD) | {Path(__file__).resolve(),
        ROOT / "scripts/review_electric_rocker_clamped_fork_screen.py"}
    before = {str(path.relative_to(ROOT)): sha(path) for path in sorted(sources)}
    parts = {}
    failures = []
    for part in ("base", "rear"):
        path = OUT / f"{part}.stl"
        run = command(part, path)
        log = run.stdout + run.stderr
        parts[part] = inspect(path, watertight=True) if (
            not run.returncode and "WARNING:" not in log
            and "ERROR:" not in log and path.is_file()) else {"error": log[-900:]}
        if parts[part].get("error") or not parts[part].get("watertight") \
                or parts[part].get("connected_components") != 1:
            failures.append(f"mesh-{part}")
    cases = [(kind, t, 0, 0, 0, 0) for kind in STATIC for t in STROKES]
    for t in (0, .5, 1):
        cases += [(kind, t, 25, offset, 0, 0)
                  for kind in ("base-rocker-insertion",
                               "rocker-crosshead-insertion") for offset in OFFSETS]
        cases += [(kind, t, offset, 0, 0, 0)
                  for kind in ("rear-rocker-insertion", "rear-base-insertion",
                               "rear-carriage-insertion", "rear-fixed-insertion")
                  for offset in OFFSETS]
        cases += [("shaft-assembly-insertion", t, 0, 0, offset, 0)
                  for offset in OFFSETS]
        cases += [(kind, t, 0, 0, 0, offset)
                  for kind in ("nut-base-insertion", "nut-fixed-insertion",
                               "nut-carriage-insertion", "nut-rocker-insertion")
                  for offset in OFFSETS]
    controls = [(kind, 0, 0, 0, 0, 0)
                for kind in ("key-contact-control", "base-self-control")]
    with ThreadPoolExecutor(max_workers=4) as pool:
        clear = dict(pool.map(run_probe, cases))
        positive = dict(pool.map(run_probe, controls))
    failures += [name for name, row in clear.items()
                 if row.get("error") or row.get("occupied")]
    failures += [name for name, row in positive.items()
                 if row.get("error") or not row.get("occupied")]
    stages = (
        ("rocker-entry", "context", 0, 25, 10, "48,53,10,65,0,145,260"),
        ("rocker-seated", "context", 0, 25, 0, "48,53,10,65,0,145,260"),
        ("rear-seated", "context", 0, 0, 0, "48,53,10,65,0,145,260"),
        ("base-front", "base", 0, 0, 0, "12,54,10,90,0,0,220"),
        ("base-nut-face", "base", 0, 0, 0, "12,54,10,90,0,180,220"),
        ("base-top", "base", 0, 0, 0, "12,54,10,0,0,0,220"),
        ("base-iso", "base", 0, 0, 0, "12,54,10,60,0,35,220"),
        ("rear-front", "rear", 0, 0, 0, "12,71,10,90,0,0,180"),
        ("rear-top", "rear", 0, 0, 0, "12,71,10,0,0,0,180"),
        ("rear-iso", "rear", 0, 0, 0, "12,71,10,60,0,35,180"),
    )
    images = {}
    for label, part, t, rear, rocker, camera in stages:
        path = OUT / f"{label}.png"
        run = command(part, path, t=t, rear=rear, rocker=rocker,
                      camera=camera)
        log = run.stdout + run.stderr
        data = path.read_bytes() if path.is_file() else b""
        if (run.returncode or "WARNING:" in log or "ERROR:" in log
                or data[:8] != b"\x89PNG\r\n\x1a\n"
                or struct.unpack(">II", data[16:24]) != (1400, 1000)):
            failures.append(f"render-{label}")
            images[label] = {"error": log[-900:] or "invalid PNG"}
        else:
            images[label] = {"file": str(path.relative_to(ROOT)),
                             "sha256": sha(path)}
    after = {str(path.relative_to(ROOT)): sha(path) for path in sorted(sources)}
    if before != after:
        failures.append("source-changed-during-review")
    report = {
        "status": "SERVICE_FORK_NOMINAL_ASSEMBLY_PATH_ONLY" if not failures
                  else "SERVICE_FORK_SCREEN_FAILED",
        "source_sha256": before,
        "predecessor_sha256": {str(path.relative_to(ROOT)): sha(path)
                               for path in (PREVIOUS, CROSSHEAD, FORK)},
        "mechanical_contract": {
            "units": "mm", "process": "X1C/0.4 mm/PETG candidate",
            "mounting_face_y": 68, "rocker_pivot_xyz": [85-(75*75-15*15)**.5, 65, 25],
            "base_fixed_to_shell_at_z": [-10, 16],
            "rear_cheek_insert_direction": "from +Y toward -Y",
            "two_m3_bolt_axes_xz": [[15, -14], [15, 2]],
            "shear_key_xyz": [[10, 20], [68, 72], [-8, -4]],
            "key_nominal_clearance_mm": .3,
            "captured_nut_pocket_open_on_mating_face_y": 68,
            "selected_motor_mount_or_fasteners": False,
        },
        "parts": parts, "static_pose_count": len(STROKES),
        "static_probe_count": len(STATIC)*len(STROKES),
        "assembly_probe_count": len(clear)-len(STATIC)*len(STROKES),
        "positive_control_count": len(positive),
        "clear_probes": clear, "positive_controls": positive,
        "images": images, "replaces_one_piece_fork_candidate": True,
        "promoted_to_selected_assembly": False,
        "real_motor_interface_verified": False,
        "rear_joint_strength_and_creep_verified": False,
        "metal_pivot_bushing_and_fasteners_physically_fitted": False,
        "manufacturing_release": False, "physical_acceptance": False,
        "failures": failures,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False,
                                             indent=2) + "\n")
    print(f"Service fork: {report['status']}; "
          f"{len(clear)} clear probes, {len(positive)} controls, "
          f"failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
