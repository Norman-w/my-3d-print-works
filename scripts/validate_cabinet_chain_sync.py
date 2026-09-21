#!/usr/bin/env python3
"""Verify that the chain motion contract and exported chain meshes are one build.

This is intentionally a build/provenance check, not a physical chain-load test.
It catches the failure mode where a new motion JSON is paired with older STL
meshes in the browser preview.
"""

from __future__ import annotations

import argparse
from array import array
import json
import math
from pathlib import Path
import struct


REQUIRED_STL_NAMES = (
    "cabinet_chain_plates.stl",
    "cabinet_chain_rollers.stl",
    "cabinet_chain_pins.stl",
    "cabinet_chain_sprockets.stl",
    "cabinet_chain_idlers.stl",
    "cabinet_chain_bearings.stl",
    "cabinet_chain_clutch_trigger_magnet.stl",
)
EXPECTED_PIN_COUNT = 260


def fail(message: str) -> None:
    raise SystemExit(f"链条预览同步检查失败: {message}")


def stl_component_centers(path: Path) -> list[tuple[float, float, float]]:
    """Return bounding-box centers for each disconnected binary STL island.

    The 03C export deliberately keeps the inner bushing and visible roller as
    two islands.  Their centers, rather than a triangle centroid, are the
    useful datum for checking that both rings are seated on one pin axis.
    """

    data = path.read_bytes()
    if len(data) < 84:
        fail(f"链条 STL 太短: {path}")
    triangle_count = struct.unpack_from("<I", data, 80)[0]
    if 84 + triangle_count * 50 > len(data):
        fail(f"链条 STL 三角形数量越界: {path}")

    parent: list[int] = []
    weld: dict[tuple[int, int, int], int] = {}
    corners = array("i")

    def vertex_id(vertex: tuple[float, float, float]) -> int:
        key = tuple(round(value * 10000) for value in vertex)
        existing = weld.get(key)
        if existing is not None:
            return existing
        index = len(parent)
        parent.append(index)
        weld[key] = index
        return index

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for triangle in range(triangle_count):
        offset = 84 + triangle * 50 + 12
        ids = []
        for corner in range(3):
            ids.append(vertex_id(struct.unpack_from("<3f", data, offset + corner * 12)))
        corners.extend(ids)
        union(ids[0], ids[1])
        union(ids[0], ids[2])

    bounds: dict[int, list[float]] = {}
    for triangle in range(triangle_count):
        root = find(corners[triangle * 3])
        bound = bounds.setdefault(root, [
            math.inf, math.inf, math.inf,
            -math.inf, -math.inf, -math.inf,
        ])
        offset = 84 + triangle * 50 + 12
        for corner in range(3):
            x, y, z = struct.unpack_from("<3f", data, offset + corner * 12)
            bound[0] = min(bound[0], x)
            bound[1] = min(bound[1], y)
            bound[2] = min(bound[2], z)
            bound[3] = max(bound[3], x)
            bound[4] = max(bound[4], y)
            bound[5] = max(bound[5], z)
    return [
        ((bound[0] + bound[3]) / 2,
         (bound[1] + bound[4]) / 2,
         (bound[2] + bound[5]) / 2)
        for bound in bounds.values()
    ]


def audit_chain_axis_seating(
    payload: dict,
    stl_dir: Path,
) -> tuple[int, int, float]:
    """Check every roller/pin island against the same authoritative pin path."""

    pins = payload.get("pins")
    if not isinstance(pins, list) or not pins:
        fail("轴线复核缺少销轴路径")
    chain_y = float(payload.get("chainY", 0))
    pitch = float(payload.get("p", 0))
    tolerance = max(0.05, pitch * 0.02)
    counts = {
        "rollers": [0] * len(pins),
        "pins": [0] * len(pins),
    }
    max_error = 0.0
    component_counts = {}
    for name, expected_per_pin in (("rollers", 2), ("pins", 1)):
        path = stl_dir / f"cabinet_chain_{name}.stl"
        centers = stl_component_centers(path)
        component_counts[name] = len(centers)
        for center in centers:
            nearest_index, nearest_error = min(
                (
                    (
                        index,
                        math.sqrt(
                            (center[0] - float(pin[0])) ** 2
                            + (center[1] - chain_y) ** 2
                            + (center[2] - float(pin[1])) ** 2
                        ),
                    )
                    for index, pin in enumerate(pins)
                ),
                key=lambda value: value[1],
            )
            if nearest_error > tolerance:
                fail(
                    f"{name} 环/轴偏离真实销中心: component={center!r} "
                    f"nearestPin={nearest_index} error={nearest_error:.4f} mm"
                )
            counts[name][nearest_index] += 1
            max_error = max(max_error, nearest_error)
        bad = [
            f"{index}:{count}"
            for index, count in enumerate(counts[name])
            if count != expected_per_pin
        ]
        if bad:
            fail(
                f"{name} 每个销位必须有 {expected_per_pin} 件，"
                f"实际异常={', '.join(bad[:8])}"
            )
    return component_counts["rollers"], component_counts["pins"], max_error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--stl-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.motion.is_file():
        fail(f"找不到运动契约: {args.motion}")
    payload = json.loads(args.motion.read_text(encoding="utf-8"))
    pins = payload.get("pins")
    wheels = payload.get("wheels")
    if not isinstance(pins, list) or len(pins) < 2 or len(pins) % 2:
        fail(f"销路径数量无效: {len(pins) if isinstance(pins, list) else pins!r}")
    if not isinstance(wheels, list) or not wheels:
        fail("没有导出轮位")

    pitch = float(payload.get("p", 0))
    if pitch <= 0:
        fail(f"节距无效: {pitch}")
    distances = []
    for index, point in enumerate(pins):
        try:
            x0, z0 = map(float, point[:2])
            x1, z1 = map(float, pins[(index + 1) % len(pins)][:2])
        except (TypeError, ValueError, IndexError) as exc:
            fail(f"销路径点 {index} 无效: {exc}")
        distances.append(math.hypot(x1 - x0, z1 - z0))
    tolerance = max(0.02, pitch * 0.02)
    if min(distances) < pitch - tolerance or max(distances) > pitch + tolerance:
        fail(
            "销间距不是统一节距: "
            f"min={min(distances):.6f} max={max(distances):.6f} P={pitch:.6f}"
        )

    drive_teeth = int(payload.get("driveTeeth", 0))
    guide_teeth = int(payload.get("guideTeeth", 0))
    sprockets = [wheel for wheel in wheels if wheel.get("kind") == "sprocket"]
    idlers = [wheel for wheel in wheels if wheel.get("kind") == "idler"]
    if len(pins) != EXPECTED_PIN_COUNT:
        fail(f"当前 250 mm / 44 mm / 错向修正 5×3 蛇链应有 {EXPECTED_PIN_COUNT} 个销，实际为 {len(pins)}")
    if abs(float(payload.get("chainY", 0)) - 75.0) > 0.01:
        fail(f"后仓链条层位应为 chainY=75.000，实际为 {payload.get('chainY')!r}")
    if abs(pitch - 4.7625) > 0.001:
        fail(f"03C 链条节距应为 4.7625 mm，实际为 {pitch:.6f} mm")
    if len(sprockets) != 1:
        fail(f"主动轮数量应为 1，实际为 {len(sprockets)}")
    if sprockets[0].get("teeth") != drive_teeth:
        fail("主动轮齿数与运动契约不一致")
    if len(idlers) != 9 or any(wheel.get("teeth") != guide_teeth for wheel in idlers):
        if len(idlers) != 9:
            fail(f"当前 5×3 蛇链含下压服务轮应有 9 个导向轮，实际为 {len(idlers)}")
        fail("导向轮齿数与运动契约不一致")

    audit = payload.get("returnPathAudit")
    if not isinstance(audit, dict):
        fail("缺少右上双轮回程路径审计")
    try:
        tangent_min = float(audit["tangentMinDot"])
        return_wheel_clearance = float(audit["upperMotorLineClearanceMm"])
        return_self_clearance = float(audit["returnPathSelfClearanceMm"])
        service_motor_clearance = float(audit["serviceMotorEnvelopeClearanceMm"])
        trim = float(payload["driveReturnXTrimMm"])
        service_press_trim = float(payload["servicePressReturnXTrimMm"])
        motor_offset = float(payload["motorReturnXOffsetMm"])
    except (KeyError, TypeError, ValueError) as exc:
        fail(f"右上双轮回程路径审计字段无效: {exc}")
    if tangent_min < 0.999:
        fail(f"右上双轮切线未连续: minDot={tangent_min:.6f}")
    if return_wheel_clearance < 0.40:
        fail(
            "上下回程导向轮实体包络净空不足: "
            f"clearance={return_wheel_clearance:.3f} mm"
        )
    if return_self_clearance < 6.40:
        fail(
            "蛇链回程路径存在麻花/自交: "
            f"clearance={return_self_clearance:.3f} mm"
        )
    if service_motor_clearance < 0.40:
        fail(
            "下方服务链段与电机回程斜段的包络发生干涉: "
            f"clearance={service_motor_clearance:.3f} mm"
        )
    if (
        abs(trim + 4.00) > 0.001
        or abs(service_press_trim - 16.00) > 0.001
        or abs(motor_offset + 2.00) > 0.001
    ):
        fail(
            "错向修正回程 X 基准错误: "
            f"upper={trim:.3f} lower={service_press_trim:.3f} "
            f"motorOffset={motor_offset:.3f}"
        )
    wheel_by_id = {wheel.get("id"): wheel for wheel in wheels}
    expected_return_signs = {"drive": 1, "service-press": -1}
    for wheel_id, expected_sign in expected_return_signs.items():
        if wheel_by_id.get(wheel_id, {}).get("sign") != expected_sign:
            fail(
                f"{wheel_id} 旋向错误: "
                f"expected={expected_sign} actual={wheel_by_id.get(wheel_id, {}).get('sign')!r}"
            )

    roller_components, pin_components, axis_error = audit_chain_axis_seating(
        payload,
        args.stl_dir,
    )

    center = payload.get("centerClutch")
    datum = payload.get("chainTopDatum")
    trigger = payload.get("chainTriggerMagnet")
    if not isinstance(center, dict) or not isinstance(datum, dict) or not isinstance(trigger, dict):
        fail("缺少中心离合/蛇链磁铁高度契约")
    try:
        shift = float(payload["chainVerticalShiftMm"])
        contract_shift = float(center["snakeChainVerticalShiftMm"])
        magnet_bottom = float(datum["inputSleeveMagnetOpenBottomYMm"])
        link_top = float(datum["linkTopOffsetMm"])
        reference_path = float(datum["referencePathCenterYMm"])
        shifted_path = float(datum["referencePathShiftedCenterYMm"])
        floor_clearance = float(datum["servicePathFloorClearanceMm"])
        return_guide = float(datum["returnGuideCenterYMm"])
        contract_return_guide = float(center["snakeChainReturnGuideCenterYMm"])
        trigger_index = int(trigger["segmentIndex"])
        trigger_d = float(trigger["diameterMm"])
        trigger_l = float(trigger["lengthMm"])
        trigger_top_clearance = float(trigger["topClearanceMm"])
    except (KeyError, TypeError, ValueError) as exc:
        fail(f"蛇链磁铁高度契约字段无效: {exc}")
    if abs(shift - contract_shift) > 0.001:
        fail("链条高度偏移与中心离合契约不一致")
    if datum.get("mode") != "input-sleeve-magnet-bottom":
        fail("链条上沿基准不是公轮底部磁铁下沿")
    if abs(shifted_path - (reference_path + shift)) > 0.001:
        fail("蛇链参考服务行没有按契约偏移")
    if abs(shifted_path + link_top - magnet_bottom) > 0.001:
        fail("链节上沿没有对齐公轮底部磁铁下沿")
    if abs(return_guide - contract_return_guide) > 0.001 or return_guide < 10.0:
        fail("底部回程导向轮高度与契约或箱底安全线不一致")
    if floor_clearance <= 0:
        fail(f"底部回程导向轮侵入箱底，余量={floor_clearance:.3f} mm")
    if trigger_index < 0 or trigger_index >= len(pins):
        fail(f"触发磁铁节号越界: {trigger_index}")
    if abs(trigger_d - 2.0) > 0.001 or abs(trigger_l - 1.8) > 0.001:
        fail("链节触发磁铁必须为 Ø2×1.8 采购件参考")
    if abs(trigger_top_clearance) > 0.001:
        fail("链节触发磁铁上沿没有锁定到链节上沿基准")

    motion_mtime = args.motion.stat().st_mtime_ns
    stale = []
    for name in REQUIRED_STL_NAMES:
        path = args.stl_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"缺少链条 STL: {path}")
        if path.stat().st_mtime_ns < motion_mtime:
            stale.append(name)
    if stale:
        fail("STL 早于运动契约，疑似旧几何: " + ", ".join(stale))

    print(
        "链条预览同步通过: "
        f"pins={len(pins)} wheels={len(wheels)} "
        f"drive={drive_teeth}T idlers={len(idlers)}×{guide_teeth}T "
        f"chainY={float(payload.get('chainY', 0)):.3f} "
        f"verticalShift={shift:.3f} triggerSegment={trigger_index} "
        f"axisSeating=rollers:{roller_components}/pins:{pin_components} "
        f"maxAxisError={axis_error:.4f}mm"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
