#!/usr/bin/env python3
"""从 OpenSCAD 回显生成中心 R3C3 离合的唯一机械契约。"""

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
    "version", "axis", "role", "verticalLayoutMode",
    "centerClutchVerticalLiftMm", "axisXMm", "axisZMm", "inputBaseYMm",
    "maleBottomYMm", "outputBaseYMm", "openGapMm", "dogInsertionMm",
    "strokeMm", "pocketDepthMm", "bottomClearanceMm",
    "magnetNonContactClearanceMm", "femaleMagnetProjectionMm",
    "magnetNominalDiameterMm", "gearCenterDistanceMm", "longPitchRadiusMm",
    "inputPitchRadiusMm", "gearMeshClearanceMm", "dogPocketPhaseDeg",
    "longTipRadiusMm", "inputTipRadiusMm", "beltEnvelopeRadiusMm",
    "beltGuideRadiusMm", "motherOuterRadiusMm",
    "linearBearingNominalIdMm", "linearBearingNominalOdMm",
    "linearBearingNominalLengthMm", "linearBearingCount",
    "linearBearingCenterYOffsetMm", "linearBearingCenterYMm",
    "linearBearingSeatDiameterMm", "linearBearingSeatRadialClearanceMm",
    "linearBearingBlockWidthMm", "linearBearingBlockYLengthMm",
    "linearBearingBlockZLengthMm", "linearBearingBlockZMarginMm",
    "linearBearingBlockMountHoleDiameterMm",
    "linearBearingBlockMountHoleCount", "linearBearingBlockMountXOffsetMm",
    "linearBearingBlockMountYOffsetMm", "linearBearingBlockMount",
    "linearBearingModel", "linearBearingMovesWithInput",
    "linearBearingFitCouponPart", "linearBearingPart", "linearBearingBlockPart",
    "inputShaftProfile", "inputShaftUpperDStartMm",
    "inputShaftUpperDLengthMm", "inputShaftRoundStartMm",
    "inputShaftRoundLengthMm", "inputShaftRoundDiameterMm",
    "inputShaftLowerDStartMm", "inputShaftLowerDLengthMm",
    "inputSleeveTopOffsetMm", "inputSleeveUpperDHeightMm",
    "inputSleeveUpperDDiameterMm", "inputSleeveLowerRoundOuterDiameterMm",
    "inputSleeveLowerRoundHeightMm", "inputSleeveDSocketDepthMm",
    "inputSleeveDSocketClearanceMm", "inputSleeveMagnetNominalDiameterMm",
    "inputSleeveMagnetNominalLengthMm", "inputSleeveMagnetPocketDiameterMm",
    "inputSleeveMagnetPocketDepthMm", "inputSleeveMagnetBottomClearanceMm",
    "inputShaftPart", "inputSleevePart", "inputSleeveMagnetPart",
    "outputShaftStartMm", "outputShaftLengthMm", "outputBearingCount",
    "bearingCount", "bearingNominal", "bearingSeatDiameterMm",
    "bearingSeatDepthMm", "bearingBackShoulderMm",
    "bearingReferenceCenterOffsetMm", "bearingCenterOffsetMm",
    "bearingPairSpacingMm", "bearingBlockThicknessMm", "shaftDiameterMm",
    "shaftCollarOdMm", "shaftCollarBoreMm", "matingMagnetCount",
    "inputSleeveMagnetCount", "totalModeledMagnetCount",
    "rotaryBearingArrangement", "linearBearingArrangement", "plateWidthMm",
    "plateKeyWidthMm", "plateKeyHeightMm", "plateKeyClearanceMm",
    "plateM3ClearanceMm", "plateBeltPassageHalfWidthMm",
    "plateBeltPassageAxialWidthMm", "plateBeltPassageRadialClearanceMm",
    "plateBeltPassageAxialClearanceMm", "plateSupport", "actuation",
    "engageOnlyWhenStopped", "releaseBeforeReturn",
    "inputSideAdditionalMechanism", "centerCol", "centerRow", "inputPart",
    "outputPart", "outputCagePart", "mechanismPlatePart", "outputShaftPart",
    "outputBearingsPart",
}
FLOAT_KEYS = {key for key in REQUIRED if key.endswith("Mm") or key.endswith("Deg")}
INT_KEYS = {
    "version", "linearBearingCount", "linearBearingBlockMountHoleCount",
    "outputBearingCount", "bearingCount", "matingMagnetCount",
    "inputSleeveMagnetCount", "totalModeledMagnetCount", "centerCol", "centerRow",
}
BOOL_KEYS = {
    "linearBearingMovesWithInput", "engageOnlyWhenStopped", "releaseBeforeReturn",
}

# ===== 分区：私有成员 =====
def parse_echo(output: str) -> dict[str, str]:
    for line in output.splitlines():
        if MARKER not in line:
            continue
        tokens = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
        if not tokens or tokens[0] != MARKER:
            continue
        values = {
            key: value
            for token in tokens[1:]
            if "=" in token
            for key, value in [token.split("=", 1)]
        }
        missing = REQUIRED - values.keys()
        if missing:
            raise RuntimeError("中心离合契约缺少字段: " + ", ".join(sorted(missing)))
        return values
    raise RuntimeError("OpenSCAD 输出中没有 CENTER_CLUTCH_CONTRACT_DYNAMIC 回显")


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


def n(contract: dict[str, object], key: str) -> float:
    value = contract.get(key)
    if not isinstance(value, (int, float)):
        raise RuntimeError(f"中心离合契约数值字段无效: {key}={value!r}")
    return float(value)


def expect(contract: dict[str, object], key: str, value: float, label: str) -> None:
    actual = n(contract, key)
    if abs(actual - value) > 0.001:
        raise RuntimeError(f"{label}: {actual:.4f}，期望 {value:.4f}")


def validate_contract(contract: dict[str, object]) -> None:
    if contract.get("version") != 1:
        raise RuntimeError("中心离合契约版本必须为 1")
    if contract.get("axis") != "+Y" or contract.get("role") != "input/output":
        raise RuntimeError("中心离合契约轴向/角色不匹配")
    if contract.get("verticalLayoutMode") != "center-clutch-lift":
        raise RuntimeError("中心离合垂直布局必须是整体上移首件方案")
    expect(contract, "centerClutchVerticalLiftMm", 5.0, "中心离合垂直抬高")
    if contract.get("actuation") != "permanent-magnet":
        raise RuntimeError("中心离合必须使用永磁动作")
    if contract.get("engageOnlyWhenStopped") is not True:
        raise RuntimeError("中心离合必须停稳后接合")
    if contract.get("releaseBeforeReturn") is not True:
        raise RuntimeError("中心离合必须释放后返回")
    if contract.get("inputSideAdditionalMechanism") != "none":
        raise RuntimeError("公轮端不能残留滑架、止挡或拨叉等机构")
    if contract.get("linearBearingMovesWithInput") is not False:
        raise RuntimeError("固定长方条 LM3UU 不能随公轮移动")
    if (n(contract, "linearBearingBlockMountHoleCount") != 0
            or n(contract, "linearBearingBlockMountHoleDiameterMm") != 0
            or n(contract, "linearBearingBlockMountXOffsetMm") != 0
            or n(contract, "linearBearingBlockMountYOffsetMm") != 0):
        raise RuntimeError("一体式 LM3UU 轴承座不得保留座体 M3 固定孔")

    exact = {
        "linearBearingBlockMount": "mechanism-plate-integral-press-fit",
        "linearBearingModel": "LM3UU-cutaway-reference",
        "linearBearingFitCouponPart": "cabinet-clutch/center_linear_bearing_fit_coupon",
        "linearBearingPart": "cabinet-clutch/center_linear_bearings_reference",
        "linearBearingBlockPart": "cabinet-clutch/center_mechanism_plate",
        "inputShaftProfile": "D-round-D",
        "inputShaftPart": "cabinet-clutch/center_input_shaft_reference",
        "inputSleevePart": "cabinet-clutch/center_input_sleeve",
        "inputSleeveMagnetPart": "cabinet-clutch/center_input_sleeve_magnet_reference",
        "bearingNominal": "3x6x2",
        "rotaryBearingArrangement": "output-two-3x6x2-axially-spaced-input-free",
        "linearBearingArrangement": "single-coaxial-with-integrated-seat",
        "plateSupport": "partition-through-M3",
        "inputPart": "cabinet-clutch/center_input_rotor",
        "outputPart": "cabinet-clutch/center_output_rotor",
        "outputCagePart": "cabinet-clutch/center_output_cage",
        "mechanismPlatePart": "cabinet-clutch/center_mechanism_plate",
        "outputShaftPart": "cabinet-clutch/center_output_shaft_reference",
        "outputBearingsPart": "cabinet-clutch/center_output_bearings_reference",
    }
    for key, value in exact.items():
        if contract.get(key) != value:
            raise RuntimeError(f"中心离合契约字段错误: {key}={contract.get(key)!r}")

    frozen = {
        "openGapMm": 0.60, "dogInsertionMm": 2.40, "strokeMm": 3.00,
        "pocketDepthMm": 3.25, "bottomClearanceMm": 0.85,
        "magnetNonContactClearanceMm": 0.40, "femaleMagnetProjectionMm": 0.45,
        "magnetNominalDiameterMm": 2.00, "dogPocketPhaseDeg": 60.00,
        "linearBearingNominalIdMm": 3.00, "linearBearingNominalOdMm": 7.00,
        "linearBearingNominalLengthMm": 10.00, "linearBearingCount": 1.0,
        "linearBearingCenterYOffsetMm": -7.00, "linearBearingSeatDiameterMm": 7.20,
        "linearBearingSeatRadialClearanceMm": 0.10, "linearBearingBlockWidthMm": 18.00,
        "linearBearingBlockYLengthMm": 14.00, "linearBearingBlockZMarginMm": 1.00,
        "linearBearingBlockZLengthMm": 19.7208,
        "linearBearingBlockMountHoleDiameterMm": 0.00,
        "linearBearingBlockMountHoleCount": 0.0,
        "linearBearingBlockMountXOffsetMm": 0.00,
        "linearBearingBlockMountYOffsetMm": 0.00,
        "inputShaftUpperDStartMm": -0.40, "inputShaftUpperDLengthMm": 3.60,
        "inputShaftRoundStartMm": -20.60, "inputShaftRoundLengthMm": 20.40,
        "inputShaftRoundDiameterMm": 3.00, "inputShaftLowerDStartMm": -20.40,
        "inputShaftLowerDLengthMm": 3.60, "inputSleeveTopOffsetMm": -17.00,
        "inputSleeveUpperDHeightMm": 4.20, "inputSleeveUpperDDiameterMm": 7.60,
        "inputSleeveLowerRoundOuterDiameterMm": 8.00,
        "inputSleeveLowerRoundHeightMm": 6.40, "inputSleeveDSocketDepthMm": 3.60,
        "inputSleeveDSocketClearanceMm": 0.16,
        "inputSleeveMagnetNominalDiameterMm": 5.00,
        "inputSleeveMagnetNominalLengthMm": 5.00,
        "inputSleeveMagnetPocketDiameterMm": 5.20,
        "inputSleeveMagnetPocketDepthMm": 5.20,
        "inputSleeveMagnetBottomClearanceMm": 1.20,
        "outputShaftStartMm": -3.40, "outputShaftLengthMm": 14.00,
        "outputBearingCount": 2.0, "bearingCount": 2.0,
        "bearingSeatDiameterMm": 6.10, "bearingSeatDepthMm": 2.60,
        "bearingBackShoulderMm": 0.60, "bearingReferenceCenterOffsetMm": -0.60,
        "bearingCenterOffsetMm": 4.20, "bearingPairSpacingMm": 4.00,
        "bearingBlockThicknessMm": 3.20, "shaftDiameterMm": 3.00,
        "shaftCollarOdMm": 7.20, "shaftCollarBoreMm": 3.35,
        "matingMagnetCount": 2.0, "inputSleeveMagnetCount": 1.0,
        "totalModeledMagnetCount": 3.0, "plateWidthMm": 34.00,
        "plateKeyWidthMm": 4.00, "plateKeyHeightMm": 6.00,
        "plateKeyClearanceMm": 0.30, "plateM3ClearanceMm": 3.40,
        "plateBeltPassageRadialClearanceMm": 0.45,
        "plateBeltPassageAxialClearanceMm": 0.45,
    }
    for key, value in frozen.items():
        expect(contract, key, value, f"中心离合冻结值 {key}")

    if abs(n(contract, "strokeMm") - n(contract, "openGapMm")
           - n(contract, "dogInsertionMm")) > 0.001:
        raise RuntimeError("总行程必须等于开位间隙 + 有效公牙插入")
    if abs(n(contract, "pocketDepthMm") - n(contract, "dogInsertionMm")
           - n(contract, "bottomClearanceMm")) > 0.001:
        raise RuntimeError("母槽深度必须等于有效插入 + 槽底余量")
    if abs(n(contract, "bottomClearanceMm") - n(contract, "femaleMagnetProjectionMm")
           - n(contract, "magnetNonContactClearanceMm")) > 0.001:
        raise RuntimeError("磁铁非接触余量推导不一致")

    bearing_center = n(contract, "linearBearingCenterYOffsetMm")
    bearing_half = n(contract, "linearBearingNominalLengthMm") / 2
    round_start = n(contract, "inputShaftRoundStartMm")
    round_end = round_start + n(contract, "inputShaftRoundLengthMm")
    stroke = n(contract, "strokeMm")
    if round_start > bearing_center - bearing_half + 0.001:
        raise RuntimeError("公轮圆轴段开位没有完全穿过 LM3UU")
    if round_end + stroke < bearing_center + bearing_half - 0.001:
        raise RuntimeError("公轮圆轴段合位没有完全穿过 LM3UU")
    upper_start = n(contract, "inputShaftUpperDStartMm")
    upper_end = upper_start + n(contract, "inputShaftUpperDLengthMm")
    lower_start = n(contract, "inputShaftLowerDStartMm")
    lower_end = lower_start + n(contract, "inputShaftLowerDLengthMm")
    if upper_end < 3.0 - 0.001:
        raise RuntimeError("上 D 段没有达到公轮盲孔底")
    if round_end < upper_start - 0.001:
        raise RuntimeError("圆滑动段没有与上 D 段形成过渡重叠")
    if lower_start > round_end + 0.001 or lower_end < round_start - 0.001:
        raise RuntimeError("下 D 段没有与圆滑动段形成过渡重叠")

    bearing_y0 = bearing_center - n(contract, "linearBearingBlockYLengthMm") / 2
    sleeve_open_top = n(contract, "inputSleeveTopOffsetMm")
    sleeve_engaged_top = sleeve_open_top + stroke
    if abs(sleeve_engaged_top - bearing_y0) > 0.001:
        raise RuntimeError("合位圆套上沿必须刚好接触一体式轴承座下沿")
    if bearing_y0 - sleeve_open_top < stroke - 0.001:
        raise RuntimeError("开位圆套没有与一体式轴承座保持完整行程间隙")

    if n(contract, "inputSleeveDSocketDepthMm") > n(contract, "inputSleeveUpperDHeightMm"):
        raise RuntimeError("圆套上方 D 型插孔越过上方 D 型段")
    if n(contract, "inputSleeveDSocketDepthMm") > n(contract, "inputShaftLowerDLengthMm"):
        raise RuntimeError("下 D 轴段长度不足以插入圆套")
    if n(contract, "inputSleeveMagnetPocketDiameterMm") < n(contract, "inputSleeveMagnetNominalDiameterMm"):
        raise RuntimeError("M5 磁铁槽孔径不足")
    if n(contract, "inputSleeveMagnetPocketDepthMm") < n(contract, "inputSleeveMagnetNominalLengthMm"):
        raise RuntimeError("M5 磁铁槽深不足")
    sleeve_wall = (n(contract, "inputSleeveLowerRoundOuterDiameterMm")
                   - n(contract, "inputSleeveMagnetPocketDiameterMm")) / 2
    if sleeve_wall < 1.40 - 0.001:
        raise RuntimeError("M5 圆柱磁铁周围圆套壁厚不足 1.40 mm")
    if n(contract, "inputSleeveMagnetBottomClearanceMm") < 1.0:
        raise RuntimeError("M5 磁铁下方实体底厚不足")

    if abs(n(contract, "bearingReferenceCenterOffsetMm")
           + n(contract, "bearingBackShoulderMm")) > 0.001:
        raise RuntimeError("输出轴承参考件没有按后肩偏移")
    if n(contract, "bearingSeatDepthMm") < n(contract, "bearingBackShoulderMm") + 2.0:
        raise RuntimeError("输出 3x6x2 轴承座深度不足")
    if n(contract, "shaftCollarOdMm") <= 6.0:
        raise RuntimeError("输出轴肩/挡圈外径不能捕获 3x6x2 轴承")
    if n(contract, "shaftCollarBoreMm") <= n(contract, "shaftDiameterMm"):
        raise RuntimeError("输出轴肩孔不能通过 3 mm D 轴")

    center_distance = n(contract, "gearCenterDistanceMm")
    if abs(center_distance - n(contract, "longPitchRadiusMm")
           - n(contract, "inputPitchRadiusMm")
           - n(contract, "gearMeshClearanceMm")) > 0.001:
        raise RuntimeError("长花键与公轮中心距不是节圆半径和 + 啮合余量")
    for key in ("beltEnvelopeRadiusMm", "beltGuideRadiusMm", "motherOuterRadiusMm"):
        if center_distance - n(contract, "longTipRadiusMm") - n(contract, key) < 0.45 - 0.001:
            raise RuntimeError(f"{key} 到长花键的径向余量不足")

    if n(contract, "plateBeltPassageHalfWidthMm") <= n(contract, "beltEnvelopeRadiusMm"):
        raise RuntimeError("机构板贯穿槽没有包住 2GT 背包络")
    if n(contract, "plateBeltPassageAxialWidthMm") <= 6.0:
        raise RuntimeError("机构板贯穿槽没有覆盖 6 mm 皮带宽度")
    if n(contract, "plateBeltPassageHalfWidthMm") >= n(contract, "plateWidthMm") / 2:
        raise RuntimeError("机构板贯穿槽穿出侧壁")
    if n(contract, "outputShaftLengthMm") <= n(contract, "inputShaftUpperDLengthMm"):
        raise RuntimeError("输出 D 轴长度不足")
    if n(contract, "centerCol") != 2 or n(contract, "centerRow") != 2:
        raise RuntimeError("当前契约必须锁定中心 R3C3（零基准 2,2）")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
        completed = subprocess.run(
            [str(args.openscad), "--backend", "Manifold", "--export-format", "binstl",
             "-D", 'CLUTCH_PART="contract"', "-o", temp.name, str(scad_path)],
            cwd=scad_path.parent, capture_output=True, text=True, check=False,
        )
    output = f"{completed.stdout}\n{completed.stderr}"
    try:
        contract = coerce(parse_echo(output))
        validate_contract(contract)
    except RuntimeError as exc:
        if completed.returncode != 0:
            raise RuntimeError(
                f"OpenSCAD 契约模式失败（{completed.returncode}）：\n{output[-4000:]}"
            ) from exc
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
        f"bearing=LM3UU {contract['linearBearingNominalIdMm']}x"
        f"{contract['linearBearingNominalOdMm']}x{contract['linearBearingNominalLengthMm']} "
        f"profile={contract['inputShaftProfile']} "
        f"sleeve-magnet=Ø{contract['inputSleeveMagnetNominalDiameterMm']}x"
        f"{contract['inputSleeveMagnetNominalLengthMm']} stroke={contract['strokeMm']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
