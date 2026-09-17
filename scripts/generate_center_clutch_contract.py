#!/usr/bin/env python3
"""从 OpenSCAD 的中心离合参数回显生成唯一机械契约。"""

# ===== 分区：导入/依赖 =====
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

# ===== 分区：常量/配置 =====
MARKER = "CENTER_CLUTCH_CONTRACT_DYNAMIC"
REQUIRED = {
    "axis",
    "role",
    "verticalLayoutMode",
    "centerClutchVerticalLiftMm",
    "openGapMm",
    "dogInsertionMm",
    "strokeMm",
    "pocketDepthMm",
    "bottomClearanceMm",
    "magnetNonContactClearanceMm",
    "femaleMagnetProjectionMm",
    "magnetNominalDiameterMm",
    "maleBottomYMm",
    "dogPocketPhaseDeg",
    "actuation",
    "engageOnlyWhenStopped",
    "releaseBeforeReturn",
    "bearingReferenceCenterOffsetMm",
    "bearingCenterOffsetMm",
    "inputBearingCenterOffsetMm",
    "bearingPairSpacingMm",
    "bearingBlockThicknessMm",
    "bearingBlockWidthMm",
    "bearingBlockHeightMm",
    "guideRailXOffsetMm",
    "guideRailZOffsetMm",
    "guideRodXOffsetMm",
    "guideRodZOffsetMm",
    "guideRodDiameterMm",
    "guideRodCaptureMm",
    "guideRodY0Mm",
    "guideRodY1Mm",
    "linearBearingNominalIdMm",
    "linearBearingNominalOdMm",
    "linearBearingNominalLengthMm",
    "linearBearingCount",
    "linearBearingCenterYOffsetMm",
    "linearBearingSeatDiameterMm",
    "linearBearingSeatDepthMm",
    "linearBearingHolderOuterDiameterMm",
    "linearBearingHolderLengthMm",
    "linearBearingHolderBackShoulderMm",
    "linearBearingHolderFrontNeckDiameterMm",
    "linearBearingHolderFrontNeckLengthMm",
    "linearBearingRetainerInnerDiameterMm",
    "linearBearingRetainerOuterDiameterMm",
    "linearBearingRetainerThicknessMm",
    "linearBearingRetainerLipOuterDiameterMm",
    "linearBearingRetainerSkirtInnerDiameterMm",
    "linearBearingRetainerSkirtOuterDiameterMm",
    "linearBearingRetainerSkirtLengthMm",
    "linearBearingSeatRadialClearanceMm",
    "linearBearingRodNominalClearanceMm",
    "linearBearingModel",
    "linearBearingFitCouponPart",
    "linearBearingFitCouponGuideCount",
    "linearBearingFitCouponGuideXOffsetMm",
    "linearBearingPart",
    "linearBearingRetainerPart",
    "rotaryBearingArrangement",
    "linearBearingArrangement",
    "selectorShoeLinearBearingCollisionPart",
    "stopPadWidthMm",
    "stopPadXOffsetMm",
    "stopLugXOffsetMm",
    "stopLugWidthMm",
    "stopLugZOffsetMm",
    "stopLugHeightMm",
    "stopLugRouteXOffsetMm",
    "stopLugRouteWidthMm",
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
    "selectorShoeAnchorXMm",
    "selectorShoeAnchorYMm",
    "selectorShoeAnchorZMm",
    "selectorShoeMagnetFaceOffsetMm",
    "selectorShoeMagnetFaceYMm",
    "selectorShoeTriggerClearanceMm",
    "selectorShoeMagnetAxis",
    "selectorShoeChainAttachYMm",
    "selectorShoeChainAttachZMm",
    "selectorShoeChainAttachXMm",
    "selectorShoeChainContactDiameterMm",
    "selectorShoeSupportXOffsetMm",
    "selectorShoeSupportArmXOffsetMm",
    "selectorShoeSupportXWidthMm",
    "selectorShoeSupportChainYOverhangMm",
    "selectorShoeSupportChainZT",
    "selectorShoeSupportBridgeOverlapMm",
    "selectorShoeSupportDropMm",
    "selectorShoeSupportReachMm",
    "selectorShoeChainSupportPart",
    "selectorShoeBodyWidthMm",
    "selectorShoeBodyDepthMm",
    "selectorShoeBodyHeightMm",
    "selectorShoePocketRimHeightMm",
    "inputShaftStartMm",
    "inputShaftLengthMm",
    "outputShaftStartMm",
    "outputShaftLengthMm",
    "inputGearBandThicknessMm",
    "dBoreDepthMm",
    "bearingCountPerRotor",
}
FLOAT_KEYS = {
    "axisXMm",
    "axisZMm",
    "inputBaseYMm",
    "outputBaseYMm",
    "centerClutchVerticalLiftMm",
    "maleBottomYMm",
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
    "inputBearingCenterOffsetMm",
    "bearingPairSpacingMm",
    "bearingBlockThicknessMm",
    "bearingBlockWidthMm",
    "bearingBlockHeightMm",
    "guideRailXOffsetMm",
    "guideRailZOffsetMm",
    "guideRodXOffsetMm",
    "guideRodZOffsetMm",
    "guideRodDiameterMm",
    "guideRodCaptureMm",
    "guideRodY0Mm",
    "guideRodY1Mm",
    "linearBearingNominalIdMm",
    "linearBearingNominalOdMm",
    "linearBearingNominalLengthMm",
    "linearBearingCenterYOffsetMm",
    "linearBearingSeatDiameterMm",
    "linearBearingSeatDepthMm",
    "linearBearingHolderOuterDiameterMm",
    "linearBearingHolderLengthMm",
    "linearBearingHolderBackShoulderMm",
    "linearBearingHolderFrontNeckDiameterMm",
    "linearBearingHolderFrontNeckLengthMm",
    "linearBearingRetainerInnerDiameterMm",
    "linearBearingRetainerOuterDiameterMm",
    "linearBearingRetainerThicknessMm",
    "linearBearingRetainerLipOuterDiameterMm",
    "linearBearingRetainerSkirtInnerDiameterMm",
    "linearBearingRetainerSkirtOuterDiameterMm",
    "linearBearingRetainerSkirtLengthMm",
    "linearBearingSeatRadialClearanceMm",
    "linearBearingRodNominalClearanceMm",
    "linearBearingFitCouponGuideXOffsetMm",
    "stopPadWidthMm",
    "stopPadXOffsetMm",
    "stopLugXOffsetMm",
    "stopLugWidthMm",
    "stopLugZOffsetMm",
    "stopLugHeightMm",
    "stopLugRouteXOffsetMm",
    "stopLugRouteWidthMm",
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
    "selectorShoeAnchorXMm",
    "selectorShoeAnchorYMm",
    "selectorShoeAnchorZMm",
    "selectorShoeMagnetFaceOffsetMm",
    "selectorShoeMagnetFaceYMm",
    "selectorShoeTriggerClearanceMm",
    "selectorShoeChainAttachYMm",
    "selectorShoeChainAttachZMm",
    "selectorShoeChainAttachXMm",
    "selectorShoeChainContactDiameterMm",
    "selectorShoeSupportXOffsetMm",
    "selectorShoeSupportArmXOffsetMm",
    "selectorShoeSupportXWidthMm",
    "selectorShoeSupportChainYOverhangMm",
    "selectorShoeSupportChainZT",
    "selectorShoeSupportBridgeOverlapMm",
    "selectorShoeSupportDropMm",
    "selectorShoeSupportReachMm",
    "selectorShoeBodyWidthMm",
    "selectorShoeBodyDepthMm",
    "selectorShoeBodyHeightMm",
    "selectorShoePocketRimHeightMm",
    "inputShaftStartMm",
    "inputShaftLengthMm",
    "outputShaftStartMm",
    "outputShaftLengthMm",
    "inputGearBandThicknessMm",
    "dBoreDepthMm",
}
INT_KEYS = {
    "version",
    "bearingCountPerRotor",
    "linearBearingCount",
    "bearingCount",
    "shaftCount",
    "matingMagnetCount",
    "selectorMagnetCount",
    "totalMagnetCount",
    "linearBearingFitCouponGuideCount",
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
    if contract.get("verticalLayoutMode") != "center-clutch-lift":
        raise RuntimeError("中心离合垂直布局必须是整体上移的首件方案")
    if contract.get("selectorShoeCoordinateFrame") != "native-world":
        raise RuntimeError("磁力靴必须使用原生世界坐标")
    if contract.get("selectorShoeMagnetAxis") != "+Y":
        raise RuntimeError("磁力靴磁面必须朝世界 +Y，从公轮底部触发")
    if contract.get("actuation") != "permanent-magnet":
        raise RuntimeError("中心离合契约不是纯永磁动作")
    if contract.get("engageOnlyWhenStopped") is not True:
        raise RuntimeError("中心离合必须停稳后接合")
    if contract.get("releaseBeforeReturn") is not True:
        raise RuntimeError("中心离合必须释放后返回")
    if contract.get("rotaryBearingArrangement") != "two-per-rotor-axially-spaced":
        raise RuntimeError("转子旋转轴承必须是每个转子两枚、沿轴向分隔")
    if contract.get("linearBearingArrangement") != "single-under-male-rotor":
        raise RuntimeError("竖直直线轴承必须是公轮底下单枚、单根导杆")
    if contract.get("linearBearingModel") != "LM3UU-cutaway-reference":
        raise RuntimeError("直线轴承采购参考必须是 LM3UU 可识别模型")
    if contract.get("linearBearingFitCouponPart") \
            != "cabinet-clutch/center_linear_bearing_fit_coupon":
        raise RuntimeError("直线轴承配合测试片零件 ID 不匹配")
    if contract.get("selectorShoeChainSupportPart") \
            != "cabinet-clutch/center_selector_chain_support_contact":
        raise RuntimeError("磁力靴必须包含链条支撑接触见证零件")
    if contract.get("selectorShoeLinearBearingCollisionPart") \
            != "cabinet-clutch/center_selector_linear_bearing_collision":
        raise RuntimeError("磁力靴必须包含单直线轴承路径干涉见证零件")

    def number(key: str) -> float:
        value = contract.get(key)
        if not isinstance(value, (int, float)):
            raise RuntimeError(f"中心离合契约缺少数值字段: {key}")
        return float(value)

    frozen = {
        "centerClutchVerticalLiftMm": 5.00,
        "openGapMm": 0.60,
        "dogInsertionMm": 2.40,
        "strokeMm": 3.00,
        "pocketDepthMm": 3.25,
        "bottomClearanceMm": 0.85,
        "magnetNonContactClearanceMm": 0.40,
        "femaleMagnetProjectionMm": 0.45,
        "magnetNominalDiameterMm": 2.00,
        "selectorTriggerSpacingMm": 12.00,
        "guideRodDiameterMm": 3.00,
        "guideRodCaptureMm": 0.80,
        "linearBearingNominalIdMm": 3.00,
        "linearBearingNominalOdMm": 7.00,
        "linearBearingNominalLengthMm": 10.00,
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
        "linearBearingFitCouponGuideCount": 1.00,
        "linearBearingFitCouponGuideXOffsetMm": 0.00,
        "bearingSeatDiameterMm": 6.10,
        "bearingSeatDepthMm": 2.60,
        "bearingBackShoulderMm": 0.60,
        "bearingReferenceCenterOffsetMm": -0.60,
        "bearingCenterOffsetMm": 4.20,
        "inputBearingCenterOffsetMm": 7.50,
        "bearingPairSpacingMm": 4.00,
        "bearingBlockThicknessMm": 3.20,
        "bearingBlockWidthMm": 14.00,
        "bearingBlockHeightMm": 14.00,
        "guideRailXOffsetMm": 0.00,
        "guideRailZOffsetMm": -14.00,
        "guideRodXOffsetMm": 0.00,
        "guideRodZOffsetMm": -14.00,
        "linearBearingCenterYOffsetMm": -4.60,
        "carriageUprightCenterXOffsetMm": 6.20,
        "carriageUprightWidthMm": 2.00,
        "carriageUprightZ0Mm": 5.20,
        "carriageUprightHeightMm": 3.00,
        "carriageUprightY0Mm": -10.00,
        "carriageUprightLengthMm": 8.40,
        "dogPocketPhaseDeg": 60.00,
        "stopPadWidthMm": 4.00,
        "stopPadXOffsetMm": 0.60,
        "stopLugXOffsetMm": 8.00,
        "stopLugWidthMm": 4.00,
        "stopLugZOffsetMm": -8.20,
        "stopLugHeightMm": 2.00,
        "stopLugRouteXOffsetMm": 16.90,
        "stopLugRouteWidthMm": 0.80,
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
    if abs(
        number("guideRodY1Mm")
        - number("engagedStopY0Mm")
        - number("linearBearingRetainerThicknessMm")
        - number("guideRodCaptureMm")
    ) > 0.001:
        raise RuntimeError("合位导杆捕获端必须位于直线轴承压盖之后")
    if number("stopLugWidthMm") <= 0 or number("stopLugHeightMm") <= 0:
        raise RuntimeError("滑架独立硬止挡耳位尺寸无效")
    if number("stopLugZOffsetMm") + number("stopLugHeightMm") / 2 \
            >= -number("bearingBlockHeightMm") / 2 - 0.10:
        raise RuntimeError("滑架硬止挡耳位没有避开下方旋转轴承块")
    if number("stopLugXOffsetMm") - number("stopLugWidthMm") / 2 <= 0:
        raise RuntimeError("滑架硬止挡耳位没有位于中心支撑外侧")
    if number("stopLugRouteWidthMm") <= 0:
        raise RuntimeError("滑架硬止挡耳位外侧支撑宽度无效")
    route_inner_clearance = (
        number("stopLugRouteXOffsetMm")
        - number("stopLugRouteWidthMm") / 2
        - number("guideRailXOffsetMm")
        - number("linearBearingRetainerOuterDiameterMm") / 2
    )
    if route_inner_clearance < 0.30 - 0.001:
        raise RuntimeError("滑架硬止挡耳位外侧支撑没有避开直线轴承压盖")
    if abs(number("maleBottomYMm") - number("inputBaseYMm")) > 0.001:
        raise RuntimeError("公轮底部基准没有和输入公轮基准统一")
    if abs(
        number("selectorShoeMagnetFaceYMm")
        + number("selectorShoeTriggerClearanceMm")
        - number("maleBottomYMm")
    ) > 0.001:
        raise RuntimeError("磁力靴磁面没有落在公轮底部下方的触发间隙")
    if abs(
        number("selectorShoeTargetYMm")
        + number("selectorShoeMagnetFaceOffsetMm")
        - number("selectorShoeMagnetFaceYMm")
    ) > 0.001:
        raise RuntimeError("磁力靴磁面 Y 没有由其原生锚点推导")
    if number("bearingCountPerRotor") != 2:
        raise RuntimeError("每个转子必须使用两枚轴承形成轴向间距")
    if number("bearingSeatDepthMm") < number("bearingBackShoulderMm") + 2.0:
        raise RuntimeError("轴承座深度不足以容纳 3x6x2 轴承和后肩")
    if number("bearingCenterOffsetMm") <= number("bearingBlockThicknessMm"):
        raise RuntimeError("轴承中心偏置不足以让双轴承块脱离转子端面")
    if number("inputBearingCenterOffsetMm") <= number("bearingBlockThicknessMm"):
        raise RuntimeError("输入转子轴承中心偏置不足以让拨叉通道脱离旋转轴承块")
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
    if contract.get("selectorShoePart") != "cabinet-clutch/center_selector_shoe":
        raise RuntimeError("磁力靴零件 ID 不是原生中心离合零件")
    if number("selectorShoeAnchorXMm") != number("axisXMm") + 6.0:
        raise RuntimeError("磁力靴原生 X 锚点没有把 M_engage 对准公轮轴心")
    if abs(number("selectorShoeAnchorYMm") - number("selectorShoeTargetYMm")) > 0.001:
        raise RuntimeError("磁力靴 Y 锚点没有和目标基准统一")
    if abs(number("selectorShoeAnchorZMm") - number("selectorShoeZMm")) > 0.001:
        raise RuntimeError("磁力靴 Z 锚点没有和离合轴统一")
    if number("selectorShoeSupportXWidthMm") <= 0:
        raise RuntimeError("磁力靴链条支撑臂宽度无效")
    if number("selectorShoeSupportArmXOffsetMm") < 0:
        raise RuntimeError("磁力靴支撑臂导轨避让偏置不能为负")
    if abs(
        number("selectorShoeChainAttachXMm")
        - number("axisXMm")
        - number("selectorShoeSupportXOffsetMm")
    ) > 0.001:
        raise RuntimeError("磁力靴链条支撑 X 没有由轴心和支撑偏置推导")
    if number("selectorShoeChainContactDiameterMm") <= 0:
        raise RuntimeError("磁力靴链条支撑接触见证直径无效")
    if abs(number("selectorShoeChainAttachYMm") - 149.0) > 0.001:
        raise RuntimeError("磁力靴链条支撑 Y 没有落在蛇链层")
    if abs(number("selectorShoeChainAttachZMm") + 75.0) > 0.001:
        raise RuntimeError("磁力靴链条支撑 Z 没有落在蛇链层")
    if number("selectorShoeSupportDropMm") <= 0 or number("selectorShoeSupportReachMm") <= 0:
        raise RuntimeError("磁力靴链条支撑臂没有连接到既有蛇链平面")
    if number("linearBearingCount") != 1:
        raise RuntimeError("中心滑架必须配置一枚公轮底下直线轴承")
    if number("linearBearingFitCouponGuideCount") != 1:
        raise RuntimeError("直线轴承配合测试片必须只配置一根导杆")
    if abs(number("linearBearingFitCouponGuideXOffsetMm")) > 0.001:
        raise RuntimeError("单导杆配合测试片导杆必须位于中心 X")
    if abs(number("guideRodXOffsetMm") - number("guideRailXOffsetMm")) > 0.001 \
            or abs(number("guideRodZOffsetMm") - number("guideRailZOffsetMm")) > 0.001:
        raise RuntimeError("导杆位置字段与导轨兼容字段不一致")
    if abs(number("guideRodXOffsetMm")) > 0.001 \
            or number("guideRodZOffsetMm") >= -number("bearingBlockHeightMm") / 2:
        raise RuntimeError("单导杆没有位于公轮下方并避开旋转轴承块")
    expected_center_y_offset = (
        number("openTabY0Mm") - number("inputBaseYMm")
        + number("linearBearingHolderLengthMm") / 2
    )
    if abs(number("linearBearingCenterYOffsetMm") - expected_center_y_offset) > 0.001:
        raise RuntimeError("单直线轴承 Y 中心没有由滑架承载窗口推导")
    if abs(number("linearBearingNominalIdMm")
           - number("guideRodDiameterMm")) > 0.001:
        raise RuntimeError("直线轴承名义内径必须匹配 Ø3 导杆")
    if number("linearBearingNominalOdMm") <= number("linearBearingNominalIdMm"):
        raise RuntimeError("直线轴承内外径关系无效")
    if number("linearBearingNominalLengthMm") <= 0:
        raise RuntimeError("直线轴承长度无效")
    if abs(
        number("linearBearingSeatRadialClearanceMm")
        - (number("linearBearingSeatDiameterMm")
           - number("linearBearingNominalOdMm")) / 2
    ) > 0.001:
        raise RuntimeError("直线轴承座径向间隙没有由座孔和外径推导")
    if number("linearBearingSeatDiameterMm") <= number(
        "linearBearingNominalOdMm"
    ):
        raise RuntimeError("直线轴承座没有给采购件外径留装配间隙")
    if number("linearBearingHolderOuterDiameterMm") < number(
        "linearBearingSeatDiameterMm"
    ) + 4.0:
        raise RuntimeError("直线轴承套径向打印壁厚不足")
    if number("linearBearingSeatDepthMm") < (
        number("linearBearingHolderBackShoulderMm")
        + number("linearBearingNominalLengthMm")
    ):
        raise RuntimeError("直线轴承套座深度不足")
    if number("linearBearingHolderLengthMm") < (
        number("linearBearingHolderBackShoulderMm")
        + number("linearBearingNominalLengthMm")
        + number("linearBearingRetainerThicknessMm")
        - 0.001
    ):
        raise RuntimeError("直线轴承套长度不足以保留前端压盖空间")
    if number("linearBearingHolderFrontNeckDiameterMm") >= number(
        "linearBearingHolderOuterDiameterMm"
    ) or number("linearBearingHolderFrontNeckLengthMm") <= 0:
        raise RuntimeError("直线轴承套前端定位颈无效")
    if not (
        number("linearBearingRetainerInnerDiameterMm")
        > number("guideRodDiameterMm")
        and number("linearBearingRetainerInnerDiameterMm")
        < number("linearBearingNominalOdMm")
    ):
        raise RuntimeError("直线轴承压盖孔不能同时通过导杆并捕获轴承")
    if number("linearBearingRetainerOuterDiameterMm") <= number(
        "linearBearingHolderOuterDiameterMm"
    ) or number("linearBearingRetainerThicknessMm") <= 0:
        raise RuntimeError("直线轴承压盖外径/厚度无效")
    if number("linearBearingRetainerLipOuterDiameterMm") > number(
        "linearBearingNominalOdMm"
    ):
        raise RuntimeError("直线轴承压盖内唇超出轴承座包络")
    if number("linearBearingRetainerSkirtInnerDiameterMm") <= number(
        "linearBearingHolderFrontNeckDiameterMm"
    ):
        raise RuntimeError("直线轴承压盖定位裙边没有避开前端定位颈")
    if not (
        number("linearBearingRetainerSkirtOuterDiameterMm")
        > number("linearBearingRetainerSkirtInnerDiameterMm")
        and number("linearBearingRetainerSkirtLengthMm")
        >= number("linearBearingHolderFrontNeckLengthMm")
    ):
        raise RuntimeError("直线轴承压盖定位裙边无效")
    if number("linearBearingRodNominalClearanceMm") < -0.001:
        raise RuntimeError("直线轴承与导杆的名义孔径关系为负")
    holder_rotor_clearance = math.hypot(
        number("guideRailXOffsetMm"),
        number("guideRailZOffsetMm"),
    ) - number("linearBearingHolderOuterDiameterMm") / 2 \
        - number("inputTipRadiusMm")
    if holder_rotor_clearance < 0.45:
        raise RuntimeError("直线轴承套到输入公轮径向净空不足")
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
