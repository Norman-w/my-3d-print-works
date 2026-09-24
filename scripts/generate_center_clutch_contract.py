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
    "verticalSplineBearingSeatDepthMm", "verticalSplineBearingSeatShoulderMm",
    "verticalSplineBearingSeatBottomYMm",
    "verticalSplineBearingAxisZMm", "verticalSplineBearingCenterYMm",
    "verticalSplineBearingUpperCount", "verticalSplineBearingTotalCount",
    "verticalSplineBearingUpperPulleyTopYMm",
    "verticalSplineBearingUpperCarrierClearanceMm",
    "verticalSplineBearingUpperCarrierPlateX0Mm",
    "verticalSplineBearingUpperCarrierPlateX1Mm",
    "verticalSplineBearingUpperCarrierPlateXLengthMm",
    "verticalSplineBearingUpperCarrierPlateZ0Mm",
    "verticalSplineBearingUpperCarrierPlateZ1Mm",
    "verticalSplineBearingUpperCarrierPlateZLengthMm",
    "verticalSplineBearingUpperCarrierPlateBottomYMm",
    "verticalSplineBearingUpperCarrierPlateTopYMm",
    "verticalSplineBearingUpperCarrierPlateThicknessMm",
    "verticalSplineBearingUpperBossCount",
    "verticalSplineBearingUpperBossOdMm",
    "verticalSplineBearingUpperBossHeightMm",
    "verticalSplineBearingUpperBossTopYMm",
    "verticalSplineBearingUpperBossBottomYMm",
    "verticalSplineBearingUpperBossPilotDiameterMm",
    "verticalSplineBearingUpperBossPilotDepthMm",
    "verticalSplineBearingUpperBossPilotTopYMm",
    "verticalSplineBearingUpperCarrierBossClearDiameterMm",
    "verticalSplineBearingUpperBossMount",
    "verticalSplineBearingUpperSeatBottomYMm", "verticalSplineBearingUpperSeatTopYMm",
    "verticalSplineBearingUpperCenterYMm", "verticalSplineBearingUpperBearingTopYMm",
    "verticalSplineBearingUpperDStubEndYMm",
    "verticalSplineBearingCapBottomYMm", "verticalSplineBearingCapTopYMm",
    "verticalSplineBearingCarrierPlateX0Mm", "verticalSplineBearingCarrierPlateX1Mm",
    "verticalSplineBearingCarrierPlateXLengthMm",
    "verticalSplineBearingCarrierPlateZ0Mm", "verticalSplineBearingCarrierPlateZ1Mm",
    "verticalSplineBearingCarrierPlateZLengthMm",
    "verticalSplineBearingCarrierPlateBottomYMm", "verticalSplineBearingCarrierPlateTopYMm",
    "verticalSplineBearingCarrierPlateThicknessMm",
    "verticalSplineBearingCarrierBossCount",
    "verticalSplineBearingFloorBossOdMm", "verticalSplineBearingFloorBossBaseOdMm",
    "verticalSplineBearingFloorBossBaseHeightMm", "verticalSplineBearingFloorBossTopYMm",
    "verticalSplineBearingFloorBossHeightMm", "verticalSplineBearingFloorBossPilotDiameterMm",
    "verticalSplineBearingFloorBossPilotDepthMm", "verticalSplineBearingFloorBossPilotBottomYMm",
    "verticalSplineBearingCarrierBossClearDiameterMm",
    "verticalSplineBearingCarrierBossCounterboreDiameterMm",
    "verticalSplineBearingCarrierBossCounterboreDepthMm",
    "verticalSplineBearingCarrierBossMount",
    "verticalSplineBearingTowerBodyXWidthMm", "verticalSplineBearingTowerBodyZDepthMm",
    "verticalSplineBearingTowerBoreDiameterMm", "verticalSplineBearingTowerRootFlareHeightMm",
    "verticalSplineBearingTowerRootXWidthMm", "verticalSplineBearingTowerRootZDepthMm",
    "verticalSplineBearingTowerColumnDiameterMm",
    "verticalSplineBearingTowerCapC5XWidthMm", "verticalSplineBearingTowerCapZDepthMm",
    "verticalSplineBearingTowerCapC5ZDepthMm",
    "verticalSplineBearingC5RailWidthMm", "verticalSplineBearingC5RailZDepthMm",
    "verticalSplineBearingC5RailCenterOffsetXMm",
    "verticalSplineBearingC5RailBottomCenterOffsetXMm",
    "verticalSplineBearingC5RailRootWidthMm", "verticalSplineBearingC5RailRootZDepthMm",
    "verticalSplineBearingC5RailCornerRadiusMm", "verticalSplineBearingC5RailProfile",
    "verticalSplineBearingC5RailClearanceMm", "verticalSplineBearingC5RailBottomClearanceMm",
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
    "verticalSplineBearingUpperSupportPart",
    "verticalSplineBearingCarrierPart",
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
    "linearBearingPart", "linearBearingBlockPart",
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
    "snakeChainReturnDriveXTrimMm", "snakeChainServicePressXTrimMm",
    "snakeChainMotorXOffsetMm",
    "snakeChainTriggerMagnetSegmentIndex",
    "snakeChainTriggerMagnetDiameterMm", "snakeChainTriggerMagnetLengthMm",
    "snakeChainTriggerMagnetNormalOffsetMm",
    "snakeChainTriggerMagnetTopClearanceMm",
    "snakeChainTriggerMagnetAxialStartOffsetMm",
    "chainMotherSupportReliefMode",
    "chainMotherSupportReliefRadialClearanceMm",
    "chainMotherSupportReliefAxialClearanceMm",
    "chainMotherSupportReliefZMinMm",
    "chainMotherSupportReliefZMaxMm",
    "chainMotherSupportReliefBearingWebMm",
    "chainMotherSupportCollisionPart",
    "chainIdlerCount", "chainIdlerPartitionMountCount", "chainIdlerRowMountCount",
    "chainIdlerPowerWheelExcluded", "chainIdlerBearingNominal",
    "chainIdlerBearingIdMm", "chainIdlerBearingOdMm", "chainIdlerBearingWidthMm",
    "chainIdlerAxleAxis", "chainIdlerAxleProfile",
    "chainIdlerAxleSmoothDiameterMm", "chainIdlerAxleSmoothLengthMm",
    "chainIdlerThreadLengthMm", "chainIdlerThreadPilotDiameterMm",
    "chainIdlerThreadPilotDepthMm", "chainIdlerBossOuterDiameterMm",
    "chainIdlerBossRootDiameterMm", "chainIdlerBossRootFlareThicknessMm",
    "chainIdlerBossRootOverlapMm",
    "chainIdlerBossRearZMm", "chainIdlerBossAxialClearanceMm",
    "chainIdlerBossMountMode", "chainIdlerBossScrewEntry",
    "chainIdlerMountPart", "chainIdlerAxlePart",
    "chainMotherSupportEmbossMode",
    "chainMotherSupportEmbossForcePoint",
    "chainMotherSupportEmbossForceDirection",
    "chainMotherSupportEmbossForceMagnitudeScale",
    "chainMotherSupportEmbossBrushRadiusScale",
    "chainMotherSupportEmbossBrushAxialScale",
    "chainMotherSupportEmbossBrushFalloff",
    "chainMotherSupportEmbossDepthMm",
    "chainMotherSupportEmbossRootWidthMm",
    "chainMotherSupportEmbossRootMinimumWidthMm",
    "chainMotherSupportEmbossOuterWidthMm",
    "chainMotherSupportEmbossRootRadiusMm",
    "chainMotherSupportEmbossOuterRadiusMm",
    "chainMotherSupportEmbossRootOverlapMm",
    "chainMotherSupportEmbossZMarginMm",
    "chainMotherSupportEmbossRootSupportMarginMm",
    "chainMotherSupportEmbossRadialBulgeMm",
    "chainMotherSupportEmbossEdgeRadiusMm",
    "chainMotherSupportEmbossRootFilletRadiusMm",
    "chainMotherSupportEmbossRootFlareMm",
    "chainMotherSupportEmbossRootFilletSteps",
    "chainMotherSupportEmbossProfileSteps",
    "chainMotherSupportEmbossCapSteps",
    "chainMotherSupportEmbossPart",
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
    "partitionMountType", "partitionMountScrewEntry",
    "partitionMountInstallDirection", "partitionMountCount",
    "partitionMountPerSideCount", "partitionMountEdgeMarginMm",
    "partitionMountXSideLowYMm", "partitionMountXSideHighYMm",
    "partitionMountXPlusLowYMm", "partitionMountXPlusHighYMm",
    "partitionMountXMinusLowYMm", "partitionMountXMinusHighYMm",
    "partitionMountYSideLowXMm", "partitionMountYSideHighXMm",
    "partitionMountScrewAxes",
    "partitionReferenceReceiverLengthMm", "partitionReferenceReceiverHeightMm",
    "partitionReferenceReceiverThicknessMm", "partitionReferenceReceiverRadiusMm",
    "partitionReferenceReceiverStraightMm", "partitionReferenceReceiverHoleDiameterMm",
    "partitionReferenceReceiverCapDirection", "partitionReferenceReceiverProfile",
    "partitionReferenceCoverLengthMm", "partitionReferenceCoverHeightMm",
    "partitionReferenceCoverRadiusMm", "partitionReferenceCoverInnerRadiusMm",
    "partitionReferenceCoverStraightMm", "partitionReferenceCoverBaseDepthMm",
    "partitionReferenceCoverStepDepthMm", "partitionReferenceCoverTotalDepthMm",
    "partitionReferenceCoverHoleDiameterMm", "partitionReferenceCoverProfile",
    "partitionReferenceCoverScrewFaceRadiusMm",
    "partitionReferenceCoverScrewFaceStraightMm",
    "partitionReferenceCoverScrewFaceProfile",
    "partitionReferenceRoundSleeveOuterDiameterMm",
    "partitionReferenceRoundSleeveInnerDiameterMm",
    "partitionReferenceRoundSleeveLengthMm",
    "partitionReferenceRoundSleeveCollarDepthMm",
    "partitionMountSleeveEntryProfile",
    "partitionMountSleeveCrossSectionProfile",
    "partitionMountSleeveMouthProfile", "partitionMountSleeveMouthWidthMm",
    "partitionMountSleeveSupportType",
    "partitionMountSleeveSupportArmWidthMm",
    "partitionMountSleeveSupportArmLengthMm",
    "partitionMountSleeveSupportPlateOverlapMm",
    "partitionMountSleeveSupportRootOverlapMm",
    "partitionMountSleeveSupportRibWidthMm",
    "partitionMountSleeveSupportRibTangentClearanceMm",
    "partitionMountSleeveWallMm", "partitionMountSleeveLengthMm",
    "partitionMountCenterZMm",
    "partitionFramePlateClearanceMm", "partitionFramePlateX0Mm",
    "partitionFramePlateY0Mm", "partitionFramePlateWidthMm",
    "partitionFramePlateHeightMm", "partitionMountInsertionReliefWidthMm",
    "partitionMountInsertionReliefType",
    "partitionMountInsertionReliefDepthMm",
    "partitionMountInsertionReliefEndClearanceMm",
    "partitionServiceWindowType", "partitionServiceWindowX0Mm",
    "partitionServiceWindowX1Mm", "partitionServiceWindowY0Mm",
    "partitionServiceWindowY1Mm", "partitionServiceWindowWidthMm",
    "partitionServiceWindowHeightMm", "partitionServiceWindowCornerRadiusMm",
    "partitionServiceCutOvertravelMm",
    "partitionServiceXMinusOpenX0Mm", "partitionServiceXMinusOpenX1Mm",
    "partitionServiceXMinusOpenY0Mm", "partitionServiceXMinusOpenY1Mm",
    "partitionServiceXMinusOpenWidthMm", "partitionServiceXMinusOpenHeightMm",
    "partitionServiceYMinusOpenX0Mm", "partitionServiceYMinusOpenX1Mm",
    "partitionServiceYMinusOpenY0Mm", "partitionServiceYMinusOpenY1Mm",
    "partitionServiceYMinusOpenWidthMm", "partitionServiceYMinusOpenHeightMm",
    "partitionServiceXMinusOpenCornerRadiusMm",
    "partitionServiceYMinusOpenCornerRadiusMm",
    "partitionServiceMountPierHalfWidthMm",
    "partitionServiceRemainingGridWebXMm",
    "partitionServiceRemainingGridWebYMm",
    "partitionSleeveFrontOverlapMm",
    "partitionMountLoadPath", "partitionMountPanelRole",
    "engageOnlyWhenStopped", "releaseBeforeReturn",
    "inputSideAdditionalMechanism", "centerCol", "centerRow", "inputPart",
    "drawerLayerCount", "drawerColumnCount", "serviceLayerCount", "drawerBayHeightMm",
    "drawerShelfThicknessMm",
    "cabinetWidthMm", "serviceWidthMm", "gridWidthMm", "drawerBayWidthMm",
    "drawerColumnPitchMm", "rearClutchCarrierMode", "rearClutchRowPlateCount",
    "rearClutchRowPlateStationCount", "rearClutchRowPlateLengthMm",
    "rearClutchRowPlateX0Mm", "rearClutchRowPlateX1Mm",
    "rearClutchRowPlateLeftClearanceMm", "rearClutchRowPlateRightClearanceMm",
    "drawerStationTemplateOriginXMm", "drawerStationTemplateOriginYMm",
    "drawerStationColumnPitchMm", "drawerStationRowPitchMm",
    "drawerStationCount", "drawerStationInstanceCount", "stationDriveMode",
    "drawerRackBodyWidthMm", "drawerRackBodyHeightMm", "drawerRackPitchMm",
    "drawerRackGearTeeth", "drawerRackToothHeightMm", "drawerRackToothOverhangMm",
    "drawerBodyPart", "drawerBodyOuterWidthMm", "drawerBodyOuterHeightMm",
    "drawerBodyDepthMm", "drawerBodyRearZMm", "drawerBodyFrontZMm",
    "drawerBodyWallMm", "drawerBodyFloorMm", "drawerBodyFrontWallMm",
    "drawerBodyRearWallMm", "drawerBodyGuideReliefClearanceMm",
    "drawerBodyDriveClearanceMm",
    "frontTimingPulleyTeeth", "frontTimingBeltPitchMm",
    "drawerRackTravelMmPerShaftTurn", "frontTimingBeltAdvanceMmPerShaftTurn",
    "centerFrontDriveLiftMm", "frontRackAboveShelfGapMm",
    "drawerRackLowerYMm", "drawerShelfTopYMm",
    "frontTimingBearingReinforcementDiscDiameterMm",
    "frontTimingBearingReinforcementDiscThicknessMm",
    "drawerRackMount", "drawerMassLoadPath",
    "drawerGuideBearing", "drawerGuideRail",
    "drawerGuideBearingArrangement", "drawerGuideBearingAxis",
    "drawerGuideLoadPath", "drawerFrontPinionBearing",
    "drawerGuideRailSupport", "drawerGuideFlangeDirection",
    "drawerGuideRailClearanceMm", "drawerGuidePartitionThicknessMm",
    "drawerGuideRailAttachOverlapMm",
    "drawerGuideBearingSeatDiameterMm",
    "drawerGuideSlotHeightMm", "drawerGuideRailDepthMm",
    "drawerGuideFlangeThicknessMm", "drawerGuideFlangeProjectionMm",
    "drawerGuideFlangeClearanceMm", "drawerGuideDrawerEdgeInsetMm",
    "drawerGuideFlangeEndClearanceMm",
    "drawerGuideFrontSupportClearanceMm", "drawerGuideTailBearingAxis",
    "drawerGuideFrontBearingAxis",
    "drawerFrontPinionBearingSeatDiameterMm",
    "columnSyncBeltTeeth", "columnSyncBeltLengthMm",
    "columnSyncBeltCenterDistanceMm",
    "columnSyncTensionerReferenceBearingXMm",
    "columnSyncTensionerNominalXMm", "columnSyncTensionerAxisXMm",
    "columnSyncTensionerBearingAlignmentErrorXMm",
    "columnSyncTensionerBearingNominal", "columnSyncTensionerBearingCount",
    "columnSyncTensionerBearingIdMm", "columnSyncTensionerBearingOdMm",
    "columnSyncTensionerBearingWidthMm",
    "columnSyncTensionerBearingSeatDiameterMm",
    "columnSyncTensionerBearingCenterOffsetYMm",
    "columnSyncTensionerBearingReferenceMode",
    "columnSyncTensionerPulleyTotalHeightMm",
    "columnSyncTensionerSupportHeightYMm",
    "columnSyncTensionerSupportEdgeClearanceYMm",
    "columnSyncTensionerSupportRingCenterOffsetYMm",
    "columnSyncTensionerSupportPlacementMode",
    "columnSyncTensionerBearingAxis", "columnSyncTensionerBearingAxisXMm",
    "columnSyncTensionerBearingAxisZMm",
    "columnSyncTensionerLowerPulleyLowerEdgeYMm",
    "columnSyncTensionerLowerPulleyUpperEdgeYMm",
    "columnSyncTensionerUpperPulleyLowerEdgeYMm",
    "columnSyncTensionerUpperPulleyUpperEdgeYMm",
    "columnSyncTensionerLowerBearingCenterYMm",
    "columnSyncTensionerUpperBearingCenterYMm",
    "columnSyncTensionerSupportCenterXMm",
    "columnSyncTensionerSupportCenterZMm",
    "columnSyncTensionerUpperSupportCenterYMm",
    "columnSyncTensionerLowerSupportCenterYMm",
    "columnSyncTensionerOuterCShellMode",
    "columnSyncTensionerOuterCShellAxis",
    "columnSyncTensionerOuterCShellDepthXMm",
    "columnSyncTensionerOuterCShellJunctionOverlapMm",
    "columnSyncTensionerOuterCShellCutZMm",
    "columnSyncTensionerOuterCShellArmLengthZMm",
    "columnSyncTensionerOuterCShellHolePattern",
    "columnSyncTensionerOuterCShellClearanceMm",
    "columnSyncTensionerOuterCShellWallMm",
    "columnSyncTensionerOuterCShellBossCount",
    "columnSyncTensionerOuterCShellBossOdMm",
    "columnSyncTensionerOuterCShellBossLengthXMm",
    "columnSyncTensionerOuterCShellBossClearanceHoleMm",
    "columnSyncTensionerOuterCShellBossPilotDiameterMm",
    "columnSyncTensionerOuterCShellBossPilotDepthMm",
    "columnSyncTensionerOuterCShellBossPilotFloorMm",
    "columnSyncTensionerOuterCShellBossRadialClearanceMm",
    "columnSyncTensionerOuterCShellTStemClearanceMm",
    "columnSyncTensionerOuterCShellPart",
    "columnSyncTensionerOuterCShellCabinetBossPart",
    "outputPart", "outputBearingSupportPart", "mechanismPlatePart", "outputShaftPart",
    "outputBearingsPart",
}
FLOAT_KEYS = {
    key for key in REQUIRED if key.endswith("Mm") or key.endswith("Deg")
}
FLOAT_KEYS.update({
    "drawerRackTravelMmPerShaftTurn",
    "frontTimingBeltAdvanceMmPerShaftTurn",
    "chainMotherSupportEmbossForceMagnitudeScale",
    "chainMotherSupportEmbossBrushRadiusScale",
    "chainMotherSupportEmbossBrushAxialScale",
    "chainMotherSupportEmbossBrushFalloff",
})
INT_KEYS = {
    "version", "linearBearingCount", "linearBearingBlockMountHoleCount",
    "outputBearingCount", "bearingCount", "matingMagnetCount",
    "inputSleeveMagnetCount", "totalModeledMagnetCount", "centerCol", "centerRow",
    "drawerLayerCount", "drawerColumnCount", "serviceLayerCount", "frontTimingPulleyDrawerRow",
    "plateBeltPassageSlotCount", "partitionBeltPassageWindowCount",
    "partitionBeltPassage2GTWindowCount", "plateFastenerCount",
    "partitionMountCount", "partitionMountPerSideCount",
    "partitionBossPerCellCount", "partitionBossCount",
    "snakeChainReferenceRow",
    "snakeChainTriggerMagnetSegmentIndex",
    "columnSyncBeltTeeth",
    "columnSyncTensionerBearingCount",
    "columnSyncTensionerOuterCShellBossCount",
    "chainMotherSupportEmbossProfileSteps",
    "chainMotherSupportEmbossCapSteps",
    "chainMotherSupportEmbossRootFilletSteps",
    "chainIdlerCount", "chainIdlerPartitionMountCount", "chainIdlerRowMountCount",
    "verticalSplineBearingCount", "verticalSplineBearingUpperCount",
    "verticalSplineBearingTotalCount", "verticalSplineBearingCarrierBossCount",
    "verticalSplineBearingUpperBossCount",
    "verticalSplineBearingDetourColumn",
    "drawerStationCount", "drawerStationInstanceCount", "rearClutchRowPlateCount",
    "rearClutchRowPlateStationCount",
    "drawerRackGearTeeth", "frontTimingPulleyTeeth",
}
BOOL_KEYS = {
    "linearBearingMovesWithInput", "engageOnlyWhenStopped", "releaseBeforeReturn",
    "chainIdlerPowerWheelExcluded",
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
    if contract.get("rearClutchCarrierMode") != "row-strip":
        raise RuntimeError("后仓离合承载板必须是按抽屉层连续横向承载板")
    for key, value, label in (
        ("cabinetWidthMm", 250.0, "箱体总宽"),
        ("serviceWidthMm", 44.0, "X- 服务区宽度"),
        ("gridWidthMm", 199.6, "五列抽屉区净宽"),
        ("drawerBayWidthMm", 38.0, "抽屉格净宽"),
        ("drawerColumnPitchMm", 40.4, "抽屉列节距"),
        ("rearClutchRowPlateLengthMm", 195.6, "连续离合行板长度"),
        ("rearClutchRowPlateX0Mm", 49.2, "连续离合行板 X- 起点"),
        ("rearClutchRowPlateX1Mm", 244.8, "连续离合行板 X+ 终点"),
        ("rearClutchRowPlateLeftClearanceMm", 2.0, "连续离合行板左侧净空"),
        ("rearClutchRowPlateRightClearanceMm", 2.0, "连续离合行板右侧净空"),
    ):
        expect(contract, key, value, label)
    if n(contract, "rearClutchRowPlateCount") != 3:
        raise RuntimeError("后仓连续离合承载板必须按三层抽屉生成三条")
    if n(contract, "rearClutchRowPlateStationCount") != 5:
        raise RuntimeError("每条后仓连续离合承载板必须覆盖五个站点")
    expect(contract, "snakeChainReturnDriveXTrimMm", -4.00, "蛇链上方回程轮 X 相位偏移")
    expect(contract, "snakeChainServicePressXTrimMm", 16.00, "蛇链下方回程轮 X 相位偏移")
    expect(contract, "snakeChainMotorXOffsetMm", -2.00, "蛇链电机轮 X 偏移")
    expect(contract, "centerClutchDriveLayerOffsetMm", 0.0, "中心驱动层偏置")
    expect(contract, "centerClutchVerticalLiftMm", 0.0, "兼容垂直偏置")
    if n(contract, "columnSyncBeltTeeth") != 220:
        raise RuntimeError("列同步皮带必须使用 220T 2GT 闭环")
    expect(contract, "columnSyncBeltLengthMm", 440.0, "列同步皮带长度")
    if n(contract, "columnSyncBeltCenterDistanceMm") <= 0:
        raise RuntimeError("列同步皮带中心距无效")
    if abs(n(contract, "columnSyncTensionerBearingAlignmentErrorXMm")) > 0.45:
        raise RuntimeError("列同步张紧轮没有对到默认张紧轴承基准")
    if abs(
        n(contract, "columnSyncTensionerAxisXMm")
        - n(contract, "columnSyncTensionerNominalXMm")
    ) > 0.001:
        raise RuntimeError("列同步张紧轮轴位置没有保持在默认调节基准")
    if contract.get("columnSyncTensionerBearingNominal") != "3x6x2":
        raise RuntimeError("张紧轮轴承必须是 3x6x2")
    if contract.get("columnSyncTensionerBearingReferenceMode") != "existing-3x6x2-reference":
        raise RuntimeError("张紧轮必须复用既有 3x6x2 轴承参考件，不得新增独立轴承 STL")
    if contract.get("columnSyncTensionerSupportPlacementMode") != "pulley-edge-relative":
        raise RuntimeError("张紧轮支撑必须按皮带轮上下沿相对定位")
    if n(contract, "columnSyncTensionerBearingCount") != 2:
        raise RuntimeError("张紧轮必须安装上下两枚轴承")
    for key, value, label in (
        ("columnSyncTensionerBearingIdMm", 3.0, "张紧轮轴承内径"),
        ("columnSyncTensionerBearingOdMm", 6.0, "张紧轮轴承外径"),
        ("columnSyncTensionerBearingWidthMm", 2.0, "张紧轮轴承宽度"),
        ("columnSyncTensionerBearingSeatDiameterMm", 6.10, "张紧轮轴承座直径"),
    ):
        expect(contract, key, value, label)
    if contract.get("columnSyncTensionerBearingAxis") != "+Y":
        raise RuntimeError("张紧轮轴承轴向必须是世界 +Y")
    if abs(
        n(contract, "columnSyncTensionerBearingAxisXMm")
        - n(contract, "columnSyncTensionerAxisXMm")
    ) > 0.001:
        raise RuntimeError("张紧轮轴承 X 轴位没有对到张紧轮轴")
    if n(contract, "columnSyncTensionerUpperBearingCenterYMm") <= n(
        contract, "columnSyncTensionerLowerBearingCenterYMm"
    ):
        raise RuntimeError("张紧轮上下轴承中心 Y 轴位顺序无效")
    expect(
        contract,
        "columnSyncTensionerSupportCenterXMm",
        n(contract, "columnSyncTensionerBearingAxisXMm") + 5.4,
        "张紧轮支撑模板 X 中心",
    )
    expect(
        contract,
        "columnSyncTensionerSupportCenterZMm",
        n(contract, "columnSyncTensionerBearingAxisZMm") + 1.0,
        "张紧轮支撑模板 Z 中心",
    )
    if n(contract, "columnSyncTensionerUpperSupportCenterYMm") <= n(
        contract, "columnSyncTensionerLowerSupportCenterYMm"
    ):
        raise RuntimeError("张紧轮上下支撑模板中心 Y 轴位顺序无效")
    expect(
        contract,
        "columnSyncTensionerPulleyTotalHeightMm",
        8.8,
        "张紧轮总轴向高度",
    )
    expect(
        contract,
        "columnSyncTensionerSupportHeightYMm",
        9.0,
        "张紧轮支撑模板 Y 高度",
    )
    expect(
        contract,
        "columnSyncTensionerSupportEdgeClearanceYMm",
        0.6,
        "张紧轮支撑与皮带轮边缘净空",
    )
    expect(
        contract,
        "columnSyncTensionerSupportRingCenterOffsetYMm",
        1.0,
        "张紧轮支撑环相对模板中心偏移",
    )
    lower_pulley_lower = n(contract, "columnSyncTensionerLowerPulleyLowerEdgeYMm")
    lower_pulley_upper = n(contract, "columnSyncTensionerLowerPulleyUpperEdgeYMm")
    upper_pulley_lower = n(contract, "columnSyncTensionerUpperPulleyLowerEdgeYMm")
    upper_pulley_upper = n(contract, "columnSyncTensionerUpperPulleyUpperEdgeYMm")
    if not lower_pulley_lower < lower_pulley_upper < upper_pulley_lower < upper_pulley_upper:
        raise RuntimeError("张紧轮上下皮带轮边缘顺序无效")
    support_half_height = n(contract, "columnSyncTensionerSupportHeightYMm") / 2
    edge_clearance = n(contract, "columnSyncTensionerSupportEdgeClearanceYMm")
    if abs(
        n(contract, "columnSyncTensionerLowerSupportCenterYMm")
        - (lower_pulley_upper + support_half_height + edge_clearance)
    ) > 0.001:
        raise RuntimeError("下张紧支撑没有按下轮上沿向 Y+ 相对定位")
    if abs(
        n(contract, "columnSyncTensionerUpperSupportCenterYMm")
        - (upper_pulley_lower - support_half_height - edge_clearance)
    ) > 0.001:
        raise RuntimeError("上张紧支撑没有按上轮下沿向 Y− 相对定位")
    if n(contract, "columnSyncTensionerLowerSupportCenterYMm") - support_half_height <= lower_pulley_upper:
        raise RuntimeError("下张紧支撑仍与下皮带轮轴向包络重叠")
    if n(contract, "columnSyncTensionerUpperSupportCenterYMm") + support_half_height >= upper_pulley_lower:
        raise RuntimeError("上张紧支撑仍与上皮带轮轴向包络重叠")
    ring_offset = n(contract, "columnSyncTensionerSupportRingCenterOffsetYMm")
    if n(contract, "columnSyncTensionerLowerSupportCenterYMm") + ring_offset <= lower_pulley_lower:
        raise RuntimeError("下张紧支撑轴承环没有落在连续张紧轴跨度内")
    if n(contract, "columnSyncTensionerUpperSupportCenterYMm") + ring_offset >= upper_pulley_upper:
        raise RuntimeError("上张紧支撑轴承环没有落在连续张紧轴跨度内")
    if contract.get("columnSyncTensionerOuterCShellMode") != "low-x-wall-mounted-large-C-over-small-c":
        raise RuntimeError("张紧轮外包络必须是低 X 箱壁安装的大 C 套小 c")
    if contract.get("columnSyncTensionerOuterCShellAxis") != "+X":
        raise RuntimeError("张紧轮外包络安装 boss 轴向必须是世界 +X")
    if contract.get("columnSyncTensionerOuterCShellPart") != (
        "cabinet-clutch/cabinet_clutch_column_sync_tensioner_integral"
    ):
        raise RuntimeError("张紧轮外包络必须复用唯一张紧总成 STL")
    if contract.get("columnSyncTensionerOuterCShellCabinetBossPart") != (
        "cabinet-clutch/cabinet_frame"
    ):
        raise RuntimeError("张紧轮外包络 boss 必须落在唯一箱体框架件中")
    if n(contract, "columnSyncTensionerOuterCShellBossCount") != 4:
        raise RuntimeError("张紧轮外包络必须有四个 boss 通孔")
    if contract.get("columnSyncTensionerOuterCShellHolePattern") != (
        "backRail2-topArm1-bottomArm1"
    ):
        raise RuntimeError("张紧轮外包络孔位必须是后/左竖边两孔、上下臂各一孔")
    if n(contract, "columnSyncTensionerOuterCShellArmLengthZMm") < 7.0:
        raise RuntimeError("张紧轮外包络上下臂长度不足以容纳 Ø6 通孔")
    for key, value, label in (
        ("columnSyncTensionerOuterCShellDepthXMm", 3.0, "张紧轮外 C 轴向厚度"),
        ("columnSyncTensionerOuterCShellJunctionOverlapMm", 3.0, "张紧轮外 C 根部承力重叠"),
        ("columnSyncTensionerOuterCShellClearanceMm", 0.6, "张紧轮大小 C 间隙"),
        ("columnSyncTensionerOuterCShellWallMm", 7.0, "张紧轮外 C 壁厚"),
        ("columnSyncTensionerOuterCShellBossOdMm", 5.0, "张紧轮箱体 boss 外径"),
        ("columnSyncTensionerOuterCShellBossLengthXMm", 2.5, "张紧轮箱体 boss 长度"),
        ("columnSyncTensionerOuterCShellBossClearanceHoleMm", 6.0, "张紧轮外套 boss 通孔"),
        ("columnSyncTensionerOuterCShellBossPilotDiameterMm", 2.4, "张紧轮 boss 盲孔"),
        ("columnSyncTensionerOuterCShellBossPilotDepthMm", 2.0, "张紧轮 boss 盲孔深度"),
        ("columnSyncTensionerOuterCShellBossPilotFloorMm", 0.5, "张紧轮 boss 盲孔底厚"),
        ("columnSyncTensionerOuterCShellBossRadialClearanceMm", 0.5, "张紧轮 boss 径向间隙"),
        ("columnSyncTensionerOuterCShellTStemClearanceMm", 0.8, "张紧轮 T 竖杆避让"),
    ):
        expect(contract, key, value, label)
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
        "verticalSplineBearingSupport": "removable-floor-carrier-plus-roof-boss-mounted-upper-carrier",
        "verticalSplineBearingSupportPart": "cabinet-clutch/vertical_spline_bearing_support",
        "verticalSplineBearingUpperSupportPart": "cabinet-clutch/vertical_spline_bearing_upper_support",
        "verticalSplineBearingCarrierPart": "cabinet-clutch/vertical_spline_bearing_support",
        "verticalSplineBearingsPart": "cabinet-clutch/vertical_spline_bearings_reference",
        "linearBearingBlockMount": "mechanism-plate-integral-press-fit",
        "linearBearingModel": "LM3UU-cutaway-reference",
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
        "drawerFrontPinionBearing": "integral-shelf-stepped-3x6x2",
        "drawerGuideBearing": "681-1x3x1-X-axis-C-slot",
        "drawerGuideRail": "partition-integral-inward-C-lips",
        "drawerGuideRailSupport": "existing-divider-or-side-panel-vertical-member",
        "drawerGuideFlangeDirection": "toward-drawer-center",
        "drawerGuideBearingArrangement": "tail-moving-plus-front-lower-fixed",
        "drawerGuideBearingAxis": "+X/-X",
        "drawerGuideLoadPath": "Y-support-Z-travel",
        "drawerGuideTailBearingAxis": "+X/-X",
        "drawerGuideFrontBearingAxis": "+X/-X",
        "rearClutchCarrierMode": "row-strip",
        "partitionMountType": "skp-mm-d-receiver-plus-open-d-ring-cover-full-d-screw-face",
        "partitionMountScrewEntry": "-X,+X,+Y,-Y",
        "partitionMountInstallDirection": "+Z",
        "partitionReferenceReceiverCapDirection": "-Z",
        "partitionReferenceReceiverProfile": "D-r3-straight9-through-hole2p4",
        "partitionReferenceCoverProfile": "open-D-ring-r5-inner-r3-plus-full-outer-D-backplate-r5-hole3",
        "partitionReferenceCoverScrewFaceProfile": "full-outer-D-backplate-r5-straight9-hole3",
        "partitionMountSleeveEntryProfile": "full-width-d-mouth-no-narrow-neck",
        "partitionMountSleeveCrossSectionProfile": "skp-open-d-ring-around-d-door-full-d-screw-face",
        "partitionMountSleeveMouthProfile": "complete-d-profile-entry",
        "partitionMountSleeveSupportType": "integral-skp-cover-to-partition-with-dual-root-ribs",
        "partitionMountInsertionReliefType": "open-edge-slot-full-width-entry",
        "partitionServiceWindowType": "compact-x-minus-service-column-plus-compact-y-minus-service-row",
        "partitionMountLoadPath": "cabinet-wall-receiver-to-partition-sleeve",
        "partitionMountPanelRole": "locating-sleeve-and-clamped-independent-panel",
    }
    for key, value in exact.items():
        if contract.get(key) != value:
            raise RuntimeError(f"中心离合契约字段错误: {key}={contract.get(key)!r}")

    if n(contract, "verticalSplineBearingCount") != 5:
        raise RuntimeError("抽屉电机花键轴必须为 5 根列轴")
    if n(contract, "partitionMountCount") != 8:
        raise RuntimeError("前后仓隔板必须使用四边各两套壁法向挂接件")
    if n(contract, "partitionMountPerSideCount") != 2:
        raise RuntimeError("前后仓隔板每条边必须有两套挂接件")
    if contract.get("partitionMountScrewAxes") != "-X,+X,+Y,-Y":
        raise RuntimeError("前后仓隔板螺丝轴线必须覆盖 x+/x-/y-/y+ 四条边")
    expect(contract, "partitionReferenceReceiverLengthMm", 12.0, "SKP 箱体泪滴耳总长")
    expect(contract, "partitionReferenceReceiverHeightMm", 6.0, "SKP 箱体泪滴耳总高")
    expect(contract, "partitionReferenceReceiverThicknessMm", 3.0, "SKP 箱体泪滴耳厚度")
    expect(contract, "partitionReferenceReceiverRadiusMm", 3.0, "SKP 箱体泪滴耳圆头半径")
    expect(contract, "partitionReferenceReceiverStraightMm", 9.0, "SKP 箱体泪滴耳直段")
    expect(contract, "partitionReferenceReceiverHoleDiameterMm", 2.4, "SKP 箱体泪滴耳通孔")
    expect(contract, "partitionReferenceCoverLengthMm", 14.0, "SKP 隔板泪滴外套总长")
    expect(contract, "partitionReferenceCoverHeightMm", 10.0, "SKP 隔板泪滴外套总高")
    expect(contract, "partitionReferenceCoverRadiusMm", 5.0, "SKP 隔板泪滴外套外圆头半径")
    expect(contract, "partitionReferenceCoverInnerRadiusMm", 3.0, "SKP 隔板泪滴外套内圆头半径")
    expect(contract, "partitionReferenceCoverStraightMm", 9.0, "SKP 隔板泪滴外套直段")
    expect(contract, "partitionReferenceCoverBaseDepthMm", 3.0, "SKP 隔板泪滴外套 U 环深")
    expect(contract, "partitionReferenceCoverStepDepthMm", 2.0, "SKP 隔板泪滴外套 D 台阶深")
    expect(contract, "partitionReferenceCoverTotalDepthMm", 5.0, "SKP 隔板泪滴外套总深")
    expect(contract, "partitionReferenceCoverHoleDiameterMm", 3.0, "SKP 隔板泪滴外套螺丝孔")
    expect(contract, "partitionReferenceRoundSleeveOuterDiameterMm", 5.0, "SKP 独立圆套外径")
    expect(contract, "partitionReferenceRoundSleeveInnerDiameterMm", 3.0, "SKP 独立圆套内径")
    expect(contract, "partitionReferenceRoundSleeveLengthMm", 7.0, "SKP 独立圆套总长")
    expect(contract, "partitionReferenceRoundSleeveCollarDepthMm", 2.0, "SKP 独立圆套台阶深")
    expect(contract, "partitionMountSleeveMouthWidthMm", 10.0, "隔板完整D入口宽")
    expect(contract, "partitionMountSleeveSupportArmWidthMm", 2.0, "隔板开放D环外套承力臂宽")
    expect(contract, "partitionMountSleeveSupportArmLengthMm", 7.0, "隔板开放D环外套承力臂长")
    expect(contract, "partitionMountSleeveSupportPlateOverlapMm", 3.0, "隔板开放D环外套与板厚重叠")
    expect(contract, "partitionMountSleeveSupportRootOverlapMm", 2.0, "隔板开放D环外套与根部重叠")
    expect(contract, "partitionMountSleeveSupportRibWidthMm", 2.0, "隔板开放D环外套根部肋宽")
    expect(contract, "partitionMountSleeveSupportRibTangentClearanceMm", 0.2, "隔板开放D环外套根部肋切向净空")
    expect(contract, "partitionMountSleeveWallMm", 2.0, "隔板套筒壁厚")
    expect(contract, "partitionMountSleeveLengthMm", 5.0, "隔板套筒轴向长度")
    expect(contract, "partitionFramePlateClearanceMm", 0.3, "隔板外框内净装配间隙")
    expect(contract, "partitionFramePlateX0Mm", 3.5, "隔板内净 X 起点")
    expect(contract, "partitionFramePlateY0Mm", 3.5, "隔板内净 Y 起点")
    expect(contract, "partitionFramePlateWidthMm", 243.0, "隔板内净宽")
    expect(contract, "partitionFramePlateHeightMm", 227.8, "隔板内净高")
    expect(contract, "partitionMountEdgeMarginMm", 36.0, "隔板四边挂接件边距")
    expect(contract, "partitionMountXSideLowYMm", 76.2, "隔板 x+ 边 y- 挂接件 Y 坐标")
    expect(contract, "partitionMountXSideHighYMm", 195.3, "隔板 x+ 边高位挂接件 Y 坐标")
    expect(contract, "partitionMountXPlusLowYMm", 76.2, "隔板 x+ 边 y- 挂接件 Y 坐标")
    expect(contract, "partitionMountXPlusHighYMm", 195.3, "隔板 x+ 边高位挂接件 Y 坐标")
    expect(contract, "partitionMountXMinusLowYMm", 18.0, "隔板 x- 边低位挂接件 Y 坐标")
    expect(contract, "partitionMountXMinusHighYMm", 195.3, "隔板 x- 边高位挂接件 Y 坐标")
    expect(contract, "partitionMountYSideLowXMm", 39.5, "隔板 y 边低位挂接件 X 坐标")
    expect(contract, "partitionMountYSideHighXMm", 210.5, "隔板 y 边高位挂接件 X 坐标")
    expect(contract, "partitionReferenceCoverScrewFaceRadiusMm", 5.0, "隔板完整外D螺丝面圆头半径")
    expect(contract, "partitionReferenceCoverScrewFaceStraightMm", 9.0, "隔板完整外D螺丝面直段")
    expect(contract, "partitionMountInsertionReliefWidthMm", 10.2, "隔板挂接导入槽宽")
    expect(contract, "partitionMountInsertionReliefDepthMm", 3.1, "隔板挂接导入槽深")
    expect(contract, "partitionMountInsertionReliefEndClearanceMm", 0.1, "隔板挂接导入槽止端余量")
    expect(contract, "partitionServiceWindowX0Mm", 2.5, "隔板服务窗 X 起点")
    expect(contract, "partitionServiceWindowX1Mm", 15.5, "隔板服务窗 X 终点")
    expect(contract, "partitionServiceWindowY0Mm", 2.5, "隔板服务窗 Y 起点")
    expect(contract, "partitionServiceWindowY1Mm", 15.5, "隔板服务窗 Y 终点")
    expect(contract, "partitionServiceWindowWidthMm", 13.0, "隔板服务窗宽")
    expect(contract, "partitionServiceWindowHeightMm", 13.0, "隔板服务窗高")
    expect(contract, "partitionServiceWindowCornerRadiusMm", 0.0, "隔板服务窗圆角")
    expect(contract, "partitionServiceCutOvertravelMm", 1.0, "隔板服务口过切量")
    expect(contract, "partitionServiceXMinusOpenX0Mm", 2.5, "隔板 x- 服务口 X 起点")
    expect(contract, "partitionServiceXMinusOpenX1Mm", 15.5, "隔板 x- 服务口 X 终点")
    expect(contract, "partitionServiceXMinusOpenY0Mm", 2.5, "隔板 x- 服务口 Y 起点")
    expect(contract, "partitionServiceXMinusOpenY1Mm", 232.3, "隔板 x- 服务口 Y 终点")
    expect(contract, "partitionServiceXMinusOpenWidthMm", 13.0, "隔板 x- 服务口宽")
    expect(contract, "partitionServiceXMinusOpenHeightMm", 229.8, "隔板 x- 服务口高")
    expect(contract, "partitionServiceYMinusOpenX0Mm", 2.5, "隔板 y- 服务口 X 起点")
    expect(contract, "partitionServiceYMinusOpenX1Mm", 247.5, "隔板 y- 服务口 X 终点")
    expect(contract, "partitionServiceYMinusOpenY0Mm", 2.5, "隔板 y- 服务口 Y 起点")
    expect(contract, "partitionServiceYMinusOpenY1Mm", 15.5, "隔板 y- 服务口 Y 终点")
    expect(contract, "partitionServiceYMinusOpenWidthMm", 245.0, "隔板 y- 服务口宽")
    expect(contract, "partitionServiceYMinusOpenHeightMm", 13.0, "隔板 y- 服务口高")
    expect(contract, "partitionServiceXMinusOpenCornerRadiusMm", 0.0, "隔板 x- 服务口圆角")
    expect(contract, "partitionServiceYMinusOpenCornerRadiusMm", 0.0, "隔板 y- 服务口圆角")
    expect(contract, "partitionServiceMountPierHalfWidthMm", 8.0, "隔板安装耳承力墩半宽")
    expect(contract, "partitionServiceRemainingGridWebXMm", 31.7, "隔板 x- 服务口后剩余承力网格宽")
    expect(contract, "partitionServiceRemainingGridWebYMm", 45.4, "隔板 y- 服务口后剩余承力网格高")
    expect(contract, "partitionSleeveFrontOverlapMm", 0.0, "隔板套 z+ 实体重叠")
    if n(contract, "verticalSplineBearingUpperCount") != 5:
        raise RuntimeError("抽屉电机花键轴上方必须为 5 枚固定轴承")
    if n(contract, "verticalSplineBearingTotalCount") != 10:
        raise RuntimeError("抽屉电机花键轴上下固定轴承总数必须为 10 枚")
    if n(contract, "verticalSplineBearingTotalCount") != (
        n(contract, "verticalSplineBearingCount")
        + n(contract, "verticalSplineBearingUpperCount")
    ):
        raise RuntimeError("抽屉电机花键轴上下轴承数量契约不一致")
    expect(contract, "verticalSplineBearingIdMm", 3.0, "花键轴承内径")
    expect(contract, "verticalSplineBearingOdMm", 6.0, "花键轴承外径")
    expect(contract, "verticalSplineBearingWidthMm", 2.0, "花键轴承宽度")
    expect(contract, "verticalSplineBearingSeatDiameterMm", 6.10, "花键轴承座孔")
    expect(contract, "verticalSplineBearingSeatDepthMm", 2.0, "花键轴承座深度")
    expect(contract, "verticalSplineBearingSeatShoulderMm", 0.20, "花键轴承座底部肩厚")
    expect(
        contract,
        "verticalSplineBearingUpperSeatBottomYMm",
        n(contract, "verticalSplineBearingUpperCarrierPlateBottomYMm"),
        "上方轴承座底面/可拆上承载板底面",
    )
    expect(
        contract,
        "verticalSplineBearingUpperSeatTopYMm",
        n(contract, "verticalSplineBearingUpperSeatBottomYMm")
        + n(contract, "verticalSplineBearingSeatDepthMm"),
        "上方轴承座深度",
    )
    expect(
        contract,
        "verticalSplineBearingUpperCenterYMm",
        n(contract, "verticalSplineBearingUpperSeatBottomYMm")
        + n(contract, "verticalSplineBearingWidthMm") / 2,
        "上方轴承中心",
    )
    expect(
        contract,
        "verticalSplineBearingUpperBearingTopYMm",
        n(contract, "verticalSplineBearingUpperCenterYMm")
        + n(contract, "verticalSplineBearingWidthMm") / 2,
        "上方轴承上沿",
    )
    expect(
        contract,
        "verticalSplineBearingUpperCarrierPlateThicknessMm",
        n(contract, "verticalSplineBearingSeatDepthMm")
        + n(contract, "verticalSplineBearingSeatShoulderMm"),
        "可拆上承载板厚度",
    )
    expect(
        contract,
        "verticalSplineBearingUpperCarrierClearanceMm",
        n(contract, "verticalSplineBearingUpperCarrierPlateBottomYMm")
        - n(contract, "verticalSplineBearingUpperPulleyTopYMm"),
        "可拆上承载板/上方2GT轮净空",
    )
    if n(contract, "verticalSplineBearingUpperCarrierClearanceMm") < 0.45:
        raise RuntimeError("可拆上承载板与上方 2GT 轮净空不足")
    if n(contract, "verticalSplineBearingUpperDStubEndYMm") < (
        n(contract, "verticalSplineBearingUpperBearingTopYMm") - 0.15
    ):
        raise RuntimeError("花键齿上端 D 轴没有穿过上方轴承")
    if contract.get("verticalSplineBearingSupport") != "removable-floor-carrier-plus-roof-boss-mounted-upper-carrier":
        raise RuntimeError("花键轴承必须使用下方 Boss 板 + 屋顶 Boss 套板 + 下方蘑菇头 M3")
    expect(contract, "verticalSplineBearingCarrierBossCount", 8.0, "花键轴承可拆承载板 Boss 数")
    expect(contract, "verticalSplineBearingUpperBossCount", 8.0, "上方花键轴承承载板 Boss 数")
    expect(contract, "verticalSplineBearingUpperBossOdMm", 5.0, "上方屋顶 Boss 外径")
    expect(contract, "verticalSplineBearingUpperBossPilotDiameterMm", 2.4, "上方屋顶 Boss 自攻导孔")
    expect(contract, "verticalSplineBearingUpperBossHeightMm", n(contract, "verticalSplineBearingUpperCarrierPlateThicknessMm"), "上方屋顶 Boss 高度")
    expect(contract, "verticalSplineBearingUpperBossTopYMm", n(contract, "verticalSplineBearingUpperCarrierPlateTopYMm"), "上方屋顶 Boss 顶面")
    expect(contract, "verticalSplineBearingUpperBossBottomYMm", n(contract, "verticalSplineBearingUpperCarrierPlateBottomYMm"), "上方屋顶 Boss 底面")
    expect(contract, "verticalSplineBearingUpperBossPilotTopYMm", n(contract, "verticalSplineBearingUpperBossBottomYMm") + n(contract, "verticalSplineBearingUpperBossPilotDepthMm"), "上方屋顶 Boss 导孔顶面")
    expect(contract, "verticalSplineBearingUpperCarrierBossClearDiameterMm", 5.2, "上方承载板 Boss 通孔")
    if contract.get("verticalSplineBearingUpperBossMount") != "bottom-mushroom-head-M3-into-roof-boss-over-5.2-hole":
        raise RuntimeError("上方承载板必须由下方蘑菇头 M3 自攻螺丝锁入屋顶 Boss")
    if n(contract, "verticalSplineBearingCarrierPlateX0Mm") >= n(contract, "verticalSplineBearingCarrierPlateX1Mm"):
        raise RuntimeError("花键轴承可拆承载板 X 范围无效")
    if n(contract, "verticalSplineBearingCarrierPlateZ0Mm") >= n(contract, "verticalSplineBearingCarrierPlateZ1Mm"):
        raise RuntimeError("花键轴承可拆承载板 Z 范围无效")
    expect(
        contract,
        "verticalSplineBearingCarrierPlateXLengthMm",
        n(contract, "verticalSplineBearingCarrierPlateX1Mm")
        - n(contract, "verticalSplineBearingCarrierPlateX0Mm"),
        "花键轴承可拆承载板 X 长度",
    )
    expect(
        contract,
        "verticalSplineBearingCarrierPlateZLengthMm",
        n(contract, "verticalSplineBearingCarrierPlateZ1Mm")
        - n(contract, "verticalSplineBearingCarrierPlateZ0Mm"),
        "花键轴承可拆承载板 Z 长度",
    )
    expect(
        contract,
        "verticalSplineBearingCarrierPlateTopYMm",
        n(contract, "verticalSplineBearingCarrierPlateBottomYMm")
        + n(contract, "verticalSplineBearingCarrierPlateThicknessMm"),
        "花键轴承可拆承载板 Y 厚度",
    )
    if n(contract, "verticalSplineBearingCarrierPlateThicknessMm") < 3.0:
        raise RuntimeError("花键轴承可拆承载板厚度不足以承受轴承塔")
    expect(
        contract,
        "verticalSplineBearingFloorBossHeightMm",
        n(contract, "verticalSplineBearingFloorBossTopYMm") - 3.2,
        "底板 Boss 高度",
    )
    if abs(n(contract, "verticalSplineBearingCarrierPlateBottomYMm") - 3.2) > 0.001:
        raise RuntimeError("花键轴承承载板底面必须与箱体底板顶面重合")
    if abs(n(contract, "verticalSplineBearingFloorBossTopYMm")
           - n(contract, "verticalSplineBearingCarrierPlateTopYMm")) > 0.001:
        raise RuntimeError("底板圆柱 Boss 顶面必须与 3 mm 承载板上表面齐平")
    if n(contract, "verticalSplineBearingFloorBossPilotBottomYMm") < 3.2 - 0.001:
        raise RuntimeError("底板 Boss 自攻导孔穿透了底板安全余量")
    if (
        n(contract, "verticalSplineBearingCarrierBossCounterboreDiameterMm") != 0
        or n(contract, "verticalSplineBearingCarrierBossCounterboreDepthMm") != 0
    ):
        raise RuntimeError("可拆承载板不得保留底部定位窝，只能由顶部螺丝压在圆柱 Boss 上")
    if contract.get("verticalSplineBearingCarrierBossMount") != "top-washer-or-wide-head-M3-over-5.2-hole":
        raise RuntimeError("花键轴承承载板固定方式必须是垫片或大头 M3 螺丝压在 5.2 mm 通孔上")
    expect(
        contract,
        "verticalSplineBearingCenterYMm",
        n(contract, "verticalSplineBearingSeatBottomYMm")
        + n(contract, "verticalSplineBearingWidthMm") / 2,
        "花键轴承中心必须位于轴承座中部",
    )
    if n(contract, "verticalSplineBearingCapBottomYMm") <= n(contract, "verticalSplineBearingChainTopYMm") + 0.45:
        raise RuntimeError("花键轴承座下沿进入蛇链回程包络")
    if n(contract, "verticalSplineBearingCapTopYMm") >= n(contract, "verticalSplineBearingLowerPulleyBottomYMm") - 0.45:
        raise RuntimeError("花键轴承座上沿进入下方 2GT 轮包络")
    if n(contract, "verticalSplineBearingReturnGuideClearanceMm") < 0.45:
        raise RuntimeError("花键轴承座与 8T 蛇链导向轮净空不足")
    if n(contract, "verticalSplineBearingLowerPulleyClearanceMm") < 0.45:
        raise RuntimeError("花键轴承座与下方 2GT 轮净空不足")
    if n(contract, "verticalSplineBearingReturnDriveClearanceMm") < 0.45:
        raise RuntimeError("花键轴承座与 12T 蛇链回程主动轮净空不足")
    expect(
        contract,
        "verticalSplineBearingBarZLengthMm",
        n(contract, "verticalSplineBearingBarZMaxMm")
        - n(contract, "verticalSplineBearingBarZMinMm"),
        "花键轴承座兼容 Z 包络",
    )
    expect(contract, "verticalSplineBearingCarrierPlateThicknessMm", 3.0, "花键轴承承载板厚度")
    expect(contract, "verticalSplineBearingFloorBossOdMm", 5.0, "圆柱 Boss 外径")
    expect(contract, "verticalSplineBearingFloorBossBaseOdMm", 5.0, "圆柱 Boss 基准外径")
    expect(contract, "verticalSplineBearingFloorBossBaseHeightMm", 3.0, "圆柱 Boss 高度")
    expect(contract, "verticalSplineBearingFloorBossPilotDepthMm", 3.0, "圆柱 Boss 自攻导孔深度")
    expect(contract, "verticalSplineBearingCarrierBossClearDiameterMm", 5.2, "承载板 Boss 通孔直径")
    expect(contract, "verticalSplineBearingTowerBodyXWidthMm", 12.0, "轴承塔柱 X 宽")
    expect(contract, "verticalSplineBearingTowerBodyZDepthMm", 12.0, "轴承塔柱 Z 深")
    expect(contract, "verticalSplineBearingTowerColumnDiameterMm", 12.0, "圆形轴承座柱直径")
    expect(contract, "verticalSplineBearingTowerRootXWidthMm", 20.0, "轴承塔根部 X 宽")
    expect(contract, "verticalSplineBearingTowerRootZDepthMm", 20.0, "轴承塔根部 Z 深")
    expect(contract, "verticalSplineBearingTowerCapC5XWidthMm", 20.0, "C5 轴承塔帽 X 宽")
    expect(contract, "verticalSplineBearingTowerCapC5ZDepthMm", 18.0, "C5 轴承塔帽 Z 深")
    expect(contract, "verticalSplineBearingC5RailWidthMm", 4.5, "C5 圆角梯形支撑上段宽")
    expect(contract, "verticalSplineBearingC5RailZDepthMm", 16.4, "C5 圆角梯形支撑上段 Z 深")
    expect(contract, "verticalSplineBearingC5RailCenterOffsetXMm", 8.0, "C5 支撑上段中心偏移")
    expect(contract, "verticalSplineBearingC5RailBottomCenterOffsetXMm", 10.5, "C5 支撑根部中心偏移")
    expect(contract, "verticalSplineBearingC5RailRootWidthMm", 6.4, "C5 支撑根部宽")
    expect(contract, "verticalSplineBearingC5RailRootZDepthMm", 18.4, "C5 支撑根部 Z 深")
    expect(contract, "verticalSplineBearingC5RailCornerRadiusMm", 1.2, "C5 支撑圆角半径")
    if contract.get("verticalSplineBearingC5RailProfile") != "rounded-trapezoid-xy-with-rounded-xz-section":
        raise RuntimeError("C5 支撑必须是 XY 圆角梯形、XZ 圆角矩形截面")
    expect(contract, "verticalSplineBearingC5RailClearanceMm", 0.75, "C5 电机旁轴承塔上段净空")
    expect(contract, "verticalSplineBearingC5RailBottomClearanceMm", 2.3, "C5 电机旁轴承塔根部净空")
    expect(contract, "verticalSplineBearingLowerDStubLengthMm", 12.0, "花键轴下端 D 段")
    expect(contract, "verticalSplineBearingUpperDStubLengthMm", 11.7, "花键轴上端 D 段")

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
        "cabinetWidthMm": 250.00, "serviceWidthMm": 44.00,
        "gridWidthMm": 199.60, "drawerBayWidthMm": 38.00,
        "drawerColumnPitchMm": 40.40,
        "rearClutchRowPlateCount": 3.0,
        "rearClutchRowPlateStationCount": 5.0,
        "rearClutchRowPlateLengthMm": 195.60,
        "rearClutchRowPlateX0Mm": 49.20,
        "rearClutchRowPlateX1Mm": 244.80,
        "rearClutchRowPlateLeftClearanceMm": 2.00,
        "rearClutchRowPlateRightClearanceMm": 2.00,
        "frontTimingBearingWidthMm": 2.00,
        "frontTimingBearingIdMm": 3.00,
        "frontTimingBearingOdMm": 6.00,
        "frontTimingBearingSeatDiameterMm": 6.10,
        "frontTimingBearingSeatDepthMm": 2.00,
        "frontTimingBearingRetainerThicknessMm": 0.40,
        "frontTimingBearingRetainerBoreDiameterMm": 3.40,
        "drawerGuideRailClearanceMm": 0.30,
        "drawerGuidePartitionThicknessMm": 2.40,
        "drawerGuideRailAttachOverlapMm": 0.05,
        "drawerGuideSlotHeightMm": 3.60,
        "drawerGuideRailDepthMm": 4.50,
        "drawerGuideFlangeThicknessMm": 2.40,
        "drawerGuideFlangeProjectionMm": 3.00,
        "drawerGuideFlangeClearanceMm": 0.30,
        "drawerGuideDrawerEdgeInsetMm": 1.00,
        "drawerGuideFlangeEndClearanceMm": 0.50,
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
        "snakeChainReturnDriveXTrimMm",
        -4.00,
        "蛇链上方回程轮 X 相位偏移",
    )
    expect(
        contract,
        "snakeChainServicePressXTrimMm",
        16.00,
        "蛇链下方回程轮 X 相位偏移",
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
    if n(contract, "snakeChainTriggerMagnetSegmentIndex") != 182:
        raise RuntimeError("蛇链触发磁铁节号必须落在中心服务直线段 182")

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
    if n(contract, "drawerStationCount") != 15:
        raise RuntimeError("当前柜体必须有 15 个抽屉离合站点")
    if n(contract, "drawerStationInstanceCount") != 14:
        raise RuntimeError("中心同款离合总成模板必须由 14 个非中心实例补齐 5×3 世界总装")
    if contract.get("stationDriveMode") != "sequential-selected-station":
        raise RuntimeError("当前预览必须使用逐站选择、单站接合的动力模式")
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
    if contract.get("drawerBodyPart") != "cabinet-clutch/20_drawer_body_candidate":
        raise RuntimeError("真实抽屉壳体必须使用唯一 20_drawer_body_candidate 源件")
    expect(contract, "drawerBodyOuterWidthMm", n(contract, "drawerBayWidthMm") - 2 * n(contract, "drawerGuideDrawerEdgeInsetMm"), "真实抽屉壳体外宽")
    expect(contract, "drawerBodyOuterHeightMm", n(contract, "drawerBayHeightMm") - 2 * n(contract, "drawerGuideDrawerEdgeInsetMm"), "真实抽屉壳体外高")
    if n(contract, "drawerBodyDepthMm") <= 0:
        raise RuntimeError("真实抽屉壳体深度无效")
    expect(contract, "drawerBodyDepthMm", n(contract, "drawerBodyFrontZMm") - n(contract, "drawerBodyRearZMm"), "真实抽屉壳体 Z 深度")
    expect(contract, "drawerBodyRearZMm", -59.6, "真实抽屉壳体后端 Z")
    expect(contract, "drawerBodyFrontZMm", -0.2, "真实抽屉壳体前端 Z")
    for key, label in (
        ("drawerBodyWallMm", "真实抽屉壳体侧壁厚度"),
        ("drawerBodyFloorMm", "真实抽屉壳体底板厚度"),
        ("drawerBodyFrontWallMm", "真实抽屉壳体前壁厚度"),
        ("drawerBodyRearWallMm", "真实抽屉壳体后壁厚度"),
        ("drawerBodyGuideReliefClearanceMm", "真实抽屉 C 槽让位余量"),
        ("drawerBodyDriveClearanceMm", "真实抽屉齿排/主动轮让位余量"),
    ):
        if n(contract, key) <= 0:
            raise RuntimeError(f"{label}必须为正")
    if n(contract, "drawerBodyOuterWidthMm") <= 2 * n(contract, "drawerBodyWallMm"):
        raise RuntimeError("真实抽屉壳体侧壁占满外宽，无法形成内腔")
    if n(contract, "drawerBodyOuterHeightMm") <= n(contract, "drawerBodyFloorMm"):
        raise RuntimeError("真实抽屉壳体底板占满外高，无法形成内腔")
    if n(contract, "drawerBodyDepthMm") <= n(contract, "drawerBodyRearWallMm") + n(contract, "drawerBodyFrontWallMm"):
        raise RuntimeError("真实抽屉壳体前后壁占满 Z 深度，无法形成内腔")
    expect(contract, "drawerRackPitchMm", 3.0, "直线齿排/前端主动轮圆周齿距")
    if n(contract, "drawerRackGearTeeth") != 16:
        raise RuntimeError("前端直齿主动轮必须是 16T")
    if n(contract, "frontTimingPulleyTeeth") != 12:
        raise RuntimeError("前端同步轮必须是 12T")
    expect(contract, "frontTimingBeltPitchMm", 2.0, "前端同步轮皮带齿距")
    expect(
        contract,
        "drawerRackTravelMmPerShaftTurn",
        n(contract, "drawerRackGearTeeth") * n(contract, "drawerRackPitchMm"),
        "直线齿排每根同轴轴转一圈的行程",
    )
    expect(
        contract,
        "frontTimingBeltAdvanceMmPerShaftTurn",
        n(contract, "frontTimingPulleyTeeth") * n(contract, "frontTimingBeltPitchMm"),
        "同步皮带每根同轴轴转一圈的推进量",
    )
    if abs(
        n(contract, "drawerRackTravelMmPerShaftTurn")
        / n(contract, "frontTimingBeltAdvanceMmPerShaftTurn")
        - 2.0
    ) > 0.001:
        raise RuntimeError("直线齿排与下层 2GT 同步轮的同轴传动比必须是 2:1")
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
    if contract.get("drawerGuideRailSupport") != "existing-divider-or-side-panel-vertical-member":
        raise RuntimeError("C 形导向槽必须直接使用箱体立板/侧板作为竖直承力段")
    if contract.get("drawerGuideFlangeDirection") != "toward-drawer-center":
        raise RuntimeError("抽屉导向凸缘必须朝本格抽屉内侧伸出")
    if n(contract, "drawerGuideSlotHeightMm") <= n(contract, "drawerGuideBearingSeatDiameterMm"):
        raise RuntimeError("C 形导向槽高度不足以容纳 681 轴承")
    if n(contract, "drawerGuidePartitionThicknessMm") <= 0:
        raise RuntimeError("C 形导向槽立板承力厚度无效")
    if not 0 < n(contract, "drawerGuideRailAttachOverlapMm") < n(contract, "drawerGuidePartitionThicknessMm"):
        raise RuntimeError("C 形导向槽与立板的融合重叠无效")
    if n(contract, "drawerGuideFlangeThicknessMm") >= n(contract, "drawerGuideSlotHeightMm"):
        raise RuntimeError("抽屉侧向导轨凸缘没有留出 C 槽上下间隙")
    if n(contract, "drawerGuideRailDepthMm") <= (
        n(contract, "drawerGuideDrawerEdgeInsetMm")
        + n(contract, "drawerGuideFlangeProjectionMm")
        + n(contract, "drawerGuideFlangeClearanceMm")
    ):
        raise RuntimeError("内向 C 形导向唇没有越过抽屉凸缘并留出端部间隙")
    expected_end_clearance = (
        n(contract, "drawerGuideRailDepthMm")
        - n(contract, "drawerGuideDrawerEdgeInsetMm")
        - n(contract, "drawerGuideFlangeProjectionMm")
    )
    if abs(
        n(contract, "drawerGuideFlangeEndClearanceMm")
        - expected_end_clearance
    ) > 0.001:
        raise RuntimeError("内向 C 形导向唇端部净空推导不一致")
    if n(contract, "drawerGuideFlangeEndClearanceMm") < n(contract, "drawerGuideFlangeClearanceMm"):
        raise RuntimeError("内向 C 形导向唇端部净空不足")
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
