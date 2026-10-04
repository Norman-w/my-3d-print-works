#!/usr/bin/env python3
"""Compare real STL sections around the service fork's lower anchor screw.

This screens section topology and area only. It is not a stress, fatigue,
layer-strength, or fastener-bearing calculation.
"""

from __future__ import annotations

from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path

import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_REVIEW = ROOT / "output/electric-rocker-service-fork-screen/review.json"
REINFORCEMENT_REVIEW = ROOT / "output/electric-rocker-service-fork-reinforcement-screen/review.json"
ORIGINAL_STL = ROOT / "output/electric-rocker-service-fork-screen/base.stl"
REINFORCED_STL = ROOT / "output/electric-rocker-service-fork-reinforcement-screen/base-reinforced-screen.stl"
OUT = ROOT / "output/electric-rocker-service-fork-reinforcement-screen/root-section-screen.json"
REQUIREMENTS = ROOT / "analysis/service_fork_section_requirements.txt"
SAMPLE_Y_MM = (39.5, 40.5, 45.5, 50.5, 55.5)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def world_polygon(polygon: Polygon, transform) -> Polygon:
    def xz(ring):
        return [(float(transform[0, 0] * u + transform[0, 1] * v + transform[0, 3]),
                 float(transform[2, 0] * u + transform[2, 1] * v + transform[2, 3]))
                for u, v in ring.coords]
    return Polygon(xz(polygon.exterior), [xz(hole) for hole in polygon.interiors])


def section(mesh: trimesh.Trimesh, y_mm: float) -> tuple[dict, object]:
    line = mesh.section(plane_origin=[0, y_mm, 0], plane_normal=[0, 1, 0])
    if line is None:
        raise RuntimeError(f"Empty Y={y_mm} section")
    flat, transform = line.to_2D()
    polygons = [world_polygon(poly, transform) for poly in flat.polygons_full]
    if not polygons or not all(poly.is_valid and poly.area > 0 for poly in polygons):
        raise RuntimeError(f"Invalid Y={y_mm} section polygons")
    material = unary_union(polygons)
    lower = [poly for poly in polygons if poly.bounds[3] < -9.0]
    row = {
        "y_mm": y_mm,
        "polygon_count": len(polygons),
        "area_mm2": round(material.area, 3),
        "lower_lobe_area_mm2": round(sum(poly.area for poly in lower), 3),
        "lower_lobe_count": len(lower),
    }
    return row, material


def main() -> int:
    pinned = dict(line.split("==", 1) for line in REQUIREMENTS.read_text().splitlines())
    actual = {package: version(package) for package in pinned}
    if actual != pinned:
        raise RuntimeError(f"Section-screen dependencies differ from pinned versions: {actual}")
    original_review = json.loads(ORIGINAL_REVIEW.read_text())
    reinforced_review = json.loads(REINFORCEMENT_REVIEW.read_text())
    if original_review["status"] != "SERVICE_FORK_NOMINAL_ASSEMBLY_PATH_ONLY" \
            or reinforced_review["status"] != "REINFORCED_BEAM_GEOMETRY_SCREEN_ONLY" \
            or original_review["parts"]["base"]["sha256"] != digest(ORIGINAL_STL) \
            or reinforced_review["reinforced_base"]["sha256"] != digest(REINFORCED_STL) \
            or reinforced_review["original_review_sha256"] != digest(ORIGINAL_REVIEW):
        raise RuntimeError("Service fork meshes or predecessor reviews are stale")
    meshes = {
        "original": trimesh.load_mesh(ORIGINAL_STL),
        "reinforced": trimesh.load_mesh(REINFORCED_STL),
    }
    if not all(isinstance(mesh, trimesh.Trimesh) and mesh.is_watertight
               for mesh in meshes.values()):
        raise RuntimeError("Both sections require watertight single meshes")

    samples = {}
    for y_mm in SAMPLE_Y_MM:
        key = f"y{y_mm:.1f}"
        original, original_material = section(meshes["original"], y_mm)
        reinforced, reinforced_material = section(meshes["reinforced"], y_mm)
        samples[key] = {
            "original": original,
            "reinforced": reinforced,
            "symmetric_difference_area_mm2": round(
                original_material.symmetric_difference(reinforced_material).area, 6),
        }

    root = samples["y39.5"]
    straight = samples["y45.5"]
    checks = {
        "upstream_anchor_section_unchanged":
            root["symmetric_difference_area_mm2"] < 0.001,
        "anchor_screw_splits_section_into_three_lobes":
            root["original"]["polygon_count"] == root["reinforced"]["polygon_count"] == 3,
        "upstream_lower_lobe_unchanged":
            abs(root["original"]["lower_lobe_area_mm2"]
                - root["reinforced"]["lower_lobe_area_mm2"]) < 0.001,
        "straight_low_beam_widened":
            abs(straight["original"]["area_mm2"] - 33.0) < 0.01
            and abs(straight["reinforced"]["area_mm2"] - 77.0) < 0.01,
    }
    report = {
        "status": "ROOT_SECTION_UNCHANGED_REINFORCEMENT_UNRELEASED"
                  if all(checks.values()) else "FAIL",
        "source_sha256": {
            str(path.relative_to(ROOT)): digest(path)
            for path in (Path(__file__).resolve(), ORIGINAL_REVIEW,
                         REINFORCEMENT_REVIEW, ORIGINAL_STL, REINFORCED_STL,
                         REQUIREMENTS)
        },
        "analysis_dependencies": actual,
        "scope": "Y-normal material sections near the lower shell anchor screw and low beam",
        "units": "mm and mm^2 (OpenSCAD model assumption; STL contains no units)",
        "samples": samples,
        "checks": checks,
        "interpretation": (
            "The extension widens the straight low beam after Y=40, but the "
            "Y=39.5 section upstream of the lower shell screw is unchanged "
            "and split into three material lobes. A straight unperforated "
            "beam stress estimate cannot approve this root load path."
        ),
        "three_dimensional_stress_or_fatigue_verified": False,
        "real_motor_load_and_print_layer_strength_measured": False,
        "structural_release": False,
        "manufacturing_release": False,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{report['status']}: Y=39.5 unchanged; Y=45.5 "
          f"{straight['original']['area_mm2']} -> {straight['reinforced']['area_mm2']} mm^2")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
