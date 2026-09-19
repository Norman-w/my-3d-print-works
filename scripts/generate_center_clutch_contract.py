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
    "centerClutchDriveLayerOffsetMm", "centerClutchVerticalLiftMm",
    "axisXMm", "axisZMm", "drawerBottomYMm", "drawerRackYMm",
    "frontPinionCenterYMm", "frontPinionLowerFaceYMm",
    "frontTimingPulleyDrawerRow", "frontTimingPulleyLayer",
    "frontTimingPulleyZMm",
    "frontTimingBeltYMm", "frontTimingPulleyCenterYMm",
    "frontTimingPulleyBottomYMm", "frontTimingPulleyTopYMm",
    "frontTimingPulleyToPinionGapMm", "frontTimingBearingCenterYMm",
    "frontTimingBearingUpperFaceYMm", "frontTimingBearingLowerFaceYMm",
    "frontTimingBearingWidthMm", "frontTimingBearingIdMm",
    "frontTimingBearingOdMm", "frontTimingBearingSeatDiameterMm",
    "frontTimingBearingSeatDepthMm",
    "frontTimingBearingRetainerThicknessMm",
    "frontTimingBearingRetainerBoreDiameterMm",
    "frontTimingBearingShelfLowerFaceYMm",
    "frontTimingBearingBossFusionOverlapMm",
    "frontTimingBearingBossBottomYMm",
    "frontTimingBearingGearClearanceMm",
    "frontTimingBearingPulleyClearanceMm", "frontTimingBearingSupport",
    "frontTimingBearingFit", "frontDshaftProfile", "frontDshaftStartYMm",
    "frontDshaftEndYMm", "frontDshaftLengthMm", "frontPinionThicknessMm",
    "verticalSplineBearingNominal", "verticalSplineBearingCount",
    "verticalSplineBearingIdMm", "verticalSplineBearingOdMm",
    "verticalSplineBearingWidthMm", "verticalSplineBearingSeatDiameterMm",
    "verticalSplineBearingAxisZMm", "verticalSplineBearingCenterYMm",
    "verticalSplineBearingBarY0Mm", "verticalSplineBearingBarY1Mm",
    "verticalSplineBearingBarXWidthMm", "verticalSplineBearingBarYThicknessMm",
    "verticalSplineBearingBarZMinMm", "verticalSplineBearingBarZMaxMm",
    "verticalSplineBearingBarZLengthMm",
    "verticalSplineBearingPartitionOverlapMm",
    "verticalSplineBearingPartitionKeyWidthMm",
    "verticalSplineBearingPartitionKeyClearanceMm",
    "verticalSplineBearingPartitionKeyZLengthMm",
    "verticalSplineBearingChainTopYMm",
    "verticalSplineBearingLowerPulleyBottomYMm",
    "verticalSplineBearingReturnGuideClearanceMm",
    "verticalSplineBearingLowerPulleyClearanceMm",
    "verticalSplineBearingReturnDriveClearanceMm",
    "verticalSplineBearingDetourColumn",
    "verticalSplineBearingDetourXOffsetMm",
    "verticalSplineBearingDetourXClearanceMm",
    "verticalSplineBearingDetourZClearanceMm",
    "verticalSplineBearingLowerDStubLengthMm",
    "verticalSplineBearingUpperDStubLengthMm",
    "verticalSplineBearingSupport", "verticalSplineBearingSupportPart",
    "verticalSplineBearingsPart",
    "inputBaseYMm",
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
    "linearBearingInputRotorClearanceMm",
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
    "inputSleeveMagnetOpenBottomYMm", "snakeChainHeightDatum",
    "snakeChainLinkTopOffsetMm", "snakeChainReferenceRow",
    "snakeChainReferencePathCenterYMm", "snakeChainVerticalShiftMm",
    "snakeChainServicePathCenterYMm", "snakeChainReturnGuideCenterYMm",
    "snakeChainTriggerMagnetSegmentIndex",
    "snakeChainTriggerMagnetDiameterMm", "snakeChainTriggerMagnetLengthMm",
    "snakeChainTriggerMagnetNormalOffsetMm",
    "snakeChainTriggerMagnetTopClearanceMm",
    "snakeChainTriggerMagnetAxialStartOffsetMm",
    "selectorShoePart", "selectorShoeSupport", "selectorShoeRotationMode",
    "selectorShoeAnchorXMm", "selectorShoeAnchorYMm",
    "selectorShoeAnchorZMm", "selectorShoeTangentOffsetMm",
    "selectorShoeNormalOffsetMm", "selectorShoeChainAttachXMm",
    "selectorShoeChainAttachYMm", "selectorShoeChainAttachZMm",
    "selectorShoeSupportArmDiameterMm", "selectorShoeTargetYMm",
    "selectorShoeTriggerClearanceMm",
    "inputShaftPart", "inputSleevePart", "inputSleeveMagnetPart",
    "outputShaftStartMm", "outputShaftLengthMm", "outputShaftProfile",
    "outputShaftDStartMm", "outputShaftDLengthMm",
    "outputShaftRoundStartMm", "outputShaftRoundLengthMm",
    "outputShaftRoundDiameterMm", "outputShaftTopProtrusionMm",
    "outputShaftMotherSocketOverlapMm", "outputBearingCount",
    "bearingCount", "bearingNominal", "bearingSeatDiameterMm",
    "bearingSeatDepthMm", "bearingBackShoulderMm",
    "bearingReferenceCenterOffsetMm", "bearingCenterOffsetMm",
    "bearingPairSpacingMm", "outputBearingBarWidthMm",
    "outputBearingBarYLengthMm", "outputBearingBarY0OffsetMm",
    "outputBearingBarZLengthMm", "outputBearingBarZMarginMm",
    "outputBearingBarZMinMm", "outputBearingBarZMaxMm",
    "outputBearingBarMotherClearanceMm", "outputBearingBarPlateOverlapMm",
    "shaftDiameterMm", "matingMagnetCount",
    "inputSleeveMagnetCount", "totalModeledMagnetCount",
    "rotaryBearingArrangement", "linearBearingArrangement", "plateWidthMm",
    "plateThicknessMm", "platePartitionGapMm", "plateFastenerCount",
    "plateM3ClearanceMm", "partitionSelfTapPilotDiameterMm",
    "partitionSelfTapPilotDepthMm", "partitionSelfTapBottomWallMm",
    "partitionBossPerCellCount", "partitionBossCount",
    "partitionBossCenterOffsetXMm", "partitionBossCenterOffsetYMm",
    "partitionBossOuterDiameterMm", "partitionBossHeightMm",
    "partitionBossHeightDeficitMm", "plateBeltPassageHalfWidthMm",
    "plateBeltPassageSlotCount", "plateBeltPassageSlotCenterOffsetMm",
    "plateBeltPassageSlotWidthMm",
    "plateBeltPassageAxialWidthMm", "plateBeltPassageRadialClearanceMm",
    "plateBeltPassageAxialClearanceMm", "plateSupport", "actuation",
    "partitionBeltPassageType", "partitionBeltPassageCenterXMm",
    "partitionBeltPassageCenterYMm", "partitionBeltPassageRelativeXMm",
    "partitionBeltPassageRelativeYMm", "partitionBeltPassagePlateZMm",
    "partitionBeltPassagePlateThicknessMm", "partitionBeltPassageHalfWidthMm",
    "partitionBeltPassageWindowCount", "partitionBeltPassage2GTWindowCount",
    "partitionBeltPassageAxialWidthMm",
    "partitionBeltPassageRadialClearanceMm",
    "partitionBeltPassageAxialClearanceMm",
    "engageOnlyWhenStopped", "releaseBeforeReturn",
    "inputSideAdditionalMechanism", "centerCol", "centerRow", "inputPart",
    "drawerLayerCount", "drawerColumnCount", "serviceLayerCount", "drawerBayHeightMm",
    "drawerShelfThicknessMm",
    "drawerStationTemplateOriginXMm", "drawerStationTemplateOriginYMm",
    "drawerStationColumnPitchMm", "drawerStationRowPitchMm",
    "drawerStationInstanceCount",
    "drawerRackBodyWidthMm", "drawerRackBodyHeightMm",
    "drawerRackToothHeightMm", "drawerRackToothOverhangMm",
    "centerFrontDriveLiftMm", "frontRackAboveShelfGapMm",
    "drawerRackLowerYMm", "drawerShelfTopYMm",
    "frontTimingBearingReinforcementDiscDiameterMm",
    "frontTimingBearingReinforcementDiscThicknessMm",
    "drawerRackMount", "drawerMassLoadPath",
    "drawerGuideBearing", "drawerGuideRail",
    "drawerGuideBearingArrangement", "drawerGuideBearingAxis",
    "drawerGuideLoadPath", "drawerFrontPinionBearing",
    "drawerGuideRailClearanceMm", "drawerGuideRailWallThicknessMm",
    "drawerGuideBearingSeatDiameterMm",
    "drawerGuideSlotHeightMm", "drawerGuideRailDepthMm",
    "drawerGuideFlangeThicknessMm", "drawerGuideFlangeProjectionMm",
    "drawerGuideFlangeClearanceMm", "drawerGuideFlangeBackClearanceMm",
    "drawerGuideFrontSupportClearanceMm", "drawerGuideTailBearingAxis",
    "drawerGuideFrontBearingAxis",
    "drawerFrontPinionBearingSeatDiameterMm",
    "outputPart", "outputBearingSupportPart", "mechanismPlatePart", "outputShaftPart",
    "outputBearingsPart",
}
FLOAT_KEYS = {key for key in REQUIRED if key.endswith("Mm") or key.endswith("Deg")}
INT_KEYS = {
    "version", "linearBearingCount", "linearBearingBlockMountHoleCount",
    "outputBearingCount", "bearingCount", "matingMagnetCount",
    "inputSleeveMagnetCount", "totalModeledMagnetCount", "centerCol", "centerRow",
    "drawerLayerCount", "drawerColumnCount", "serviceLayerCount", "frontTimingPulleyDrawerRow",
    "plateBeltPassageSlotCount", "partitionBeltPassageWindowCount",
    "partitionBeltPassage2GTWindowCount", "plateFastenerCount",
    "partitionBossPerCellCount", "partitionBossCount",
    "snakeChainReferenceRow",
    "snakeChainTriggerMagnetSegmentIndex",
    "verticalSplineBearingCount", "verticalSplineBearingDetourColumn",
    "drawerStationInstanceCount",
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
    if contract.get("verticalLayoutMode") != "drawer-bottom-drive-layer-lower-pulley":
        raise RuntimeError("中心离合垂直布局必须使用抽屉底部主动轮+下层同步轮")
    expect(contract, "centerClutchDriveLayerOffsetMm", 0.0, "中心驱动层偏置")
    expect(contract, "centerClutchVerticalLiftMm", 0.0, "兼容垂直偏置")
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
        "verticalSplineBearingNominal": "3x6x2",
        "verticalSplineBearingSupport": "partition-integral-rearward-stepped-bar-with-side-keys",
        "verticalSplineBearingSupportPart": "cabinet-clutch/vertical_spline_bearing_support",
        "verticalSplineBearingsPart": "cabinet-clutch/vertical_spline_bearings_reference",
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
        "outputShaftProfile": "D-round",
        "rotaryBearingArrangement": "output-two-3x6x2-in-one-integral-bar-input-free",
        "linearBearingArrangement": "single-coaxial-with-integrated-seat",
        "plateSupport": "partition-boss-locators-plus-four-self-tapping-screws",
        "inputPart": "cabinet-clutch/center_input_rotor",
        "outputPart": "cabinet-clutch/center_output_rotor",
        "outputBearingSupportPart": "cabinet-clutch/center_mechanism_plate",
        "mechanismPlatePart": "cabinet-clutch/center_mechanism_plate",
        "outputShaftPart": "cabinet-clutch/center_output_shaft_reference",
        "outputBearingsPart": "cabinet-clutch/center_output_bearings_reference",
        "frontTimingPulleyLayer": "next-drawer-bay",
        "frontTimingBearingSupport": "integral-shelf-stepped-seat",
        "frontTimingBearingFit": "press-fit-3x6x2-bottom-captive",
        "frontDshaftProfile": "D",
        "selectorShoePart": "cabinet-clutch/center_selector_shoe",
        "selectorShoeSupport": "chain-mounted-smooth-hull-arm",
        "selectorShoeRotationMode": "fixed-world-center-row",
        "drawerFrontPinionBearing": "integral-shelf-stepped-3x6x2",
        "drawerGuideBearing": "681-1x3x1-X-axis-C-slot",
        "drawerGuideRail": "dual-inward-C-slot",
        "drawerGuideBearingArrangement": "tail-moving-plus-front-lower-fixed",
        "drawerGuideBearingAxis": "+X/-X",
        "drawerGuideLoadPath": "Y-support-Z-travel",
        "drawerGuideTailBearingAxis": "+X/-X",
        "drawerGuideFrontBearingAxis": "+X/-X",
    }
    for key, value in exact.items():
        if contract.get(key) != value:
            raise RuntimeError(f"中心离合契约字段错误: {key}={contract.get(key)!r}")

    if n(contract, "verticalSplineBearingCount") != 5:
        raise RuntimeError("抽屉电机花键轴必须为 5 根列轴各配一枚固定轴承")
    if n(contract, "selectorShoeTangentOffsetMm") <= 0:
        raise RuntimeError("选择指磁力靴必须保留正的半间距触发位")
    if n(contract, "selectorShoeNormalOffsetMm") != 0:
        raise RuntimeError("选择指锚点必须直接落在中心链条路径，不得再叠加法向偏移")
    expect(
        contract,
        "selectorShoeAnchorXMm",
        n(contract, "axisXMm"),
        "选择指路径锚点 X",
    )
    chain_pitch = n(contract, "drawerBayHeightMm") + n(contract, "drawerShelfThicknessMm")
    expected_selector_y = (
        n(contract, "snakeChainReferencePathCenterYMm")
        + (n(contract, "centerRow") - n(contract, "snakeChainReferenceRow")) * chain_pitch
        + n(contract, "snakeChainVerticalShiftMm")
    )
    expect(
        contract,
        "selectorShoeAnchorYMm",
        expected_selector_y,
        "选择指中心行链条路径锚点 Y",
    )
    expect(
        contract,
        "selectorShoeChainAttachYMm",
        expected_selector_y,
        "选择指链条接触 Y",
    )
    expect(
        contract,
        "selectorShoeChainAttachZMm",
        n(contract, "selectorShoeAnchorZMm"),
        "选择指链条接触 Z",
    )
    if n(contract, "selectorShoeSupportArmDiameterMm") < 2.4:
        raise RuntimeError("选择指平滑支撑臂直径不足 2.4 mm")
    if n(contract, "selectorShoeTriggerClearanceMm") <= 0:
        raise RuntimeError("选择指磁铁触发净空无效")
    expect(contract, "verticalSplineBearingIdMm", 3.0, "花键轴承内径")
    expect(contract, "verticalSplineBearingOdMm", 6.0, "花键轴承外径")
    expect(contract, "verticalSplineBearingWidthMm", 2.0, "花键轴承宽度")
    expect(contract, "verticalSplineBearingSeatDiameterMm", 6.10, "花键轴承座孔")
    expect(contract, "verticalSplineBearingBarXWidthMm", 14.0, "花键轴承长方条 X 宽")
    expect(contract, "verticalSplineBearingBarYThicknessMm", 2.20, "花键轴承长方条 Y 厚")
    expect(
        contract,
        "verticalSplineBearingBarY1Mm"
        , n(contract, "verticalSplineBearingBarY0Mm")
        + n(contract, "verticalSplineBearingBarYThicknessMm"),
        "花键轴承长方条 Y 包络",
    )
    expect(
        contract,
        "verticalSplineBearingCenterYMm",
        (n(contract, "verticalSplineBearingChainTopYMm")
         + n(contract, "verticalSplineBearingLowerPulleyBottomYMm")) / 2,
        "花键轴承高度必须位于链条和下方 2GT 轮之间",
    )
    if n(contract, "verticalSplineBearingBarY0Mm") <= n(contract, "verticalSplineBearingChainTopYMm"):
        raise RuntimeError("花键轴承长方条下沿进入蛇链回程包络")
    if n(contract, "verticalSplineBearingBarY1Mm") >= n(contract, "verticalSplineBearingLowerPulleyBottomYMm"):
        raise RuntimeError("花键轴承长方条上沿进入下方 2GT 轮包络")
    if n(contract, "verticalSplineBearingReturnGuideClearanceMm") < 0.45:
        raise RuntimeError("花键轴承长方条与 8T 蛇链导向轮净空不足")
    if n(contract, "verticalSplineBearingLowerPulleyClearanceMm") < 0.45:
        raise RuntimeError("花键轴承长方条与下方 2GT 轮净空不足")
    if n(contract, "verticalSplineBearingReturnDriveClearanceMm") < 0.45:
        raise RuntimeError("花键轴承长方条与 12T 蛇链回程主动轮净空不足")
    expect(
        contract,
        "verticalSplineBearingBarZLengthMm",
        n(contract, "verticalSplineBearingBarZMaxMm")
        - n(contract, "verticalSplineBearingBarZMinMm"),
        "花键轴承长方条 Z 长度",
    )
    if n(contract, "verticalSplineBearingBarXWidthMm") <= 2 * n(contract, "partitionBeltPassageHalfWidthMm"):
        raise RuntimeError("花键轴承长方条不能形成隔板皮带孔外侧定位键")
    if n(contract, "verticalSplineBearingPartitionKeyWidthMm") <= 0 or n(contract, "verticalSplineBearingPartitionKeyClearanceMm") <= 0:
        raise RuntimeError("花键轴承隔板侧键必须在皮带孔外侧并留出净空")
    expect(
        contract,
        "verticalSplineBearingPartitionKeyZLengthMm",
        n(contract, "partitionBeltPassagePlateThicknessMm")
        + n(contract, "verticalSplineBearingPartitionOverlapMm")
        + 0.0,
        "花键轴承隔板侧键穿板长度",
    )
    expect(contract, "verticalSplineBearingDetourColumn", 0.0, "花键轴承避让列")
    expect(contract, "verticalSplineBearingDetourXOffsetMm", 14.0, "花键轴承 C1 避让 X 偏移")
    expect(contract, "verticalSplineBearingDetourZClearanceMm", 0.60, "花键轴承 C1 避让 Z 净空")
    if n(contract, "verticalSplineBearingDetourXClearanceMm") < 0.45:
        raise RuntimeError("C1 花键轴承折线支架与 12T 蛇链主动轮净空不足")
    expect(contract, "verticalSplineBearingLowerDStubLengthMm", 12.0, "花键轴下端 D 段")
    expect(contract, "verticalSplineBearingUpperDStubLengthMm", 6.0, "花键轴上端 D 段")

    if n(contract, "platePartitionGapMm") != 0:
        raise RuntimeError("离合机构板必须贴合前后仓隔板后表面")
    if n(contract, "partitionBossPerCellCount") != 4:
        raise RuntimeError("每个抽屉格必须提供四个角部定位 Boss")
    if n(contract, "partitionBossCount") != n(contract, "partitionBossPerCellCount") * 15:
        raise RuntimeError("前后仓隔板必须把四角 Boss 重复到 15 个抽屉格")
    if n(contract, "plateFastenerCount") != 4:
        raise RuntimeError("离合机构板必须保留四个自攻螺丝固定点")
    if n(contract, "partitionBossHeightMm") >= n(contract, "plateThicknessMm"):
        raise RuntimeError("定位 Boss 高度不能达到离合机构板后表面")
    expect(
        contract,
        "partitionBossHeightDeficitMm",
        0.50,
        "定位 Boss 相对机构板的高度差",
    )
    if n(contract, "partitionBossCenterOffsetXMm") != 12.0 or n(contract, "partitionBossCenterOffsetYMm") != 4.0:
        raise RuntimeError("每格四角 Boss 必须复用机构板四角安装坐标")
    if n(contract, "partitionSelfTapPilotDepthMm") <= 0:
        raise RuntimeError("隔板自攻螺丝导孔深度无效")
    expect(
        contract,
        "partitionSelfTapPilotDepthMm",
        n(contract, "partitionBossHeightMm")
        - n(contract, "partitionSelfTapBottomWallMm"),
        "Boss 内自攻螺丝导孔底厚",
    )

    frozen = {
        "openGapMm": 0.60, "dogInsertionMm": 2.40, "strokeMm": 3.00,
        "pocketDepthMm": 3.25, "bottomClearanceMm": 0.85,
        "magnetNonContactClearanceMm": 0.40, "femaleMagnetProjectionMm": 0.45,
        "magnetNominalDiameterMm": 2.00, "dogPocketPhaseDeg": 60.00,
        "linearBearingNominalIdMm": 3.00, "linearBearingNominalOdMm": 7.00,
        "linearBearingNominalLengthMm": 10.00, "linearBearingCount": 1.0,
        "linearBearingCenterYOffsetMm": -5.40,
        "linearBearingInputRotorClearanceMm": 0.40,
        "linearBearingSeatDiameterMm": 7.20,
        "linearBearingSeatRadialClearanceMm": 0.10, "linearBearingBlockWidthMm": 18.00,
        "linearBearingBlockYLengthMm": 10.00, "linearBearingBlockZMarginMm": 1.00,
        "linearBearingBlockZLengthMm": 20.5208,
        "linearBearingBlockMountHoleDiameterMm": 0.00,
        "linearBearingBlockMountHoleCount": 0.0,
        "linearBearingBlockMountXOffsetMm": 0.00,
        "linearBearingBlockMountYOffsetMm": 0.00,
        "inputShaftUpperDStartMm": -0.40, "inputShaftUpperDLengthMm": 3.60,
        "inputShaftRoundStartMm": -17.00, "inputShaftRoundLengthMm": 16.80,
        "inputShaftRoundDiameterMm": 3.00, "inputShaftLowerDStartMm": -16.80,
        "inputShaftLowerDLengthMm": 3.60, "inputSleeveTopOffsetMm": -13.40,
        "inputSleeveUpperDHeightMm": 4.20, "inputSleeveUpperDDiameterMm": 7.60,
        "inputSleeveLowerRoundOuterDiameterMm": 8.00,
        "inputSleeveLowerRoundHeightMm": 6.40, "inputSleeveDSocketDepthMm": 3.60,
        "inputSleeveDSocketClearanceMm": 0.16,
        "inputSleeveMagnetNominalDiameterMm": 5.00,
        "inputSleeveMagnetNominalLengthMm": 5.00,
        "inputSleeveMagnetPocketDiameterMm": 5.20,
        "inputSleeveMagnetPocketDepthMm": 5.20,
        "inputSleeveMagnetBottomClearanceMm": 1.20,
        "outputShaftStartMm": -3.40, "outputShaftLengthMm": 11.00,
        "outputShaftDStartMm": -3.40, "outputShaftDLengthMm": 3.60,
        "outputShaftRoundStartMm": -0.20, "outputShaftRoundLengthMm": 7.80,
        "outputShaftRoundDiameterMm": 3.00,
        "outputShaftTopProtrusionMm": 0.80,
        "outputShaftMotherSocketOverlapMm": 3.00,
        "outputBearingCount": 2.0, "bearingCount": 2.0,
        "bearingSeatDiameterMm": 6.10, "bearingSeatDepthMm": 2.60,
        "bearingBackShoulderMm": 0.60, "bearingReferenceCenterOffsetMm": 0.00,
        "bearingCenterOffsetMm": 1.40, "bearingPairSpacingMm": 4.40,
        "outputBearingBarWidthMm": 14.00,
        "outputBearingBarYLengthMm": 6.40,
        "outputBearingBarY0OffsetMm": 0.40,
        "outputBearingBarZLengthMm": 20.2208,
        "outputBearingBarZMarginMm": 1.00,
        "outputBearingBarMotherClearanceMm": 0.40,
        "outputBearingBarPlateOverlapMm": 0.20,
        "matingMagnetCount": 2.0, "inputSleeveMagnetCount": 1.0,
        "totalModeledMagnetCount": 3.0, "plateWidthMm": 34.00,
        "plateThicknessMm": 3.20, "platePartitionGapMm": 0.00,
        "plateFastenerCount": 4.0, "plateM3ClearanceMm": 3.40,
        "partitionSelfTapPilotDiameterMm": 2.40,
        "partitionSelfTapPilotDepthMm": 2.20,
        "partitionSelfTapBottomWallMm": 0.50,
        "partitionBossPerCellCount": 4.0,
        "partitionBossCount": 60.0,
        "partitionBossCenterOffsetXMm": 12.00,
        "partitionBossCenterOffsetYMm": 4.00,
        "partitionBossOuterDiameterMm": 5.00,
        "partitionBossHeightMm": 2.70,
        "partitionBossHeightDeficitMm": 0.50,
        "drawerShelfThicknessMm": 2.40,
        "frontTimingBearingWidthMm": 2.00,
        "frontTimingBearingIdMm": 3.00,
        "frontTimingBearingOdMm": 6.00,
        "frontTimingBearingSeatDiameterMm": 6.10,
        "frontTimingBearingSeatDepthMm": 2.00,
        "frontTimingBearingRetainerThicknessMm": 0.40,
        "frontTimingBearingRetainerBoreDiameterMm": 3.40,
        "drawerGuideRailClearanceMm": 0.30,
        "drawerGuideRailWallThicknessMm": 1.20,
        "drawerGuideSlotHeightMm": 3.60,
        "drawerGuideRailDepthMm": 4.50,
        "drawerGuideFlangeThicknessMm": 2.40,
        "drawerGuideFlangeProjectionMm": 3.00,
        "drawerGuideFlangeClearanceMm": 0.30,
        "drawerGuideFlangeBackClearanceMm": 0.60,
        "drawerGuideFrontSupportClearanceMm": 0.00,
        "plateBeltPassageSlotCount": 2.0,
        "plateBeltPassageRadialClearanceMm": 0.45,
        "plateBeltPassageAxialClearanceMm": 0.45,
        "partitionBeltPassageWindowCount": 15.0,
        "partitionBeltPassage2GTWindowCount": 15.0,
        "partitionBeltPassagePlateThicknessMm": 3.0,
        "partitionBeltPassageRadialClearanceMm": 0.90,
        "partitionBeltPassageAxialClearanceMm": 0.45,
    }
    for key, value in frozen.items():
        expect(contract, key, value, f"中心离合冻结值 {key}")

    bearing_top = (n(contract, "linearBearingCenterYOffsetMm")
                   + n(contract, "linearBearingNominalLengthMm") / 2)
    if abs(bearing_top + n(contract, "linearBearingInputRotorClearanceMm")) > 0.001:
        raise RuntimeError("LM3UU/一体座上沿与公轮下沿间隙推导不一致")
    if not 0.30 - 0.001 <= n(contract, "linearBearingInputRotorClearanceMm") <= 0.60 + 0.001:
        raise RuntimeError("LM3UU/公轮上沿间隙必须保持 0.30-0.60 mm")

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

    if contract.get("snakeChainHeightDatum") != "input-sleeve-magnet-bottom":
        raise RuntimeError("蛇链高度基准必须锁定公轮底部 M5 磁铁下沿")
    expected_magnet_bottom = (
        n(contract, "inputBaseYMm")
        + n(contract, "inputSleeveTopOffsetMm")
        - n(contract, "inputSleeveUpperDHeightMm")
        - n(contract, "inputSleeveLowerRoundHeightMm")
        + 0.10
    )
    expect(
        contract,
        "inputSleeveMagnetOpenBottomYMm",
        expected_magnet_bottom,
        "公轮底部磁铁开位下沿",
    )
    if n(contract, "snakeChainReferenceRow") != n(contract, "centerRow") - 1:
        raise RuntimeError("蛇链参考服务行必须对应中心离合下方的服务行")
    expected_reference_path = (
        n(contract, "drawerShelfTopYMm")
        - (n(contract, "centerRow") - n(contract, "snakeChainReferenceRow"))
        * (n(contract, "drawerBayHeightMm") + n(contract, "drawerShelfThicknessMm"))
        + n(contract, "drawerBayHeightMm") / 2
    )
    expect(
        contract,
        "snakeChainReferencePathCenterYMm",
        expected_reference_path,
        "蛇链参考服务行中心高度",
    )
    expect(contract, "snakeChainLinkTopOffsetMm", 2.15, "03C 链节上沿偏移")
    expected_shift = (
        n(contract, "inputSleeveMagnetOpenBottomYMm")
        - n(contract, "snakeChainLinkTopOffsetMm")
        - n(contract, "snakeChainReferencePathCenterYMm")
    )
    expect(contract, "snakeChainVerticalShiftMm", expected_shift, "蛇链服务层高度偏移")
    expect(
        contract,
        "snakeChainServicePathCenterYMm",
        expected_reference_path
        - (n(contract, "drawerBayHeightMm") + n(contract, "drawerShelfThicknessMm"))
        + n(contract, "snakeChainVerticalShiftMm"),
        "蛇链服务层中心高度",
    )
    expect(
        contract,
        "snakeChainReturnGuideCenterYMm",
        41.20,
        "蛇链回程导向轮中心高度",
    )
    expect(
        contract,
        "snakeChainTriggerMagnetDiameterMm",
        2.0,
        "蛇链触发磁铁直径",
    )
    expect(
        contract,
        "snakeChainTriggerMagnetLengthMm",
        1.8,
        "蛇链触发磁铁长度",
    )
    expect(
        contract,
        "snakeChainTriggerMagnetNormalOffsetMm",
        1.15,
        "蛇链触发磁铁上沿偏移",
    )
    expect(
        contract,
        "snakeChainTriggerMagnetTopClearanceMm",
        0.0,
        "蛇链触发磁铁上沿基准余量",
    )
    expect(
        contract,
        "snakeChainTriggerMagnetAxialStartOffsetMm",
        2.44,
        "蛇链触发磁铁轴向起点",
    )
    if n(contract, "snakeChainTriggerMagnetSegmentIndex") != 143:
        raise RuntimeError("蛇链触发磁铁节号必须落在中心服务直线段 143")

    if abs(n(contract, "bearingReferenceCenterOffsetMm")) > 0.001:
        raise RuntimeError("输出轴承参考件必须与长方条轴承孔同心")
    if n(contract, "bearingSeatDepthMm") < n(contract, "bearingBackShoulderMm") + 2.0:
        raise RuntimeError("输出 3x6x2 轴承座深度不足")
    if n(contract, "outputBearingBarWidthMm") <= n(contract, "bearingSeatDiameterMm") + 2.0:
        raise RuntimeError("输出轴承长方条孔周围壁厚不足")
    if n(contract, "outputBearingBarYLengthMm") < 2 * n(contract, "bearingSeatDepthMm") - 2.0 + 1.0:
        raise RuntimeError("输出轴承长方条无法容纳上下两个轴承孔")
    if n(contract, "outputBearingBarZLengthMm") <= n(contract, "outputBearingBarZMarginMm"):
        raise RuntimeError("输出轴承长方条没有接到机构板")
    if n(contract, "outputBearingBarMotherClearanceMm") <= 0:
        raise RuntimeError("母轮与输出轴承固定条没有防摩擦间隙")

    bar_y0 = n(contract, "outputBearingBarY0OffsetMm")
    bar_y1 = bar_y0 + n(contract, "outputBearingBarYLengthMm")
    lower_center = n(contract, "bearingCenterOffsetMm")
    upper_center = lower_center + n(contract, "bearingPairSpacingMm")
    if abs(lower_center - (bar_y0 + 1.0)) > 0.001:
        raise RuntimeError("下输出轴承没有落在长方条下端孔内")
    if abs(upper_center - (bar_y1 - 1.0)) > 0.001:
        raise RuntimeError("上输出轴承没有落在长方条上端孔内")
    if bar_y1 - n(contract, "bearingSeatDepthMm") - (bar_y0 + n(contract, "bearingSeatDepthMm")) < 1.0 - 0.001:
        raise RuntimeError("上下输出轴承孔之间没有保留中间实体隔墙")

    d_start = n(contract, "outputShaftDStartMm")
    d_end = d_start + n(contract, "outputShaftDLengthMm")
    round_start = n(contract, "outputShaftRoundStartMm")
    round_end = round_start + n(contract, "outputShaftRoundLengthMm")
    if d_start > -3.0 + 0.001 or d_end < 0.0 - 0.001:
        raise RuntimeError("输出 D 轴没有完整进入母轮 3 mm 盲孔")
    if round_start > d_end + 0.001 or round_end < d_start - 0.001:
        raise RuntimeError("输出 D 轴到圆轴没有形成短过渡")
    if round_start > lower_center - 1.0 + 0.001 or round_end < upper_center + 1.0 - 0.001:
        raise RuntimeError("输出圆轴没有穿过上下两枚 3x6x2 轴承")
    if abs(min(d_end, 0.0) - max(d_start, -3.0)
           - n(contract, "outputShaftMotherSocketOverlapMm")) > 0.001:
        raise RuntimeError("输出 D 轴与母轮盲孔重叠量不一致")
    if abs(round_end - bar_y1 - n(contract, "outputShaftTopProtrusionMm")) > 0.001:
        raise RuntimeError("输出圆轴上端露出量不一致")
    if abs(round_end - n(contract, "outputShaftStartMm")
           - n(contract, "outputShaftLengthMm")) > 0.001:
        raise RuntimeError("输出轴总长度没有覆盖 D 到圆轴端")

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
    if n(contract, "plateBeltPassageSlotCount") != 2:
        raise RuntimeError("机构板必须只为中心皮带保留左右两个穿板槽")
    if n(contract, "plateBeltPassageSlotCenterOffsetMm") <= 0:
        raise RuntimeError("机构板皮带槽中心偏移无效")
    if n(contract, "plateBeltPassageSlotWidthMm") <= 0:
        raise RuntimeError("机构板皮带槽宽度无效")
    if abs(
        n(contract, "plateBeltPassageSlotCenterOffsetMm")
        + n(contract, "plateBeltPassageSlotWidthMm") / 2
        - n(contract, "plateBeltPassageHalfWidthMm")
    ) > 0.001:
        raise RuntimeError("机构板皮带槽外包络没有由槽中心和槽宽推导")
    if n(contract, "plateBeltPassageAxialWidthMm") <= 6.0:
        raise RuntimeError("机构板贯穿槽没有覆盖 6 mm 皮带宽度")
    if n(contract, "plateBeltPassageHalfWidthMm") >= n(contract, "plateWidthMm") / 2:
        raise RuntimeError("机构板贯穿槽穿出侧壁")
    if contract.get("partitionBeltPassageType") != "per-drawer-cell-2GT-straight-run-windows":
        raise RuntimeError("前后仓隔板必须使用逐抽屉格统一 2GT 直线段窗口")
    if n(contract, "partitionBeltPassageWindowCount") != 15:
        raise RuntimeError("前后仓隔板必须有 5×3 共 15 个抽屉格皮带窗口")
    if n(contract, "partitionBeltPassage2GTWindowCount") != 15:
        raise RuntimeError("前后仓隔板的 15 个窗口必须全部使用 2GT 包络")
    if abs(
        n(contract, "partitionBeltPassageCenterXMm")
        - n(contract, "axisXMm")
    ) > 0.001:
        raise RuntimeError("前后仓隔板皮带窗口没有对准中心离合轴线")
    if abs(
        n(contract, "partitionBeltPassageCenterYMm")
        - n(contract, "frontTimingBeltYMm")
    ) > 0.001:
        raise RuntimeError("前后仓隔板皮带窗口没有对准真实皮带中心高度")
    if abs(n(contract, "partitionBeltPassageRelativeXMm")) > 0.001:
        raise RuntimeError("前后仓隔板皮带窗口相对 X 必须统一")
    if abs(n(contract, "partitionBeltPassageRelativeYMm")) >= n(contract, "drawerBayHeightMm") / 2:
        raise RuntimeError("前后仓隔板皮带窗口相对 Y 超出抽屉格")
    if n(contract, "partitionBeltPassagePlateThicknessMm") <= 0:
        raise RuntimeError("前后仓隔板厚度无效")
    if n(contract, "partitionBeltPassageHalfWidthMm") <= n(contract, "beltEnvelopeRadiusMm"):
        raise RuntimeError("前后仓隔板皮带窗口没有包住真实皮带包络")
    if n(contract, "partitionBeltPassageAxialWidthMm") <= 6.0:
        raise RuntimeError("前后仓隔板皮带窗口没有覆盖 6 mm 皮带宽度")
    partition_z = n(contract, "partitionBeltPassagePlateZMm")
    belt_z0 = min(n(contract, "axisZMm"), n(contract, "frontTimingPulleyZMm"))
    belt_z1 = max(n(contract, "axisZMm"), n(contract, "frontTimingPulleyZMm"))
    if not belt_z0 < partition_z < belt_z1:
        raise RuntimeError("前后仓隔板皮带窗口没有穿过中心皮带直线段")
    if n(contract, "outputShaftRoundDiameterMm") != n(contract, "shaftDiameterMm"):
        raise RuntimeError("输出圆轴直径必须与 3 mm D 轴名义尺寸一致")
    if n(contract, "centerCol") != 2 or n(contract, "centerRow") != 1:
        raise RuntimeError("当前契约必须锁定三层柜体中心格（零基准 2,1）")
    if n(contract, "drawerStationInstanceCount") != 14:
        raise RuntimeError("中心同款离合总成模板必须由 14 个非中心实例补齐 5×3 世界总装")
    if n(contract, "drawerColumnCount") != 5:
        raise RuntimeError("当前中心同款离合总成模板实例布局必须锁定 5 列")
    if n(contract, "drawerStationColumnPitchMm") <= 0 or n(contract, "drawerStationRowPitchMm") <= 0:
        raise RuntimeError("中心同款离合总成模板实例间距必须为正")
    if n(contract, "frontTimingPulleyDrawerRow") != n(contract, "centerRow") - 1:
        raise RuntimeError("前端同步轮必须落在中心抽屉的下一层格口")
    if n(contract, "drawerLayerCount") != 3 or n(contract, "serviceLayerCount") != 1:
        raise RuntimeError("当前柜体必须是三层抽屉加一层服务空间")
    if n(contract, "drawerBayHeightMm") < 55.29:
        raise RuntimeError("三层抽屉净高没有达到 55.30 mm 方案值")
    if n(contract, "drawerRackBodyHeightMm") <= 0:
        raise RuntimeError("抽屉底部齿条背板高度无效")
    if n(contract, "drawerRackBodyWidthMm") <= 0:
        raise RuntimeError("抽屉底部齿条背板宽度无效")
    if n(contract, "drawerRackToothHeightMm") <= 0:
        raise RuntimeError("抽屉底部直齿高度无效")
    if n(contract, "centerFrontDriveLiftMm") <= 0:
        raise RuntimeError("中心前端驱动必须整体上移到完整层板上方")
    if n(contract, "frontRackAboveShelfGapMm") < 0.05 - 0.001:
        raise RuntimeError("直齿排下沿必须与层板上沿保留至少 0.05 mm")
    if n(contract, "drawerRackLowerYMm") <= n(contract, "drawerShelfTopYMm"):
        raise RuntimeError("直齿排下沿仍沉入完整层板")
    if abs(
        n(contract, "drawerRackLowerYMm")
        - n(contract, "drawerShelfTopYMm")
        - n(contract, "frontRackAboveShelfGapMm")
    ) > 0.001:
        raise RuntimeError("直齿排下沿/层板上沿间隙推导不一致")
    if abs(
        n(contract, "frontTimingBearingUpperFaceYMm")
        - n(contract, "drawerShelfTopYMm")
    ) > 0.001:
        raise RuntimeError("层间轴承上沿必须与层板上沿齐平")
    if n(contract, "frontTimingBearingReinforcementDiscDiameterMm") <= n(contract, "frontTimingBearingOdMm"):
        raise RuntimeError("层间轴承下方加固圆盘必须大于轴承外径")
    if n(contract, "frontTimingBearingReinforcementDiscThicknessMm") <= 0:
        raise RuntimeError("层间轴承下方加固圆盘厚度无效")
    if n(contract, "drawerGuideBearingSeatDiameterMm") <= 3.0:
        raise RuntimeError("681 导向轴承座孔没有保留打印配合余量")
    if n(contract, "drawerFrontPinionBearingSeatDiameterMm") <= 6.0:
        raise RuntimeError("前端层板 3x6x2 轴承座孔没有保留打印配合余量")
    if abs(n(contract, "frontPinionCenterYMm") - n(contract, "drawerRackYMm")) > 0.001:
        raise RuntimeError("前端主动轮必须与抽屉底部直线齿排同高")
    if abs(
        n(contract, "frontPinionLowerFaceYMm")
        - (n(contract, "frontPinionCenterYMm")
           - n(contract, "frontPinionThicknessMm") / 2)
    ) > 0.001:
        raise RuntimeError("前端主动轮下沿推导不一致")
    if abs(
        n(contract, "frontTimingPulleyCenterYMm")
        - n(contract, "frontTimingBeltYMm")
    ) > 0.001:
        raise RuntimeError("前端同步轮中心必须跟随 2GT 皮带中心")
    if abs(
        n(contract, "frontTimingBearingUpperFaceYMm")
        - (n(contract, "frontTimingBearingCenterYMm")
           + n(contract, "frontTimingBearingWidthMm") / 2)
    ) > 0.001 or abs(
        n(contract, "frontTimingBearingLowerFaceYMm")
        - (n(contract, "frontTimingBearingCenterYMm")
           - n(contract, "frontTimingBearingWidthMm") / 2)
    ) > 0.001:
        raise RuntimeError("层间同步轮轴承上下沿推导不一致")
    if abs(
        n(contract, "frontTimingBearingUpperFaceYMm")
        + n(contract, "frontTimingBearingGearClearanceMm")
        - n(contract, "frontPinionLowerFaceYMm")
    ) > 0.001:
        raise RuntimeError("层间轴承上沿没有与主动轮保持间隙")
    if abs(
        n(contract, "frontTimingPulleyTopYMm")
        + n(contract, "frontTimingBearingPulleyClearanceMm")
        - n(contract, "frontTimingBearingLowerFaceYMm")
    ) > 0.001:
        raise RuntimeError("同步轮上沿没有与层间轴承保持间隙")
    if abs(
        n(contract, "frontTimingPulleyToPinionGapMm")
        - (n(contract, "frontPinionLowerFaceYMm")
           - n(contract, "frontTimingPulleyTopYMm"))
    ) > 0.001:
        raise RuntimeError("同步轮/主动轮总层间间距推导不一致")
    if n(contract, "frontTimingBearingWidthMm") <= 0:
        raise RuntimeError("层间同步轮轴承厚度无效")
    if n(contract, "frontTimingBearingWidthMm") >= n(contract, "drawerShelfThicknessMm"):
        raise RuntimeError("3x6x2 轴承必须在层板内留下底部承托肩")
    if abs(
        n(contract, "frontTimingBearingSeatDepthMm")
        - n(contract, "frontTimingBearingWidthMm")
    ) > 0.001:
        raise RuntimeError("层板轴承座深度必须等于 3x6x2 轴承宽度")
    if abs(
        n(contract, "frontTimingBearingRetainerThicknessMm")
        - n(contract, "drawerShelfThicknessMm")
        + n(contract, "frontTimingBearingWidthMm")
    ) > 0.001:
        raise RuntimeError("层板轴承底部承托肩厚度推导不一致")
    if n(contract, "frontTimingBearingRetainerBoreDiameterMm") <= n(contract, "frontTimingBearingIdMm"):
        raise RuntimeError("层板轴承底部承托孔没有给 D 轴留通道")
    if n(contract, "frontTimingBearingRetainerBoreDiameterMm") >= n(contract, "frontTimingBearingOdMm"):
        raise RuntimeError("层板轴承底部承托孔不能切掉轴承外圈承托面")
    if abs(
        n(contract, "frontTimingBearingBossBottomYMm")
        + n(contract, "frontTimingBearingRetainerThicknessMm")
        + n(contract, "frontTimingBearingReinforcementDiscThicknessMm")
        - n(contract, "frontTimingBearingLowerFaceYMm")
    ) > 0.001:
        raise RuntimeError("层板轴承底部 Boss 与承托肩不一致")
    if n(contract, "frontTimingBearingShelfLowerFaceYMm") <= n(contract, "frontTimingBearingBossBottomYMm"):
        raise RuntimeError("层板一体轴承座没有从层板下侧连续落到承托肩")
    if n(contract, "frontTimingBearingBossFusionOverlapMm") <= 0:
        raise RuntimeError("层板一体轴承座必须保留正的实体融合重叠量")
    if n(contract, "drawerGuideSlotHeightMm") <= n(contract, "drawerGuideBearingSeatDiameterMm"):
        raise RuntimeError("C 形导向槽高度不足以容纳 681 轴承")
    if n(contract, "drawerGuideFlangeThicknessMm") >= n(contract, "drawerGuideSlotHeightMm"):
        raise RuntimeError("抽屉侧向导轨凸缘没有留出 C 槽上下间隙")
    if n(contract, "drawerGuideRailDepthMm") <= n(contract, "drawerGuideFlangeThicknessMm"):
        raise RuntimeError("C 形导向槽深度不足以捕获抽屉侧向凸缘")
    if n(contract, "drawerGuideRailDepthMm") <= (
        n(contract, "drawerGuideFlangeProjectionMm")
        + n(contract, "drawerGuideRailClearanceMm")
    ):
        raise RuntimeError("C 形导向槽深度不足以让抽屉凸缘在后壁前停止")
    expected_back_clearance = (
        n(contract, "drawerGuideRailDepthMm")
        + n(contract, "drawerGuideFlangeClearanceMm")
        - n(contract, "drawerGuideFlangeProjectionMm")
        - n(contract, "drawerGuideRailWallThicknessMm")
    )
    if abs(
        n(contract, "drawerGuideFlangeBackClearanceMm")
        - expected_back_clearance
    ) > 0.001:
        raise RuntimeError("C 形导向槽凸缘后壁净空推导不一致")
    if n(contract, "drawerGuideFlangeBackClearanceMm") < n(contract, "drawerGuideRailClearanceMm"):
        raise RuntimeError("C 形导向槽凸缘与后壁的净空不足")
    if n(contract, "drawerGuideFrontSupportClearanceMm") != 0:
        raise RuntimeError("前端下托 681 必须与抽屉凸缘保持名义承托接触")
    if n(contract, "frontTimingBearingSeatDiameterMm") <= n(contract, "frontTimingBearingOdMm"):
        raise RuntimeError("层间同步轮轴承座孔没有保留压入余量")
    if n(contract, "frontTimingBearingIdMm") != n(contract, "shaftDiameterMm"):
        raise RuntimeError("层间同步轮轴承内径必须与 D 轴直径一致")
    if n(contract, "frontDshaftLengthMm") <= n(contract, "frontTimingBearingWidthMm"):
        raise RuntimeError("前端 D 轴没有跨过层间轴承")
    if abs(
        n(contract, "frontTimingPulleyTopYMm")
        + n(contract, "frontTimingPulleyToPinionGapMm")
        + n(contract, "frontPinionThicknessMm") / 2
        - n(contract, "frontPinionCenterYMm")
    ) > 0.001:
        raise RuntimeError("前端 2GT 同步轮必须位于主动轮下方的固定层间距")


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
