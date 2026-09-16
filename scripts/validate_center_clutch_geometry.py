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
    "center_guide_rails",
    "center_stops",
    "center_mechanism_plate",
    "center_selector_shoe",
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
        fail(f"OpenSCAD 导出失败: {part} engaged={engaged}\n{detail}")


def run_collision_export(
    openscad: Path,
    scad: Path,
    output: Path,
) -> bool:
    """Export the actual plate/belt intersection and report whether it is empty."""
    command = [
        str(openscad),
        "--backend",
        "Manifold",
        "--export-format",
        "binstl",
        "-D",
        "QUALITY=2",
        "-D",
        'CLUTCH_PART="center_plate_belt_collision"',
        "-D",
        "ENGAGED=false",
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
        fail(f"中心机构板/皮带碰撞见证导出失败\n{detail}")
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
    return True


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
        "openGapMm": 0.60,
        "dogInsertionMm": 2.40,
        "strokeMm": 3.00,
        "pocketDepthMm": 3.25,
        "bottomClearanceMm": 0.85,
        "magnetNonContactClearanceMm": 0.40,
        "femaleMagnetProjectionMm": 0.45,
        "magnetNominalDiameterMm": 2.00,
        "selectorTriggerSpacingMm": 12.00,
        "guideRunningClearanceMm": 0.30,
        "bearingSeatDiameterMm": 6.10,
        "bearingSeatDepthMm": 2.60,
        "bearingBackShoulderMm": 0.60,
        "bearingReferenceCenterOffsetMm": -0.60,
        "bearingCenterOffsetMm": 4.20,
        "bearingPairSpacingMm": 4.00,
        "bearingBlockThicknessMm": 3.20,
        "guideRailWidthMm": 3.00,
        "guideRailHeightMm": 3.00,
        "guideRailXOffsetMm": 9.00,
        "guideRailZOffsetMm": 8.00,
        "captureShoeOuterMm": 5.20,
        "captureShoeLengthMm": 6.00,
        "carriageUprightCenterXOffsetMm": 6.40,
        "carriageUprightWidthMm": 2.40,
        "carriageUprightZ0Mm": 5.20,
        "carriageUprightHeightMm": 3.00,
        "carriageUprightY0Mm": -10.00,
        "carriageUprightLengthMm": 8.40,
        "plateKeyWidthMm": 4.00,
        "plateKeyHeightMm": 6.00,
        "plateKeyClearanceMm": 0.30,
        "plateM3ClearanceMm": 3.40,
        "plateBeltPassageHalfWidthMm": 5.61972,
        "plateBeltPassageAxialWidthMm": 6.90,
        "plateBeltPassageRadialClearanceMm": 0.45,
        "plateBeltPassageAxialClearanceMm": 0.45,
        "selectorShoeTangentOffsetMm": 6.00,
        "selectorShoeNormalOffsetMm": -6.50,
        "selectorShoeFrontClearanceMm": 0.70,
        "selectorShoeRearProjectionMm": 2.55,
        "inputShaftStartMm": -10.90,
        "inputShaftLengthMm": 13.90,
        "outputShaftStartMm": -3.40,
        "outputShaftLengthMm": 14.00,
        "inputGearBandThicknessMm": 3.20,
        "dBoreDepthMm": 3.00,
    }
    if contract.get("axis") != "+Y" or contract.get("role") != "input/output":
        fail("中心离合不是 +Y input/output 契约")
    if contract.get("actuation") != "permanent-magnet":
        fail("中心离合不是纯永磁动作契约")
    if contract.get("engageOnlyWhenStopped") is not True:
        fail("中心离合没有停稳接合门槛")
    if contract.get("releaseBeforeReturn") is not True:
        fail("中心离合没有释放后返回门槛")
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

    if number(contract, "captureShoeOuterMm") <= number(
        contract, "guideRailWidthMm"
    ) + 2 * number(contract, "guideRunningClearanceMm"):
        fail("捕获滑靴没有包住导轨运行间隙")
    capture_wall = (
        number(contract, "captureShoeOuterMm")
        - number(contract, "guideRailWidthMm")
        - 2 * number(contract, "guideRunningClearanceMm")
    ) / 2
    expect_at_least(capture_wall, 0.60, "捕获滑靴单侧实体壁厚")

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
    if contract.get("selectorShoeCoordinateFrame") != "native-world":
        fail("磁力靴必须使用原生世界坐标")
    if contract.get("selectorShoePart") != "cabinet-clutch/center_selector_shoe":
        fail("磁力靴零件 ID 不是原生中心离合零件")
    if number(contract, "selectorShoeTangentOffsetMm") != 6.0:
        fail("M_engage 选择指切向基准必须位于磁力靴中心前 6 mm")
    if number(contract, "selectorShoeFrontClearanceMm") < 0.70:
        fail("磁力靴到输入转子前侧间隙不足")

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
    rail_w = number(contract, "guideRailWidthMm")
    rail_x_offset = number(contract, "guideRailXOffsetMm")
    expect_close(
        rail_bounds["min"][0],
        axis_x - rail_x_offset - rail_w / 2,
        "左导轨外侧 X 基准",
    )
    expect_close(
        rail_bounds["max"][0],
        axis_x + rail_x_offset + rail_w / 2,
        "右导轨外侧 X 基准",
    )
    expect_close(rail_bounds["min"][1], rail_y0, "导轨下端 Y 基准")
    expect_close(rail_bounds["max"][1], rail_y1, "导轨上端 Y 基准")

    block_half_x = number(contract, "bearingBlockWidthMm") / 2
    rail_inner_clear = rail_x_offset - rail_w / 2 - block_half_x
    expect_at_least(rail_inner_clear, CLEARANCE_FLOOR_MM, "导轨到轴承块的横向净空")

    for engaged in (False, True):
        carriage = bounds(reports[("center_input_carriage", engaged)])
        if carriage["min"][1] < rail_y0 - TOLERANCE_MM:
            fail(f"滑架开/合位脱出导轨下端: engaged={engaged}")
        if carriage["max"][1] > rail_y1 + TOLERANCE_MM:
            fail(f"滑架开/合位脱出导轨上端: engaged={engaged}")
        expected_capture_min_x = axis_x - rail_x_offset - number(
            contract, "captureShoeOuterMm"
        ) / 2
        expected_capture_max_x = axis_x + rail_x_offset + number(
            contract, "captureShoeOuterMm"
        ) / 2
        if carriage["min"][0] > expected_capture_min_x + TOLERANCE_MM:
            fail(f"滑架没有覆盖左侧导轨捕获位置: engaged={engaged}")
        if carriage["max"][0] < expected_capture_max_x - TOLERANCE_MM:
            fail(f"滑架没有覆盖右侧导轨捕获位置: engaged={engaged}")

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
    for key in ("openStopY0Mm", "engagedStopY0Mm"):
        stop_y = number(contract, key)
        if stop_y < rail_y0 - TOLERANCE_MM or stop_y > rail_y1 + TOLERANCE_MM:
            fail(f"实体止挡超出导轨服务范围: {key}={stop_y}")


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

    # The carriage and input rotor are separate solids. Their Y gap is the
    # assembly clearance at both stops; it must not be consumed by the stroke.
    input_carriage_gap_open = input_open["min"][1] - carriage_open["max"][1]
    input_carriage_gap_engaged = input_engaged["min"][1] - carriage_engaged["max"][1]
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
    # checked so a misplaced one of the two references cannot hide in the set.
    bearing_ref_bounds = {
        "input": bounds(reports[("center_input_bearings", False)]),
        "output": bounds(reports[("center_output_bearings", False)]),
    }
    for role, base, sign in (("input", input_base, -1), ("output", output_base, 1)):
        centers = [
            base
            + sign * number(contract, "bearingCenterOffsetMm")
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
        expect_close(actual_min, expected_union_min, f"{role} 双轴承参考件最小 Y")
        expect_close(actual_max, expected_union_max, f"{role} 双轴承参考件最大 Y")

    # The native shoe is authored in the same world frame. Its square-marked
    # M_engage pocket is at axis X, while the complete shoe is offset +6 mm.
    shoe_center_x = (shoe["min"][0] + shoe["max"][0]) / 2
    shoe_center_y = (shoe["min"][1] + shoe["max"][1]) / 2
    expect_close(
        shoe_center_x,
        axis_x + number(contract, "selectorShoeTangentOffsetMm"),
        "原生磁力靴 X 基准",
    )
    expect_close(
        shoe_center_y,
        number(contract, "selectorShoeTargetYMm"),
        "原生磁力靴 Y 基准",
    )
    expect_close(
        shoe["min"][2],
        number(contract, "selectorShoeZMm")
        - number(contract, "selectorShoeRearProjectionMm"),
        "原生磁力靴最近后侧面 Z",
    )
    shoe_front_clearance = shoe["min"][2] - (
        axis_z + number(contract, "inputTipRadiusMm")
    )
    expect_at_least(
        shoe_front_clearance,
        number(contract, "selectorShoeFrontClearanceMm"),
        "磁力靴到输入公轮前侧净空",
    )
    expect_at_least(
        shoe["min"][1] - carriage_engaged["max"][1],
        CLEARANCE_FLOOR_MM,
        "合位磁力靴到滑架顶部净空",
    )
    expect_at_least(
        shoe["min"][2] - output["max"][2],
        CLEARANCE_FLOOR_MM,
        "磁力靴到输出母轮前侧净空",
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
        number(contract, "railY1Mm") - number(contract, "railY0Mm") + 2.0,
        "机构板服务高度",
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
        "shoeFrontClearance": shoe_front_clearance,
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

        collision_stl = temp_dir / "center_plate_belt_collision.stl"
        if run_collision_export(openscad, scad, collision_stl):
            fail("机构板与中心 2GT 皮带实际网格仍有交集")

        validate_sweep(contract, reports)
        metrics = validate_interference(contract, reports)

    print(
        "中心离合几何扫掠通过: "
        f"gap={metrics['openGap']:.2f}mm, "
        f"insertion={metrics['insertion']:.2f}mm, "
        f"stroke={metrics['stroke']:.2f}mm, "
        f"bottom={metrics['bottomClearance']:.2f}mm, "
        f"guide_clear={number(contract, 'guideRunningClearanceMm'):.2f}mm, "
        f"shoe_front={metrics['shoeFrontClearance']:.2f}mm, "
        f"upright_radial={metrics['uprightRadialClearance']:.2f}mm; "
        "输入/输出不漂移、轴承盲座、独立 D 轴、双导轨、实体止挡、原生磁力靴和机构板皮带通道均已检查"
    )
    print("实体轴承/磁铁装配、打印配合、低速负载和 20 次循环仍未验收")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
