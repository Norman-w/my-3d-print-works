#!/usr/bin/env python3
"""Screen the unselected tapered root web around the fork anchor screw."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from review_electric_rocker_service_fork_screen import inspect, source_closure


ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "cad/electric-rocker-root-gusset-screen.scad"
PRIOR = ROOT / "output/electric-rocker-service-fork-reinforcement-screen/review.json"
ROOT_SECTION = ROOT / "output/electric-rocker-service-fork-reinforcement-screen/root-section-screen.json"
OUT = ROOT / "output/electric-rocker-root-gusset-screen"
OPENSCAD = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
STROKES = tuple(i / 20 for i in range(21))
INSERTION_X_MM = tuple(i / 2 for i in range(41))
STATIC = ("fixed", "hardware", "motor", "rear", "anchor-hole")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build(part: str, destination: Path, *, probe: str = "",
          t: float = 0, offset_x: float = 0) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    cmd = [str(OPENSCAD), "--hardwarnings", "--backend", "Manifold",
           "-D", f'rg_part="{part}"', "-D", f'rg_probe="{probe}"',
           "-D", f"oc_t={t}", "-D", f"rg_offset_x={offset_x}"]
    if destination.suffix == ".png":
        cmd += ["--render", "--imgsize=1400,1000",
                "--camera=13,51,-1,67,0,145,170"]
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
        if not destination.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            return {"error": "invalid PNG"}
        return {"file": str(destination.relative_to(ROOT)),
                "sha256": digest(destination)}
    mesh = inspect(destination, watertight=part in ("base", "added"))
    if mesh.get("error"):
        return mesh
    return {"occupied": mesh["volume_mm3"] > 1e-6, **mesh}


def probe(case: tuple[str, float, float]) -> tuple[str, dict]:
    name, t, offset_x = case
    key = (f"{name}-t{t:.2f}" if name.startswith("moving") else
           f"{name}-x{offset_x:.1f}" if name.startswith("insertion") else name)
    return key, build("probe", OUT / "probes" / f"{key}.stl",
                      probe=name, t=t, offset_x=offset_x)


def main() -> int:
    prior = json.loads(PRIOR.read_text())
    root_section = json.loads(ROOT_SECTION.read_text())
    if prior["status"] != "REINFORCED_BEAM_GEOMETRY_SCREEN_ONLY" \
            or root_section["status"] != "ROOT_SECTION_UNCHANGED_REINFORCEMENT_UNRELEASED" \
            or root_section["source_sha256"][str(PRIOR.relative_to(ROOT))] != digest(PRIOR):
        raise RuntimeError("Predecessor root section is missing or stale")
    OUT.mkdir(parents=True, exist_ok=True)
    sources = source_closure(CAD) | {Path(__file__).resolve()}
    before = {str(path.relative_to(ROOT)): digest(path) for path in sorted(sources)}
    base = build("base", OUT / "base-root-web-screen.stl")
    added = build("added", OUT / "added-root-web-screen.stl")
    rows = [("moving", t, 0) for t in STROKES]
    rows += [("insertion-fixed", 0, x) for x in INSERTION_X_MM]
    rows += [("moving-margin", t, 0) for t in STROKES]
    rows += [("insertion-margin", 0, x) for x in INSERTION_X_MM]
    rows += [(name, 0, 0) for name in STATIC]
    rows += [("positive", 0, 0), ("margin-positive", 0, 0)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        probes = dict(pool.map(probe, rows))
    context = build("context", OUT / "root-web-context.png")
    after = {str(path.relative_to(ROOT)): digest(path) for path in sorted(sources)}
    failures = []
    if before != after:
        failures.append("source changed during screen")
    for name, part in (("base", base), ("added", added)):
        if part.get("error") or not part.get("occupied") \
                or not part.get("watertight") \
                or part.get("connected_components") != 1:
            failures.append(f"{name} mesh")
    if not base.get("error") and base.get("volume_mm3", 0) \
            <= prior["reinforced_base"]["volume_mm3"]:
        failures.append("base volume did not grow")
    if context.get("error"):
        failures.append("context image")
    for key, row in probes.items():
        expected = key in ("positive", "margin-positive")
        if row.get("error") or row.get("occupied") is not expected:
            failures.append(key)
    report = {
        "status": "ROOT_WEB_NOMINAL_GEOMETRY_ONLY_UNRELEASED" if not failures else "FAIL",
        "source_sha256": before,
        "predecessor_reinforcement_sha256": digest(PRIOR),
        "predecessor_root_section_sha256": digest(ROOT_SECTION),
        "base": base,
        "added_only": added,
        "context_image": context,
        "probes": probes,
        "failures": failures,
        "assembly_insertion_screen": "+X offsets 0..20 mm in 0.5 mm steps; only new material checked",
        "clearance_screen": "0.8 mm polyhedral dilation of only added material against fixed components along +X insertion and moving carriage through 0..20 mm; 1.2 mm shell overlap positive control",
        "real_motor_force_measured": False,
        "shell_fastener_bearing_and_layer_strength_verified": False,
        "structural_release": False,
        "manufacturing_release": False,
        "selected_for_printing": False,
    }
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False,
                                             indent=2) + "\n")
    print(f"{report['status']}: {len(probes)} probes; {len(failures)} failures")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
