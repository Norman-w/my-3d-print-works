#!/usr/bin/env python3
"""Build two M6 print-bed STL files using rigid transforms only.

The assembly geometry is never rescaled, remeshed, welded, or booleaned. Each
plate contains two independent source meshes positioned inside a 256 mm cube.
"""

from __future__ import annotations

import json
import hashlib
import argparse
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterable

from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
STL = ROOT / "enclosure" / "stl"
OUT = STL / "print"
BUILD_MM = 256.0
GAP_MM = 5.0
X1C_EDGE_MARGIN_MM = 5.0
X1C_SUPPORT_RESERVE_MM = 5.0
X1C_EXCLUDE = (0.0, 0.0, 18.0, 28.0)
CONTACT_PLANE_TOL_MM = 0.03
NECK_CONTACT_MIN_AREA_MM2 = 25.0
NECK_CONTACT_MIN_WIDTH_MM = 20.0
NECK_CONTACT_MIN_DEPTH_MM = 1.5
TRIANGLE = struct.Struct("<12fH")
Matrix = tuple[tuple[float, float, float], ...]


@dataclass(frozen=True)
class BinaryStl:
    path: Path
    triangles: tuple[tuple[float, ...], ...]
    bounds: tuple[tuple[float, float, float], tuple[float, float, float]]


@dataclass(frozen=True)
class OrientedPart:
    mesh: BinaryStl
    triangles: tuple[tuple[float, ...], ...]
    bounds: tuple[tuple[float, float, float], tuple[float, float, float]]
    matrix: Matrix
    orientation: dict[str, object]


def load_binary_stl(path: Path) -> BinaryStl:
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"STL 文件过短: {path}")
    count = struct.unpack_from("<I", data, 80)[0]
    expected = 84 + count * TRIANGLE.size
    if len(data) != expected:
        raise ValueError(f"仅支持 OpenSCAD 二进制 STL: {path} ({len(data)} != {expected})")
    triangles: list[tuple[float, ...]] = []
    offset = 84
    for _ in range(count):
        triangles.append(TRIANGLE.unpack_from(data, offset))
        offset += TRIANGLE.size
    return BinaryStl(path, tuple(triangles), bounds_of(triangles))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mat_mul(a: Matrix, b: Matrix) -> Matrix:
    return tuple(
        tuple(sum(a[row][k] * b[k][column] for k in range(3)) for column in range(3))
        for row in range(3)
    )


def rotation_x(degrees: float) -> Matrix:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def rotation_z(degrees: float) -> Matrix:
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def rotate_vector(matrix: Matrix, vector: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(sum(matrix[row][axis] * vector[axis] for axis in range(3)) for row in range(3))


def transform_triangles(
    triangles: Iterable[tuple[float, ...]],
    matrix: Matrix,
    shift: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> tuple[tuple[float, ...], ...]:
    transformed: list[tuple[float, ...]] = []
    for values in triangles:
        moved = list(values)
        moved[0:3] = rotate_vector(matrix, (values[0], values[1], values[2]))
        for start in (3, 6, 9):
            point = rotate_vector(matrix, (values[start], values[start + 1], values[start + 2]))
            moved[start:start + 3] = [point[axis] + shift[axis] for axis in range(3)]
        transformed.append(tuple(moved))
    return tuple(transformed)


def bounds_of(triangles: Iterable[tuple[float, ...]]):
    mins = [float("inf")] * 3
    maxs = [float("-inf")] * 3
    for values in triangles:
        for start in (3, 6, 9):
            for axis in range(3):
                value = values[start + axis]
                mins[axis] = min(mins[axis], value)
                maxs[axis] = max(maxs[axis], value)
    return (tuple(mins), tuple(maxs))


def orient(mesh: BinaryStl, matrix: Matrix, orientation: dict[str, object]) -> OrientedPart:
    triangles = transform_triangles(mesh.triangles, matrix)
    return OrientedPart(mesh, triangles, bounds_of(triangles), matrix, orientation)


def flat_core(mesh: BinaryStl, *, flip_face_up: bool = False) -> OrientedPart:
    face_flip = (
        ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0))
        if flip_face_up
        else ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    )
    # Flip around the part-local X axis first, then apply the requested 45°
    # rotation in the bed plane. Both operations are rigid transforms.
    matrix = mat_mul(rotation_z(45.0), face_flip)
    return orient(mesh, matrix, {
        "flatOnBed": True,
        "bedRotationZDeg": 45.0,
        "threadEntryFacesPositiveZ": flip_face_up,
        "faceFlipped": flip_face_up,
    })


def upright_thick_part(mesh: BinaryStl, *, bed_end: str = "shoulder") -> OrientedPart:
    # Discover the paddle-head-side shoulder/neck cut plane from the actual
    # mesh (maximum source Y), then put that plane on Z=0. This avoids relying
    # on a fixed model coordinate and gives the narrow shoulder a broad,
    # planar contact patch on the bed.
    if bed_end not in {"shoulder", "base"}:
        raise ValueError(f"未知竖立落床端: {bed_end}")
    shoulder_y = mesh.bounds[1][1] if bed_end == "shoulder" else mesh.bounds[0][1]
    contact_triangles = [
        values for values in mesh.triangles
        if all(abs(values[index + 1] - shoulder_y) <= CONTACT_PLANE_TOL_MM for index in (3, 6, 9))
    ]
    contact_points = [
        (values[index], values[index + 2])
        for values in contact_triangles for index in (3, 6, 9)
    ]
    if not contact_points:
        raise ValueError(f"{mesh.path.name} 未找到肩颈平面接触带")
    def triangle_area(values: tuple[float, ...]) -> float:
        a = tuple(values[6 + axis] - values[3 + axis] for axis in range(3))
        b = tuple(values[9 + axis] - values[3 + axis] for axis in range(3))
        cross = (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )
        return 0.5 * math.sqrt(sum(value * value for value in cross))
    contact_area = sum(triangle_area(values) for values in contact_triangles)
    contact_width = max(x for x, _ in contact_points) - min(x for x, _ in contact_points)
    contact_depth = max(z for _, z in contact_points) - min(z for _, z in contact_points)
    if (
        contact_area < NECK_CONTACT_MIN_AREA_MM2
        or contact_width < NECK_CONTACT_MIN_WIDTH_MM
        or contact_depth < NECK_CONTACT_MIN_DEPTH_MM
    ):
        raise ValueError(
            f"{mesh.path.name} 肩颈接触带不足: area={contact_area:.2f}mm² "
            f"width={contact_width:.2f}mm depth={contact_depth:.2f}mm"
        )
    base = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0))
    # Shoulder-down uses z=-sourceY. Base-down is the actual vertical flip:
    # z=+sourceY and bed-Y=-sourceZ. It cannot be replaced by an XY rotation.
    matrix = base if bed_end == "shoulder" else mat_mul(rotation_x(180.0), base)
    return orient(mesh, matrix, {
        "bedContact": "detectedShoulderNeckPlane" if bed_end == "shoulder" else "detectedPhysicalBasePlane",
        "contactSourceY": shoulder_y,
        "contactAreaMm2": contact_area,
        "contactWidthMm": contact_width,
        "contactDepthMm": contact_depth,
        "uprightAlongZ": True,
        "baseFacesBed": bed_end == "base",
        "verticalFlipXDeg": 180.0 if bed_end == "base" else 0.0,
        "supportRecommendation": "在 Bambu Studio 中为此竖立件开启树状自动支撑",
    })


def footprint(part: OrientedPart):
    polygons = []
    for values in part.triangles:
        polygon = Polygon([(values[index], values[index + 1]) for index in (3, 6, 9)])
        if polygon.area > 1e-7:
            polygons.append(polygon)
    return unary_union(polygons)


def place_x1c_rear(parts: list[OrientedPart]):
    """Solve the layer 3+4 layout from mesh footprints and X1C constraints."""
    skin, core = parts
    skin_shape, core_shape = footprint(skin), footprint(core)
    safe_bed = box(
        X1C_EDGE_MARGIN_MM, X1C_EDGE_MARGIN_MM,
        BUILD_MM - X1C_EDGE_MARGIN_MM, BUILD_MM - X1C_EDGE_MARGIN_MM,
    ).difference(box(*X1C_EXCLUDE).buffer(X1C_SUPPORT_RESERVE_MM, join_style=2))

    def feasible(shape, dx, dy):
        moved = affinity.translate(shape, dx, dy)
        envelope = moved.buffer(X1C_SUPPORT_RESERVE_MM, join_style=2)
        return safe_bed.covers(envelope), moved, envelope

    # Mesh-derived translations are sampled rather than fixed. The core's
    # candidate range follows its actual bounds; the upright skin is searched
    # over the remaining bed. A 1 mm grid is finer than normal slicer placement
    # nudges and makes the solver deterministic under parameter changes.
    candidates = []
    cb = core_shape.bounds
    sb = skin_shape.bounds
    skin_candidates = []
    for skin_left in range(
        math.ceil(X1C_EDGE_MARGIN_MM - sb[0] + X1C_SUPPORT_RESERVE_MM),
        math.floor(BUILD_MM - X1C_EDGE_MARGIN_MM - sb[2] - X1C_SUPPORT_RESERVE_MM) + 1,
        2,
    ):
        for skin_bottom in range(
            math.ceil(X1C_EDGE_MARGIN_MM - sb[1] + X1C_SUPPORT_RESERVE_MM),
            math.floor(BUILD_MM - X1C_EDGE_MARGIN_MM - sb[3] - X1C_SUPPORT_RESERVE_MM) + 1,
            2,
        ):
            skin_ok, skin_moved, skin_env = feasible(skin_shape, skin_left, skin_bottom)
            if skin_ok:
                skin_candidates.append((
                    skin_left, skin_bottom, skin_moved, skin_env,
                    skin_moved.centroid.x, skin_moved.centroid.y,
                    skin_moved.area, skin_moved.bounds,
                ))
    SEARCH_STEP_MM = 2
    for core_left in range(math.ceil(X1C_EDGE_MARGIN_MM - cb[0] + X1C_SUPPORT_RESERVE_MM),
                           math.floor(BUILD_MM - X1C_EDGE_MARGIN_MM - cb[2] - X1C_SUPPORT_RESERVE_MM) + 1,
                           SEARCH_STEP_MM):
        for core_bottom in range(math.ceil(X1C_EDGE_MARGIN_MM - cb[1] + X1C_SUPPORT_RESERVE_MM),
                                 math.floor(BUILD_MM - X1C_EDGE_MARGIN_MM - cb[3] - X1C_SUPPORT_RESERVE_MM) + 1,
                                 SEARCH_STEP_MM):
            core_ok, core_moved, core_env = feasible(core_shape, core_left, core_bottom)
            if not core_ok:
                continue
            # The requested solution characteristic is rear skin to the right,
            # near the core shoulder/neck. Its exact coordinate remains solved.
            core_cx, core_cy = core_moved.centroid.x, core_moved.centroid.y
            core_area, core_bounds = core_moved.area, core_moved.bounds
            for skin_left, skin_bottom, skin_moved, skin_env, skin_cx, skin_cy, skin_area, skin_bounds in skin_candidates:
                    if skin_cx < core_cx:
                        continue
                    # Cheap AABB rejection avoids almost all expensive GEOS
                    # intersections while preserving exact footprint checks.
                    envelopes_overlap = not (
                        skin_env.bounds[0] > core_env.bounds[2]
                        or skin_env.bounds[2] < core_env.bounds[0]
                        or skin_env.bounds[1] > core_env.bounds[3]
                        or skin_env.bounds[3] < core_env.bounds[1]
                    )
                    if envelopes_overlap and core_env.intersects(skin_env):
                        continue
                    total_area = core_area + skin_area
                    combined_cx = (
                        core_cx * core_area + skin_cx * skin_area
                    ) / total_area
                    combined_cy = (
                        core_cy * core_area + skin_cy * skin_area
                    ) / total_area
                    center_error = math.hypot(combined_cx - BUILD_MM / 2, combined_cy - BUILD_MM / 2)
                    # Prefer the skin beside the narrow handle/shoulder side,
                    # then minimize combined off-centering and unused span.
                    shoulder_error = abs(skin_cy - core_cy)
                    combined_span = max(core_bounds[2], skin_bounds[2]) - min(core_bounds[0], skin_bounds[0])
                    score = center_error + 0.08 * shoulder_error + 0.01 * combined_span
                    candidates.append((score, core_left, core_bottom, skin_left, skin_bottom,
                                       core_moved, skin_moved, core_env, skin_env))
    if not candidates:
        raise ValueError("第3+4拼板在 X1C 可用区域、禁区、支撑预留和5mm分隔约束下无解")
    _, cdx, cdy, sdx, sdy, core_moved, skin_moved, core_env, skin_env = min(candidates, key=lambda x: x[0])
    shifts = [(sdx, sdy, -skin.bounds[0][2]), (cdx, cdy, -core.bounds[0][2])]
    final_parts, metadata = [], []
    for part, shift in zip(parts, shifts):
        triangles = transform_triangles(part.triangles, rotation_x(0), shift)
        final_parts.append(triangles)
        metadata.append({
            "source": part.mesh.path.name, "sourceSha256": sha256_file(part.mesh.path),
            "triangleCount": len(part.mesh.triangles),
            "rotationMatrix": [list(row) for row in part.matrix],
            "translationAfterRotation": list(shift), "orientation": part.orientation,
            "sourceBounds": [list(part.mesh.bounds[0]), list(part.mesh.bounds[1])],
            "finalBounds": [list(v) for v in bounds_of(triangles)],
        })
    clearance = core_moved.distance(skin_moved)
    if clearance < GAP_MM - 1e-6:
        raise ValueError(f"第3+4拼板实际轮廓间距不足: {clearance:.3f}mm")
    validation = {
        "printer": "Bambu Lab X1 Carbon 0.4 nozzle",
        "profileSource": "Bambu Studio 01.10.02.76 / Bambu Lab X1 Carbon 0.4 nozzle.json",
        "printableArea": [[0, 0], [256, 0], [256, 256], [0, 256]],
        "bedExcludeArea": [[0, 0], [18, 0], [18, 28], [0, 28]],
        "edgeMarginMm": X1C_EDGE_MARGIN_MM,
        "supportReserveMm": X1C_SUPPORT_RESERVE_MM,
        "partClearanceMm": clearance,
        "excludedAreaOverlapMm2": core_env.intersection(box(*X1C_EXCLUDE)).area + skin_env.intersection(box(*X1C_EXCLUDE)).area,
        "solver": "actual-mesh-footprints, detected bed-contact plane, 2mm deterministic search",
        "candidateCount": len(candidates),
        "passed": True,
    }
    return final_parts, metadata, validation


def flat_skin(mesh: BinaryStl, front: bool) -> OrientedPart:
    # Front outer/rubber face is +Z, so flip it downward. Back outer/rubber
    # face is already -Z and needs no rotation.
    # Use exact axis matrices here. Trigonometric 180° introduces tiny
    # non-zero terms which can break vertex welding when the combined STL is
    # checked for connected bodies, despite the geometry being unchanged.
    matrix = (
        ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0))
        if front
        else ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    )
    return orient(mesh, matrix, {
        "rubberFaceOnBed": True,
        "rotationXDeg": 180.0 if front else 0.0,
    })


def place_parts(
    parts: list[OrientedPart],
    *,
    y_alignments: list[str] | None = None,
) -> tuple[list[tuple[tuple[float, ...], ...]], list[dict[str, object]]]:
    if y_alignments is None:
        y_alignments = ["low"] * len(parts)
    if len(y_alignments) != len(parts) or any(value not in {"low", "high"} for value in y_alignments):
        raise ValueError("y_alignments 必须逐件指定 low 或 high")
    max_y_size = max(part.bounds[1][1] - part.bounds[0][1] for part in parts)
    cursor_x = 0.0
    placed: list[tuple[tuple[float, ...], ...]] = []
    metadata: list[dict[str, object]] = []
    preliminary_bounds = []
    preliminary_shifts = []
    for part, y_alignment in zip(parts, y_alignments):
        lo, hi = part.bounds
        y_size = hi[1] - lo[1]
        y_offset = max_y_size - y_size if y_alignment == "high" else 0.0
        shift = (cursor_x - lo[0], y_offset - lo[1], -lo[2])
        triangles = transform_triangles(part.triangles, rotation_x(0.0), shift)
        bounds = bounds_of(triangles)
        placed.append(triangles)
        preliminary_bounds.append(bounds)
        preliminary_shifts.append(shift)
        cursor_x = bounds[1][0] + GAP_MM

    combined_lo = [min(bounds[0][axis] for bounds in preliminary_bounds) for axis in range(3)]
    combined_hi = [max(bounds[1][axis] for bounds in preliminary_bounds) for axis in range(3)]
    size = [combined_hi[axis] - combined_lo[axis] for axis in range(3)]
    if any(value > BUILD_MM + 1e-6 for value in size):
        raise ValueError(f"拼板尺寸 {size} 超过 {BUILD_MM:g}mm 构建体积")
    center_shift = (
        (BUILD_MM - size[0]) / 2 - combined_lo[0],
        (BUILD_MM - size[1]) / 2 - combined_lo[1],
        -combined_lo[2],
    )

    final_parts = []
    for part, triangles, initial_shift in zip(parts, placed, preliminary_shifts):
        final_triangles = transform_triangles(triangles, rotation_x(0.0), center_shift)
        final_bounds = bounds_of(final_triangles)
        final_parts.append(final_triangles)
        total_shift = [initial_shift[axis] + center_shift[axis] for axis in range(3)]
        metadata.append({
            "source": part.mesh.path.name,
            "sourceSha256": sha256_file(part.mesh.path),
            "triangleCount": len(part.mesh.triangles),
            "rotationMatrix": [list(row) for row in part.matrix],
            "translationAfterRotation": total_shift,
            "orientation": part.orientation,
            "sourceBounds": [list(part.mesh.bounds[0]), list(part.mesh.bounds[1])],
            "finalBounds": [list(final_bounds[0]), list(final_bounds[1])],
        })

    first, second = [bounds_of(triangles) for triangles in final_parts]
    gap = second[0][0] - first[1][0]
    if gap < GAP_MM - 1e-5:
        raise ValueError(f"零件排版间隔不足: {gap:.4f}mm")
    for item in metadata:
        lo, hi = item["finalBounds"]
        if any(lo[axis] < -1e-5 or hi[axis] > BUILD_MM + 1e-5 for axis in range(3)):
            raise ValueError(f"{item['source']} 超出 {BUILD_MM:g}mm 构建体积: {item['finalBounds']}")
    return final_parts, metadata


def write_plate(
    filename: str,
    label: str,
    parts: list[OrientedPart],
    *,
    y_alignments: list[str] | None = None,
    x1c_rear_solver: bool = False,
) -> dict[str, object]:
    x1c_validation = None
    if x1c_rear_solver:
        placed, part_metadata, x1c_validation = place_x1c_rear(parts)
    else:
        placed, part_metadata = place_parts(parts, y_alignments=y_alignments)
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / filename
    count = sum(len(triangles) for triangles in placed)
    header = f"SmartPaddle {filename}; rigid transforms; two independent parts".encode("ascii")[:80]
    with output.open("wb") as handle:
        handle.write(header.ljust(80, b"\0"))
        handle.write(struct.pack("<I", count))
        for triangles in placed:
            for triangle in triangles:
                handle.write(TRIANGLE.pack(*triangle))
    result = {
        "label": label,
        "path": f"print/{filename}",
        "buildVolumeMm": [BUILD_MM, BUILD_MM, BUILD_MM],
        "gapMm": GAP_MM,
        "assemblyGeometryUnchanged": True,
        "sha256": sha256_file(output),
        "parts": part_metadata,
    }
    if x1c_validation is not None:
        result["x1cValidation"] = x1c_validation
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plate", choices=("all", "1_2", "3_4"), default="all")
    args = parser.parse_args()
    layer1 = load_binary_stl(STL / "paddle_m6_layer1_handle_skin_front.stl")
    layer2 = load_binary_stl(STL / "paddle_m6_layer2_core_front.stl")
    layer3 = load_binary_stl(STL / "paddle_m6_layer3_core_back.stl")
    layer4 = load_binary_stl(STL / "paddle_m6_layer4_handle_skin_back.stl")
    builders = [
        # Bambu Studio check: layer 1 is flipped, moved to the upper-left;
        # layer 2 remains flat at 45° but is shifted right. Bounds and the
        # exact 5 mm X gap are calculated from the source meshes.
        lambda: write_plate(
                "paddle_m6_print_plate_layers_1_2.stl",
                "第1+2块：长承力板平放45° + 加厚外贴件竖立",
                [upright_thick_part(layer1, bed_end="shoulder"), flat_core(layer2, flip_face_up=True)],
                y_alignments=["high", "low"],
            ),
        # Mirrored bed layout with the same per-part orientations.
        lambda: write_plate(
                "paddle_m6_print_plate_layers_3_4.stl",
                "第3+4块：长承力板平放45° + 加厚外贴件竖立",
                [upright_thick_part(layer4, bed_end="base"), flat_core(layer3)],
                x1c_rear_solver=True,
            ),
    ]
    metadata = OUT / "print_plates.json"
    if args.plate == "all":
        plates = [build() for build in builders]
    else:
        selected = 0 if args.plate == "1_2" else 1
        if not metadata.is_file():
            raise ValueError("单板更新要求已有 print_plates.json")
        previous = json.loads(metadata.read_text(encoding="utf-8"))
        by_path = {item["path"]: item for item in previous.get("plates", [])}
        replacement = builders[selected]()
        by_path[replacement["path"]] = replacement
        order = ["print/paddle_m6_print_plate_layers_1_2.stl", "print/paddle_m6_print_plate_layers_3_4.stl"]
        plates = [by_path[path] for path in order]
    metadata.write_text(
        json.dumps({
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "assemblyGeometryUnchanged": True,
            "plates": plates,
        }, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    for plate in plates:
        print(
            f"✓ {STL / str(plate['path'])}  build={BUILD_MM:g}³mm  "
            f"gap={GAP_MM:g}mm  bodies=2"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
