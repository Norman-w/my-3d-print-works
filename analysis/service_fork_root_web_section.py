#!/usr/bin/env python3
"""Screen lower-lobe section gain of the unselected fork root web."""

from __future__ import annotations

from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path

import trimesh

from service_fork_root_section_screen import section


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "analysis/service_fork_section_requirements.txt"
PREVIOUS = ROOT / "output/electric-rocker-service-fork-reinforcement-screen/root-section-screen.json"
PREVIOUS_STL = ROOT / "output/electric-rocker-service-fork-reinforcement-screen/base-reinforced-screen.stl"
REVIEW = ROOT / "output/electric-rocker-root-gusset-screen/review.json"
WEB_STL = ROOT / "output/electric-rocker-root-gusset-screen/base-root-web-screen.stl"
OUT = ROOT / "output/electric-rocker-root-gusset-screen/root-web-section.json"
SAMPLE_Y_MM = (38.5, 39.5, 40.5, 45.5)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    pinned = dict(line.split("==", 1) for line in REQUIREMENTS.read_text().splitlines())
    actual = {package: version(package) for package in pinned}
    if actual != pinned:
        raise RuntimeError(f"Section-screen dependencies differ from pinned versions: {actual}")
    previous = json.loads(PREVIOUS.read_text())
    review = json.loads(REVIEW.read_text())
    if previous["status"] != "ROOT_SECTION_UNCHANGED_REINFORCEMENT_UNRELEASED" \
            or review["status"] != "ROOT_WEB_NOMINAL_GEOMETRY_ONLY_UNRELEASED" \
            or review["predecessor_root_section_sha256"] != digest(PREVIOUS) \
            or review["base"]["sha256"] != digest(WEB_STL):
        raise RuntimeError("Root-web mesh or predecessor review is stale")
    meshes = {
        "widened_only": trimesh.load_mesh(PREVIOUS_STL),
        "root_web": trimesh.load_mesh(WEB_STL),
    }
    if not all(isinstance(mesh, trimesh.Trimesh) and mesh.is_watertight
               and len(mesh.split(only_watertight=False)) == 1
               for mesh in meshes.values()):
        raise RuntimeError("Both section sources must be single watertight meshes")
    samples = {}
    for y_mm in SAMPLE_Y_MM:
        name = f"y{y_mm:.1f}"
        previous_row, _ = section(meshes["widened_only"], y_mm)
        root_web_row, _ = section(meshes["root_web"], y_mm)
        samples[name] = {"widened_only": previous_row, "root_web": root_web_row}
    root = samples["y39.5"]
    before = root["widened_only"]["lower_lobe_area_mm2"]
    after = root["root_web"]["lower_lobe_area_mm2"]
    checks = {
        "baseline_matches_predecessor_root_screen":
            before == previous["samples"]["y39.5"]["reinforced"]["lower_lobe_area_mm2"],
        "root_lower_lobe_area_more_than_tripled": after > 3 * before,
        "root_section_still_split_by_anchor_screw":
            root["widened_only"]["polygon_count"] ==
            root["root_web"]["polygon_count"] == 3,
        "straight_beam_area_not_lost":
            samples["y45.5"]["root_web"]["area_mm2"] >=
            samples["y45.5"]["widened_only"]["area_mm2"],
    }
    report = {
        "status": "ROOT_WEB_LOBE_AREA_GAIN_ONLY_UNRELEASED"
                  if all(checks.values()) else "FAIL",
        "source_sha256": {
            str(path.relative_to(ROOT)): digest(path)
            for path in (Path(__file__).resolve(),
                         ROOT / "analysis/service_fork_root_section_screen.py",
                         REQUIREMENTS, PREVIOUS, PREVIOUS_STL, REVIEW, WEB_STL)
        },
        "analysis_dependencies": actual,
        "scope": "Y-normal STL material sections only; no stress or layer-strength inference",
        "samples": samples,
        "root_lower_lobe_area_ratio": round(after / before, 3),
        "checks": checks,
        "three_dimensional_stress_or_fatigue_verified": False,
        "real_motor_load_and_shell_fastener_capacity_measured": False,
        "structural_release": False,
        "manufacturing_release": False,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{report['status']}: Y=39.5 lower lobe {before} -> {after} mm^2")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
