#!/usr/bin/env python3
"""Validate the center clutch contract and its open-to-engaged geometry sweep.

This is an analytic/OpenSCAD geometry gate. It checks exported part bounds,
shared travel equations, hard-stop datums, axial retention, guide capture and
the radial clearance budget. It does not replace a printed fit test, bearing
installation, magnet-polarity check or the required 20-cycle physical test.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import json
import math
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

# ===== 分区：常量/配置 =====
MOVING_PARTS = (
    "center_input_rotor",
    "center_input_carriage",
    "center_input_shaft",
    "center_input_bearings",
    "center_linear_bearings",
    "center_linear_bearing_retainers",
)
FIXED_PARTS = (
    "center_output_rotor",
    "center_output_cage",
    "center_guide_rails",
    "center_stops",
    "center_mechanism_plate",
    "center_output_shaft",
    "center_output_bearings",
    "center_selector_shoe",
)
PRINTED_PARTS = {
    "center_input_rotor",
    "center_input_carriage",
    "center_output_rotor",
    "center_output_cage",
    "center_stops",
    "center_mechanism_plate",
    "center_selector_shoe",
    "center_linear_bearing_retainers",
}
TOLERANCE_MM = 0.02
CLEARANCE_FLOOR_MM = 0.45
BEARING_NOMINAL_WIDTH_MM = 2.00
BEARING_NOMINAL_OD_MM = 6.00

# ===== 分区：模型/类型 =====
Contract = dict[str, object]
Bounds = dict[str, list[float]]

# ===== 分区：私有成员 =====
def fail(message: str) -> None:
    raise RuntimeError(message)


def number(contract: Contract, key: str) -> float:
    value = contract.get(key)
    if not isinstance(value, (int, float)):
        fail(f"契约数值字段无效: {key}={value!r}")
    return float(value)


def close(actual: float, expected: float, tolerance: float = TOLERANCE_MM) -> bool:
    return abs(actual - expected) <= tolerance


def expect_close(
    actual: float,
    expected: float,
    label: str,
    tolerance: float = TOLERANCE_MM,
) -> None:
    if not close(actual, expected, tolerance):
        fail(f"{label}: 实际={actual:.4f} mm, 期望={expected:.4f} mm")


def expect_at_least(actual: float, expected: float, label: str) -> None:
    if actual < expected - TOLERANCE_MM:
        fail(f"{label}: 实际={actual:.4f} mm, 需要至少={expected:.4f} mm")


def run_export(
    openscad: Path,
    scad: Path,
    output: Path,
    part: str,
    engaged: bool,
    travel_mm: float | None = None,
) -> None:
    command = [
        str(openscad),
        "--backend",
        "Manifold",
        "--export-format",
        "binstl",
        "-D",
        "QUALITY=2",
        "-D",
        f'CLUTCH_PART="{part}"',
        "-D",
        f"ENGAGED={'true' if engaged else 'false'}",
        "-D",
        (
            f"CENTER_CLUTCH_TRAVEL_MM={travel_mm:.6f}"
            if travel_mm is not None
            else "CENTER_CLUTCH_TRAVEL_MM="
            + ("3.000000" if engaged else "0.000000")
        ),
        "-D",
        "SELECTED_COLUMN=2",
        "-D",
        "SELECTED_ROW=2",
        "-D",
        "SHOW_LEGACY_STATIONS=false",
        "-o",
        str(output),
        str(scad),
    ]
    completed = subprocess.run(
        command,
        cwd=scad.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        detail = (completed.stderr or completed.stdout)[-3000:]
        fail(
            f"OpenSCAD 导出失败: {part} engaged={engaged} "
            f"travel={travel_mm}\n{detail}"
        )


INTERSECTION_VOLUME_TOLERANCE_MM3 = 0.01


def run_intersection_export(
    openscad: Path,
    scad: Path,
    output: Path,
    inspect_py: Path,
    part: str,
    engaged: bool,
    travel_mm: float | None = None,
) -> bool:
    """Export one actual CSG intersection and report positive solid volume."""
    command = [
        str(openscad),
        "--backend",
        "Manifold",
        "--export-format",
        "binstl",
        "-D",
        "QUALITY=2",
        "-D",
        f'CLUTCH_PART="{part}"',
        "-D",
        f"ENGAGED={'true' if engaged else 'false'}",
        "-D",
        (
            f"CENTER_CLUTCH_TRAVEL_MM={travel_mm:.6f}"
            if travel_mm is not None
            else "CENTER_CLUTCH_TRAVEL_MM="
            + ("3.000000" if engaged else "0.000000")
        ),
        "-D",
        "SELECTED_COLUMN=2",
        "-D",
        "SELECTED_ROW=2",
        "-D",
        "SHOW_LEGACY_STATIONS=false",
        "-o",
        str(output),
        str(scad),
    ]
    completed = subprocess.run(
        command,
        cwd=scad.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        if "Current top level object is empty" in (
            completed.stderr + completed.stdout
        ):
            return False
        detail = (completed.stderr or completed.stdout)[-3000:]
        fail(
            f"中心离合交集见证导出失败: {part} engaged={engaged} "
            f"travel={travel_mm}\n{detail}"
        )
    if not output.is_file() or output.stat().st_size == 0:
        return False
    raw = output.read_bytes()
    # OpenSCAD's binary STL has an 80-byte header and a little-endian triangle
    # count. Empty intersections may be emitted as no file or as an 84-byte
    # zero-triangle file; both are valid no-collision results.
    if len(raw) >= 84:
        triangle_count = struct.unpack_from("<I", raw, 80)[0]
        if triangle_count == 0:
            return False
    report = inspect(inspect_py, output)
    volume = report.get("volume")
    if not isinstance(volume, (int, float)):
        fail(f"中心离合交集见证缺少体积: {part} engaged={engaged}")
    # Exact face contact (for example, the carriage shoe against a hard stop)
    # may produce zero-area STL facets. It is a valid kinematic datum, not a
    # volume collision; only a positive solid intersection fails the gate.
    return abs(float(volume)) > INTERSECTION_VOLUME_TOLERANCE_MM3


def inspect(inspect_py: Path, stl: Path) -> dict[str, object]:
    completed = subprocess.run(
        ["python3", str(inspect_py), str(stl), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        fail(f"STL 检查失败: {stl.name}\n{completed.stdout}\n{completed.stderr}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        fail(f"STL 检查不是 JSON: {stl}: {exc}")


def bounds(report: dict[str, object]) -> Bounds:
    raw = report.get("bounds")
    if not isinstance(raw, dict):
        fail("STL 检查缺少 bounds")
    minimum = raw.get("min")
    maximum = raw.get("max")
    if not isinstance(minimum, list) or not isinstance(maximum, list):
        fail("STL bounds 格式无效")
    if len(minimum) != 3 or len(maximum) != 3:
        fail("STL bounds 必须有 XYZ 三个分量")
    return {
        "min": [float(value) for value in minimum],
        "max": [float(value) for value in maximum],
    }


def interval(report: dict[str, object], axis: int) -> tuple[float, float]:
    box = bounds(report)
    return box["min"][axis], box["max"][axis]


def assert_watertight(report: dict[str, object], label: str) -> None:
    if report.get("watertightByEdgeTopology") is not True:
        fail(f"{label} 不是闭合流形")


def validate_contract(contract: Contract) -> None:
    expected = {
        "centerClutchVerticalLiftMm": 5.00,
        "openGapMm": 0.60,
        "dogInsertionMm": 2.40,
        "strokeMm": 3.00,
        "pocketDepthMm": 3.25,
        "bottomClearanceMm": 0.85,
        "magnetNonContactClearanceMm": 0.40,
        "femaleMagnetProjectionMm": 0.45,
        "magnetNominalDiameterMm": 2.00,
        "dogPocketPhaseDeg": 60.00,
        "selectorTriggerSpacingMm": 12.00,
        "guideRodDiameterMm": 3.00,
        "guideRodCaptureMm": 0.80,
        "linearBearingNominalIdMm": 3.00,
        "linearBearingNominalOdMm": 7.00,
        "linearBearingNominalLengthMm": 10.00,
        "linearBearingCount": 1,
        "linearBearingCenterYOffsetMm": -24.50,
        "linearBearingSeatDiameterMm": 7.20,
        "linearBearingSeatDepthMm": 10.80,
        "linearBearingHolderOuterDiameterMm": 12.00,
        "linearBearingHolderLengthMm": 11.60,
        "linearBearingHolderBackShoulderMm": 0.80,
        "linearBearingHolderFrontNeckDiameterMm": 10.80,
        "linearBearingHolderFrontNeckLengthMm": 1.00,
        "linearBearingRetainerInnerDiameterMm": 6.40,
        "linearBearingRetainerOuterDiameterMm": 12.40,
        "linearBearingRetainerThicknessMm": 0.80,
        "linearBearingRetainerLipOuterDiameterMm": 7.00,
        "linearBearingRetainerSkirtInnerDiameterMm": 11.00,
        "linearBearingRetainerSkirtOuterDiameterMm": 11.60,
        "linearBearingRetainerSkirtLengthMm": 1.00,
        "linearBearingSeatRadialClearanceMm": 0.10,
        "linearBearingRodNominalClearanceMm": 0.00,
        "linearBearingFitCouponGuideCount": 1,
        "linearBearingFitCouponGuideXOffsetMm": 0.00,
        "bearingSeatDiameterMm": 6.10,
        "bearingSeatDepthMm": 2.60,
        "bearingBackShoulderMm": 0.60,
        "bearingReferenceCenterOffsetMm": -0.60,
        "bearingCenterOffsetMm": 4.20,
        "inputBearingCenterOffsetMm": 7.50,
        "bearingPairSpacingMm": 4.00,
        "bearingBlockThicknessMm": 3.20,
        "guideRailXOffsetMm": 0.00,
        "guideRailZOffsetMm": 0.00,
        "guideRodXOffsetMm": 0.00,
        "guideRodZOffsetMm": 0.00,
        "stopPadWidthMm": 4.00,
        "stopPadXOffsetMm": 0.60,
        "stopLugXOffsetMm": 10.00,
        "stopLugWidthMm": 3.00,
        "stopLugZOffsetMm": 5.00,
        "stopLugHeightMm": 2.00,
        "stopLugRouteXOffsetMm": 10.00,
        "stopLugRouteWidthMm": 0.80,
        "carriageUprightCenterXOffsetMm": 6.20,
        "carriageUprightWidthMm": 2.00,
        "carriageUprightZ0Mm": 5.20,
        "carriageUprightHeightMm": 3.00,
        "carriageUprightY0Mm": -30.60,
        "carriageUprightLengthMm": 25.00,
        "plateKeyWidthMm": 4.00,
        "plateKeyHeightMm": 6.00,
        "plateKeyClearanceMm": 0.30,
        "plateM3ClearanceMm": 3.40,
        "plateBeltPassageHalfWidthMm": 5.61972,
        "plateBeltPassageAxialWidthMm": 6.90,
        "plateBeltPassageRadialClearanceMm": 0.45,
        "plateBeltPassageAxialClearanceMm": 0.45,
        "selectorShoeTangentOffsetMm": 6.00,
        "selectorShoeNormalOffsetMm": -8.00,
        "selectorShoeTargetYMm": 141.00,
        "selectorShoeZMm": -82.2208,
        "selectorShoeAnchorXMm": 146.00,
        "selectorShoeAnchorYMm": 141.00,
        "selectorShoeAnchorZMm": -82.2208,
        "selectorShoeMagnetFaceOffsetMm": 1.00,
        "selectorShoeMagnetFaceYMm": 142.00,
        "selectorShoeTriggerClearanceMm": 0.40,
        "selectorShoeChainAttachYMm": 149.00,
        "selectorShoeChainAttachZMm": -75.00,
        "selectorShoeChainAttachXMm": 152.40,
        "selectorShoeChainContactDiameterMm": 2.40,
        "selectorShoeSupportXOffsetMm": 12.40,
        "selectorShoeSupportArmXOffsetMm": 0.80,
        "selectorShoeSupportXWidthMm": 2.40,
        "selectorShoeSupportChainYOverhangMm": 1.20,
        "selectorShoeSupportChainZT": 2.40,
        "selectorShoeSupportBridgeOverlapMm": 0.30,
        "selectorShoeSupportDropMm": 8.00,
        "selectorShoeSupportReachMm": 5.92084,
        "selectorShoeBodyWidthMm": 17.50,
        "selectorShoeBodyDepthMm": 5.60,
        "selectorShoeBodyHeightMm": 2.00,
        "selectorShoePocketRimHeightMm": 0.35,
        "inputShaftStartMm": -13.70,
        "inputShaftLengthMm": 16.70,
        "outputShaftStartMm": -3.40,
        "outputShaftLengthMm": 14.00,
        "inputGearBandThicknessMm": 3.20,
        "dBoreDepthMm": 3.00,
    }
    if contract.get("axis") != "+Y" or contract.get("role") != "input/output":
        fail("中心离合不是 +Y input/output 契约")
    if contract.get("verticalLayoutMode") != "center-clutch-lift":
        fail("中心离合没有使用整体上移的垂直布局")
    if contract.get("actuation") != "permanent-magnet":
        fail("中心离合不是纯永磁动作契约")
    if contract.get("engageOnlyWhenStopped") is not True:
        fail("中心离合没有停稳接合门槛")
    if contract.get("releaseBeforeReturn") is not True:
        fail("中心离合没有释放后返回门槛")
    if contract.get("selectorShoeCoordinateFrame") != "native-world":
        fail("磁力靴必须使用原生世界坐标")
    if contract.get("selectorShoeMagnetAxis") != "+Y":
        fail("磁力靴磁面必须朝世界 +Y")
    if contract.get("rotaryBearingArrangement") \
            != "two-per-rotor-axially-spaced":
        fail("转子旋转轴承必须是每个转子两枚、沿轴向分隔")
    if contract.get("linearBearingArrangement") \
            != "single-coaxial-with-male-rotor":
        fail("竖直直线轴承必须与公轮同轴且只配置一枚、单根导杆")
    if contract.get("linearBearingModel") != "LM3UU-cutaway-reference":
        fail("直线轴承采购参考必须是 LM3UU 可识别模型")
    if contract.get("linearBearingFitCouponPart") \
            != "cabinet-clutch/center_linear_bearing_fit_coupon":
        fail("直线轴承配合测试片零件 ID 不匹配")
    if contract.get("selectorShoeChainSupportPart") \
            != "cabinet-clutch/center_selector_chain_support_contact":
        fail("磁力靴必须包含链条支撑接触见证零件")
    if contract.get("selectorShoeLinearBearingCollisionPart") \
            != "cabinet-clutch/center_selector_linear_bearing_collision":
        fail("磁力靴必须包含单直线轴承路径干涉见证零件")
    for key, value in expected.items():
        actual = number(contract, key)
        if not close(actual, value, 0.001):
            fail(f"冻结值错误: {key}={actual}, 期望 {value}")

    if not close(
        number(contract, "strokeMm"),
        number(contract, "openGapMm") + number(contract, "dogInsertionMm"),
        0.001,
    ):
        fail("总行程不是开位间隙 + 有效插入")
    if not close(
        number(contract, "pocketDepthMm"),
        number(contract, "dogInsertionMm") + number(contract, "bottomClearanceMm"),
        0.001,
    ):
        fail("母槽深度不是有效插入 + 槽底余量")
    if not close(
        number(contract, "bottomClearanceMm"),
        number(contract, "femaleMagnetProjectionMm")
        + number(contract, "magnetNonContactClearanceMm"),
        0.001,
    ):
        fail("磁铁非接触余量不是由槽底余量推导")
    if not close(
        number(contract, "guideRodY1Mm"),
        number(contract, "engagedStopY0Mm")
        + number(contract, "linearBearingRetainerThicknessMm")
        + number(contract, "guideRodCaptureMm"),
        0.001,
    ):
        fail("合位导杆捕获端必须位于直线轴承压盖之后")
    if number(contract, "stopLugWidthMm") <= 0 or number(
        contract, "stopLugHeightMm"
    ) <= 0:
        fail("滑架独立硬止挡耳位尺寸无效")
    lug_x_min = number(contract, "stopLugXOffsetMm") \
        - number(contract, "stopLugWidthMm") / 2
    lug_x_max = number(contract, "stopLugXOffsetMm") \
        + number(contract, "stopLugWidthMm") / 2
    lug_low_z = number(contract, "stopLugZOffsetMm") \
        - number(contract, "stopLugHeightMm") / 2
    if math.hypot(lug_x_min, lug_low_z) \
            - number(contract, "inputTipRadiusMm") < 0.45 - 0.001:
        fail("侧向硬止挡耳位没有避开输入公轮径向包络")
    if lug_x_min <= 0:
        fail("滑架硬止挡耳位没有位于中心支撑外侧")
    route_inner_clearance = (
        number(contract, "stopLugRouteXOffsetMm")
        - number(contract, "stopLugRouteWidthMm") / 2
        - number(contract, "guideRailXOffsetMm")
        - number(contract, "linearBearingRetainerOuterDiameterMm") / 2
    )
    if route_inner_clearance < 0.30 - 0.001:
        fail("滑架硬止挡耳位外侧支撑没有避开直线轴承压盖")
    if not close(
        number(contract, "maleBottomYMm"), number(contract, "inputBaseYMm"), 0.001
    ):
        fail("公轮底部基准没有和输入公轮基准统一")
    if not close(
        number(contract, "selectorShoeMagnetFaceYMm")
        + number(contract, "selectorShoeTriggerClearanceMm"),
        number(contract, "maleBottomYMm"),
        0.001,
    ):
        fail("磁力靴磁面没有落在公轮底部下方的触发间隙")
    if not close(
        number(contract, "selectorShoeTargetYMm")
        + number(contract, "selectorShoeMagnetFaceOffsetMm"),
        number(contract, "selectorShoeMagnetFaceYMm"),
        0.001,
    ):
        fail("磁力靴磁面 Y 没有由锚点和面偏置推导")
    if number(contract, "bearingCountPerRotor") != 2:
        fail("每个转子必须配置两枚轴承")

    if number(contract, "bearingSeatDiameterMm") <= BEARING_NOMINAL_OD_MM:
        fail("轴承座没有给 3x6x2 外径留装配间隙")
    if number(contract, "bearingSeatDepthMm") < (
        BEARING_NOMINAL_WIDTH_MM + number(contract, "bearingBackShoulderMm")
    ):
        fail("轴承盲座深度不足")
    if number(contract, "bearingCenterOffsetMm") <= number(
        contract, "bearingBlockThicknessMm"
    ):
        fail("轴承中心偏置不足以让双轴承块脱离转子端面")
    if number(contract, "inputBearingCenterOffsetMm") <= number(
        contract, "bearingBlockThicknessMm"
    ):
        fail("输入转子轴承中心偏置不足以让拨叉通道脱离旋转轴承块")
    if number(contract, "bearingPairSpacingMm") < number(
        contract, "bearingBlockThicknessMm"
    ):
        fail("同轴双轴承间距不足以分隔两枚轴承块")
    if number(contract, "shaftCollarOdMm") <= BEARING_NOMINAL_OD_MM:
        fail("轴肩/挡圈外径不能捕获轴承")
    if number(contract, "shaftCollarBoreMm") <= number(contract, "shaftDiameterMm"):
        fail("轴肩/挡圈内孔不能通过 3 mm D 轴")

    input_end = number(contract, "inputShaftStartMm") + number(
        contract, "inputShaftLengthMm"
    )
    if not close(input_end, number(contract, "dBoreDepthMm"), 0.001):
        fail("输入 D 轴没有停在齿轮盲孔底基准")
    if number(contract, "dBoreDepthMm") > number(contract, "inputGearBandThicknessMm"):
        fail("输入 D 轴盲孔深度越过齿轮带厚度")
    if number(contract, "outputShaftLengthMm") <= number(contract, "dBoreDepthMm"):
        fail("输出 D 轴长度不足以穿过母轮盲孔和轴向保持段")

    center_distance = number(contract, "gearCenterDistanceMm")
    pitch_sum = number(contract, "longPitchRadiusMm") + number(
        contract, "inputPitchRadiusMm"
    )
    if not close(
        center_distance,
        pitch_sum + number(contract, "gearMeshClearanceMm"),
        0.001,
    ):
        fail("长花键与输入公轮中心距不是节圆半径 + 啮合余量")
    for key, label in (
        ("beltEnvelopeRadiusMm", "GT2 皮带背包络"),
        ("beltGuideRadiusMm", "GT2 皮带导向唇"),
        ("motherOuterRadiusMm", "母轮外壁"),
    ):
        clearance = center_distance - number(contract, "longTipRadiusMm") - number(
            contract, key
        )
        expect_at_least(clearance, CLEARANCE_FLOOR_MM, f"{label} 到长花键径向余量")

    if number(contract, "linearBearingCount") != 1:
        fail("中心滑架必须配置一枚与公轮同轴直线轴承")
    expect_close(
        number(contract, "linearBearingFitCouponGuideCount"),
        1.0,
        "直线轴承配合测试片导杆数量",
        0.001,
    )
    expect_close(
        number(contract, "linearBearingFitCouponGuideXOffsetMm"),
        0.0,
        "单导杆配合测试片中心 X 偏置",
        0.001,
    )
    expect_close(
        number(contract, "guideRodXOffsetMm"),
        number(contract, "guideRailXOffsetMm"),
        "导杆/导轨 X 偏置契约",
        0.001,
    )
    expect_close(
        number(contract, "guideRodZOffsetMm"),
        number(contract, "guideRailZOffsetMm"),
        "导杆/导轨 Z 偏置契约",
        0.001,
    )
    if abs(number(contract, "guideRodXOffsetMm")) > 0.001 \
            or abs(number(contract, "guideRodZOffsetMm")) > 0.001:
        fail("单导杆没有与公轮共享 X/Z 轴心")
    expect_close(
        number(contract, "linearBearingCenterYOffsetMm"),
        number(contract, "openTabY0Mm") - number(contract, "inputBaseYMm")
        + number(contract, "linearBearingHolderLengthMm") / 2,
        "单直线轴承 Y 中心由滑架承载窗口推导",
        0.001,
    )
    expect_close(
        number(contract, "linearBearingNominalIdMm"),
        number(contract, "guideRodDiameterMm"),
        "直线轴承名义内径与导杆直径",
        0.001,
    )
    if number(contract, "linearBearingNominalOdMm") <= number(
        contract, "linearBearingNominalIdMm"
    ):
        fail("直线轴承内外径关系无效")
    if number(contract, "linearBearingNominalLengthMm") <= 0:
        fail("直线轴承长度无效")
    expect_close(
        number(contract, "linearBearingSeatRadialClearanceMm"),
        (
            number(contract, "linearBearingSeatDiameterMm")
            - number(contract, "linearBearingNominalOdMm")
        ) / 2,
        "直线轴承座径向装配间隙",
        0.001,
    )
    if number(contract, "linearBearingSeatDiameterMm") <= number(
        contract, "linearBearingNominalOdMm"
    ):
        fail("直线轴承座没有给采购件外径留装配间隙")
    holder_wall = (
        number(contract, "linearBearingHolderOuterDiameterMm")
        - number(contract, "linearBearingSeatDiameterMm")
    ) / 2
    expect_at_least(holder_wall, 1.50, "直线轴承套单侧打印壁厚")
    if number(contract, "linearBearingSeatDepthMm") < (
        number(contract, "linearBearingHolderBackShoulderMm")
        + number(contract, "linearBearingNominalLengthMm")
    ):
        fail("直线轴承套座深度不足")
    if number(contract, "linearBearingHolderLengthMm") < (
        number(contract, "linearBearingHolderBackShoulderMm")
        + number(contract, "linearBearingNominalLengthMm")
        + number(contract, "linearBearingRetainerThicknessMm")
        - 0.001
    ):
        fail("直线轴承套长度不足以保留压盖空间")
    if number(contract, "linearBearingHolderFrontNeckDiameterMm") >= number(
        contract, "linearBearingHolderOuterDiameterMm"
    ):
        fail("直线轴承套前端定位颈无效")
    if not (
        number(contract, "linearBearingRetainerInnerDiameterMm")
        > number(contract, "guideRodDiameterMm")
        and number(contract, "linearBearingRetainerInnerDiameterMm")
        < number(contract, "linearBearingNominalOdMm")
    ):
        fail("直线轴承压盖孔不能同时通过导杆并捕获轴承")
    if number(contract, "linearBearingRetainerOuterDiameterMm") <= number(
        contract, "linearBearingHolderOuterDiameterMm"
    ):
        fail("直线轴承压盖没有覆盖轴承套前端")
    if number(contract, "linearBearingRetainerLipOuterDiameterMm") > number(
        contract, "linearBearingNominalOdMm"
    ):
        fail("直线轴承压盖内唇超出轴承外径")
    if number(contract, "linearBearingRetainerSkirtInnerDiameterMm") <= number(
        contract, "linearBearingHolderFrontNeckDiameterMm"
    ):
        fail("直线轴承压盖裙边没有避开前端定位颈")
    if not (
        number(contract, "linearBearingRetainerSkirtOuterDiameterMm")
        > number(contract, "linearBearingRetainerSkirtInnerDiameterMm")
        and number(contract, "linearBearingRetainerSkirtLengthMm")
        >= number(contract, "linearBearingHolderFrontNeckLengthMm")
    ):
        fail("直线轴承压盖裙边无效")
    if number(contract, "linearBearingRodNominalClearanceMm") < -0.001:
        fail("直线轴承与导杆的名义间隙为负")
    guide_rod_end = (
        number(contract, "linearBearingCenterYOffsetMm")
        + number(contract, "linearBearingHolderLengthMm") / 2
        + number(contract, "strokeMm")
        + number(contract, "linearBearingRetainerThicknessMm")
        + number(contract, "guideRodCaptureMm")
    )
    guide_to_input_shaft_clearance = (
        number(contract, "inputShaftStartMm") - guide_rod_end
    )
    expect_at_least(
        guide_to_input_shaft_clearance,
        0.40,
        "同轴导杆/轴承套扫掠到输入 D 轴的轴向净空",
    )

    if contract.get("plateSupport") != "partition-through-M3":
        fail("机构板承接界面不是隔板 M3 贯穿固定")
    if number(contract, "plateKeyClearanceMm") < 0.20:
        fail("机构板定位键装配间隙不足")
    if number(contract, "plateM3ClearanceMm") <= 3.0:
        fail("机构板 M3 贯穿孔没有留通孔间隙")
    expect_at_least(
        number(contract, "plateBeltPassageHalfWidthMm")
        - number(contract, "beltEnvelopeRadiusMm"),
        number(contract, "plateBeltPassageRadialClearanceMm") * 2,
        "机构板皮带通道横向净空",
    )
    expect_at_least(
        number(contract, "plateBeltPassageAxialWidthMm") - 6.0,
        number(contract, "plateBeltPassageAxialClearanceMm") * 2,
        "机构板皮带通道轴向净空",
    )
    if number(contract, "plateBeltPassageHalfWidthMm") >= number(
        contract, "plateWidthMm"
    ) / 2:
        fail("机构板皮带通道穿出机构板侧边")
    if contract.get("selectorShoePart") != "cabinet-clutch/center_selector_shoe":
        fail("磁力靴零件 ID 不是原生中心离合零件")
    if number(contract, "selectorShoeTangentOffsetMm") != 6.0:
        fail("M_engage 选择指切向基准必须位于磁力靴中心前 6 mm")
    if not close(
        number(contract, "selectorShoeAnchorXMm"),
        number(contract, "axisXMm") + 6.0,
        0.001,
    ):
        fail("磁力靴 M_engage 没有对准公轮轴心")
    if not close(
        number(contract, "selectorShoeAnchorYMm"),
        number(contract, "selectorShoeTargetYMm"),
        0.001,
    ) or not close(
        number(contract, "selectorShoeAnchorZMm"),
        number(contract, "selectorShoeZMm"),
        0.001,
    ):
        fail("磁力靴原生锚点没有和目标基准统一")
    if not close(
        number(contract, "selectorShoeChainAttachXMm"),
        number(contract, "axisXMm")
        + number(contract, "selectorShoeSupportXOffsetMm"),
        0.001,
    ):
        fail("磁力靴链条支撑 X 没有由轴心和支撑偏置推导")
    if number(contract, "selectorShoeChainContactDiameterMm") <= 0:
        fail("磁力靴链条支撑接触见证直径无效")
    if not close(number(contract, "selectorShoeChainAttachYMm"), 149.0, 0.001):
        fail("磁力靴链条支撑 Y 没有落在蛇链层")
    if not close(number(contract, "selectorShoeChainAttachZMm"), -75.0, 0.001):
        fail("磁力靴链条支撑 Z 没有落在蛇链层")
    if number(contract, "selectorShoeSupportXWidthMm") <= 0:
        fail("磁力靴链条支撑臂宽度无效")
    if number(contract, "selectorShoeSupportArmXOffsetMm") < 0:
        fail("磁力靴支撑臂导轨避让偏置不能为负")
    if number(contract, "selectorShoeSupportDropMm") <= 0 or number(
        contract, "selectorShoeSupportReachMm"
    ) <= 0:
        fail("磁力靴链条支撑臂没有连接到蛇链平面")

    inner_upright_x = number(contract, "carriageUprightCenterXOffsetMm") - number(
        contract, "carriageUprightWidthMm"
    ) / 2
    expected_upright_clearance = math.hypot(
        inner_upright_x, number(contract, "carriageUprightZ0Mm")
    ) - number(contract, "inputTipRadiusMm")
    expect_close(
        number(contract, "carriageUprightRadialClearanceMm"),
        expected_upright_clearance,
        "滑架立柱径向净空契约",
        0.001,
    )
    expect_at_least(
        number(contract, "carriageUprightRadialClearanceMm"),
        CLEARANCE_FLOOR_MM,
        "滑架立柱到输入转子径向净空",
    )


def validate_sweep(
    contract: Contract,
    reports: dict[tuple[str, bool], dict[str, object]],
) -> None:
    stroke = number(contract, "strokeMm")
    rail_y0 = number(contract, "railY0Mm")
    rail_y1 = number(contract, "railY1Mm")
    if rail_y1 - rail_y0 <= stroke:
        fail("导轨有效长度不足以覆盖 3 mm 行程")

    for part in MOVING_PARTS:
        open_bounds = bounds(reports[(part, False)])
        engaged_bounds = bounds(reports[(part, True)])
        for axis, index in (("X", 0), ("Z", 2)):
            expect_close(
                engaged_bounds["min"][index],
                open_bounds["min"][index],
                f"{part} 在 {axis} 方向的最小值漂移",
            )
            expect_close(
                engaged_bounds["max"][index],
                open_bounds["max"][index],
                f"{part} 在 {axis} 方向的最大值漂移",
            )
        min_shift = engaged_bounds["min"][1] - open_bounds["min"][1]
        max_shift = engaged_bounds["max"][1] - open_bounds["max"][1]
        expect_close(min_shift, stroke, f"{part} 的 Y 最小值行程")
        expect_close(max_shift, stroke, f"{part} 的 Y 最大值行程")

    rail_bounds = bounds(reports[("center_guide_rails", False)])
    axis_x = number(contract, "axisXMm")
    axis_z = number(contract, "axisZMm")
    rail_x_offset = number(contract, "guideRailXOffsetMm")
    rail_z_offset = number(contract, "guideRailZOffsetMm")
    expect_close(
        rail_bounds["min"][0],
        axis_x + rail_x_offset - number(contract, "guideRodDiameterMm") / 2,
        "同轴导杆 X 下限",
    )
    expect_close(
        rail_bounds["max"][0],
        axis_x + rail_x_offset + number(contract, "guideRodDiameterMm") / 2,
        "同轴导杆 X 上限",
    )
    expect_close(
        rail_bounds["min"][2],
        axis_z + rail_z_offset - number(contract, "guideRodDiameterMm") / 2,
        "同轴导杆 Z 下限",
    )
    expect_close(
        rail_bounds["max"][2],
        axis_z + rail_z_offset + number(contract, "guideRodDiameterMm") / 2,
        "同轴导杆 Z 上限",
    )
    expect_close(
        rail_bounds["min"][1],
        number(contract, "guideRodY0Mm"),
        "导向杆捕获下端 Y 基准",
    )
    expect_close(
        rail_bounds["max"][1],
        number(contract, "guideRodY1Mm"),
        "导向杆捕获上端 Y 基准",
    )

    guide_rod_end = (
        number(contract, "linearBearingCenterYOffsetMm")
        + number(contract, "linearBearingHolderLengthMm") / 2
        + number(contract, "strokeMm")
        + number(contract, "linearBearingRetainerThicknessMm")
        + number(contract, "guideRodCaptureMm")
    )
    guide_to_input_shaft_clearance = (
        number(contract, "inputShaftStartMm") - guide_rod_end
    )
    expect_at_least(
        guide_to_input_shaft_clearance,
        0.40,
        "同轴导杆捕获端到输入 D 轴的轴向净空",
    )

    for engaged in (False, True):
        carriage = bounds(reports[("center_input_carriage", engaged)])
        shoe_y0 = number(contract, "openTabY0Mm") + (
            stroke if engaged else 0.0
        )
        shoe_y1 = number(contract, "openTabY1Mm") + (
            stroke if engaged else 0.0
        )
        if shoe_y0 < rail_y0 - TOLERANCE_MM:
            fail(f"滑架捕获滑靴开/合位脱出导轨下端: engaged={engaged}")
        if shoe_y1 > rail_y1 + TOLERANCE_MM:
            fail(f"滑架捕获滑靴开/合位脱出导轨上端: engaged={engaged}")
        holder_radius = number(contract, "linearBearingHolderOuterDiameterMm") / 2
        expected_capture_min_x = axis_x + rail_x_offset - holder_radius
        expected_capture_max_x = axis_x + rail_x_offset + holder_radius
        expected_capture_min_z = axis_z + rail_z_offset - holder_radius
        expected_capture_max_z = axis_z + rail_z_offset + holder_radius
        if carriage["min"][0] > expected_capture_min_x + TOLERANCE_MM:
            fail(f"滑架没有覆盖同轴导杆 X 捕获位置: engaged={engaged}")
        if carriage["max"][0] < expected_capture_max_x - TOLERANCE_MM:
            fail(f"滑架没有覆盖同轴导杆 X 捕获位置: engaged={engaged}")
        if carriage["min"][2] > expected_capture_min_z + TOLERANCE_MM:
            fail(f"滑架没有覆盖同轴导杆 Z 捕获位置: engaged={engaged}")
        if carriage["max"][2] < expected_capture_max_z - TOLERANCE_MM:
            fail(f"滑架没有覆盖同轴导杆 Z 捕获位置: engaged={engaged}")

        linear_bearing = bounds(reports[("center_linear_bearings", engaged)])
        bearing_center_y = number(contract, "inputBaseYMm") \
            + number(contract, "linearBearingCenterYOffsetMm") \
            + (stroke if engaged else 0.0)
        expect_close(
            linear_bearing["min"][0],
            axis_x + rail_x_offset
            - number(contract, "linearBearingNominalOdMm") / 2,
            f"直线轴承 {('合位' if engaged else '开位')} X 下限",
        )
        expect_close(
            linear_bearing["max"][0],
            axis_x + rail_x_offset
            + number(contract, "linearBearingNominalOdMm") / 2,
            f"直线轴承 {('合位' if engaged else '开位')} X 上限",
        )
        expect_close(
            linear_bearing["min"][1],
            bearing_center_y - number(contract, "linearBearingNominalLengthMm") / 2,
            f"直线轴承 {('合位' if engaged else '开位')} Y 下限",
        )
        expect_close(
            linear_bearing["max"][1],
            bearing_center_y + number(contract, "linearBearingNominalLengthMm") / 2,
            f"直线轴承 {('合位' if engaged else '开位')} Y 上限",
        )
        expect_close(
            linear_bearing["min"][2],
            axis_z + rail_z_offset
            - number(contract, "linearBearingNominalOdMm") / 2,
            f"直线轴承 {('合位' if engaged else '开位')} Z 下限",
        )
        expect_close(
            linear_bearing["max"][2],
            axis_z + rail_z_offset
            + number(contract, "linearBearingNominalOdMm") / 2,
            f"直线轴承 {('合位' if engaged else '开位')} Z 上限",
        )

        retainer = bounds(
            reports[("center_linear_bearing_retainers", engaged)]
        )
        holder_front_y = bearing_center_y + number(
            contract, "linearBearingHolderLengthMm"
        ) / 2
        expect_close(
            retainer["min"][0],
            axis_x + rail_x_offset
            - number(contract, "linearBearingRetainerOuterDiameterMm") / 2,
            f"直线轴承压盖 {('合位' if engaged else '开位')} X 下限",
        )
        expect_close(
            retainer["max"][0],
            axis_x + rail_x_offset
            + number(contract, "linearBearingRetainerOuterDiameterMm") / 2,
            f"直线轴承压盖 {('合位' if engaged else '开位')} X 上限",
        )
        expect_close(
            retainer["min"][1],
            holder_front_y
            - number(contract, "linearBearingRetainerSkirtLengthMm"),
            f"直线轴承压盖 {('合位' if engaged else '开位')} Y 下限",
        )
        expect_close(
            retainer["max"][1],
            holder_front_y + number(contract, "linearBearingRetainerThicknessMm"),
            f"直线轴承压盖 {('合位' if engaged else '开位')} Y 上限",
        )
        expect_close(
            retainer["min"][2],
            axis_z + rail_z_offset
            - number(contract, "linearBearingRetainerOuterDiameterMm") / 2,
            f"直线轴承压盖 {('合位' if engaged else '开位')} Z 下限",
        )
        expect_close(
            retainer["max"][2],
            axis_z + rail_z_offset
            + number(contract, "linearBearingRetainerOuterDiameterMm") / 2,
            f"直线轴承压盖 {('合位' if engaged else '开位')} Z 上限",
        )

    if not close(
        number(contract, "openStopY1Mm"), number(contract, "openTabY0Mm"), 0.001
    ):
        fail("开位止挡没有与滑架止挡片实体接触")
    if not close(
        number(contract, "engagedStopY0Mm"),
        number(contract, "engagedTabY1Mm"),
        0.001,
    ):
        fail("合位止挡没有与滑架止挡片实体接触")
    expect_close(
        number(contract, "openStopY1Mm"),
        rail_y0,
        "开位止挡与导轨下端的端面基准",
        0.001,
    )
    expect_close(
        number(contract, "engagedStopY0Mm"),
        rail_y1,
        "合位止挡与导轨上端的端面基准",
        0.001,
    )


def validate_intermediate_sweep(
    openscad: Path,
    scad: Path,
    inspect_path: Path,
    temp_dir: Path,
    contract: Contract,
    open_reports: dict[str, dict[str, object]],
) -> None:
    """Check real CSG witnesses and rigid-body travel between the two stops."""
    stroke = number(contract, "strokeMm")
    # Endpoint checks alone can miss a tooth flank, upright or shoe corner that
    # crosses another solid only while the carriage is moving. These three
    # quarter points are intentionally exported with a numeric OpenSCAD travel
    # override, not reconstructed from endpoint bounding boxes.
    intermediate_fractions = (0.25, 0.50, 0.75)
    collision_checks = (
        (
            "center_clutch_pair_collision",
            "公母离合轮在中间行程仍有实体交集",
        ),
        (
            "center_carriage_rail_collision",
            "滑架在中间行程与单根同轴导杆仍有实体交集",
        ),
        (
            "center_selector_linear_bearing_collision",
            "磁力靴在中间行程经过单直线轴承/轴承套时仍有实体交集",
        ),
        (
            "center_input_rotor_carriage_collision",
            "输入公轮在中间行程与整个滑架仍有实体交集",
        ),
        (
            "center_selector_male_collision",
            "磁力靴在中间行程与公轮仍有实体交集",
        ),
        (
            "center_stops_carriage_collision",
            "止挡在中间行程与滑架仍有实体穿插",
        ),
        (
            "center_stops_retainer_collision",
            "止挡在中间行程与直线轴承压盖仍有实体穿插",
        ),
    )
    for fraction in intermediate_fractions:
        travel = stroke * fraction
        for part in MOVING_PARTS:
            stl = temp_dir / f"{part}_travel_{travel:.3f}.stl"
            run_export(
                openscad,
                scad,
                stl,
                part,
                False,
                travel_mm=travel,
            )
            report = inspect(inspect_path, stl)
            if part in PRINTED_PARTS:
                assert_watertight(report, stl.name)
            current = bounds(report)
            opened = bounds(open_reports[part])
            for axis, index in (("X", 0), ("Z", 2)):
                expect_close(
                    current["min"][index],
                    opened["min"][index],
                    f"{part} 在中间行程 {travel:.2f} mm 的 {axis} 最小值漂移",
                )
                expect_close(
                    current["max"][index],
                    opened["max"][index],
                    f"{part} 在中间行程 {travel:.2f} mm 的 {axis} 最大值漂移",
                )
            expect_close(
                current["min"][1] - opened["min"][1],
                travel,
                f"{part} 在中间行程 {travel:.2f} mm 的 Y 最小值位移",
            )
            expect_close(
                current["max"][1] - opened["max"][1],
                travel,
                f"{part} 在中间行程 {travel:.2f} mm 的 Y 最大值位移",
            )

        for part, message in collision_checks:
            witness = temp_dir / f"{part}_travel_{travel:.3f}_collision.stl"
            if run_intersection_export(
                openscad,
                scad,
                witness,
                inspect_path,
                part,
                False,
                travel_mm=travel,
            ):
                fail(f"{message}: travel={travel:.2f} mm")


def validate_interference(
    contract: Contract,
    reports: dict[tuple[str, bool], dict[str, object]],
) -> dict[str, float]:
    input_open = bounds(reports[("center_input_rotor", False)])
    input_engaged = bounds(reports[("center_input_rotor", True)])
    output = bounds(reports[("center_output_rotor", False)])
    carriage_open = bounds(reports[("center_input_carriage", False)])
    carriage_engaged = bounds(reports[("center_input_carriage", True)])
    shoe = bounds(reports[("center_selector_shoe", False)])
    cage = bounds(reports[("center_output_cage", False)])
    input_shaft_open = bounds(reports[("center_input_shaft", False)])
    input_shaft_engaged = bounds(reports[("center_input_shaft", True)])
    output_shaft = bounds(reports[("center_output_shaft", False)])

    axis_x = number(contract, "axisXMm")
    axis_z = number(contract, "axisZMm")
    expect_close(
        (input_open["min"][0] + input_open["max"][0]) / 2,
        axis_x,
        "输入公轮轴心 X",
    )
    expect_close(
        (output["min"][0] + output["max"][0]) / 2,
        axis_x,
        "输出母轮轴心 X",
    )
    expect_close(
        (input_open["min"][2] + input_open["max"][2]) / 2,
        axis_z,
        "输入公轮轴心 Z",
    )
    expect_close(
        (output["min"][2] + output["max"][2]) / 2,
        axis_z,
        "输出母轮轴心 Z",
    )

    input_base = number(contract, "inputBaseYMm")
    output_base = number(contract, "outputBaseYMm")
    expect_close(input_open["min"][1], input_base, "输入公轮基准 Y")
    expect_close(
        input_engaged["min"][1],
        input_base + number(contract, "strokeMm"),
        "输入公轮合位基准 Y",
    )
    expect_close(output["max"][1], output_base, "输出母轮基准 Y")

    open_gap = output["min"][1] - input_open["max"][1]
    insertion = input_engaged["max"][1] - output["min"][1]
    actual_stroke = input_engaged["max"][1] - input_open["max"][1]
    pocket_bottom_clearance = (
        output["min"][1]
        + number(contract, "pocketDepthMm")
        - input_engaged["max"][1]
    )
    expect_close(open_gap, number(contract, "openGapMm"), "公母轮开位间隙")
    expect_close(insertion, number(contract, "dogInsertionMm"), "公牙合位有效插入")
    expect_close(actual_stroke, number(contract, "strokeMm"), "公轮实际总行程")
    expect_close(
        pocket_bottom_clearance,
        number(contract, "bottomClearanceMm"),
        "合位槽底余量",
    )

    # The single long linear-bearing holder sits radially below the male rotor,
    # so its Y projection is not an axial gap to the coaxial rotor. Measure the
    # central rotary support envelope here; the rotor-vs-whole-carriage CSG
    # witness below covers the radial holder/web envelope as well.
    central_carriage_max_y = input_base + max(
        number(contract, "carriageUprightY0Mm")
        + number(contract, "carriageUprightLengthMm"),
        -number(contract, "inputBearingCenterOffsetMm")
        + number(contract, "bearingBlockThicknessMm") / 2,
    )
    input_carriage_gap_open = input_open["min"][1] - central_carriage_max_y
    input_carriage_gap_engaged = (
        input_engaged["min"][1]
        - (central_carriage_max_y + number(contract, "strokeMm"))
    )
    expect_at_least(
        input_carriage_gap_open,
        CLEARANCE_FLOOR_MM,
        "开位滑架到输入公轮轴向净空",
    )
    expect_at_least(
        input_carriage_gap_engaged,
        CLEARANCE_FLOOR_MM,
        "合位滑架到输入公轮轴向净空",
    )

    cage_rotor_gap = cage["min"][1] - output["max"][1]
    expect_at_least(
        cage_rotor_gap,
        CLEARANCE_FLOOR_MM,
        "输出母轮到固定轴承笼的轴向净空",
    )

    # The two independent D shafts must not become one continuous rod through
    # the clutch. Check the exported reference intervals in both carriage
    # states, not just the nominal shaft lengths in the contract.
    shaft_gap_open = output_shaft["min"][1] - input_shaft_open["max"][1]
    shaft_gap_engaged = output_shaft["min"][1] - input_shaft_engaged["max"][1]
    expect_at_least(shaft_gap_open, CLEARANCE_FLOOR_MM, "开位两根独立 D 轴之间净空")
    expect_at_least(shaft_gap_engaged, CLEARANCE_FLOOR_MM, "合位两根独立 D 轴之间净空")

    input_shaft_start = input_base + number(contract, "inputShaftStartMm")
    input_shaft_end = input_base + number(contract, "dBoreDepthMm")
    output_shaft_start = output_base + number(contract, "outputShaftStartMm")
    output_shaft_end = output_shaft_start + number(contract, "outputShaftLengthMm")
    expect_close(input_shaft_open["min"][1], input_shaft_start, "输入 D 轴开位起点")
    expect_close(input_shaft_open["max"][1], input_shaft_end, "输入 D 轴盲孔止点")
    expect_close(
        input_shaft_engaged["min"][1],
        input_shaft_start + number(contract, "strokeMm"),
        "输入 D 轴合位起点",
    )
    expect_close(
        input_shaft_engaged["max"][1],
        input_shaft_end + number(contract, "strokeMm"),
        "输入 D 轴合位止点",
    )
    expect_close(output_shaft["min"][1], output_shaft_start, "输出 D 轴起点")
    expect_close(output_shaft["max"][1], output_shaft_end, "输出 D 轴终点")
    if number(contract, "inputShaftStartMm") >= 0:
        fail("输入 D 轴没有从齿轮背面进入")
    if number(contract, "outputShaftStartMm") >= 0:
        fail("输出 D 轴没有覆盖母轮背面盲孔")

    # Each purchased bearing reference must remain inside its own blind seat,
    # with the 0.60 mm rear shoulder left behind it. The union bounds are also
    # checked so a misplaced reference cannot hide in the set.
    bearing_ref_bounds = {
        "input": bounds(reports[("center_input_bearings", False)]),
        "output": bounds(reports[("center_output_bearings", False)]),
    }
    for role, base, sign, center_offset in (
        ("input", input_base, -1, number(contract, "inputBearingCenterOffsetMm")),
        ("output", output_base, 1, number(contract, "bearingCenterOffsetMm")),
    ):
        centers = [
            base
            + sign * center_offset
            + sign * index * number(contract, "bearingPairSpacingMm")
            for index in (0, 1)
        ]
        expected_union_min = math.inf
        expected_union_max = -math.inf
        for index, center in enumerate(centers):
            seat_min = center - number(contract, "bearingBlockThicknessMm") / 2
            seat_max = seat_min + number(contract, "bearingSeatDepthMm")
            reference_center = center + number(
                contract, "bearingReferenceCenterOffsetMm"
            )
            reference_min = reference_center - BEARING_NOMINAL_WIDTH_MM / 2
            reference_max = reference_center + BEARING_NOMINAL_WIDTH_MM / 2
            if reference_min < seat_min - TOLERANCE_MM or reference_max > seat_max + TOLERANCE_MM:
                fail(
                    f"{role} 轴承 {index} 不在盲座内: "
                    f"ref=[{reference_min:.3f},{reference_max:.3f}] "
                    f"seat=[{seat_min:.3f},{seat_max:.3f}]"
                )
            expected_union_min = min(expected_union_min, reference_min)
            expected_union_max = max(expected_union_max, reference_max)
        actual_min = bearing_ref_bounds[role]["min"][1]
        actual_max = bearing_ref_bounds[role]["max"][1]
        expect_close(actual_min, expected_union_min, f"{role} 轴承参考件最小 Y")
        expect_close(actual_max, expected_union_max, f"{role} 轴承参考件最大 Y")

    # One purchased linear bearing travels with the input carriage on the
    # single Ø3 guide rod coaxial with and behind the male rotor. The holder/cap geometry is
    # checked separately so the intentional bearing-to-rod interface is never
    # mislabeled as a solid collision.
    linear_bearing_ref = bounds(
        reports[("center_linear_bearings", False)]
    )
    linear_bearing_retainer = bounds(
        reports[("center_linear_bearing_retainers", False)]
    )
    linear_center_y = number(contract, "inputBaseYMm") \
        + number(contract, "linearBearingCenterYOffsetMm")
    expected_linear_min_y = linear_center_y - number(
        contract, "linearBearingNominalLengthMm"
    ) / 2
    expected_linear_max_y = linear_center_y + number(
        contract, "linearBearingNominalLengthMm"
    ) / 2
    expect_close(
        linear_bearing_ref["min"][1],
        expected_linear_min_y,
        "开位直线轴承参考件最小 Y",
    )
    expect_close(
        linear_bearing_ref["max"][1],
        expected_linear_max_y,
        "开位直线轴承参考件最大 Y",
    )
    expect_close(
        linear_bearing_retainer["min"][1],
        number(contract, "openTabY1Mm")
        - number(contract, "linearBearingRetainerSkirtLengthMm"),
        "开位直线轴承压盖最小 Y",
    )
    expect_close(
        linear_bearing_retainer["max"][1],
        number(contract, "openTabY1Mm")
        + number(contract, "linearBearingRetainerThicknessMm"),
        "开位直线轴承压盖最大 Y",
    )
    expect_close(
        linear_bearing_ref["min"][0],
        axis_x + number(contract, "guideRailXOffsetMm")
        - number(contract, "linearBearingNominalOdMm") / 2,
        "开位直线轴承 X 下限",
    )
    expect_close(
        linear_bearing_ref["max"][0],
        axis_x + number(contract, "guideRailXOffsetMm")
        + number(contract, "linearBearingNominalOdMm") / 2,
        "开位直线轴承 X 上限",
    )
    expect_close(
        linear_bearing_ref["min"][2],
        number(contract, "axisZMm") + number(contract, "guideRailZOffsetMm")
        - number(contract, "linearBearingNominalOdMm") / 2,
        "开位直线轴承 Z 下限",
    )
    expect_close(
        linear_bearing_ref["max"][2],
        number(contract, "axisZMm") + number(contract, "guideRailZOffsetMm")
        + number(contract, "linearBearingNominalOdMm") / 2,
        "开位直线轴承 Z 上限",
    )

    # The native shoe is authored in the same world frame. Its square-marked
    # M_engage pocket is at axis X, while the body is offset +6 mm. The STL
    # also contains the chain support arm, so its overall Y/Z midpoint is not
    # a valid shoe anchor; use the explicit contract anchor instead.
    shoe_anchor_x = number(contract, "selectorShoeAnchorXMm")
    shoe_anchor_y = number(contract, "selectorShoeAnchorYMm")
    shoe_anchor_z = number(contract, "selectorShoeAnchorZMm")
    expect_close(
        shoe_anchor_x,
        axis_x + number(contract, "selectorShoeTangentOffsetMm"),
        "原生磁力靴 X 锚点",
    )
    expect_close(
        shoe_anchor_y,
        number(contract, "selectorShoeTargetYMm"),
        "原生磁力靴 Y 锚点",
    )
    expect_close(
        shoe_anchor_z,
        number(contract, "selectorShoeZMm"),
        "原生磁力靴 Z 锚点",
    )
    shoe_body_half_w = number(contract, "selectorShoeBodyWidthMm") / 2
    shoe_body_half_d = number(contract, "selectorShoeBodyDepthMm") / 2
    shoe_body_half_h = number(contract, "selectorShoeBodyHeightMm") / 2
    expect_close(
        shoe["min"][0],
        shoe_anchor_x - shoe_body_half_w,
        "磁力靴本体最小 X",
    )
    expect_close(
        shoe["max"][0],
        shoe_anchor_x + shoe_body_half_w,
        "磁力靴本体最大 X",
    )
    expect_close(
        shoe["min"][1],
        shoe_anchor_y - shoe_body_half_h,
        "磁力靴本体最小 Y",
    )
    expect_close(
        shoe["max"][1],
        number(contract, "selectorShoeChainAttachYMm")
        + number(contract, "selectorShoeSupportChainYOverhangMm"),
        "磁力靴链条支撑 Y 上限",
    )
    expect_close(
        shoe["min"][2],
        shoe_anchor_z - shoe_body_half_d,
        "磁力靴本体最小 Z",
    )
    expect_close(
        shoe["max"][2],
        number(contract, "selectorShoeChainAttachZMm")
        + number(contract, "selectorShoeSupportChainZT") / 2,
        "磁力靴链条支撑 Z 上限",
    )
    shoe_trigger_gap = number(contract, "maleBottomYMm") - number(
        contract, "selectorShoeMagnetFaceYMm"
    )
    expect_close(
        shoe_trigger_gap,
        number(contract, "selectorShoeTriggerClearanceMm"),
        "磁力靴 M_engage 到公轮底部触发间隙",
    )
    support_min_x = number(contract, "selectorShoeChainAttachXMm") \
        + number(contract, "selectorShoeSupportArmXOffsetMm") \
        - number(contract, "selectorShoeSupportXWidthMm") / 2
    expect_at_least(
        support_min_x - output["max"][0],
        CLEARANCE_FLOOR_MM,
        "磁力靴支撑臂到输出母轮横向净空",
    )

    plate = bounds(reports[("center_mechanism_plate", False)])
    expect_close(
        (plate["min"][0] + plate["max"][0]) / 2,
        axis_x,
        "机构板 X 中心",
    )
    expect_close(
        plate["max"][0] - plate["min"][0],
        number(contract, "plateWidthMm"),
        "机构板总宽",
    )
    expect_close(
        plate["max"][1] - plate["min"][1],
        number(contract, "outputBaseYMm")
        - number(contract, "railY0Mm")
        + 11.0,
        "机构板服务高度（覆盖输出轴承笼）",
    )

    return {
        "openGap": open_gap,
        "insertion": insertion,
        "stroke": actual_stroke,
        "bottomClearance": pocket_bottom_clearance,
        "inputCarriageGapOpen": input_carriage_gap_open,
        "inputCarriageGapEngaged": input_carriage_gap_engaged,
        "cageRotorGap": cage_rotor_gap,
        "shaftGapOpen": shaft_gap_open,
        "shaftGapEngaged": shaft_gap_engaged,
        "shoeTriggerGap": shoe_trigger_gap,
        "uprightRadialClearance": number(
            contract, "carriageUprightRadialClearanceMm"
        ),
    }


# ===== 分区：公开 API =====
def main() -> int:
    parser = argparse.ArgumentParser(description="检查中心 R3C3 离合开合几何扫掠")
    parser.add_argument("--openscad", required=True, type=Path)
    parser.add_argument("--scad", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--inspect", required=True, type=Path)
    args = parser.parse_args()
    openscad = args.openscad.resolve()
    scad = args.scad.resolve()
    contract_path = args.contract.resolve()
    inspect_path = args.inspect.resolve()

    contract_payload = json.loads(contract_path.read_text(encoding="utf-8"))
    contract = contract_payload.get("centerClutch")
    if not isinstance(contract, dict):
        fail("contract JSON 缺少 centerClutch")
    validate_contract(contract)

    with tempfile.TemporaryDirectory(prefix="smartpartsdrawer-center-clutch-") as temp:
        temp_dir = Path(temp)
        reports: dict[tuple[str, bool], dict[str, object]] = {}
        for part in MOVING_PARTS:
            for engaged in (False, True):
                stl = temp_dir / f"{part}_{'engaged' if engaged else 'open'}.stl"
                run_export(openscad, scad, stl, part, engaged)
                report = inspect(inspect_path, stl)
                if part in PRINTED_PARTS:
                    assert_watertight(report, stl.name)
                reports[(part, engaged)] = report
        for part in FIXED_PARTS:
            stl = temp_dir / f"{part}_open.stl"
            run_export(openscad, scad, stl, part, False)
            report = inspect(inspect_path, stl)
            if part in PRINTED_PARTS:
                assert_watertight(report, stl.name)
            reports[(part, False)] = report

        # The printable cabinet is included in this gate so the partition
        # support cut stays in the same compile/export path as the plate.
        cabinet_stl = temp_dir / "cabinet_open.stl"
        run_export(openscad, scad, cabinet_stl, "cabinet", False)
        cabinet_report = inspect(inspect_path, cabinet_stl)
        assert_watertight(cabinet_report, cabinet_stl.name)

        # The fit coupon is a real printable test artifact, not part of the
        # installed mechanism. Keep it in this same OpenSCAD/inspection gate
        # so a changed holder or cap cannot silently invalidate the physical
        # smoothness check described in the build notes.
        coupon_stl = temp_dir / "center_linear_bearing_fit_coupon.stl"
        run_export(
            openscad,
            scad,
            coupon_stl,
            "center_linear_bearing_fit_coupon",
            False,
        )
        coupon_report = inspect(inspect_path, coupon_stl)
        assert_watertight(coupon_report, coupon_stl.name)
        coupon_box = bounds(coupon_report)
        expect_close(
            coupon_box["max"][0] - coupon_box["min"][0],
            44.4,
            "直线轴承配合测试片总宽",
            0.05,
        )
        expect_close(
            coupon_box["max"][1] - coupon_box["min"][1],
            34.0,
            "直线轴承配合测试片导杆框长度",
            0.05,
        )

        intersection_checks = (
            (
                "center_plate_belt_collision",
                False,
                "center_plate_belt_collision.stl",
                "机构板与中心 2GT 皮带实际网格仍有交集",
            ),
            (
                "center_clutch_pair_collision",
                False,
                "center_clutch_pair_collision_open.stl",
                "公母离合轮开位仍有实体交集",
            ),
            (
                "center_clutch_pair_collision",
                True,
                "center_clutch_pair_collision_engaged.stl",
                "公母离合轮合位仍有实体交集",
            ),
            (
                "center_selector_linear_bearing_collision",
                False,
                "center_selector_linear_bearing_collision_open.stl",
                "磁力靴开位与单直线轴承/轴承套仍有实体交集",
            ),
            (
                "center_selector_linear_bearing_collision",
                True,
                "center_selector_linear_bearing_collision_engaged.stl",
                "磁力靴合位与单直线轴承/轴承套仍有实体交集",
            ),
            (
                "center_selector_male_collision",
                False,
                "center_selector_male_collision_open.stl",
                "磁力靴开位与公轮仍有实体交集",
            ),
            (
                "center_selector_male_collision",
                True,
                "center_selector_male_collision_engaged.stl",
                "磁力靴合位与公轮仍有实体交集",
            ),
            (
                "center_carriage_rail_collision",
                False,
                "center_carriage_rail_collision_open.stl",
                "滑架开位与单根同轴导杆仍有实体交集",
            ),
            (
                "center_carriage_rail_collision",
                True,
                "center_carriage_rail_collision_engaged.stl",
                "滑架合位与单根同轴导杆仍有实体交集",
            ),
            (
                "center_input_rotor_carriage_collision",
                False,
                "center_input_rotor_carriage_collision_open.stl",
                "输入公轮开位与整个滑架仍有实体交集",
            ),
            (
                "center_input_rotor_carriage_collision",
                True,
                "center_input_rotor_carriage_collision_engaged.stl",
                "输入公轮合位与整个滑架仍有实体交集",
            ),
            (
                "center_stops_carriage_collision",
                False,
                "center_stops_carriage_collision_open.stl",
                "开位止挡与滑架仍有实体穿插",
            ),
            (
                "center_stops_carriage_collision",
                True,
                "center_stops_carriage_collision_engaged.stl",
                "合位止挡与滑架仍有实体穿插",
            ),
            (
                "center_stops_retainer_collision",
                False,
                "center_stops_retainer_collision_open.stl",
                "开位止挡与直线轴承压盖仍有实体穿插",
            ),
            (
                "center_stops_retainer_collision",
                True,
                "center_stops_retainer_collision_engaged.stl",
                "合位止挡与直线轴承压盖仍有实体穿插",
            ),
            (
                "center_guide_stop_collision",
                False,
                "center_guide_stop_collision.stl",
                "单根同轴导杆与端部止挡支座仍有实体穿插",
            ),
        )
        for part, engaged, filename, message in intersection_checks:
            if run_intersection_export(
                openscad,
                scad,
                temp_dir / filename,
                inspect_path,
                part,
                engaged,
            ):
                fail(message)

        # Unlike the collision witnesses above, the chain-support witness must
        # contain a positive solid: the printed shoe arm has to reach the
        # authored R3C3 chain pin datum instead of merely passing nearby.
        contact_witness = temp_dir / "center_selector_chain_support_contact.stl"
        if not run_intersection_export(
            openscad,
            scad,
            contact_witness,
            inspect_path,
            "center_selector_chain_support_contact",
            False,
        ):
            fail("磁力靴链条支撑接触见证没有正体积")

        open_reports = {
            part: reports[(part, False)] for part in MOVING_PARTS
        }
        validate_intermediate_sweep(
            openscad,
            scad,
            inspect_path,
            temp_dir,
            contract,
            open_reports,
        )
        validate_sweep(contract, reports)
        metrics = validate_interference(contract, reports)

    print(
        "中心离合几何扫掠通过: "
        f"gap={metrics['openGap']:.2f}mm, "
        f"insertion={metrics['insertion']:.2f}mm, "
        f"stroke={metrics['stroke']:.2f}mm, "
        f"bottom={metrics['bottomClearance']:.2f}mm, "
        f"linear_bearing=Ø{number(contract, 'linearBearingNominalOdMm'):.2f}"
        f"/{number(contract, 'linearBearingNominalLengthMm'):.2f}mm, "
        f"seat_radial_clear={number(contract, 'linearBearingSeatRadialClearanceMm'):.2f}mm, "
        f"shoe_trigger_gap={metrics['shoeTriggerGap']:.2f}mm, "
        f"upright_radial={metrics['uprightRadialClearance']:.2f}mm; "
        "输入/输出不漂移、轴承盲座、独立 D 轴、单根同轴导杆、实体止挡、原生磁力靴路径和机构板皮带通道均已检查"
    )
    print("实体轴承/磁铁装配、打印配合、低速负载和 20 次循环仍未验收")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
