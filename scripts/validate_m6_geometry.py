#!/usr/bin/env python3
"""Validate M6 printable STL topology and the head-handle load path."""

from __future__ import annotations

import argparse
import hashlib
import json
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
    "fasteners": "paddle_m6_fasteners.stl",
}
PRINT_PLATES = {
    "plate_1_2": ("print/paddle_m6_print_plate_layers_1_2.stl", ("skin_front", "core_front")),
    "plate_3_4": ("print/paddle_m6_print_plate_layers_3_4.stl", ("core_back", "skin_back")),
}
JOIN_Y = -78.5
CORE_HALF_T = 3.0
BUILD_MM = 256.0
PLATE_GAP_MM = 5.0
SCREW_SAFETY_REPORT = ROOT / "enclosure/generated/m6_screw_safety.json"
PRINT_PLATE_REPORT = STL / "print/print_plates.json"


# ===== 分区：私有成员 =====
def _load(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(path)
    return mesh


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    triangles_y = mesh.vertices[mesh.faces][:, :, 1]
    for y in (JOIN_Y - 1.0, JOIN_Y, JOIN_Y + 1.0):
        crossing = np.count_nonzero(
            (triangles_y.min(axis=1) <= y) & (triangles_y.max(axis=1) >= y)
        )
        if crossing == 0:
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
        # The PCB-through M2 station at (0,-33) sits inside the large blade
        # cavity. It must have a full-height boss in both load-bearing cores;
        # merely retaining the 1 mm outer floor is not a usable screw column.
        vertices = mesh.vertices
        local = vertices[np.linalg.norm(vertices[:, :2] - np.array([0.0, -33.0]), axis=1) < 3.1]
        local_span = 0.0 if len(local) == 0 else float(np.ptp(local[:, 2]))
        # The back blind-pilot Boolean has no local vertices on the coplanar
        # outer floor; its cylindrical wall spans the 2 mm drilled depth while
        # the remaining 1 mm floor is part of the larger planar face.
        required_span = CORE_HALF_T - 0.1 if name == "core_front" else 1.9
        if local_span < required_span:
            errors.append(
                f"{name}: blade-cavity PCB screw boss (0,-33) missing/short, "
                f"z span={local_span:.3f}mm"
            )
        else:
            print(f"✓ {name}: blade-cavity PCB screw boss z_span={local_span:.3f}mm")

    fasteners = meshes.get("fasteners")
    if fasteners is not None:
        z_min, z_max = fasteners.bounds[:, 2]
        if z_min >= -CORE_HALF_T or z_max <= CORE_HALF_T:
            errors.append(
                "fasteners: expected layer 1→4 handle screws spanning both cores, "
                f"got Z=[{z_min:.2f}, {z_max:.2f}]"
            )

    if not SCREW_SAFETY_REPORT.is_file():
        errors.append(f"missing screw safety report: {SCREW_SAFETY_REPORT}")
    else:
        safety = json.loads(SCREW_SAFETY_REPORT.read_text(encoding="utf-8"))
        required_pcb = float(safety["requiredPcbSlotCenterClearanceMm"])
        required_edge = float(safety["requiredCoreEdgeLigamentMm"])
        moves = safety["moves"]
        for move in moves:
            clearance = float(move["pcbSlotCenterClearanceMm"])
            required_move = float(move.get("requiredCenterClearanceMm", required_pcb))
            if clearance + 1e-4 < required_move:
                errors.append(
                    f"screw {move['final']}: PCB slot clearance {clearance:.3f}mm "
                    f"< {required_move:.3f}mm"
                )
        moved = [move for move in moves if move["moved"]]
        visual_checks = [
            check for check in safety["directionChecks"]
            if check.get("visualCallout") is not None
        ]
        expected_visual = {
            "left_small_circles_tail_edge",
            "center_large_circle_pcb_slot_pair",
        }
        if len(visual_checks) != 8 or {check["visualCallout"] for check in visual_checks} != expected_visual:
            errors.append(
                "screw safety visual mapping must cover two tail stations × two sides × two directions"
            )
        if fasteners is not None:
            fastener_bodies = list(fasteners.split(only_watertight=False))
            for check in safety["directionChecks"]:
                clearance = float(check["pcbSlotCenterClearanceMm"])
                required_check = float(check.get("requiredPcbSlotCenterClearanceMm", required_pcb))
                ligament = float(check["outerEdgeLigamentMm"])
                target = np.asarray(check["position"], dtype=float)
                actual = any(
                    float(np.linalg.norm(body.centroid[:2] - target)) < 0.08
                    # The 2→1 and 3→4 preview screws meet at the Z=0 split
                    # plane and therefore load as one connected body. Its
                    # bounds must span both directions to prove both exist.
                    and body.bounds[0, 2] < -0.1
                    and body.bounds[1, 2] > 0.1
                    for body in fastener_bodies
                )
                passed = (
                    clearance + 1e-4 >= required_check
                    and ligament + 1e-4 >= required_edge
                    and actual
                )
                if not passed:
                    errors.append(
                        f"{check['direction']} {check['side']} station {check['station']}: "
                        f"pcb={clearance:.3f}mm edge={ligament:.3f}mm actual={actual}"
                    )
                print(
                    f"  {'✓' if passed else '✗'} {check['direction']} {check['side']} "
                    f"station={check['station']} pcb={clearance:.3f}mm "
                    f"edge={ligament:.3f}mm actual={actual}"
                )
        print(
            f"✓ screw_safety: moved_stations={len(moved)} "
            f"pcb_clearance_min={min(float(move['pcbSlotCenterClearanceMm']) for move in moves):.3f}mm "
            f"core_edge_min={min(float(check['outerEdgeLigamentMm']) for check in safety['edgeChecks']):.3f}mm"
        )

    plate_metadata: dict[str, dict] = {}
    if PRINT_PLATE_REPORT.is_file():
        report = json.loads(PRINT_PLATE_REPORT.read_text(encoding="utf-8"))
        plate_metadata = {str(item["path"]): item for item in report.get("plates", [])}
    else:
        errors.append(f"missing print plate metadata: {PRINT_PLATE_REPORT}")

    for name, (filename, source_names) in PRINT_PLATES.items():
        path = args.stl / filename
        if not path.is_file():
            errors.append(f"missing: {path}")
            continue
        plate = _load(path)
        metadata = plate_metadata.get(filename)
        if metadata is None:
            errors.append(f"{name}: missing metadata for {filename}")
        else:
            actual_plate_hash = _sha256(path)
            if metadata.get("sha256") != actual_plate_hash:
                errors.append(f"{name}: STL hash differs from print_plates.json")
            for part in metadata.get("parts", []):
                source_path = args.stl / str(part["source"])
                if not source_path.is_file() or part.get("sourceSha256") != _sha256(source_path):
                    errors.append(f"{name}: stale source hash for {part['source']}")
                if "handle_skin" in str(part["source"]):
                    orientation = part.get("orientation", {})
                    expected_contact = (
                        "detectedPhysicalBasePlane" if name == "plate_3_4"
                        else "detectedShoulderNeckPlane"
                    )
                    if orientation.get("bedContact") != expected_contact:
                        errors.append(f"{name}: upright skin has wrong bed-contact plane")
                    if name == "plate_3_4" and not orientation.get("baseFacesBed"):
                        errors.append(f"{name}: layer 4 physical base does not face the bed")
                    if float(orientation.get("contactAreaMm2", 0)) < 25.0:
                        errors.append(f"{name}: shoulder-neck contact area is too small")
                    if float(orientation.get("contactWidthMm", 0)) < 20.0:
                        errors.append(f"{name}: shoulder-neck contact width is too small")
                    if float(orientation.get("contactDepthMm", 0)) < 1.5:
                        errors.append(f"{name}: shoulder-neck contact depth is too small")
        shells = plate.split(only_watertight=False)
        # OpenSCAD's layer-1 source contains two zero-volume duplicate-face
        # remnants. A rigid 90° pose can expose them as separate shells after
        # STL float quantisation; they are not printable parts. Count only
        # positive-volume bodies while still preserving every source triangle.
        bodies = sorted(
            (body for body in shells if abs(float(body.volume)) > 1e-3),
            key=lambda body: body.bounds[0, 0],
        )
        printable_watertight = all(body.is_watertight for body in bodies)
        if not printable_watertight or len(bodies) != 2:
            errors.append(f"{name}: expected two independent watertight bodies, got {len(bodies)}")
            continue
        if float(plate.bounds.min()) < -1e-4 or float(plate.bounds.max()) > BUILD_MM + 1e-4:
            errors.append(f"{name}: outside {BUILD_MM:g}mm build cube: {plate.bounds}")
        if any(abs(float(body.bounds[0, 2])) > 1e-4 for body in bodies):
            errors.append(f"{name}: one or more parts are not on Z=0")
        gap = float(bodies[1].bounds[0, 0] - bodies[0].bounds[1, 0])
        if metadata is not None and metadata.get("x1cValidation"):
            x1c = metadata["x1cValidation"]
            clearance = float(x1c.get("partClearanceMm", 0))
            if not x1c.get("passed") or clearance < PLATE_GAP_MM - 1e-4:
                errors.append(f"{name}: X1C footprint clearance {clearance:.3f}mm")
            if float(x1c.get("excludedAreaOverlapMm2", 1)) > 1e-6:
                errors.append(f"{name}: X1C exclusion overlap is non-zero")
            gap = clearance
        elif gap < PLATE_GAP_MM - 1e-4:
            errors.append(f"{name}: layout gap {gap:.3f}mm < {PLATE_GAP_MM:g}mm")
        sources = [meshes[source_name] for source_name in source_names if source_name in meshes]
        if len(sources) == 2:
            if len(plate.faces) != sum(len(source.faces) for source in sources):
                errors.append(f"{name}: total triangle count differs from source parts")
            source_volumes = sorted(abs(float(source.volume)) for source in sources)
            body_volumes = sorted(abs(float(body.volume)) for body in bodies)
            if max(abs(a - b) for a, b in zip(source_volumes, body_volumes)) > 0.02:
                errors.append(f"{name}: rigid transform changed source volume")
        print(
            f"✓ {name}: watertight={printable_watertight} printable_bodies={len(bodies)} "
            f"gap={gap:.1f}mm bounds={np.round(plate.bounds, 2).tolist()}"
        )

    if errors:
        print("\nM6 geometry validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 2
    print("\nM6 geometry validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
