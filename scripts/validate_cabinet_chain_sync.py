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
    "cabinet_chain_clutch_trigger_carrier.stl",
    "cabinet_chain_clutch_trigger_magnet.stl",
    "cabinet_chain_clutch_trigger_connecting_pins.stl",
    "cabinet_chain_clutch_trigger_retaining_clip.stl",
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


def stl_bounds(path: Path) -> tuple[float, float, float]:
    """Return the absolute STL envelope dimensions in file-axis order."""

    data = path.read_bytes()
    if len(data) < 84:
        fail(f"链条 STL 太短: {path}")
    triangle_count = struct.unpack_from("<I", data, 80)[0]
    if 84 + triangle_count * 50 > len(data):
        fail(f"链条 STL 三角形数量越界: {path}")
    mins = [math.inf, math.inf, math.inf]
    maxs = [-math.inf, -math.inf, -math.inf]
    for triangle in range(triangle_count):
        offset = 84 + triangle * 50 + 12
        for corner in range(3):
            vertex = struct.unpack_from("<3f", data, offset + corner * 12)
            for axis, value in enumerate(vertex):
                mins[axis] = min(mins[axis], value)
                maxs[axis] = max(maxs[axis], value)
    return tuple(maximum - minimum for minimum, maximum in zip(mins, maxs))


def audit_chain_axis_seating(
    payload: dict,
    stl_dir: Path,
) -> tuple[int, int, int, float]:
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
        paths = [stl_dir / f"cabinet_chain_{name}.stl"]
        if name == "pins":
            # The two trigger positions are intentionally removed from the
            # ordinary pin STL. Count the existing purchased grooved pair as
            # the two physical pin islands at those same path positions.
            paths.append(stl_dir / "cabinet_chain_clutch_trigger_connecting_pins.stl")
        centers = [center for path in paths for center in stl_component_centers(path)]
        component_counts[name] = len(centers)
        for center in centers:
            nearest_index, nearest_error = min(
                (
                    (
                        index,
                        (
                            math.hypot(
                                center[0] - float(pin[0]),
                                center[2] - float(pin[1]),
                            )
                            if name == "pins"
                            else math.sqrt(
                                (center[0] - float(pin[0])) ** 2
                                + (center[1] - chain_y) ** 2
                                + (center[2] - float(pin[1])) ** 2
                            )
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
    physical_roller_count = len(pins)
    if component_counts["rollers"] != physical_roller_count * 2:
        fail(
            "滚子 STL 环岛数量不等于每个销位的内衬套+外滚子两件: "
            f"ringComponents={component_counts['rollers']} "
            f"expected={physical_roller_count * 2}"
        )
    return (
        component_counts["rollers"],
        component_counts["pins"],
        physical_roller_count,
        max_error,
    )


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

    roller_ring_components, pin_components, roller_count, axis_error = audit_chain_axis_seating(
        payload,
        args.stl_dir,
    )

    center = payload.get("centerClutch")
    datum = payload.get("chainTopDatum")
    trigger = payload.get("chainTriggerMagnet")
    carrier = payload.get("chainTriggerCarrier")
    if (
        not isinstance(center, dict)
        or not isinstance(datum, dict)
        or not isinstance(trigger, dict)
        or not isinstance(carrier, dict)
    ):
        fail("缺少中心离合/蛇链 M5 双销载架高度契约")
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
        carrier_segment = int(carrier["segmentIndex"])
        carrier_pin_spacing = float(carrier["pinSpacingMm"])
        carrier_pin_diameter = float(carrier["pinDiameterMm"])
        carrier_pin_hole = float(carrier["pinHoleDiameterMm"])
        carrier_pin_length = float(carrier["pinLengthMm"])
        carrier_plate_thickness = float(carrier["plateThicknessMm"])
        carrier_magnet_diameter = float(carrier["magnetDiameterMm"])
        carrier_magnet_length = float(carrier["magnetLengthMm"])
        carrier_pocket_diameter = float(carrier["magnetPocketDiameterMm"])
        carrier_pocket_depth = float(carrier["magnetPocketDepthMm"])
        carrier_lip = float(carrier["magnetRetentionLipMm"])
        carrier_back_wall = float(carrier["magnetBackWallMm"])
        carrier_center_along = float(carrier["magnetCenterAlongLinkMm"])
        carrier_center_normal = float(carrier["magnetCenterNormalMm"])
        trigger_axis = str(trigger["axis"])
        carrier_axis = str(carrier["magnetAxis"])
        carrier_center_reference = str(carrier["magnetCenterReference"])
        carrier_hardware_mode = str(carrier["hardwareMode"])
        carrier_clip_thickness = float(carrier["retainingClipThicknessMm"])
    except (KeyError, TypeError, ValueError) as exc:
        fail(f"蛇链 M5 双销载架契约字段无效: {exc}")
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
    if abs(trigger_d - 5.0) > 0.001 or abs(trigger_l - 4.00) > 0.001:
        fail("链节触发磁铁必须为 M5×4 采购件参考")
    if abs(trigger_top_clearance) > 0.001:
        fail("链节触发磁铁上沿没有锁定到链节上沿基准")
    if carrier_segment != trigger_index:
        fail("M5 载架与磁铁没有使用同一个链节节号")
    expected_carrier = {
        "pinSpacingMm": (carrier_pin_spacing, 4.7625),
        "pinDiameterMm": (carrier_pin_diameter, 1.62),
        "pinHoleDiameterMm": (carrier_pin_hole, 1.80),
        "pinLengthMm": (carrier_pin_length, 11.50),
        "plateThicknessMm": (carrier_plate_thickness, 4.00),
        "magnetDiameterMm": (carrier_magnet_diameter, 5.00),
        "magnetLengthMm": (carrier_magnet_length, 4.00),
        "magnetPocketDiameterMm": (carrier_pocket_diameter, 5.25),
        "magnetPocketDepthMm": (carrier_pocket_depth, 4.00),
        "magnetRetentionLipMm": (carrier_lip, 0.00),
        "magnetBackWallMm": (carrier_back_wall, 0.00),
        "magnetCenterNormalMm": (carrier_center_normal, 0.00),
    }
    for field, (actual, expected) in expected_carrier.items():
        if abs(actual - expected) > 0.001:
            fail(f"M5 双销载架字段错误: {field}={actual:.6f}, expected={expected:.6f}")
    if carrier_center_along <= 0:
        fail("M5 磁铁必须位于第二销外侧的圆角拖尾内")
    if carrier.get("mounting") != "two-adjacent-03C-pins-side-hung":
        fail("M5 载架安装方式不是相邻两根 03C 销轴侧挂")
    if carrier.get("partId") != "cabinet-chain/cabinet_chain_clutch_trigger_carrier":
        fail("M5 双销载架 partId 错误")
    if carrier.get("magnetPartId") != "cabinet-chain/cabinet_chain_clutch_trigger_magnet":
        fail("M5 磁铁 partId 错误")
    if trigger_axis != "stl-Z" or carrier_axis != "stl-Z":
        fail("M5 触发磁铁导出 STL 轴线必须是 STL Z")
    if carrier_center_reference != "rear-rounded-tail-hole-center":
        fail("M5 拖尾磁铁座必须以后侧圆角矩形磁铁座为 X 基准")
    if carrier_hardware_mode != "purchased-03C-extended-pin-pair-plus-two-U-clips":
        fail("M5 触发件必须使用现成加长双卡槽穿销与两片 U 形卡")
    if abs(carrier_clip_thickness - 0.60) > 0.001:
        fail(f"U 形卡厚度错误: {carrier_clip_thickness:.6f}")
    if carrier.get("connectingPinsPartId") != (
        "cabinet-chain/cabinet_chain_clutch_trigger_connecting_pins"
    ):
        fail("现成加长穿销 partId 错误")
    if carrier.get("retainingClipPartId") != (
        "cabinet-chain/cabinet_chain_clutch_trigger_retaining_clip"
    ):
        fail("现成 U 形卡 partId 错误")

    assembly = payload.get("chainTriggerAssembly")
    if not isinstance(assembly, dict):
        fail("运动契约缺少 chainTriggerAssembly 刚性组件关系")
    if assembly.get("id") != "chain-trigger-assembly":
        fail("chainTriggerAssembly id 错误")
    if assembly.get("componentMode") != "rigid-mounted":
        fail("chainTriggerAssembly 必须是 rigid-mounted")
    path_mount = assembly.get("pathMount") or {}
    if path_mount.get("type") != "chain-segment" \
            or int(path_mount.get("segmentIndex", -1)) != trigger_index \
            or path_mount.get("pinAxis") != "stl-Y" \
            or path_mount.get("follow") != "segment-midpoint":
        fail("chainTriggerAssembly 链节挂载基准错误")
    component_ids = {
        str(component.get("id"))
        for component in assembly.get("components", [])
        if isinstance(component, dict)
    }
    if component_ids != {"carrier", "connecting-pins", "retaining-clips", "magnet"}:
        fail("chainTriggerAssembly 组件集合必须包含载架/穿销/卡簧/磁铁")
    relations = {
        (str(relation.get("parent")), str(relation.get("child")), str(relation.get("interface")))
        for relation in assembly.get("mountRelations", [])
        if isinstance(relation, dict)
    }
    required_relations = {
        ("chain-segment", "carrier", "two-adjacent-03C-pin-bores"),
        ("carrier", "connecting-pins", "paired-pin-bores"),
        ("connecting-pins", "retaining-clips", "two-groove-capture"),
        ("carrier", "magnet", "rear-rounded-tail-through-seat"),
    }
    if not required_relations.issubset(relations):
        fail("chainTriggerAssembly 缺少完整的父子挂载关系")
    animation = assembly.get("animation") or {}
    if animation.get("mode") != "rigid-follow-segment" \
            or animation.get("allComponentsSharePose") is not True:
        fail("chainTriggerAssembly 动画必须是单刚性姿态")

    carrier_path = args.stl_dir / "cabinet_chain_clutch_trigger_carrier.stl"
    magnet_path = args.stl_dir / "cabinet_chain_clutch_trigger_magnet.stl"
    carrier_bounds = stl_bounds(carrier_path)
    magnet_bounds = stl_bounds(magnet_path)
    if carrier_bounds[0] < 16.0 or carrier_bounds[1] < 3.8 or carrier_bounds[2] < 3.8:
        fail(f"M5 双销载架包络过小，疑似导出错件: bounds={carrier_bounds!r}")
    if (
        abs(magnet_bounds[0] - 5.00) > 0.02
        or abs(magnet_bounds[1] - 5.00) > 0.02
        or abs(magnet_bounds[2] - 4.00) > 0.02
    ):
        fail(
            "M5 磁铁参考 STL 必须是 X/Y=Ø5、Z=4.00 的轴向: "
            f"bounds={magnet_bounds!r}"
        )
    connecting_pin_bounds = stl_bounds(
        args.stl_dir / "cabinet_chain_clutch_trigger_connecting_pins.stl"
    )
    if abs(connecting_pin_bounds[1] - 11.50) > 0.02:
        fail(
            "现成加长穿销 Y 向总长错误: "
            f"bounds={connecting_pin_bounds!r}"
        )
    clip_bounds = stl_bounds(
        args.stl_dir / "cabinet_chain_clutch_trigger_retaining_clip.stl"
    )
    # The exported reference intentionally contains two U clips at the two
    # grooves. Their combined Y span is the 03C plate stack plus two 0.60 mm
    # clip sections, not a single 0.60 mm solid.
    if abs(clip_bounds[1] - 5.20) > 0.02 or abs(clip_bounds[2] - 4.30) > 0.02:
        fail(f"现成双 U 形卡包络错误: bounds={clip_bounds!r}")

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
        f"triggerCarrier=M5x{carrier_magnet_length:.2f}/2pins "
        f"axisSeating=outerRollers:{roller_count}/bushings:{roller_count}/"
        f"pins:{pin_components}/ringComponents:{roller_ring_components} "
        f"maxAxisError={axis_error:.4f}mm"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
