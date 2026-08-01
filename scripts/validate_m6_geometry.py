#!/usr/bin/env python3
"""Validate M6 printable STL topology and the head-handle load path."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import trimesh


# ===== 分区：常量/配置 =====
ROOT = Path(__file__).resolve().parents[1]
STL = ROOT / "enclosure" / "stl"
PARTS = {
    "skin_front": "paddle_m6_layer1_handle_skin_front.stl",
    "core_front": "paddle_m6_layer2_core_front.stl",
    "core_back": "paddle_m6_layer3_core_back.stl",
    "skin_back": "paddle_m6_layer4_handle_skin_back.stl",
    "monolithic_front": "paddle_m6_monolithic_front.stl",
    "monolithic_back": "paddle_m6_monolithic_back.stl",
}
JOIN_Y = -78.5


# ===== 分区：私有成员 =====
def _load(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(path)
    return mesh


def _validate_mesh(name: str, mesh: trimesh.Trimesh) -> list[str]:
    errors: list[str] = []
    if mesh.is_empty:
        errors.append(f"{name}: empty")
    if not mesh.is_watertight:
        errors.append(f"{name}: not watertight")
    if abs(float(mesh.volume)) < 1.0:
        errors.append(f"{name}: no positive volume")
    return errors


def _validate_load_path(name: str, mesh: trimesh.Trimesh) -> list[str]:
    errors: list[str] = []
    bodies = mesh.split(only_watertight=False)
    significant = [body for body in bodies if abs(float(body.volume)) > 5.0]
    if len(significant) != 1:
        errors.append(f"{name}: {len(significant)} disconnected significant bodies")
    for y in (JOIN_Y - 1.0, JOIN_Y, JOIN_Y + 1.0):
        section = mesh.section(
            plane_origin=np.array([0.0, y, 0.0]),
            plane_normal=np.array([0.0, 1.0, 0.0]),
        )
        if section is None or len(section.entities) == 0:
            errors.append(f"{name}: no material section at join y={y:.1f}")
    return errors


# ===== 分区：公开 API =====
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stl", type=Path, default=STL)
    args = parser.parse_args()
    errors: list[str] = []
    meshes: dict[str, trimesh.Trimesh] = {}
    for name, filename in PARTS.items():
        path = args.stl / filename
        if not path.is_file():
            errors.append(f"missing: {path}")
            continue
        mesh = _load(path)
        meshes[name] = mesh
        errors.extend(_validate_mesh(name, mesh))
        print(
            f"✓ {name}: watertight={mesh.is_watertight} "
            f"volume={abs(float(mesh.volume)):.1f}mm³ bodies={len(mesh.split())}"
        )

    for name in ("monolithic_front", "monolithic_back"):
        if name in meshes:
            errors.extend(_validate_load_path(name, meshes[name]))

    for name in ("core_front", "core_back"):
        mesh = meshes.get(name)
        if mesh is None:
            continue
        size = mesh.bounds[1] - mesh.bounds[0]
        if size[1] < 245 or size[0] < 145:
            errors.append(f"{name}: core does not span full paddle outline: {size}")

    if errors:
        print("\nM6 geometry validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 2
    print("\nM6 geometry validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
