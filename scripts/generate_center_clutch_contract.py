#!/usr/bin/env python3
"""从 OpenSCAD 的中心离合参数回显生成唯一机械契约。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

# ===== 分区：常量/配置 =====
MARKER = "CENTER_CLUTCH_CONTRACT_DYNAMIC"
REQUIRED = {
    "axis",
    "role",
    "openGapMm",
    "dogInsertionMm",
    "strokeMm",
    "pocketDepthMm",
    "bottomClearanceMm",
    "magnetNonContactClearanceMm",
    "femaleMagnetProjectionMm",
    "magnetNominalDiameterMm",
    "dogPocketPhaseDeg",
    "actuation",
    "engageOnlyWhenStopped",
    "releaseBeforeReturn",
    "bearingReferenceCenterOffsetMm",
    "bearingCenterOffsetMm",
    "bearingPairSpacingMm",
    "bearingBlockThicknessMm",
    "bearingBlockWidthMm",
    "bearingBlockHeightMm",
    "guideRailWidthMm",
    "guideRailHeightMm",
    "guideRailXOffsetMm",
    "guideRailZOffsetMm",
    "stopPadWidthMm",
    "stopPadXOffsetMm",
    "captureShoeOuterMm",
    "captureShoeLengthMm",
    "carriageUprightCenterXOffsetMm",
    "carriageUprightWidthMm",
    "carriageUprightZ0Mm",
    "carriageUprightHeightMm",
    "carriageUprightY0Mm",
    "carriageUprightLengthMm",
    "carriageUprightRadialClearanceMm",
    "plateWidthMm",
    "plateKeyWidthMm",
    "plateKeyHeightMm",
    "plateKeyClearanceMm",
    "plateM3ClearanceMm",
    "plateBeltPassageHalfWidthMm",
    "plateBeltPassageAxialWidthMm",
    "plateBeltPassageRadialClearanceMm",
    "plateBeltPassageAxialClearanceMm",
    "plateSupport",
    "selectorShoePart",
    "selectorShoeCoordinateFrame",
    "selectorShoeTangentOffsetMm",
    "selectorShoeNormalOffsetMm",
    "selectorShoeTargetYMm",
    "selectorShoeZMm",
    "selectorShoeFrontClearanceMm",
    "selectorShoeRearProjectionMm",
    "inputShaftStartMm",
    "inputShaftLengthMm",
    "outputShaftStartMm",
    "outputShaftLengthMm",
    "inputGearBandThicknessMm",
    "dBoreDepthMm",
}
FLOAT_KEYS = {
    "axisXMm",
    "axisZMm",
    "inputBaseYMm",
    "outputBaseYMm",
    "openGapMm",
    "dogInsertionMm",
    "strokeMm",
    "pocketDepthMm",
    "bottomClearanceMm",
    "magnetNonContactClearanceMm",
    "femaleMagnetProjectionMm",
    "magnetNominalDiameterMm",
    "dogPocketPhaseDeg",
    "gearCenterDistanceMm",
    "longPitchRadiusMm",
    "inputPitchRadiusMm",
    "gearMeshClearanceMm",
    "longTipRadiusMm",
    "inputTipRadiusMm",
    "beltEnvelopeRadiusMm",
    "beltGuideRadiusMm",
    "motherOuterRadiusMm",
    "selectorTriggerSpacingMm",
    "guideRunningClearanceMm",
    "railY0Mm",
    "railY1Mm",
    "openStopY0Mm",
    "openStopY1Mm",
    "engagedStopY0Mm",
    "engagedStopY1Mm",
    "openTabY0Mm",
    "openTabY1Mm",
    "engagedTabY0Mm",
    "engagedTabY1Mm",
    "bearingSeatDiameterMm",
    "bearingSeatDepthMm",
    "bearingBackShoulderMm",
    "bearingReferenceCenterOffsetMm",
    "bearingCenterOffsetMm",
    "bearingPairSpacingMm",
    "bearingBlockThicknessMm",
    "bearingBlockWidthMm",
    "bearingBlockHeightMm",
    "guideRailWidthMm",
    "guideRailHeightMm",
    "guideRailXOffsetMm",
    "guideRailZOffsetMm",
    "stopPadWidthMm",
    "stopPadXOffsetMm",
    "captureShoeOuterMm",
    "captureShoeLengthMm",
    "carriageUprightCenterXOffsetMm",
    "carriageUprightWidthMm",
    "carriageUprightZ0Mm",
    "carriageUprightHeightMm",
    "carriageUprightY0Mm",
    "carriageUprightLengthMm",
    "carriageUprightRadialClearanceMm",
    "plateWidthMm",
    "shaftDiameterMm",
    "shaftCollarOdMm",
    "shaftCollarBoreMm",
    "plateKeyWidthMm",
    "plateKeyHeightMm",
    "plateKeyClearanceMm",
    "plateM3ClearanceMm",
    "plateBeltPassageHalfWidthMm",
    "plateBeltPassageAxialWidthMm",
    "plateBeltPassageRadialClearanceMm",
    "plateBeltPassageAxialClearanceMm",
    "selectorShoeTangentOffsetMm",
    "selectorShoeNormalOffsetMm",
    "selectorShoeTargetYMm",
    "selectorShoeZMm",
    "selectorShoeFrontClearanceMm",
    "selectorShoeRearProjectionMm",
    "inputShaftStartMm",
    "inputShaftLengthMm",
    "outputShaftStartMm",
    "outputShaftLengthMm",
    "inputGearBandThicknessMm",
    "dBoreDepthMm",
}
INT_KEYS = {
    "version",
    "bearingCount",
    "shaftCount",
    "matingMagnetCount",
    "selectorMagnetCount",
    "totalMagnetCount",
    "centerCol",
    "centerRow",
}
BOOL_KEYS = {"engageOnlyWhenStopped", "releaseBeforeReturn"}

# ===== 分区：私有成员 =====
def parse_echo(output: str) -> dict[str, str]:
    for line in output.splitlines():
        if MARKER not in line:
            continue
        tokens = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
        if not tokens or tokens[0] != MARKER:
            continue
        values: dict[str, str] = {}
        for token in tokens[1:]:
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            values[key] = value
        missing = REQUIRED - values.keys()
        if missing:
            raise RuntimeError(
                f"中心离合契约缺少字段: {', '.join(sorted(missing))}"
            )
        return values
    raise RuntimeError("OpenSCAD 输出中没有 CENTER_CLUTCH_CONTRACT 回显")


def coerce(values: dict[str, str]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in values.items():
        if key in FLOAT_KEYS:
            result[key] = float(value)
        elif key in INT_KEYS:
            result[key] = int(float(value))
        elif key in BOOL_KEYS:
            if value not in {"true", "false"}:
                raise RuntimeError(f"契约布尔字段无效: {key}={value}")
            result[key] = value == "true"
        else:
            result[key] = value
    return result


def validate_contract(contract: dict[str, object]) -> None:
    if contract.get("axis") != "+Y" or contract.get("role") != "input/output":
        raise RuntimeError("中心离合契约轴向/角色不匹配")
    if contract.get("actuation") != "permanent-magnet":
        raise RuntimeError("中心离合契约不是纯永磁动作")
    if contract.get("engageOnlyWhenStopped") is not True:
        raise RuntimeError("中心离合必须停稳后接合")
    if contract.get("releaseBeforeReturn") is not True:
        raise RuntimeError("中心离合必须释放后返回")

    def number(key: str) -> float:
        value = contract.get(key)
        if not isinstance(value, (int, float)):
            raise RuntimeError(f"中心离合契约缺少数值字段: {key}")
        return float(value)

    frozen = {
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
        "bearingBlockWidthMm": 14.00,
        "bearingBlockHeightMm": 14.00,
        "guideRailWidthMm": 3.00,
        "guideRailHeightMm": 3.00,
        "guideRailXOffsetMm": 9.00,
        "guideRailZOffsetMm": 8.00,
        "captureShoeOuterMm": 5.20,
        "captureShoeLengthMm": 6.00,
        "carriageUprightCenterXOffsetMm": 6.20,
        "carriageUprightWidthMm": 2.00,
        "carriageUprightZ0Mm": 5.20,
        "carriageUprightHeightMm": 3.00,
        "carriageUprightY0Mm": -10.00,
        "carriageUprightLengthMm": 8.40,
        "dogPocketPhaseDeg": 60.00,
        "stopPadWidthMm": 4.00,
        "stopPadXOffsetMm": 0.60,
        "plateWidthMm": 34.00,
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
    for key, expected in frozen.items():
        if abs(number(key) - expected) > 0.001:
            raise RuntimeError(
                f"中心离合冻结值错误: {key}={number(key)}，期望 {expected}"
            )
    if abs(number("strokeMm")
            - number("openGapMm")
            - number("dogInsertionMm")) > 0.001:
        raise RuntimeError("中心离合行程必须等于开位间隙加有效插入")
    if abs(number("pocketDepthMm")
            - number("dogInsertionMm")
            - number("bottomClearanceMm")) > 0.001:
        raise RuntimeError("中心母槽深度必须等于插入量加槽底余量")
    if abs(number("bottomClearanceMm")
            - number("femaleMagnetProjectionMm")
            - number("magnetNonContactClearanceMm")) > 0.001:
        raise RuntimeError("中心磁铁非接触余量推导失败")
    if number("bearingSeatDepthMm") < number("bearingBackShoulderMm") + 2.0:
        raise RuntimeError("轴承座深度不足以容纳 3x6x2 轴承和后肩")
    if number("bearingCenterOffsetMm") <= number("bearingBlockThicknessMm"):
        raise RuntimeError("轴承中心偏置不足以让双轴承块脱离转子端面")
    if number("bearingPairSpacingMm") < number("bearingBlockThicknessMm"):
        raise RuntimeError("同轴双轴承间距不足以分隔两枚轴承块")
    if abs(
        number("bearingReferenceCenterOffsetMm")
        + number("bearingBackShoulderMm")
    ) > 0.001:
        raise RuntimeError("轴承参考件没有向盲座开口侧偏移后肩厚度")
    if number("plateKeyWidthMm") <= 0 or number("plateKeyHeightMm") <= 0:
        raise RuntimeError("机构板定位键尺寸无效")
    if number("plateKeyClearanceMm") < 0.20:
        raise RuntimeError("机构板定位键装配间隙不足")
    if number("plateM3ClearanceMm") <= 3.0:
        raise RuntimeError("机构板 M3 贯穿孔没有留通孔间隙")
    if number("plateBeltPassageHalfWidthMm") <= number("beltEnvelopeRadiusMm"):
        raise RuntimeError("机构板皮带通道没有包住中心 2GT 背包络")
    if number("plateBeltPassageAxialWidthMm") <= 6.0:
        raise RuntimeError("机构板皮带通道没有覆盖 6 mm 皮带宽度")
    if number("plateBeltPassageHalfWidthMm") >= number("plateWidthMm") / 2:
        raise RuntimeError("机构板皮带通道穿出机构板侧边")
    if contract.get("plateSupport") != "partition-through-M3":
        raise RuntimeError("机构板承接界面不是隔板 M3 贯穿固定")
    if number("selectorShoeTangentOffsetMm") != 6.0:
        raise RuntimeError("M_engage 选择指切向基准必须位于磁力靴中心前 6 mm")
    if number("selectorShoeFrontClearanceMm") < 0.70:
        raise RuntimeError("磁力靴到输入转子前侧间隙不足")
    if contract.get("selectorShoeCoordinateFrame") != "native-world":
        raise RuntimeError("磁力靴必须使用原生世界坐标")
    if contract.get("selectorShoePart") != "cabinet-clutch/center_selector_shoe":
        raise RuntimeError("磁力靴零件 ID 不是原生中心离合零件")
    number("selectorShoeTargetYMm")
    number("selectorShoeZMm")
    if number("guideRailWidthMm") <= 0 or number("guideRailHeightMm") <= 0:
        raise RuntimeError("捕获导轨截面无效")
    if number("captureShoeOuterMm") <= number("guideRailWidthMm") + 2 * number("guideRunningClearanceMm"):
        raise RuntimeError("捕获滑靴没有包住导轨运行间隙")
    if number("carriageUprightCenterXOffsetMm") <= number("carriageUprightWidthMm") / 2:
        raise RuntimeError("滑架立柱没有离开轴心")
    if number("carriageUprightRadialClearanceMm") < 0.45:
        raise RuntimeError("滑架立柱径向净空低于 0.45 mm 门槛")
    input_end = number("inputShaftStartMm") + number("inputShaftLengthMm")
    if abs(input_end - number("dBoreDepthMm")) > 0.001:
        raise RuntimeError("输入 D 轴没有停在齿轮盲孔底基准")
    if number("dBoreDepthMm") > number("inputGearBandThicknessMm"):
        raise RuntimeError("输入 D 轴盲孔深度越过齿轮带厚度")
    if number("outputShaftLengthMm") <= number("dBoreDepthMm"):
        raise RuntimeError("输出 D 轴长度不足以穿过母轮盲孔和轴向保持段")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


# ===== 分区：公开 API =====
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openscad", required=True, type=Path)
    parser.add_argument("--scad", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--motion", type=Path)
    args = parser.parse_args()
    scad_path = args.scad.resolve()
    output_path = args.output.resolve()
    motion_path = args.motion.resolve() if args.motion else None

    with tempfile.NamedTemporaryFile(suffix=".stl") as temp:
        command = [
            str(args.openscad),
            "--backend",
            "Manifold",
            "--export-format",
            "binstl",
            "-D",
            'CLUTCH_PART="contract"',
            "-o",
            temp.name,
            str(scad_path),
        ]
        completed = subprocess.run(
            command,
            cwd=scad_path.parent,
            capture_output=True,
            text=True,
            check=False,
        )
    output = f"{completed.stdout}\n{completed.stderr}"
    try:
        # OpenSCAD returns 1 for an intentionally empty top-level object on
        # some releases. The contract marker is the success criterion here;
        # a non-empty diagnostic output without the marker is still a failure.
        contract = coerce(parse_echo(output))
        validate_contract(contract)
    except RuntimeError:
        if completed.returncode != 0:
            raise RuntimeError(
                f"OpenSCAD 契约模式失败（{completed.returncode}）:\n{output[-4000:]}"
            ) from None
        raise
    contract["source"] = "cad/openscad/parts/ch1_03c_gt2_clutch_pair_params.scad"
    contract["geometrySource"] = "cad/openscad/enclosure/cabinet_clutch.scad"
    write_json(output_path, {"centerClutch": contract})

    if motion_path:
        motion = json.loads(motion_path.read_text(encoding="utf-8"))
        motion["centerClutch"] = contract
        write_json(motion_path, motion)

    print(
        "centerClutch contract: "
        f"gap={contract['openGapMm']} insertion={contract['dogInsertionMm']} "
        f"stroke={contract['strokeMm']} bottom={contract['bottomClearanceMm']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
