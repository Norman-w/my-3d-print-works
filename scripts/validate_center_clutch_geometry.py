#!/usr/bin/env python3
"""Validate the center clutch contract and its open-to-engaged geometry sweep.

This is an analytic/OpenSCAD geometry gate. It checks the exported part bounds,
the shared travel equations, hard-stop datums and the radial clearance budget.
It does not replace a printed fit test, bearing installation or the required
20-cycle physical acceptance test.
"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import json
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
WATERTIGHT_PARTS = MOVING_PARTS + (
    "center_guide_rails",
    "center_stops",
)
TOLERANCE_MM = 0.02
CLEARANCE_FLOOR_MM = 0.45

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
    return {
        "min": [float(value) for value in minimum],
        "max": [float(value) for value in maximum],
    }


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

    if number(contract, "bearingSeatDiameterMm") <= 6.0:
        fail("轴承座没有给 3x6x2 外径留装配间隙")
    if number(contract, "bearingSeatDepthMm") < 2.0 + number(contract, "bearingBackShoulderMm"):
        fail("轴承盲座深度不足")
    if number(contract, "shaftCollarOdMm") <= 6.0:
        fail("轴肩/挡圈外径不能捕获轴承")
    if number(contract, "shaftCollarBoreMm") <= 3.0:
        fail("轴肩/挡圈内孔不能通过 3 mm D 轴")

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
        if clearance < CLEARANCE_FLOOR_MM - 0.001:
            fail(f"{label} 到长花键径向余量不足: {clearance:.3f} mm")


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
            if not close(
                engaged_bounds["min"][index], open_bounds["min"][index]
            ) or not close(
                engaged_bounds["max"][index], open_bounds["max"][index]
            ):
                fail(f"{part} 在 {axis} 方向发生非预期漂移")
        min_shift = engaged_bounds["min"][1] - open_bounds["min"][1]
        max_shift = engaged_bounds["max"][1] - open_bounds["max"][1]
        if not close(min_shift, stroke) or not close(max_shift, stroke):
            fail(
                f"{part} 行程错误: min={min_shift:.3f} max={max_shift:.3f}"
                f" 期望={stroke:.3f}"
            )

    rail_bounds = bounds(reports[("center_guide_rails", False)])
    for engaged in (False, True):
        carriage = bounds(reports[("center_input_carriage", engaged)])
        if carriage["min"][1] < rail_y0 - TOLERANCE_MM:
            fail(f"滑架开/合位脱出导轨下端: engaged={engaged}")
        if carriage["max"][1] > rail_y1 + TOLERANCE_MM:
            fail(f"滑架开/合位脱出导轨上端: engaged={engaged}")
        if carriage["min"][0] > rail_bounds["min"][0] + 1.0:
            fail(f"滑架没有覆盖左侧导轨捕获位置: engaged={engaged}")
        if carriage["max"][0] < rail_bounds["max"][0] - 1.0:
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
                if part in WATERTIGHT_PARTS:
                    assert_watertight(report, stl.name)
                reports[(part, engaged)] = report
        for part in ("center_guide_rails", "center_stops"):
            stl = temp_dir / f"{part}_open.stl"
            run_export(openscad, scad, stl, part, False)
            report = inspect(inspect_path, stl)
            assert_watertight(report, stl.name)
            reports[(part, False)] = report
        validate_sweep(contract, reports)

    print(
        "中心离合几何扫掠通过: "
        f"stroke={number(contract, 'strokeMm'):.2f}mm, "
        f"guide_clear={number(contract, 'guideRunningClearanceMm'):.2f}mm, "
        f"magnet_clear={number(contract, 'magnetNonContactClearanceMm'):.2f}mm, "
        "input/output 轴向保持与实体止挡已检查"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
