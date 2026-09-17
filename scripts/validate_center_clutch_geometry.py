#!/usr/bin/env python3
"""检查中心 R3C3 离合的 OpenSCAD 几何扫掠与采购件接口。

这是导出/解析层的几何门槛，不等同于打印配合、磁铁极性、低速负载或
20 次实体循环验收。
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

# ===== 分区：常量/配置 =====
MOVING_PARTS = (
    "center_input_rotor",
    "center_input_shaft",
    "center_input_sleeve",
    "center_input_sleeve_magnet",
)
FIXED_PARTS = (
    "center_output_rotor",
    "center_output_cage",
    "center_linear_bearings",
    "center_mechanism_plate",
    "center_output_shaft",
    "center_output_bearings",
)
PRINTED_PARTS = {
    "center_input_rotor",
    "center_output_rotor",
    "center_output_cage",
    "center_mechanism_plate",
    "center_input_sleeve",
}
TOLERANCE_MM = 0.02
CLEARANCE_FLOOR_MM = 0.45
INTERSECTION_VOLUME_TOLERANCE_MM3 = 0.01

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


def open_scad_command(
    openscad: Path,
    scad: Path,
    output: Path,
    part: str,
    engaged: bool,
    travel_mm: float | None = None,
) -> list[str]:
    travel = travel_mm if travel_mm is not None else (3.0 if engaged else 0.0)
    return [
        str(openscad),
        "--backend", "Manifold", "--export-format", "binstl",
        "-D", "QUALITY=2", "-D", f'CLUTCH_PART="{part}"',
        "-D", f"ENGAGED={'true' if engaged else 'false'}",
        "-D", f"CENTER_CLUTCH_TRAVEL_MM={travel:.6f}",
        "-D", "SELECTED_COLUMN=2", "-D", "SELECTED_ROW=2",
        "-D", "SHOW_LEGACY_STATIONS=false", "-o", str(output), str(scad),
    ]


def run_export(
    openscad: Path,
    scad: Path,
    output: Path,
    part: str,
    engaged: bool,
    travel_mm: float | None = None,
) -> None:
    completed = subprocess.run(
        open_scad_command(openscad, scad, output, part, engaged, travel_mm),
        cwd=scad.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        detail = (completed.stderr or completed.stdout)[-3000:]
        fail(
            f"OpenSCAD 导出失败: {part} engaged={engaged} travel={travel_mm}\n{detail}"
        )


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


def assert_watertight(report: dict[str, object], label: str) -> None:
    if report.get("watertightByEdgeTopology") is not True:
        fail(f"{label} 不是闭合流形")


def run_intersection_export(
    openscad: Path,
    scad: Path,
    output: Path,
    inspect_py: Path,
    part: str,
    engaged: bool,
    travel_mm: float | None = None,
) -> bool:
    completed = subprocess.run(
        open_scad_command(openscad, scad, output, part, engaged, travel_mm),
        cwd=scad.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = completed.stdout + completed.stderr
    if completed.returncode != 0 and "Current top level object is empty" not in combined:
        fail(f"交集见证导出失败: {part} travel={travel_mm}\n{combined[-3000:]}")
    if not output.is_file() or output.stat().st_size < 84:
        return False
    raw = output.read_bytes()
    triangles = struct.unpack_from("<I", raw, 80)[0]
    if triangles == 0:
        return False
    report = inspect(inspect_py, output)
    volume = report.get("volume")
    if not isinstance(volume, (int, float)):
        fail(f"交集见证缺少体积: {part} travel={travel_mm}")
    return abs(float(volume)) > INTERSECTION_VOLUME_TOLERANCE_MM3


def validate_contract(contract: Contract) -> None:
    if contract.get("axis") != "+Y" or contract.get("role") != "input/output":
        fail("中心离合不是 +Y input/output 契约")
    if contract.get("verticalLayoutMode") != "center-clutch-lift":
        fail("中心离合没有使用整体上移布局")
    if contract.get("actuation") != "permanent-magnet":
        fail("中心离合不是纯永磁动作契约")
    if contract.get("engageOnlyWhenStopped") is not True:
        fail("中心离合没有停稳接合门槛")
    if contract.get("releaseBeforeReturn") is not True:
        fail("中心离合没有释放后返回门槛")
    if contract.get("inputSideAdditionalMechanism") != "none":
        fail("公轮端仍声明存在其他机构")
    if contract.get("linearBearingMovesWithInput") is not False:
        fail("固定长方条 LM3UU 不能随公轮移动")
    if contract.get("inputShaftProfile") != "D-round-D":
        fail("公轮轴截面必须是 D-round-D")
    if contract.get("linearBearingModel") != "LM3UU-cutaway-reference":
        fail("直线轴承采购参考不是 LM3UU")
    if contract.get("linearBearingBlockMount") != "mechanism-plate-integral-press-fit":
        fail("直线轴承座必须与机构板一体成型并采用压入固定")
    if contract.get("linearBearingArrangement") != "single-coaxial-with-integrated-seat":
        fail("直线轴承必须是固定座内的公轮同轴单枚配置")
    if contract.get("rotaryBearingArrangement") != "output-two-3x6x2-axially-spaced-input-free":
        fail("当前公轮端不应残留输入旋转轴承组")

    for key, expected in {
        "openGapMm": 0.60, "dogInsertionMm": 2.40, "strokeMm": 3.00,
        "pocketDepthMm": 3.25, "bottomClearanceMm": 0.85,
        "magnetNonContactClearanceMm": 0.40, "femaleMagnetProjectionMm": 0.45,
        "linearBearingNominalIdMm": 3.00, "linearBearingNominalOdMm": 7.00,
        "linearBearingNominalLengthMm": 10.00, "linearBearingSeatDiameterMm": 7.20,
        "linearBearingSeatRadialClearanceMm": 0.10,
        "linearBearingBlockWidthMm": 18.00, "linearBearingBlockYLengthMm": 14.00,
        "linearBearingBlockZLengthMm": 19.7208,
        "linearBearingBlockZMarginMm": 1.00,
        "linearBearingBlockMountHoleDiameterMm": 0.00,
        "linearBearingBlockMountHoleCount": 0.00,
        "linearBearingBlockMountXOffsetMm": 0.00,
        "linearBearingBlockMountYOffsetMm": 0.00,
        "linearBearingCenterYOffsetMm": -7.00,
        "inputShaftUpperDStartMm": -0.40,
        "inputShaftUpperDLengthMm": 3.60,
        "inputShaftRoundStartMm": -20.60,
        "inputShaftRoundLengthMm": 20.40,
        "inputShaftLowerDStartMm": -20.40,
        "inputShaftLowerDLengthMm": 3.60,
        "inputSleeveTopOffsetMm": -17.00,
        "inputShaftRoundDiameterMm": 3.00,
        "inputSleeveMagnetNominalDiameterMm": 5.00,
        "inputSleeveMagnetNominalLengthMm": 5.00,
        "inputSleeveMagnetPocketDiameterMm": 5.20,
        "inputSleeveMagnetPocketDepthMm": 5.20,
    }.items():
        expect_close(number(contract, key), expected, f"冻结参数 {key}", 0.001)
    if number(contract, "centerCol") != 2 or number(contract, "centerRow") != 2:
        fail("当前几何必须锁定中心 R3C3")
    if abs(number(contract, "strokeMm") - number(contract, "openGapMm")
           - number(contract, "dogInsertionMm")) > 0.001:
        fail("stroke != openGap + dogInsertion")
    if abs(number(contract, "pocketDepthMm") - number(contract, "dogInsertionMm")
           - number(contract, "bottomClearanceMm")) > 0.001:
        fail("pocketDepth != insertion + bottomClearance")
    if abs(number(contract, "bottomClearanceMm")
           - number(contract, "femaleMagnetProjectionMm")
           - number(contract, "magnetNonContactClearanceMm")) > 0.001:
        fail("磁铁非接触余量推导不一致")

    if number(contract, "linearBearingBlockZLengthMm") <= number(contract, "linearBearingBlockZMarginMm"):
        fail("长方条轴承座没有从机构板延伸到公轮轴线")
    if number(contract, "linearBearingBlockWidthMm") <= number(contract, "linearBearingSeatDiameterMm") + 2.0:
        fail("长方条轴承孔周围壁厚不足")
    if number(contract, "linearBearingBlockYLengthMm") < number(contract, "linearBearingNominalLengthMm") + 2.0:
        fail("长方条 Y 向长度不足")
    if any(number(contract, key) != 0 for key in (
        "linearBearingBlockMountHoleCount",
        "linearBearingBlockMountHoleDiameterMm",
        "linearBearingBlockMountXOffsetMm",
        "linearBearingBlockMountYOffsetMm",
    )):
        fail("一体式 LM3UU 轴承座不得有座体 M3 固定孔")

    bearing_center = number(contract, "linearBearingCenterYOffsetMm")
    bearing_half = number(contract, "linearBearingNominalLengthMm") / 2
    round_start = number(contract, "inputShaftRoundStartMm")
    round_end = round_start + number(contract, "inputShaftRoundLengthMm")
    if round_start > bearing_center - bearing_half + 0.001:
        fail("圆滑动段开位没有穿过 LM3UU")
    if round_end + number(contract, "strokeMm") < bearing_center + bearing_half - 0.001:
        fail("圆滑动段合位没有穿过 LM3UU")
    upper_start = number(contract, "inputShaftUpperDStartMm")
    upper_end = upper_start + number(contract, "inputShaftUpperDLengthMm")
    lower_start = number(contract, "inputShaftLowerDStartMm")
    lower_end = lower_start + number(contract, "inputShaftLowerDLengthMm")
    if upper_end < 3.0 - 0.001:
        fail("上 D 段没有进入公轮盲孔深度")
    if round_end < upper_start - 0.001 or lower_start > round_end + 0.001 or lower_end < round_start - 0.001:
        fail("D-round-D 三段没有形成连续过渡")

    if number(contract, "inputSleeveDSocketDepthMm") > number(contract, "inputSleeveUpperDHeightMm"):
        fail("圆套上方 D 插孔超过上方 D 段")
    if number(contract, "inputSleeveDSocketDepthMm") > number(contract, "inputShaftLowerDLengthMm"):
        fail("下 D 轴段不足以插入圆套")
    bearing_y0 = number(contract, "linearBearingCenterYOffsetMm") - number(contract, "linearBearingBlockYLengthMm") / 2
    sleeve_open_top = number(contract, "inputSleeveTopOffsetMm")
    sleeve_engaged_top = sleeve_open_top + number(contract, "strokeMm")
    expect_close(sleeve_engaged_top, bearing_y0, "合位圆套上沿/一体轴承座下沿接触", 0.001)
    expect_close(bearing_y0 - sleeve_open_top, number(contract, "strokeMm"), "开位圆套/一体轴承座间隙", 0.001)
    sleeve_wall = (number(contract, "inputSleeveLowerRoundOuterDiameterMm")
                   - number(contract, "inputSleeveMagnetPocketDiameterMm")) / 2
    expect_at_least(sleeve_wall, 1.40, "M5 磁铁圆套单侧壁厚")
    expect_at_least(number(contract, "inputSleeveMagnetBottomClearanceMm"), 1.0, "M5 磁铁底部实体厚度")

    if number(contract, "bearingSeatDiameterMm") <= 6.0 or number(contract, "bearingSeatDepthMm") < number(contract, "bearingBackShoulderMm") + 2.0:
        fail("输出 3x6x2 轴承座尺寸不足")
    if number(contract, "shaftCollarOdMm") <= 6.0 or number(contract, "shaftCollarBoreMm") <= number(contract, "shaftDiameterMm"):
        fail("输出轴肩/挡圈不能同时捕获轴承并通过 D 轴")

    center_distance = number(contract, "gearCenterDistanceMm")
    expect_close(
        center_distance,
        number(contract, "longPitchRadiusMm")
        + number(contract, "inputPitchRadiusMm")
        + number(contract, "gearMeshClearanceMm"),
        "长花键/公轮中心距",
        0.001,
    )
    for key in ("beltEnvelopeRadiusMm", "beltGuideRadiusMm", "motherOuterRadiusMm"):
        expect_at_least(
            center_distance - number(contract, "longTipRadiusMm") - number(contract, key),
            CLEARANCE_FLOOR_MM,
            f"{key} 到长花键径向净空",
        )
    if number(contract, "plateBeltPassageHalfWidthMm") <= number(contract, "beltEnvelopeRadiusMm") or number(contract, "plateBeltPassageAxialWidthMm") <= 6.0:
        fail("机构板皮带贯穿槽尺寸不足")


def validate_sweep(contract: Contract, reports: dict[tuple[str, bool], dict[str, object]]) -> None:
    stroke = number(contract, "strokeMm")
    for part in MOVING_PARTS:
        opened = bounds(reports[(part, False)])
        engaged = bounds(reports[(part, True)])
        for axis, index in (("X", 0), ("Z", 2)):
            expect_close(engaged["min"][index], opened["min"][index], f"{part} {axis} 最小值漂移")
            expect_close(engaged["max"][index], opened["max"][index], f"{part} {axis} 最大值漂移")
        expect_close(engaged["min"][1] - opened["min"][1], stroke, f"{part} Y 最小值行程")
        expect_close(engaged["max"][1] - opened["max"][1], stroke, f"{part} Y 最大值行程")

    axis_x = number(contract, "axisXMm")
    axis_z = number(contract, "axisZMm")
    bearing = bounds(reports[("center_linear_bearings", False)])
    expect_close(bearing["min"][0], axis_x - 3.5, "LM3UU X 下限")
    expect_close(bearing["max"][0], axis_x + 3.5, "LM3UU X 上限")
    expect_close(bearing["min"][2], axis_z - 3.5, "LM3UU Z 下限")
    expect_close(bearing["max"][2], axis_z + 3.5, "LM3UU Z 上限")
    expected_center_y = number(contract, "linearBearingCenterYMm")
    expect_close(bearing["min"][1], expected_center_y - 5.0, "LM3UU Y 下限")
    expect_close(bearing["max"][1], expected_center_y + 5.0, "LM3UU Y 上限")

    plate = bounds(reports[("center_mechanism_plate", False)])
    expected_seat_z_min = axis_z - number(contract, "linearBearingNominalOdMm") / 2 - number(contract, "linearBearingBlockZMarginMm")
    expect_close(plate["min"][2], expected_seat_z_min, "一体轴承座 Z 后端包络")
    if plate["max"][2] <= plate["min"][2]:
        fail("机构板一体轴承座没有形成实体 Z 支撑")

    sleeve = bounds(reports[("center_input_sleeve", False)])
    magnet = bounds(reports[("center_input_sleeve_magnet", False)])
    for axis in (0, 2):
        if magnet["min"][axis] < sleeve["min"][axis] - TOLERANCE_MM or magnet["max"][axis] > sleeve["max"][axis] + TOLERANCE_MM:
            fail(f"M5 磁铁在 {axis} 轴方向超出圆套")
    if magnet["min"][1] < sleeve["min"][1] - TOLERANCE_MM or magnet["max"][1] > sleeve["max"][1] + TOLERANCE_MM:
        fail("M5 磁铁没有留在圆套盲槽内")


def validate_intermediate_sweep(
    openscad: Path,
    scad: Path,
    inspect_py: Path,
    temp_dir: Path,
    contract: Contract,
) -> None:
    stroke = number(contract, "strokeMm")
    for travel in (stroke * 0.25, stroke * 0.50, stroke * 0.75):
        for part in MOVING_PARTS:
            stl = temp_dir / f"{part}_{travel:.3f}.stl"
            run_export(openscad, scad, stl, part, False, travel)
            report = inspect(inspect_py, stl)
            if part in PRINTED_PARTS:
                assert_watertight(report, stl.name)
            opened_stl = temp_dir / f"{part}_open_reference.stl"
            if not opened_stl.exists():
                run_export(openscad, scad, opened_stl, part, False, 0.0)
            opened = bounds(inspect(inspect_py, opened_stl))
            current = bounds(report)
            expect_close(current["min"][1] - opened["min"][1], travel, f"{part} 中间行程最小值")
            expect_close(current["max"][1] - opened["max"][1], travel, f"{part} 中间行程最大值")


def validate_interference(contract: Contract, reports: dict[tuple[str, bool], dict[str, object]]) -> dict[str, float]:
    open_gap = number(contract, "openGapMm")
    insertion = number(contract, "dogInsertionMm")
    stroke = number(contract, "strokeMm")
    bottom = number(contract, "bottomClearanceMm")
    lower_start = number(contract, "inputShaftLowerDStartMm")
    lower_end = lower_start + number(contract, "inputShaftLowerDLengthMm")
    socket_min = number(contract, "inputSleeveTopOffsetMm") - number(contract, "inputSleeveDSocketDepthMm")
    socket_max = number(contract, "inputSleeveTopOffsetMm")
    socket_overlap = min(lower_end, socket_max) - max(lower_start, socket_min)
    expect_at_least(socket_overlap, number(contract, "inputSleeveDSocketDepthMm") - 0.20, "下 D 轴插入圆套有效深度")
    if number(contract, "inputSleeveMagnetBottomClearanceMm") < 1.0:
        fail("M5 磁铁底部没有实体保留")

    output = bounds(reports[("center_output_rotor", False)])
    cage = bounds(reports[("center_output_cage", False)])
    expect_close((output["min"][0] + output["max"][0]) / 2, number(contract, "axisXMm"), "输出母轮轴心 X")
    expect_close((cage["min"][0] + cage["max"][0]) / 2, number(contract, "axisXMm"), "输出轴承笼轴心 X")
    return {
        "openGap": open_gap,
        "insertion": insertion,
        "stroke": stroke,
        "bottomClearance": bottom,
        "sleeveSocketOverlap": socket_overlap,
        "engagedSleeveSeatContact": abs(
            (number(contract, "linearBearingCenterYOffsetMm")
             - number(contract, "linearBearingBlockYLengthMm") / 2)
            - (number(contract, "inputSleeveTopOffsetMm") + stroke)
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
    inspect_py = args.inspect.resolve()
    payload = json.loads(args.contract.resolve().read_text(encoding="utf-8"))
    contract = payload.get("centerClutch")
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
                report = inspect(inspect_py, stl)
                if part in PRINTED_PARTS:
                    assert_watertight(report, stl.name)
                reports[(part, engaged)] = report
        for part in FIXED_PARTS:
            stl = temp_dir / f"{part}_open.stl"
            run_export(openscad, scad, stl, part, False)
            report = inspect(inspect_py, stl)
            if part in PRINTED_PARTS:
                assert_watertight(report, stl.name)
            reports[(part, False)] = report

        cabinet_stl = temp_dir / "cabinet.stl"
        run_export(openscad, scad, cabinet_stl, "cabinet", False)
        assert_watertight(inspect(inspect_py, cabinet_stl), cabinet_stl.name)

        coupon_stl = temp_dir / "center_linear_bearing_fit_coupon.stl"
        run_export(openscad, scad, coupon_stl, "center_linear_bearing_fit_coupon", False)
        coupon = bounds(inspect(inspect_py, coupon_stl))
        assert_watertight(inspect(inspect_py, coupon_stl), coupon_stl.name)
        expect_close(coupon["max"][0] - coupon["min"][0], 42.0, "轴承测试片总宽", 0.05)
        expect_close(coupon["max"][1] - coupon["min"][1], 10.0, "轴承测试片 Y 厚", 0.05)
        expect_close(coupon["max"][2] - coupon["min"][2], 12.0, "轴承测试片 Z 高", 0.05)

        for travel, label in ((0.0, "open"), (1.5, "mid"), (3.0, "engaged")):
            witness = temp_dir / f"center_clutch_pair_collision_{label}.stl"
            if run_intersection_export(openscad, scad, witness, inspect_py, "center_clutch_pair_collision", False, travel):
                fail(f"公母离合轮 {label} 位存在实体交集")
        belt_witness = temp_dir / "center_plate_belt_collision.stl"
        if run_intersection_export(openscad, scad, belt_witness, inspect_py, "center_plate_belt_collision", False, 0.0):
            fail("机构板与中心 2GT 皮带存在实体交集")

        validate_intermediate_sweep(openscad, scad, inspect_py, temp_dir, contract)
        validate_sweep(contract, reports)
        metrics = validate_interference(contract, reports)

    print(
        "中心离合几何扫掠通过: "
        f"gap={metrics['openGap']:.2f}mm, insertion={metrics['insertion']:.2f}mm, "
        f"stroke={metrics['stroke']:.2f}mm, bottom={metrics['bottomClearance']:.2f}mm, "
        f"LM3UU=Ø{number(contract, 'linearBearingNominalIdMm'):.0f}×"
        f"Ø{number(contract, 'linearBearingNominalOdMm'):.0f}×"
        f"{number(contract, 'linearBearingNominalLengthMm'):.0f}mm, "
        f"M5×5 sleeve magnet, socket_overlap={metrics['sleeveSocketOverlap']:.2f}mm"
    )
    print("已检查：公轮轴 X/Z 不漂移、一体式实心 LM3UU 轴承座、D→圆→D 过渡、圆套盲槽、输出轴承笼、皮带贯穿槽")
    print("未验收：实物打印配合、LM3UU/磁铁装配、磁极、低速负载和 20 次循环")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
