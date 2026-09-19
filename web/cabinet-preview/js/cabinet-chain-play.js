//#region 导入/依赖
import * as THREE from "three";
//#endregion

//#region 常量/配置
const HZ_STEPS = [0.1, 0.5, 1, 2, 5, 10];
const DEFAULT_HZ_INDEX = 2;
const CHAIN_IDS = new Set([
  "cabinet-chain/cabinet_chain_plates",
  "cabinet-chain/cabinet_chain_rollers",
  "cabinet-chain/cabinet_chain_pins",
  "cabinet-chain/cabinet_chain_connector",
  "cabinet-chain/cabinet_chain_clutch_connector",
  "cabinet-chain/cabinet_chain_clutch_bearing",
]);
const CHAIN_TRIGGER_MAGNET_ID = "cabinet-chain/cabinet_chain_clutch_trigger_magnet";
const RIGID_CHAIN_IDS = new Set([
  "cabinet-chain/cabinet_chain_connector",
  "cabinet-chain/cabinet_chain_clutch_connector",
  "cabinet-chain/cabinet_chain_clutch_bearing",
]);
const RIGID_CHAIN_SEGMENTS = new Map([
  // These highlighted assemblies replace the corresponding two-pin link in
  // the authored SCAD path.  Keeping their logical segment explicit prevents
  // a platform/clip-heavy bounding box from becoming the animation pivot.
  ["cabinet-chain/cabinet_chain_connector", 20],
  ["cabinet-chain/cabinet_chain_clutch_connector", 140],
  ["cabinet-chain/cabinet_chain_clutch_bearing", 140],
]);
const PLATE_TEMPLATE_SEGMENTS = {
  // These are straight, ordinary links in the canonical 5x3 path.  Taking
  // templates from the straight run avoids using corner triangles twice when
  // the authored STL has been unioned into two connected surfaces.
  outer: 10,
  inner: 11,
  connector: 20,
};
const WHEEL_IDS = {
  "cabinet-chain/cabinet_chain_sprockets": "sprocket",
  "cabinet-chain/cabinet_chain_idlers": "idler",
};
const CHAIN_BEARING_ID = "cabinet-chain/cabinet_chain_bearings";
const MOTOR_SHAFT_IDS = new Set([
  "cabinet-chain/cabinet_chain_motor_shaft",
]);
const SCHEME1_POWER_ID = "cabinet-chain/cabinet_chain_scheme1_power_wheels";
const SCHEME1_OUTPUT_ID = "cabinet-chain/cabinet_chain_scheme1_output_wheels";
const SCHEME1_CLUTCH_ID = "cabinet-chain/cabinet_chain_scheme1_clutch_faces";
const SCHEME1_BEARING_ID = "cabinet-chain/cabinet_chain_scheme1_bearings";
const SCHEME1_SELECTOR_ID = "cabinet-chain/cabinet_chain_scheme1_selector";
const DRAWER_BELT_ID = "cabinet-clutch/13_drawer_timing_belt_reference";
const CURRENT_CLUTCH_IDS = new Map([
  // The native center prototype is the only visible clutch pair in the
  // default assembly. Names follow the mechanical roles, not the retired
  // upper/lower preview labels.
  ["cabinet-clutch/center_input_rotor", {
    role: "input", primary: true, moves: true, rotates: true,
  }],
  ["cabinet-clutch/center_output_rotor", {
    role: "output", primary: true, moves: false, rotates: true,
  }],
  ["cabinet-clutch/center_input_shaft_reference", {
    role: "input", moves: true, rotates: true,
  }],
  ["cabinet-clutch/center_input_sleeve", {
    role: "input", moves: true, rotates: true,
  }],
  ["cabinet-clutch/center_input_sleeve_magnet_reference", {
    role: "input", moves: true, rotates: false,
  }],
  ["cabinet-clutch/center_linear_bearings_reference", {
    role: "input", moves: false, rotates: false,
  }],
  ["cabinet-clutch/center_output_shaft_reference", {
    role: "output", moves: false, rotates: true,
  }],
  ["cabinet-clutch/center_output_bearings_reference", {
    role: "output", moves: false, rotates: false,
  }],
]);
const CURRENT_CLUTCH_STATIC_IDS = new Set([
  "cabinet-clutch/center_mechanism_plate",
]);
const DRAWER_ROTARY_IDS = new Map([
  // The center clutch pair is bound separately so its +Y engagement stroke
  // cannot be mistaken for a plain rotary pivot.  The front compound remains
  // a downstream rotary load of the engaged clutch.
  ["cabinet-clutch/14_front_timing_pulley_candidate", -1],
  ["cabinet-clutch/15_front_pinion_candidate", -1],
]);
// This is the default center station's mating pulley tooth count, not the
// total teeth in the closed belt. One pulley revolution advances the 2GT belt
// by 12 * 2 mm; using the belt's total 80 teeth would move it by one whole
// loop and make it appear stationary in the preview.
const DRAWER_PULLEY_TEETH = 12;
const DRAWER_BELT_PITCH_MM = 2;
const POWER_MOTOR_SHAFT_ID = "cabinet-clutch/cabinet_clutch_power_motor_shaft";
const POWER_COLUMN_ID_PREFIX = "cabinet-clutch/cabinet_clutch_power_column_";
const POWER_COLUMN_SYNC_BELT_IDS = new Set([
  "cabinet-clutch/cabinet_clutch_column_sync_belt_bottom",
  "cabinet-clutch/cabinet_clutch_column_sync_belt_top",
]);
const POWER_COLUMN_SYNC_TENSIONER_ID = "cabinet-clutch/cabinet_clutch_column_sync_tensioner";
const POWER_COLUMN_COUNT = 5;
const POWER_COLUMN_PULLEY_TEETH = 12;
const POWER_COLUMN_BELT_PITCH_MM = 2;
const SCHEME1_PHASE = {
  INDEX: "INDEX",
  ENGAGE: "ENGAGE",
  OPEN: "OPEN",
  CLOSE: "CLOSE",
  RELEASE: "RELEASE",
};
// One complete drawer travel is represented by the former 0.90-turn drive
// window at 1 Hz.  The value is a travel amount, not a duration, so changing
// the preview speed changes the time taken but never changes the open/close
// end positions or leaves accumulated angular error between cycles.
const SCHEME1_DRAWER_TRAVEL_TURNS = 0.90;
const SCHEME1_ENGAGE_SECONDS = 0.28;
const SCHEME1_RELEASE_SECONDS = 0.24;
const CENTER_DEMO_APPROACH_SECONDS = 0.80;
const CENTER_DEMO_ENGAGE_SECONDS = 1.10;
const CENTER_DEMO_HOLD_SECONDS = 0.80;
const CENTER_DEMO_RELEASE_SECONDS = 1.20;
const CURRENT_CLUTCH_ROW = 1;
const CURRENT_CLUTCH_COL = 2;
const MOTION_URL = "./models/cabinet-chain/cabinet_chain_motion.json";
//#endregion

//#region 模型/类型
/** @typedef {{a:number[], b:number[], s0:number, len:number}} PathSeg */
/** @typedef {{group:THREE.Group, s:number, along:number, side:number, lift:number, restYaw:number, halfSpan:number, pinIndex?:number, scaleAlong?:boolean}} ChainPart */
/** @typedef {{group:THREE.Group, teeth:number, sign:number, restY:number}} WheelPivot */
/** @typedef {{group:THREE.Group, teeth:number, sign:number, restY:number}} BearingPivot */
/** @typedef {{group:THREE.Group, restY:number}} MotorShaftPivot */
/** @typedef {{group:THREE.Group, stationIndex:number, side:string, baseY:number, openY:number, engagedY:number, restY:number}} ClutchPivot */
/** @typedef {{group:THREE.Group, role:string, sign:number, baseY:number, restY:number, moves:boolean, rotates:boolean}} CurrentClutchPivot */
//#endregion

//#region 私有成员
const play = {
  ready: false,
  motion: null,
  path: null,
  chain: /** @type {ChainPart[]} */ ([]),
  wheels: /** @type {WheelPivot[]} */ ([]),
  bearingRotaries: /** @type {BearingPivot[]} */ ([]),
  motorShafts: /** @type {MotorShaftPivot[]} */ ([]),
  drawerBelts: /** @type {Array<{mesh:THREE.Mesh,baseMesh:THREE.Mesh,path:any,toothS:Float32Array,toothCount:number,toothPitch:number,toothHeight:number,toothBase:number,toothTip:number,lastPhase:number}>} */ ([]),
  drawerRotaries: /** @type {Array<{group:THREE.Group, sign:number, restY:number}>} */ ([]),
  currentClutch: /** @type {{contract:any,input:CurrentClutchPivot|null,output:CurrentClutchPivot|null,parts:CurrentClutchPivot[]}} */ ({
    contract: null,
    input: null,
    output: null,
    parts: [],
  }),
  powerRotaries: /** @type {Array<{group:THREE.Group, sign:number, restY:number}>} */ ([]),
  columnSyncBelts: /** @type {Array<{mesh:THREE.Mesh,baseMesh:THREE.Mesh,path:any,toothS:Float32Array,toothCount:number,toothPitch:number,toothHeight:number,toothBase:number,toothTip:number,lastPhase:number}>} */ ([]),
  scheme1: {
    ready: false,
    stationS: /** @type {number[]} */ ([]),
    stations: /** @type {any[]} */ ([]),
    powerWheels: /** @type {WheelPivot[]} */ ([]),
    outputWheels: /** @type {WheelPivot[]} */ ([]),
    clutches: /** @type {ClutchPivot[]} */ ([]),
    selectorPart: null,
    selectorS: 0,
    targetIndex: 0,
    phase: SCHEME1_PHASE.INDEX,
    phaseTime: 0,
    powerTurns: 0,
    outputTurns: /** @type {number[]} */ ([]),
    cycleSign: 1,
    cycleStartPowerTurns: 0,
    cycleStartOutputTurns: 0,
    cycleProgressTurns: 0,
  },
  centerDemo: {
    active: false,
    elapsed: 0,
    engagement: 0,
    phase: "idle",
  },
  playing: true,
  dir: 1,
  motorHz: HZ_STEPS[DEFAULT_HZ_INDEX],
  motorTurns: 0,
  host: null,
  bindQueue: /** @type {Array<() => Promise<void>>} */ ([]),
  bindBusy: false,
  centerViewRequested: false,
};

function formatHz(hz) {
  return Number.isInteger(hz) ? String(hz) : String(hz);
}

function hzFromSlider(input) {
  const index = Number(input?.value ?? DEFAULT_HZ_INDEX);
  return HZ_STEPS[Math.min(HZ_STEPS.length - 1, Math.max(0, index))] ?? HZ_STEPS[DEFAULT_HZ_INDEX];
}

function sub(a, b) {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

function dot(a, b) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function length3(v) {
  return Math.hypot(v[0], v[1], v[2]);
}

function normalize(v) {
  const n = length3(v) || 1;
  return [v[0] / n, v[1] / n, v[2] / n];
}

function lerp(a, b, t) {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

function pinPoint(pin, chainY) {
  return [pin[0], chainY, pin[1]];
}

function cellKey(ix, iz) {
  return `${ix},${iz}`;
}

function buildPath(motion) {
  const chainY = motion.chainY;
  const pts = motion.pins.map((pin) => pinPoint(pin, chainY));
  const segs = [];
  let total = 0;
  for (let i = 0; i < pts.length; i += 1) {
    const a = pts[i];
    const b = pts[(i + 1) % pts.length];
    const len = length3(sub(b, a));
    segs.push({ a, b, s0: total, len });
    total += len;
  }
  const cell = 10;
  const pad = 8;
  const grid = new Map();
  for (let i = 0; i < segs.length; i += 1) {
    const seg = segs[i];
    const minx = Math.floor((Math.min(seg.a[0], seg.b[0]) - pad) / cell);
    const maxx = Math.floor((Math.max(seg.a[0], seg.b[0]) + pad) / cell);
    const minz = Math.floor((Math.min(seg.a[2], seg.b[2]) - pad) / cell);
    const maxz = Math.floor((Math.max(seg.a[2], seg.b[2]) + pad) / cell);
    for (let ix = minx; ix <= maxx; ix += 1) {
      for (let iz = minz; iz <= maxz; iz += 1) {
        const key = cellKey(ix, iz);
        if (!grid.has(key)) grid.set(key, []);
        grid.get(key).push(i);
      }
    }
  }
  return { segs, length: total, count: pts.length, grid, cell };
}

function samplePath(path, sRaw) {
  let s = ((sRaw % path.length) + path.length) % path.length;
  let lo = 0;
  let hi = path.segs.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    const seg = path.segs[mid];
    // At an exact pin position use the outgoing segment.  The authored
    // pin/roller placement also uses p[i] -> p[i+1]; choosing the incoming
    // segment here gives a 90°/turn-boundary orientation mismatch.
    if (s >= seg.s0 + seg.len) lo = mid + 1;
    else hi = mid;
  }
  const seg = path.segs[lo];
  const t = seg.len < 1e-9 ? 0 : (s - seg.s0) / seg.len;
  const tangent = normalize(sub(seg.b, seg.a));
  const normal = [-tangent[2], 0, tangent[0]];
  return { point: lerp(seg.a, seg.b, t), tangent, normal };
}

function discretePinPoint(pinIndex, phase) {
  const count = play.path?.count || 0;
  if (!count) return [0, 0, 0];
  const raw = pinIndex + phase;
  const baseRaw = Math.floor(raw);
  const base = ((baseRaw % count) + count) % count;
  const fraction = raw - baseRaw;
  const seg = play.path.segs[base];
  return lerp(seg.a, seg.b, fraction);
}

function poseDiscreteChainPart(part, offsetMm) {
  const pitch = Number(play.motion?.p)
    || play.path.length / Math.max(1, play.path.count);
  const phase = offsetMm / pitch;
  const p0 = discretePinPoint(part.pinIndex, phase);
  const p1 = discretePinPoint(part.pinIndex + 1, phase);
  const chord = Math.max(1e-6, length3(sub(p1, p0)));
  const tangent = normalize(sub(p1, p0));
  const center = [
    (p0[0] + p1[0]) / 2,
    (p0[1] + p1[1]) / 2,
    (p0[2] + p1[2]) / 2,
  ];
  const normal = [-tangent[2], 0, tangent[0]];
  part.group.position.set(
    center[0] + normal[0] * (part.side || 0),
    center[1] + (part.lift || 0),
    center[2] + normal[2] * (part.side || 0),
  );
  const yaw = Math.atan2(tangent[2], tangent[0]);
  part.group.rotation.y = -(yaw - part.restYaw);
  // At a bend, linearly interpolated pin centers are not exactly one pitch
  // apart.  Scale only the link's longitudinal axis so both holes stay on
  // the same two animated pins; this removes the visible split/spike while
  // leaving straight runs at exactly 1:1 scale.
  if (part.scaleAlong) {
    const nominal = pitch || 1;
    part.group.scale.set(chord / nominal, 1, 1);
  } else {
    part.group.scale.set(1, 1, 1);
  }
}

function projectPoint(path, x, y, z) {
  let bestD = Infinity;
  let bestS = 0;
  let bestQ = [x, y, z];
  let bestT = [1, 0, 0];
  let bestSeg = 0;
  const seen = new Set();
  const ix = Math.floor(x / (path.cell || 10));
  const iz = Math.floor(z / (path.cell || 10));
  const indices = [];
  if (path.grid) {
    for (let dx = -1; dx <= 1; dx += 1) {
      for (let dz = -1; dz <= 1; dz += 1) {
        const hits = path.grid.get(cellKey(ix + dx, iz + dz));
        if (!hits) continue;
        for (const i of hits) {
          if (seen.has(i)) continue;
          seen.add(i);
          indices.push(i);
        }
      }
    }
  }
  const scan = indices.length ? indices : path.segs.map((_, i) => i);
  for (const i of scan) {
    const seg = path.segs[i];
    const ab = sub(seg.b, seg.a);
    const ab2 = dot(ab, ab) || 1;
    const ap = [x - seg.a[0], y - seg.a[1], z - seg.a[2]];
    const t = Math.min(1, Math.max(0, dot(ap, ab) / ab2));
    const q = lerp(seg.a, seg.b, t);
    const d = (x - q[0]) ** 2 + (y - q[1]) ** 2 + (z - q[2]) ** 2;
    if (d < bestD) {
      bestD = d;
      bestS = seg.s0 + t * seg.len;
      bestQ = q;
      bestT = normalize(ab);
      bestSeg = i;
    }
  }
  const tangent = bestT;
  const normal = [-tangent[2], 0, tangent[0]];
  const delta = [x - bestQ[0], y - bestQ[1], z - bestQ[2]];
  return {
    s: bestS,
    along: dot(delta, tangent),
    side: dot(delta, normal),
    lift: delta[1],
    tangent,
    seg: bestSeg,
  };
}

function wrapPathS(s) {
  if (!play.path?.length) return 0;
  return ((s % play.path.length) + play.path.length) % play.path.length;
}

function pathDistance(from, to, dir) {
  if (!play.path?.length) return 0;
  return dir >= 0 ? wrapPathS(to - from) : wrapPathS(from - to);
}

function scheme1Status(text) {
  const out = play.host?.els?.scheme1Out;
  if (out) out.textContent = text;
}

function scheme1StationLabel(index) {
  const station = play.scheme1.stations[index];
  if (!station) return "待机";
  return `R${station.row + 1}C${station.col + 1}`;
}

function centerDemoTravelText() {
  const stroke = Number(play.currentClutch.contract?.strokeMm);
  const engagement = Math.min(1, Math.max(0, Number(play.centerDemo.engagement) || 0));
  if (!Number.isFinite(stroke)) return "0.00/0.00 mm";
  return `${(stroke * engagement).toFixed(2)}/${stroke.toFixed(2)} mm`;
}

function centerDemoStatusText() {
  const labels = {
    approach: "M5 圆套磁铁接口准备",
    engage: "M5 圆套磁铁触发公轮 +Y 接合",
    hold: "已接合保持",
    release: "磁力接口释放，公轮 +Y 回到开位",
    idle: "开位",
  };
  return `中心离合演示 · ${labels[play.centerDemo.phase] || "开位"} · 公轮轴 +Y ${centerDemoTravelText()}`;
}

function updateCenterDemoStatus() {
  scheme1Status(centerDemoStatusText());
}

function validateCenterClutchContract(contract) {
  const required = [
    "version", "axis", "role", "verticalLayoutMode",
    "centerClutchDriveLayerOffsetMm", "centerClutchVerticalLiftMm",
    "axisXMm", "axisZMm", "drawerBottomYMm", "drawerRackYMm",
    "centerFrontDriveLiftMm", "frontRackAboveShelfGapMm",
    "drawerRackLowerYMm", "drawerShelfTopYMm",
    "drawerShelfThicknessMm", "frontPinionCenterYMm",
    "frontPinionLowerFaceYMm", "frontTimingPulleyDrawerRow",
    "frontTimingPulleyLayer", "frontTimingPulleyZMm", "frontTimingBeltYMm",
    "frontTimingPulleyCenterYMm", "frontTimingPulleyBottomYMm",
    "frontTimingPulleyTopYMm", "frontTimingPulleyToPinionGapMm",
    "frontTimingBearingCenterYMm", "frontTimingBearingUpperFaceYMm",
    "frontTimingBearingLowerFaceYMm", "frontTimingBearingWidthMm",
    "frontTimingBearingIdMm", "frontTimingBearingOdMm",
    "frontTimingBearingSeatDiameterMm", "frontTimingBearingSeatDepthMm",
    "frontTimingBearingRetainerThicknessMm",
    "frontTimingBearingRetainerBoreDiameterMm",
    "frontTimingBearingReinforcementDiscDiameterMm",
    "frontTimingBearingReinforcementDiscThicknessMm",
    "frontTimingBearingShelfLowerFaceYMm",
    "frontTimingBearingBossFusionOverlapMm",
    "frontTimingBearingBossBottomYMm",
    "frontTimingBearingGearClearanceMm",
    "frontTimingBearingPulleyClearanceMm", "frontTimingBearingSupport",
    "frontTimingBearingFit", "frontDshaftProfile", "frontDshaftStartYMm",
    "frontDshaftEndYMm", "frontDshaftLengthMm", "frontPinionThicknessMm",
    "inputBaseYMm", "maleBottomYMm", "outputBaseYMm",
    "openGapMm", "dogInsertionMm", "strokeMm", "pocketDepthMm",
    "bottomClearanceMm", "magnetNonContactClearanceMm",
    "femaleMagnetProjectionMm", "magnetNominalDiameterMm",
    "gearCenterDistanceMm", "longPitchRadiusMm", "inputPitchRadiusMm",
    "gearMeshClearanceMm", "longTipRadiusMm", "inputTipRadiusMm",
    "beltEnvelopeRadiusMm", "beltGuideRadiusMm", "motherOuterRadiusMm",
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
    "linearBearingFitCouponPart", "linearBearingPart",
    "linearBearingBlockPart", "inputShaftProfile",
    "inputShaftUpperDStartMm", "inputShaftUpperDLengthMm",
    "inputShaftRoundStartMm", "inputShaftRoundLengthMm",
    "inputShaftRoundDiameterMm", "inputShaftLowerDStartMm",
    "inputShaftLowerDLengthMm", "inputSleeveTopOffsetMm",
    "inputSleeveUpperDHeightMm", "inputSleeveUpperDDiameterMm",
    "inputSleeveLowerRoundOuterDiameterMm",
    "inputSleeveLowerRoundHeightMm", "inputSleeveDSocketDepthMm",
    "inputSleeveDSocketClearanceMm", "inputSleeveMagnetNominalDiameterMm",
    "inputSleeveMagnetNominalLengthMm", "inputSleeveMagnetPocketDiameterMm",
    "inputSleeveMagnetPocketDepthMm", "inputSleeveMagnetBottomClearanceMm",
    "inputSleeveMagnetOpenBottomYMm", "snakeChainHeightDatum",
    "snakeChainLinkTopOffsetMm", "snakeChainReferenceRow",
    "snakeChainReferencePathCenterYMm", "snakeChainVerticalShiftMm",
    "snakeChainServicePathCenterYMm", "snakeChainReturnGuideCenterYMm",
    "snakeChainReturnDriveXTrimMm", "snakeChainServicePressXTrimMm",
    "snakeChainTriggerMagnetSegmentIndex",
    "snakeChainTriggerMagnetDiameterMm", "snakeChainTriggerMagnetLengthMm",
    "snakeChainTriggerMagnetNormalOffsetMm",
    "snakeChainTriggerMagnetTopClearanceMm",
    "snakeChainTriggerMagnetAxialStartOffsetMm",
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
    "shaftDiameterMm",
    "matingMagnetCount", "inputSleeveMagnetCount",
    "totalModeledMagnetCount", "rotaryBearingArrangement",
    "linearBearingArrangement", "plateWidthMm", "plateM3ClearanceMm",
    "plateBeltPassageHalfWidthMm", "plateBeltPassageSlotCount",
    "plateBeltPassageSlotCenterOffsetMm", "plateBeltPassageSlotWidthMm",
    "plateBeltPassageAxialWidthMm",
    "plateBeltPassageRadialClearanceMm",
    "plateBeltPassageAxialClearanceMm", "plateSupport", "actuation",
    "engageOnlyWhenStopped", "releaseBeforeReturn",
    "inputSideAdditionalMechanism", "centerCol", "centerRow",
    "drawerLayerCount", "serviceLayerCount", "drawerBayHeightMm",
    "drawerRackBodyHeightMm", "drawerRackMount", "drawerMassLoadPath",
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
    "inputPart", "outputPart", "outputBearingSupportPart", "mechanismPlatePart",
    "outputShaftPart", "outputBearingsPart",
  ];
  if (!contract || typeof contract !== "object") {
    throw new Error("缺少 centerClutch 机械契约");
  }
  const missing = required.filter((key) => !(key in contract));
  if (missing.length) {
    throw new Error(`centerClutch 契约缺少 ${missing.join(", ")}`);
  }
  if (contract.version !== 1
      || contract.axis !== "+Y"
      || contract.role !== "input/output"
      || contract.verticalLayoutMode !== "drawer-bottom-drive-layer-lower-pulley"
      || Math.abs(Number(contract.centerClutchDriveLayerOffsetMm)) > 0.001
      || Math.abs(Number(contract.centerClutchVerticalLiftMm)) > 0.001) {
    throw new Error("centerClutch 轴向、角色或垂直布局契约不匹配");
  }
  if (contract.actuation !== "permanent-magnet"
      || contract.engageOnlyWhenStopped !== true
      || contract.releaseBeforeReturn !== true
      || contract.inputSideAdditionalMechanism !== "none") {
    throw new Error("centerClutch 永磁动作/公轮端无额外机构门槛不满足");
  }
  if (contract.snakeChainHeightDatum !== "input-sleeve-magnet-bottom") {
    throw new Error("蛇链高度基准必须是公轮底部磁铁下沿");
  }
  if (contract.linearBearingMovesWithInput !== false
      || contract.linearBearingBlockMount !== "mechanism-plate-integral-press-fit"
      || contract.linearBearingModel !== "LM3UU-cutaway-reference"
      || contract.inputShaftProfile !== "D-round-D") {
    throw new Error("centerClutch 固定 LM3UU 或 D-round-D 契约不匹配");
  }
  const exact = {
    linearBearingFitCouponPart: "cabinet-clutch/center_linear_bearing_fit_coupon",
    linearBearingPart: "cabinet-clutch/center_linear_bearings_reference",
    linearBearingBlockPart: "cabinet-clutch/center_mechanism_plate",
    inputShaftPart: "cabinet-clutch/center_input_shaft_reference",
    inputSleevePart: "cabinet-clutch/center_input_sleeve",
    inputSleeveMagnetPart: "cabinet-clutch/center_input_sleeve_magnet_reference",
    inputPart: "cabinet-clutch/center_input_rotor",
    outputPart: "cabinet-clutch/center_output_rotor",
    mechanismPlatePart: "cabinet-clutch/center_mechanism_plate",
    outputShaftPart: "cabinet-clutch/center_output_shaft_reference",
    outputBearingsPart: "cabinet-clutch/center_output_bearings_reference",
    bearingNominal: "3x6x2",
    outputBearingSupportPart: "cabinet-clutch/center_mechanism_plate",
    outputShaftProfile: "D-round",
    rotaryBearingArrangement: "output-two-3x6x2-in-one-integral-bar-input-free",
    linearBearingArrangement: "single-coaxial-with-integrated-seat",
    plateSupport: "partition-boss-locators-plus-four-self-tapping-screws",
    drawerRackMount: "drawer-bottom-moving",
    drawerMassLoadPath: "side-slides-not-rack",
    drawerGuideBearing: "681-1x3x1-X-axis-C-slot",
    drawerGuideRail: "partition-integral-inward-C-lips",
    drawerGuideRailSupport: "existing-divider-or-side-panel-vertical-member",
    drawerGuideFlangeDirection: "toward-drawer-center",
    drawerGuideBearingArrangement: "tail-moving-plus-front-lower-fixed",
    drawerGuideBearingAxis: "+X/-X",
    drawerGuideLoadPath: "Y-support-Z-travel",
    drawerGuideTailBearingAxis: "+X/-X",
    drawerGuideFrontBearingAxis: "+X/-X",
    drawerFrontPinionBearing: "integral-shelf-stepped-3x6x2",
    frontTimingPulleyLayer: "next-drawer-bay",
    frontTimingBearingSupport: "integral-shelf-stepped-seat",
    frontTimingBearingFit: "press-fit-3x6x2-bottom-captive",
    frontDshaftProfile: "D",
  };
  for (const [key, value] of Object.entries(exact)) {
    if (contract[key] !== value) {
      throw new Error(`centerClutch 字段错误: ${key}=${contract[key]}`);
    }
  }
  const positive = [
    "openGapMm", "dogInsertionMm", "strokeMm", "pocketDepthMm",
    "bottomClearanceMm", "magnetNonContactClearanceMm",
    "femaleMagnetProjectionMm", "magnetNominalDiameterMm",
    "linearBearingNominalIdMm", "linearBearingNominalOdMm",
    "linearBearingNominalLengthMm", "linearBearingSeatDiameterMm",
    "linearBearingInputRotorClearanceMm",
    "linearBearingBlockWidthMm", "linearBearingBlockYLengthMm",
    "linearBearingBlockZLengthMm",
    "inputShaftUpperDLengthMm", "inputShaftRoundLengthMm",
    "inputShaftRoundDiameterMm", "inputShaftLowerDLengthMm",
    "inputSleeveUpperDHeightMm", "inputSleeveUpperDDiameterMm",
    "inputSleeveLowerRoundOuterDiameterMm",
    "inputSleeveLowerRoundHeightMm", "inputSleeveDSocketDepthMm",
    "inputSleeveMagnetNominalDiameterMm",
    "inputSleeveMagnetNominalLengthMm", "inputSleeveMagnetPocketDiameterMm",
    "inputSleeveMagnetPocketDepthMm", "inputSleeveMagnetOpenBottomYMm",
    "snakeChainLinkTopOffsetMm", "snakeChainReferencePathCenterYMm",
    "snakeChainServicePathCenterYMm", "snakeChainReturnGuideCenterYMm",
    "snakeChainTriggerMagnetDiameterMm",
    "snakeChainTriggerMagnetLengthMm", "snakeChainTriggerMagnetNormalOffsetMm",
    "snakeChainTriggerMagnetAxialStartOffsetMm", "outputShaftLengthMm",
    "bearingSeatDiameterMm", "bearingSeatDepthMm",
    "bearingPairSpacingMm", "outputShaftDLengthMm",
    "outputShaftRoundLengthMm", "outputShaftRoundDiameterMm",
    "outputShaftTopProtrusionMm", "outputShaftMotherSocketOverlapMm",
    "outputBearingBarWidthMm", "outputBearingBarYLengthMm",
    "outputBearingBarZLengthMm", "outputBearingBarZMarginMm",
    "outputBearingBarMotherClearanceMm", "outputBearingBarPlateOverlapMm",
    "shaftDiameterMm",
    "plateWidthMm", "plateM3ClearanceMm",
    "plateBeltPassageHalfWidthMm",
    "plateBeltPassageSlotCount", "plateBeltPassageSlotCenterOffsetMm",
    "plateBeltPassageSlotWidthMm",
    "plateBeltPassageAxialWidthMm",
    "drawerBayHeightMm", "drawerShelfThicknessMm", "drawerRackBodyHeightMm",
    "centerFrontDriveLiftMm", "frontRackAboveShelfGapMm",
    "drawerRackLowerYMm", "drawerShelfTopYMm",
    "drawerBottomYMm", "drawerRackYMm", "frontPinionCenterYMm",
    "frontPinionLowerFaceYMm", "frontTimingBeltYMm",
    "frontTimingPulleyCenterYMm", "frontTimingPulleyBottomYMm",
    "frontTimingPulleyTopYMm", "frontTimingPulleyToPinionGapMm",
    "frontTimingBearingCenterYMm", "frontTimingBearingUpperFaceYMm",
    "frontTimingBearingLowerFaceYMm", "frontTimingBearingWidthMm",
    "frontTimingBearingIdMm", "frontTimingBearingOdMm",
    "frontTimingBearingSeatDiameterMm", "frontTimingBearingSeatDepthMm",
    "frontTimingBearingRetainerThicknessMm",
    "frontTimingBearingRetainerBoreDiameterMm",
    "frontTimingBearingReinforcementDiscDiameterMm",
    "frontTimingBearingReinforcementDiscThicknessMm",
    "frontTimingBearingShelfLowerFaceYMm",
    "frontTimingBearingBossFusionOverlapMm",
    "frontTimingBearingBossBottomYMm",
    "frontTimingBearingGearClearanceMm",
    "frontTimingBearingPulleyClearanceMm", "frontDshaftStartYMm",
    "frontDshaftEndYMm", "frontDshaftLengthMm", "frontPinionThicknessMm",
    "drawerGuideRailClearanceMm", "drawerGuidePartitionThicknessMm",
    "drawerGuideRailAttachOverlapMm",
    "drawerGuideBearingSeatDiameterMm",
    "drawerGuideSlotHeightMm", "drawerGuideRailDepthMm",
    "drawerGuideFlangeThicknessMm", "drawerGuideFlangeProjectionMm",
    "drawerGuideFlangeClearanceMm", "drawerGuideDrawerEdgeInsetMm",
    "drawerGuideFlangeEndClearanceMm",
    "drawerFrontPinionBearingSeatDiameterMm",
  ];
  for (const key of positive) {
    if (!Number.isFinite(Number(contract[key])) || Number(contract[key]) <= 0) {
      throw new Error(`centerClutch 尺寸无效: ${key}`);
    }
  }
  const finite = [
    "axisXMm", "axisZMm", "centerClutchDriveLayerOffsetMm",
    "centerClutchVerticalLiftMm", "centerFrontDriveLiftMm",
    "frontRackAboveShelfGapMm", "drawerRackLowerYMm", "drawerShelfTopYMm",
    "drawerBottomYMm", "drawerRackYMm",
    "drawerGuideFrontSupportClearanceMm",
    "frontPinionCenterYMm", "frontPinionLowerFaceYMm",
    "frontTimingPulleyZMm", "frontTimingBeltYMm", "frontTimingPulleyCenterYMm",
    "frontTimingPulleyBottomYMm", "frontTimingPulleyTopYMm",
    "frontTimingBearingCenterYMm", "frontTimingBearingUpperFaceYMm",
    "frontTimingBearingLowerFaceYMm", "frontDshaftStartYMm",
    "frontDshaftEndYMm",
    "frontPinionThicknessMm", "inputBaseYMm", "maleBottomYMm", "outputBaseYMm",
    "inputSleeveMagnetOpenBottomYMm", "snakeChainReferenceRow",
    "snakeChainReferencePathCenterYMm", "snakeChainVerticalShiftMm",
    "snakeChainServicePathCenterYMm", "snakeChainReturnGuideCenterYMm",
    "snakeChainReturnDriveXTrimMm", "snakeChainServicePressXTrimMm",
    "snakeChainTriggerMagnetSegmentIndex",
    "snakeChainTriggerMagnetTopClearanceMm",
    "linearBearingCenterYOffsetMm", "linearBearingCenterYMm",
    "inputShaftUpperDStartMm", "inputShaftRoundStartMm",
    "inputShaftLowerDStartMm", "inputSleeveTopOffsetMm",
    "outputShaftStartMm", "outputShaftDStartMm", "outputShaftRoundStartMm",
    "outputBearingBarY0OffsetMm", "outputBearingBarZMinMm",
    "outputBearingBarZMaxMm",
    "plateBeltPassageRadialClearanceMm", "plateBeltPassageAxialClearanceMm",
  ];
  for (const key of finite) {
    if (!Number.isFinite(Number(contract[key]))) {
      throw new Error(`centerClutch 坐标无效: ${key}`);
    }
  }
  const n = (key) => Number(contract[key]);
  const close = (a, b, tolerance = 0.001) => Math.abs(a - b) <= tolerance;
  if (n("centerCol") !== 2 || n("centerRow") !== 1
      || n("drawerLayerCount") !== 3 || n("serviceLayerCount") !== 1
      || n("drawerBayHeightMm") < 55.29) {
    throw new Error("centerClutch 必须锁定三层柜体中心格（零基准 2,1）");
  }
  const chainPitch = n("drawerBayHeightMm") + n("drawerShelfThicknessMm");
  const expectedChainReference = n("drawerShelfTopYMm")
    - (n("centerRow") - n("snakeChainReferenceRow")) * chainPitch
    + n("drawerBayHeightMm") / 2;
  if (n("snakeChainReferenceRow") !== n("centerRow") - 1
      || !close(n("snakeChainReferencePathCenterYMm"), expectedChainReference)
      || !close(
        n("inputSleeveMagnetOpenBottomYMm"),
        n("inputBaseYMm") + n("inputSleeveTopOffsetMm")
          - n("inputSleeveUpperDHeightMm")
          - n("inputSleeveLowerRoundHeightMm") + 0.10,
      )
      || !close(
        n("snakeChainVerticalShiftMm"),
        n("inputSleeveMagnetOpenBottomYMm")
          - n("snakeChainLinkTopOffsetMm")
          - n("snakeChainReferencePathCenterYMm"),
      )
      || !close(
        n("snakeChainServicePathCenterYMm"),
        expectedChainReference - chainPitch + n("snakeChainVerticalShiftMm"),
      )
      || !close(n("snakeChainReturnGuideCenterYMm"), 41.20)
      || !close(n("snakeChainReturnDriveXTrimMm"), -4.00)
      || !close(n("snakeChainServicePressXTrimMm"), 16.00)
      || !close(n("snakeChainMotorXOffsetMm"), -2.00)
      || !close(n("snakeChainLinkTopOffsetMm"), 2.15)
      || !close(n("snakeChainTriggerMagnetDiameterMm"), 2.0)
      || !close(n("snakeChainTriggerMagnetLengthMm"), 1.8)
      || !close(n("snakeChainTriggerMagnetNormalOffsetMm"), 1.15)
      || !close(n("snakeChainTriggerMagnetTopClearanceMm"), 0)
      || !close(n("snakeChainTriggerMagnetAxialStartOffsetMm"), 2.44)
      || n("snakeChainTriggerMagnetSegmentIndex") !== 182) {
    throw new Error("蛇链服务层与公轮底部磁铁下沿的高度契约不满足");
  }
  if (n("frontTimingPulleyDrawerRow") !== n("centerRow") - 1
      || !close(n("frontPinionCenterYMm"), n("drawerRackYMm"))
      || !close(
        n("frontPinionLowerFaceYMm"),
        n("frontPinionCenterYMm") - n("frontPinionThicknessMm") / 2,
      )
      || !close(n("frontTimingPulleyCenterYMm"), n("frontTimingBeltYMm"))
      || !(n("drawerRackLowerYMm") > n("drawerShelfTopYMm"))
      || !close(
        n("drawerRackLowerYMm"),
        n("drawerShelfTopYMm") + n("frontRackAboveShelfGapMm"),
      )
      || !close(
        n("frontTimingPulleyTopYMm")
          + n("frontTimingPulleyToPinionGapMm"),
        n("frontPinionLowerFaceYMm"),
      )
      || !(n("frontTimingBeltYMm") < n("frontPinionCenterYMm"))) {
    throw new Error("centerClutch 前端同步轮没有落在主动轮下方的下一层格口");
  }
  if (!close(
        n("frontTimingBearingUpperFaceYMm"),
        n("frontTimingBearingCenterYMm") + n("frontTimingBearingWidthMm") / 2,
      )
      || !close(
        n("frontTimingBearingLowerFaceYMm"),
        n("frontTimingBearingCenterYMm") - n("frontTimingBearingWidthMm") / 2,
      )
      || !close(
        n("frontTimingBearingUpperFaceYMm")
          + n("frontTimingBearingGearClearanceMm"),
        n("frontPinionLowerFaceYMm"),
      )
      || !close(
        n("frontTimingBearingUpperFaceYMm"),
        n("drawerShelfTopYMm"),
      )
      || !close(
        n("frontTimingPulleyTopYMm")
          + n("frontTimingBearingPulleyClearanceMm"),
        n("frontTimingBearingLowerFaceYMm"),
      )
      || !(n("frontTimingBearingWidthMm") < n("drawerShelfThicknessMm"))
      || !close(
        n("frontTimingBearingSeatDepthMm"),
        n("frontTimingBearingWidthMm"),
      )
      || !close(
        n("frontTimingBearingRetainerThicknessMm")
          + n("frontTimingBearingWidthMm"),
        n("drawerShelfThicknessMm"),
      )
      || !(n("frontTimingBearingReinforcementDiscDiameterMm")
        > n("frontTimingBearingOdMm")
        && n("frontTimingBearingReinforcementDiscThicknessMm") > 0)
      || !(n("frontTimingBearingRetainerBoreDiameterMm")
        > n("frontTimingBearingIdMm")
        && n("frontTimingBearingRetainerBoreDiameterMm")
          < n("frontTimingBearingOdMm"))
      || !close(
        n("frontTimingBearingBossBottomYMm")
          + n("frontTimingBearingRetainerThicknessMm"),
        n("frontTimingBearingLowerFaceYMm")
          - n("frontTimingBearingReinforcementDiscThicknessMm"),
      )
      || !(n("frontTimingBearingBossFusionOverlapMm") > 0)
      || !(n("frontTimingBearingShelfLowerFaceYMm")
        > n("frontTimingBearingBossBottomYMm"))
      || !(n("drawerGuideSlotHeightMm")
        > n("drawerGuideBearingSeatDiameterMm")
        && n("drawerGuideFlangeThicknessMm")
          < n("drawerGuideSlotHeightMm")
        && n("drawerGuidePartitionThicknessMm") > 0
        && n("drawerGuideRailAttachOverlapMm") > 0
        && n("drawerGuideRailAttachOverlapMm")
          < n("drawerGuidePartitionThicknessMm")
        && n("drawerGuideRailDepthMm")
          > n("drawerGuideDrawerEdgeInsetMm")
            + n("drawerGuideFlangeProjectionMm")
            + n("drawerGuideRailClearanceMm")
        && close(
          n("drawerGuideFlangeEndClearanceMm"),
          n("drawerGuideRailDepthMm")
            - n("drawerGuideDrawerEdgeInsetMm")
            - n("drawerGuideFlangeProjectionMm"),
        )
        && n("drawerGuideFlangeEndClearanceMm")
          >= n("drawerGuideRailClearanceMm")
        && n("drawerGuideFrontSupportClearanceMm") === 0)
      || n("frontTimingBearingSeatDiameterMm") <= n("frontTimingBearingOdMm")
      || n("frontTimingBearingIdMm") !== n("shaftDiameterMm")
      || n("frontDshaftLengthMm") <= n("frontTimingBearingWidthMm")) {
    throw new Error("centerClutch 前端 D 轴/层间轴承的高度与配合不满足");
  }
  if (!close(n("strokeMm"), n("openGapMm") + n("dogInsertionMm"))
      || !close(n("pocketDepthMm"), n("dogInsertionMm") + n("bottomClearanceMm"))
      || !close(n("bottomClearanceMm"),
        n("femaleMagnetProjectionMm") + n("magnetNonContactClearanceMm"))) {
    throw new Error("centerClutch 行程/母槽/磁铁余量方程不满足");
  }
  if (!close(n("linearBearingSeatRadialClearanceMm"),
      (n("linearBearingSeatDiameterMm") - n("linearBearingNominalOdMm")) / 2)
      || n("linearBearingSeatDiameterMm") <= n("linearBearingNominalOdMm")
      || n("linearBearingNominalIdMm") !== n("inputShaftRoundDiameterMm")) {
    throw new Error("centerClutch LM3UU 孔径/座孔/圆滑动段不匹配");
  }
  if (n("linearBearingBlockZLengthMm") <= n("linearBearingBlockZMarginMm")
      || n("linearBearingBlockWidthMm") <= n("linearBearingSeatDiameterMm") + 2
      || !close(n("linearBearingBlockYLengthMm"),
        n("linearBearingNominalLengthMm"))
      || n("linearBearingBlockMountHoleCount") !== 0
      || n("linearBearingBlockMountHoleDiameterMm") !== 0
      || n("linearBearingBlockMountXOffsetMm") !== 0
      || n("linearBearingBlockMountYOffsetMm") !== 0) {
    throw new Error("centerClutch 一体式轴承座尺寸或无座体固定孔约束不满足");
  }
  if (!close(
    n("linearBearingCenterYOffsetMm")
      + n("linearBearingNominalLengthMm") / 2,
    -n("linearBearingInputRotorClearanceMm"),
  ) || n("linearBearingInputRotorClearanceMm") < 0.30
      || n("linearBearingInputRotorClearanceMm") > 0.60) {
    throw new Error("centerClutch 公轮与 LM3UU 一体座上沿间隙不满足");
  }
  const roundEnd = n("inputShaftRoundStartMm") + n("inputShaftRoundLengthMm");
  const bearingMin = n("linearBearingCenterYOffsetMm")
    - n("linearBearingNominalLengthMm") / 2;
  const bearingMax = n("linearBearingCenterYOffsetMm")
    + n("linearBearingNominalLengthMm") / 2;
  if (n("inputShaftRoundStartMm") > bearingMin + 0.001
      || roundEnd + n("strokeMm") < bearingMax - 0.001) {
    throw new Error("centerClutch 圆滑动段未覆盖 LM3UU 全行程");
  }
  const upperEnd = n("inputShaftUpperDStartMm") + n("inputShaftUpperDLengthMm");
  const lowerEnd = n("inputShaftLowerDStartMm") + n("inputShaftLowerDLengthMm");
  if (upperEnd < 3 - 0.001
      || roundEnd < n("inputShaftUpperDStartMm") - 0.001
      || n("inputShaftLowerDStartMm") > roundEnd + 0.001
      || lowerEnd < n("inputShaftRoundStartMm") - 0.001) {
    throw new Error("centerClutch D-round-D 三段不连续");
  }
  if (n("inputSleeveDSocketDepthMm") > n("inputSleeveUpperDHeightMm")
      || n("inputSleeveDSocketDepthMm") > n("inputShaftLowerDLengthMm")
      || n("inputSleeveMagnetPocketDiameterMm") < n("inputSleeveMagnetNominalDiameterMm")
      || n("inputSleeveMagnetPocketDepthMm") < n("inputSleeveMagnetNominalLengthMm")
      || (n("inputSleeveLowerRoundOuterDiameterMm")
        - n("inputSleeveMagnetPocketDiameterMm")) / 2 < 1.4
      || n("inputSleeveMagnetBottomClearanceMm") < 1) {
    throw new Error("centerClutch D 型圆套或 Ø5×5 磁铁槽尺寸不满足");
  }
  if (!close(n("linearBearingCenterYOffsetMm"), -5.4)
      || !close(n("linearBearingInputRotorClearanceMm"), 0.4)
      || !close(n("linearBearingBlockZMarginMm"), 1)
      || !close(n("linearBearingBlockZLengthMm"), 19.7208, 0.002)
      || !close(n("inputShaftUpperDStartMm"), -0.4)
      || !close(n("inputShaftUpperDLengthMm"), 3.6)
      || !close(n("inputShaftRoundStartMm"), -17)
      || !close(n("inputShaftRoundLengthMm"), 16.8)
      || !close(n("inputShaftLowerDStartMm"), -16.8)
      || !close(n("inputShaftLowerDLengthMm"), 3.6)
      || !close(n("inputSleeveTopOffsetMm"), -13.4)) {
    throw new Error("centerClutch 公轮轴/LM3UU/磁铁圆套新定位参数不匹配");
  }
  const seatLowerY = n("linearBearingCenterYOffsetMm")
    - n("linearBearingBlockYLengthMm") / 2;
  if (!close(seatLowerY, n("inputSleeveTopOffsetMm") + n("strokeMm"))
      || !close(seatLowerY - n("inputSleeveTopOffsetMm"), n("strokeMm"))) {
    throw new Error("centerClutch 合位圆套接触或开位完整行程间隙不满足");
  }
  if (n("bearingSeatDepthMm") < n("bearingBackShoulderMm") + 2
      || Math.abs(n("bearingReferenceCenterOffsetMm")) > 0.001
      || n("outputBearingBarWidthMm") <= n("bearingSeatDiameterMm") + 2
      || n("outputBearingBarYLengthMm")
        < 2 * n("bearingSeatDepthMm") - 2 + 1
      || n("outputBearingBarZLengthMm") <= n("outputBearingBarZMarginMm")
      || n("outputBearingBarMotherClearanceMm") <= 0) {
    throw new Error("centerClutch 输出双轴承一体长方条尺寸不满足");
  }
  const outputBarY0 = n("outputBearingBarY0OffsetMm");
  const outputBarY1 = outputBarY0 + n("outputBearingBarYLengthMm");
  const lowerOutputBearingCenter = n("bearingCenterOffsetMm");
  const upperOutputBearingCenter = lowerOutputBearingCenter
    + n("bearingPairSpacingMm");
  if (!close(lowerOutputBearingCenter, outputBarY0 + 1)
      || !close(upperOutputBearingCenter, outputBarY1 - 1)
      || outputBarY1 - n("bearingSeatDepthMm")
        - (outputBarY0 + n("bearingSeatDepthMm")) < 1 - 0.001) {
    throw new Error("centerClutch 上下输出轴承孔或中间实心隔墙不满足");
  }
  const outputDStart = n("outputShaftDStartMm");
  const outputDEnd = outputDStart + n("outputShaftDLengthMm");
  const outputRoundStart = n("outputShaftRoundStartMm");
  const outputRoundEnd = outputRoundStart + n("outputShaftRoundLengthMm");
  if (outputDStart > -3 + 0.001 || outputDEnd < -0.001
      || outputRoundStart > outputDEnd + 0.001
      || outputRoundEnd < outputDStart - 0.001
      || outputRoundStart > lowerOutputBearingCenter - 1 + 0.001
      || outputRoundEnd < upperOutputBearingCenter + 1 - 0.001
      || !close(
        Math.min(outputDEnd, 0) - Math.max(outputDStart, -3),
        n("outputShaftMotherSocketOverlapMm"),
      )
      || !close(outputRoundEnd - outputBarY1,
        n("outputShaftTopProtrusionMm"))
      || !close(outputRoundEnd - n("outputShaftStartMm"),
        n("outputShaftLengthMm"))) {
    throw new Error("centerClutch 输出短 D-round 轴未覆盖母轮盲孔和上下轴承");
  }
  if (!close(n("gearCenterDistanceMm"),
      n("longPitchRadiusMm") + n("inputPitchRadiusMm") + n("gearMeshClearanceMm"))) {
    throw new Error("centerClutch 长花键中心距不满足");
  }
  for (const key of ["beltEnvelopeRadiusMm", "beltGuideRadiusMm", "motherOuterRadiusMm"]) {
    if (n("gearCenterDistanceMm") - n("longTipRadiusMm") - n(key) < 0.45 - 0.001) {
      throw new Error(`centerClutch ${key} 径向净空不足`);
    }
  }
  if (n("plateBeltPassageHalfWidthMm") <= n("beltEnvelopeRadiusMm")
      || n("plateBeltPassageAxialWidthMm") <= 6
      || n("plateBeltPassageHalfWidthMm") >= n("plateWidthMm") / 2) {
    throw new Error("centerClutch 机构板皮带贯穿槽不满足");
  }
  if (n("plateBeltPassageSlotCount") !== 2
      || n("plateBeltPassageSlotCenterOffsetMm") <= 0
      || n("plateBeltPassageSlotWidthMm") <= 0
      || !close(
        n("plateBeltPassageSlotCenterOffsetMm")
          + n("plateBeltPassageSlotWidthMm") / 2,
        n("plateBeltPassageHalfWidthMm"),
      )) {
    throw new Error("centerClutch 机构板必须使用中心皮带左右两条真实穿板槽");
  }
  return contract;
}

function playScene() {
  return play.host?.state?.legacyRoot ?? play.host?.state?.scene ?? null;
}

function replaceMesh(item, group, parent = playScene()) {
  if (!parent || !item.mesh) return;
  group.visible = item.mesh.visible;
  // Keep the coordinate parent that app.js selected for this part.  Native
  // cabinet-clutch STL files live directly in the world scene, while the
  // older snake-chain files live under the legacy adapter.  Reparenting every
  // animated mesh to legacyRoot silently applied the old -90° transform to
  // drawer pulleys and was a major source of apparent belt breakage.
  const currentParent = item.mesh.parent || parent;
  item.mesh.parent?.remove(item.mesh);
  currentParent.add(group);
  item.mesh = group;
  item.box = new THREE.Box3().setFromObject(group);
}

function find(parent, i) {
  while (parent[i] !== i) {
    parent[i] = parent[parent[i]];
    i = parent[i];
  }
  return i;
}

function yieldFrame() {
  return new Promise((resolve) => requestAnimationFrame(resolve));
}

async function splitIslands(geometry) {
  const pos = geometry.getAttribute("position");
  const nTri = Math.floor(pos.count / 3);
  const weld = new Map();
  const parent = [];
  const canon = new Int32Array(pos.count);
  const quant = 1000;
  for (let i = 0; i < pos.count; i += 1) {
    const key = `${Math.round(pos.getX(i) * quant)},${Math.round(pos.getY(i) * quant)},${Math.round(pos.getZ(i) * quant)}`;
    let id = weld.get(key);
    if (id === undefined) {
      id = parent.length;
      parent.push(id);
      weld.set(key, id);
    }
    canon[i] = id;
    if (i % 12000 === 0) await yieldFrame();
  }
  for (let t = 0; t < nTri; t += 1) {
    const a = find(parent, canon[t * 3]);
    const b = find(parent, canon[t * 3 + 1]);
    const c = find(parent, canon[t * 3 + 2]);
    parent[b] = a;
    parent[c] = a;
    if (t % 8000 === 0) await yieldFrame();
  }
  const groups = new Map();
  for (let t = 0; t < nTri; t += 1) {
    const root = find(parent, canon[t * 3]);
    if (!groups.has(root)) groups.set(root, []);
    groups.get(root).push(t);
  }
  const geos = [];
  let built = 0;
  for (const tris of groups.values()) {
    const arr = new Float32Array(tris.length * 9);
    let w = 0;
    for (const t of tris) {
      for (let k = 0; k < 9; k += 1) arr[w++] = pos.array[t * 9 + k];
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(arr, 3));
    geo.computeVertexNormals();
    geo.computeBoundingBox();
    geos.push(geo);
    built += 1;
    if (built % 40 === 0) await yieldFrame();
  }
  return geos;
}

function buildDrawerBeltPath(geometry) {
  geometry.computeBoundingBox();
  const bounds = geometry.boundingBox;
  const size = bounds.getSize(new THREE.Vector3());
  const centerX = (bounds.min.x + bounds.max.x) / 2;
  // The belt runs along Z, so its X extent is the pulley diameter.  Using the
  // larger Z extent here makes the whole belt length look like a radius and
  // sends the teeth onto a huge, wrong loop.  Keep the derivation in the
  // canonical world frame: X is radial width, Y is belt width, Z is drawer
  // travel.
  const outerRadius = Math.max(1, size.x / 2);
  // The authored center belt is a 12T 2GT pulley.  Its STL outer radius is
  // the belt back envelope, not the pitch radius; subtracting an arbitrary
  // fraction of the pitch made every tooth sit inside the pulley root.  Keep
  // the animation path on the exact mating pitch circle.
  const pitchRadius = DRAWER_PULLEY_TEETH * DRAWER_BELT_PITCH_MM / (2 * Math.PI);
  const z0 = bounds.min.z + outerRadius;
  const z1 = bounds.max.z - outerRadius;
  const y = (bounds.min.y + bounds.max.y) / 2;
  const straight = Math.max(0.01, z1 - z0);
  const segments = [
    { type: "line", a: [centerX + pitchRadius, z0], b: [centerX + pitchRadius, z1] },
    { type: "arc", cx: centerX, cz: z1, a0: 0, a1: Math.PI },
    { type: "line", a: [centerX - pitchRadius, z1], b: [centerX - pitchRadius, z0] },
    { type: "arc", cx: centerX, cz: z0, a0: Math.PI, a1: Math.PI * 2 },
  ];
  let total = 0;
  for (const segment of segments) {
    segment.s0 = total;
    segment.len = segment.type === "line" ? straight : pitchRadius * Math.abs(segment.a1 - segment.a0);
    total += segment.len;
  }
  return { centerX, z0, z1, pitchRadius, y, outerRadius, segments, length: total };
}

function sampleDrawerBeltPath(path, sRaw) {
  let s = ((sRaw % path.length) + path.length) % path.length;
  for (const segment of path.segments) {
    if (s > segment.s0 + segment.len && segment !== path.segments[path.segments.length - 1]) continue;
    const t = segment.len < 1e-9 ? 0 : (s - segment.s0) / segment.len;
    if (segment.type === "line") {
      const dx = segment.b[0] - segment.a[0];
      const dz = segment.b[1] - segment.a[1];
      const length = Math.hypot(dx, dz) || 1;
      return {
        point: [segment.a[0] + dx * t, path.y, segment.a[1] + dz * t],
        tangent: [dx / length, 0, dz / length],
      };
    }
    const angle = segment.a0 + (segment.a1 - segment.a0) * t;
    const sign = segment.a1 >= segment.a0 ? 1 : -1;
    return {
      point: [segment.cx + path.pitchRadius * Math.cos(angle), path.y, segment.cz + path.pitchRadius * Math.sin(angle)],
      tangent: [-Math.sin(angle) * sign, 0, Math.cos(angle) * sign],
    };
  }
  return { point: [path.centerX + path.pitchRadius, path.y, path.z0], tangent: [0, 0, 1] };
}

function projectDrawerBeltPoint(path, x, z) {
  let best = { s: 0, distance: Infinity };
  for (const segment of path.segments) {
    if (segment.type === "line") {
      const ax = segment.a[0];
      const az = segment.a[1];
      const bx = segment.b[0];
      const bz = segment.b[1];
      const dx = bx - ax;
      const dz = bz - az;
      const len2 = dx * dx + dz * dz || 1;
      const t = Math.min(1, Math.max(0, ((x - ax) * dx + (z - az) * dz) / len2));
      const qx = ax + dx * t;
      const qz = az + dz * t;
      const distance = (x - qx) ** 2 + (z - qz) ** 2;
      if (distance < best.distance) best = { s: segment.s0 + segment.len * t, distance };
      continue;
    }
    const angle = Math.atan2(z - segment.cz, x - segment.cx);
    const start = segment.a0;
    const end = segment.a1;
    let candidate = angle;
    while (candidate < start) candidate += Math.PI * 2;
    while (candidate > end) candidate -= Math.PI * 2;
    candidate = Math.min(end, Math.max(start, candidate));
    const qx = segment.cx + path.pitchRadius * Math.cos(candidate);
    const qz = segment.cz + path.pitchRadius * Math.sin(candidate);
    const distance = (x - qx) ** 2 + (z - qz) ** 2;
    if (distance < best.distance) {
      best = { s: segment.s0 + path.pitchRadius * (candidate - start), distance };
    }
  }
  return best.s;
}

function isCurrentClutchStation(index = play.scheme1.targetIndex) {
  const station = play.scheme1.stations[index];
  return Boolean(
    station
      && Number(station.row) === CURRENT_CLUTCH_ROW
      && Number(station.col) === CURRENT_CLUTCH_COL,
  );
}

function currentClutchDrivesDrawer() {
  if (!play.scheme1.ready || !play.currentClutch.contract) return false;
  // The current assembly contains one real clutch pair: the center-cell first
  // article. Never proxy that pair onto the other selector stations. Once
  // the selector leaves the center cell it may continue indexing, but the center input
  // must stay open and the drawer/power belts must stop until a real clutch is
  // added for that station.
  return isCurrentClutchStation();
}

function drawerDriveTurns() {
  // Do not let the drawer take-off borrow the snake motor while the motion
  // manifest is still loading.  The drawer power datum becomes live only
  // inside the explicit OPEN/CLOSE phases below.
  if (!play.scheme1.ready || !currentClutchDrivesDrawer()) return 0;
  const phase = play.scheme1.phase;
  if (phase !== SCHEME1_PHASE.OPEN && phase !== SCHEME1_PHASE.CLOSE) return 0;
  return play.scheme1.powerTurns;
}

function drawerPathNormal(sample) {
  // Path coordinates are X/Z while the belt's axial width is Y.  This is the
  // inward in-plane normal: the belt teeth point toward the pulley center.
  return [-sample.tangent[2], sample.tangent[0]];
}

const BELT_TOOTH_HEIGHT = 0.63;
const BELT_TOOTH_BASE = 0.72;
const BELT_TOOTH_TIP = 0.44;
const BELT_BODY_SAMPLE_STEP = 0.65;
const BELT_TOOTH_BODY_OVERLAP = 0.03;

function buildContinuousBeltBaseGeometry(path, beltThickness, beltWidth) {
  // The authored STL is an excellent manufacturing reference, but it is a
  // union of a closed ribbon and hundreds of separate tooth prisms.  Bending
  // that non-indexed STL vertex-by-vertex makes a face cross a line/arc seam
  // at different times from its neighbours.  Rebuild only the smooth ribbon
  // from the same pitch path so its topology stays continuous for the whole
  // animation.
  const sampleCount = Math.max(128, Math.ceil(path.length / BELT_BODY_SAMPLE_STEP));
  const positions = new Float32Array(sampleCount * 4 * 3);
  const indices = [];
  const y0 = path.y - beltWidth / 2;
  const y1 = path.y + beltWidth / 2;
  for (let i = 0; i < sampleCount; i += 1) {
    const sample = path.sample(path.length * i / sampleCount);
    const normal = path.normal(sample);
    const inner = [sample.point[0], sample.point[2]];
    const outer = [
      sample.point[0] - normal[0] * beltThickness,
      sample.point[2] - normal[1] * beltThickness,
    ];
    const offset = i * 12;
    const values = [
      inner[0], y0, inner[1],
      inner[0], y1, inner[1],
      outer[0], y1, outer[1],
      outer[0], y0, outer[1],
    ];
    positions.set(values, offset);
  }
  for (let i = 0; i < sampleCount; i += 1) {
    const next = (i + 1) % sampleCount;
    for (let side = 0; side < 4; side += 1) {
      const a = i * 4 + side;
      const b = next * 4 + side;
      const c = next * 4 + (side + 1) % 4;
      const d = i * 4 + (side + 1) % 4;
      indices.push(a, b, d, b, c, d);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}

function beltToothPoint(sample, normal, along, radial) {
  return [
    sample.point[0] + sample.tangent[0] * along + normal[0] * radial,
    sample.point[1],
    sample.point[2] + sample.tangent[2] * along + normal[1] * radial,
  ];
}

function writeBeltToothVertices(position, toothIndex, belt, phaseMm) {
  const sample = belt.path.sample(belt.toothS[toothIndex] + phaseMm);
  const normal = belt.path.normal(sample);
  const outline = [
    [-belt.toothBase / 2, -BELT_TOOTH_BODY_OVERLAP],
    [belt.toothBase / 2, -BELT_TOOTH_BODY_OVERLAP],
    [belt.toothTip / 2, belt.toothHeight],
    [-belt.toothTip / 2, belt.toothHeight],
  ];
  const positionOffset = toothIndex * 8;
  for (let side = 0; side < 2; side += 1) {
    const y = belt.path.y + (side === 0 ? -belt.width / 2 : belt.width / 2);
    for (let corner = 0; corner < outline.length; corner += 1) {
      const point = beltToothPoint(
        sample,
        normal,
        outline[corner][0],
        outline[corner][1],
      );
      position.setXYZ(
        positionOffset + side * 4 + corner,
        point[0],
        y,
        point[2],
      );
    }
  }
}

function buildBeltToothGeometry(path, belt, phaseMm = 0) {
  const positions = new Float32Array(belt.toothCount * 8 * 3);
  const indices = [];
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  for (let tooth = 0; tooth < belt.toothCount; tooth += 1) {
    writeBeltToothVertices(geometry.getAttribute("position"), tooth, belt, phaseMm);
    const base = tooth * 8;
    // Bottom and top faces.
    indices.push(base, base + 1, base + 2, base, base + 2, base + 3);
    indices.push(base + 4, base + 6, base + 5, base + 4, base + 7, base + 6);
    // Four side faces of one complete tooth prism.
    for (let side = 0; side < 4; side += 1) {
      const a = base + side;
      const b = base + (side + 1) % 4;
      const c = base + 4 + (side + 1) % 4;
      const d = base + 4 + side;
      indices.push(a, b, d, b, c, d);
    }
  }
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}

function poseBeltTeeth(belt, phaseMm) {
  if (Number.isFinite(belt.lastPhase) && Math.abs(belt.lastPhase - phaseMm) < 1e-6) return;
  const position = belt.mesh.geometry.getAttribute("position");
  for (let tooth = 0; tooth < belt.toothCount; tooth += 1) {
    writeBeltToothVertices(position, tooth, belt, phaseMm);
  }
  position.needsUpdate = true;
  belt.mesh.geometry.computeVertexNormals();
  belt.mesh.geometry.computeBoundingBox();
  belt.mesh.geometry.computeBoundingSphere();
  belt.lastPhase = phaseMm;
}

function createAnimatedBelt(item, path, pitchMm, phaseSign = 1) {
  const sourceMesh = item.mesh;
  const sourceGeometry = sourceMesh.geometry;
  sourceGeometry.computeBoundingBox();
  const size = sourceGeometry.boundingBox.getSize(new THREE.Vector3());
  const beltWidth = Math.max(0.1, size.y);
  const beltThickness = Math.max(0.1, path.outerRadius - path.pitchRadius);
  const belt = {
    mesh: null,
    baseMesh: null,
    path,
    toothS: new Float32Array(Math.max(1, Math.round(path.length / pitchMm))),
    toothCount: Math.max(1, Math.round(path.length / pitchMm)),
    toothPitch: pitchMm,
    toothHeight: BELT_TOOTH_HEIGHT,
    toothBase: BELT_TOOTH_BASE,
    toothTip: BELT_TOOTH_TIP,
    width: beltWidth,
    phaseSign,
    lastPhase: Number.NaN,
  };
  for (let tooth = 0; tooth < belt.toothCount; tooth += 1) {
    belt.toothS[tooth] = (tooth + 0.5) * pitchMm;
  }
  // Keep the belt double-sided so its surface is visible from either side, but
  // leave depth testing enabled.  The belt must be occluded by the shafts,
  // gears, drawer parts, and cabinet surfaces that are actually in front of it.
  const beltMaterial = sourceMesh.material.clone();
  beltMaterial.side = THREE.DoubleSide;
  beltMaterial.transparent = false;
  beltMaterial.opacity = 1;
  beltMaterial.depthTest = true;
  beltMaterial.depthWrite = true;
  const baseMesh = new THREE.Mesh(
    buildContinuousBeltBaseGeometry(path, beltThickness, beltWidth),
    beltMaterial,
  );
  const toothMesh = new THREE.Mesh(
    buildBeltToothGeometry(path, belt, 0),
    beltMaterial,
  );
  baseMesh.renderOrder = 0;
  toothMesh.renderOrder = 1;
  const group = new THREE.Group();
  group.name = "continuous-timing-belt";
  group.userData.animatedBelt = true;
  group.visible = sourceMesh.visible;
  group.add(baseMesh, toothMesh);
  replaceMesh(item, group, sourceMesh.parent || playScene());
  sourceGeometry.dispose();
  belt.mesh = toothMesh;
  belt.baseMesh = baseMesh;
  return belt;
}

function bindDrawerBeltMesh(item) {
  if (!item.mesh?.isMesh || !play.host?.state?.scene) return;
  const geometry = item.mesh.geometry;
  const path = buildDrawerBeltPath(geometry);
  path.sample = (s) => sampleDrawerBeltPath(path, s);
  path.normal = drawerPathNormal;
  play.drawerBelts.push(createAnimatedBelt(item, path, DRAWER_BELT_PITCH_MM, -1));
}

function bindDrawerRotaryMesh(item, sign = 1) {
  if (!item.mesh?.isMesh || !play.host?.state?.scene) return;
  const geometry = item.mesh.geometry;
  geometry.computeBoundingBox();
  const center = geometry.boundingBox.getCenter(new THREE.Vector3());
  geometry.translate(-center.x, -center.y, -center.z);
  const pivot = new THREE.Group();
  pivot.position.copy(center);
  pivot.add(new THREE.Mesh(geometry, item.mesh.material));
  const group = new THREE.Group();
  group.name = "drawer-drive-rotary-animated";
  group.add(pivot);
  replaceMesh(item, group, play.host.state.scene);
  play.drawerRotaries.push({ group: pivot, sign, restY: 0 });
}

function bindCurrentClutchMesh(item, config) {
  if (!item.mesh?.isMesh || !play.host?.state?.scene) return;
  const geometry = item.mesh.geometry;
  geometry.computeBoundingBox();
  const center = geometry.boundingBox.getCenter(new THREE.Vector3());
  const contract = play.currentClutch.contract;
  const axisX = Number(contract?.axisXMm);
  const axisZ = Number(contract?.axisZMm);
  const pivotX = Number.isFinite(axisX) ? axisX : center.x;
  const pivotZ = Number.isFinite(axisZ) ? axisZ : center.z;
  // A D shaft's flat shifts its bounding-box centre by half the flat depth;
  // the carriage also contains off-axis guide shoes. Use the OpenSCAD axis
  // datum whenever the contract provides it so rotations stay coaxial and
  // only the explicitly moving parts receive the +Y stroke.
  geometry.translate(-pivotX, -center.y, -pivotZ);
  const pivot = new THREE.Group();
  pivot.position.set(pivotX, center.y, pivotZ);
  pivot.name = `current-clutch-${config.role}`;
  pivot.add(new THREE.Mesh(geometry, item.mesh.material));
  const group = new THREE.Group();
  group.name = `current-clutch-${config.role}-container`;
  group.add(pivot);
  // Native center parts belong directly to the canonical world scene. Do not
  // send them through legacyRoot: that old -90° adapter is only for the
  // cabinet-chain coordinate frame.
  replaceMesh(item, group, play.host.state.scene);
  const part = {
    group: pivot,
    role: config.role,
    sign: -1,
    baseY: center.y,
    restY: 0,
    moves: Boolean(config.moves),
    rotates: Boolean(config.rotates),
  };
  play.currentClutch.parts.push(part);
  if (config.primary) play.currentClutch[config.role] = part;
}

function bindWorldYAxisRotaryMesh(item, target, name, sign = 1) {
  if (!item.mesh?.isMesh || !playScene()) return;
  const geometry = item.mesh.geometry;
  geometry.computeBoundingBox();
  const center = geometry.boundingBox.getCenter(new THREE.Vector3());
  geometry.translate(-center.x, -center.y, -center.z);
  const pivot = new THREE.Group();
  pivot.position.copy(center);
  pivot.name = name;
  pivot.add(new THREE.Mesh(geometry, item.mesh.material));
  const group = new THREE.Group();
  group.name = `${name}-container`;
  group.add(pivot);
  replaceMesh(item, group);
  target.push({ group: pivot, sign, restY: 0 });
}

function buildHorizontalBeltPath(geometry) {
  geometry.computeBoundingBox();
  const bounds = geometry.boundingBox;
  const size = bounds.getSize(new THREE.Vector3());
  const centerZ = (bounds.min.z + bounds.max.z) / 2;
  // The column belt runs along world X.  Its Z extent is the pulley diameter;
  // the Y extent is the 6 mm axial belt width.
  const outerRadius = Math.max(1, size.z / 2);
  const pitchRadius = POWER_COLUMN_PULLEY_TEETH * POWER_COLUMN_BELT_PITCH_MM
    / (2 * Math.PI);
  const x0 = bounds.min.x + outerRadius;
  const x1 = bounds.max.x - outerRadius;
  const y = (bounds.min.y + bounds.max.y) / 2;
  const straight = Math.max(0.01, x1 - x0);
  const segments = [
    { type: "line", a: [x0, centerZ - pitchRadius], b: [x1, centerZ - pitchRadius] },
    { type: "arc", cx: x1, cz: centerZ, a0: -Math.PI / 2, a1: Math.PI / 2 },
    { type: "line", a: [x1, centerZ + pitchRadius], b: [x0, centerZ + pitchRadius] },
    { type: "arc", cx: x0, cz: centerZ, a0: Math.PI / 2, a1: Math.PI * 1.5 },
  ];
  let total = 0;
  for (const segment of segments) {
    segment.s0 = total;
    segment.len = segment.type === "line"
      ? straight
      : pitchRadius * Math.abs(segment.a1 - segment.a0);
    total += segment.len;
  }
  return { centerZ, x0, x1, pitchRadius, y, outerRadius, segments, length: total };
}

function sampleHorizontalBeltPath(path, sRaw) {
  const s = ((sRaw % path.length) + path.length) % path.length;
  for (const segment of path.segments) {
    if (s > segment.s0 + segment.len
      && segment !== path.segments[path.segments.length - 1]) continue;
    const t = segment.len < 1e-9 ? 0 : (s - segment.s0) / segment.len;
    if (segment.type === "line") {
      const dx = segment.b[0] - segment.a[0];
      const dz = segment.b[1] - segment.a[1];
      const length = Math.hypot(dx, dz) || 1;
      return {
        point: [segment.a[0] + dx * t, path.y, segment.a[1] + dz * t],
        tangent: [dx / length, 0, dz / length],
      };
    }
    const angle = segment.a0 + (segment.a1 - segment.a0) * t;
    const direction = segment.a1 >= segment.a0 ? 1 : -1;
    return {
      point: [
        segment.cx + path.pitchRadius * Math.cos(angle),
        path.y,
        segment.cz + path.pitchRadius * Math.sin(angle),
      ],
      tangent: [
        -Math.sin(angle) * direction,
        0,
        Math.cos(angle) * direction,
      ],
    };
  }
  return {
    point: [path.x0, path.y, path.centerZ - path.pitchRadius],
    tangent: [1, 0, 0],
  };
}

function projectHorizontalBeltPoint(path, x, z) {
  let best = { s: 0, distance: Infinity };
  for (const segment of path.segments) {
    if (segment.type === "line") {
      const ax = segment.a[0];
      const az = segment.a[1];
      const bx = segment.b[0];
      const bz = segment.b[1];
      const dx = bx - ax;
      const dz = bz - az;
      const len2 = dx * dx + dz * dz || 1;
      const t = Math.min(1, Math.max(0,
        ((x - ax) * dx + (z - az) * dz) / len2));
      const qx = ax + dx * t;
      const qz = az + dz * t;
      const distance = (x - qx) ** 2 + (z - qz) ** 2;
      if (distance < best.distance) {
        best = { s: segment.s0 + segment.len * t, distance };
      }
      continue;
    }
    const angle = Math.atan2(z - segment.cz, x - segment.cx);
    const start = segment.a0;
    const end = segment.a1;
    let candidate = angle;
    while (candidate < start) candidate += Math.PI * 2;
    while (candidate > end) candidate -= Math.PI * 2;
    candidate = Math.min(end, Math.max(start, candidate));
    const qx = segment.cx + path.pitchRadius * Math.cos(candidate);
    const qz = segment.cz + path.pitchRadius * Math.sin(candidate);
    const distance = (x - qx) ** 2 + (z - qz) ** 2;
    if (distance < best.distance) {
      best = { s: segment.s0 + path.pitchRadius * (candidate - start), distance };
    }
  }
  return best.s;
}

function bindColumnSyncBeltMesh(item) {
  if (!item.mesh?.isMesh || !playScene()) return;
  const path = buildHorizontalBeltPath(item.mesh.geometry);
  path.sample = (s) => sampleHorizontalBeltPath(path, s);
  path.normal = drawerPathNormal;
  play.columnSyncBelts.push(createAnimatedBelt(
    item,
    path,
    POWER_COLUMN_BELT_PITCH_MM,
    1,
  ));
}

function makePlateTemplateGeometry(values, seg) {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(values), 3));
  geo.computeVertexNormals();
  geo.translate(
    -(seg.a[0] + seg.b[0]) / 2,
    -(seg.a[1] + seg.b[1]) / 2,
    -(seg.a[2] + seg.b[2]) / 2,
  );
  geo.computeBoundingBox();
  return {
    geometry: geo,
    restYaw: Math.atan2(seg.b[2] - seg.a[2], seg.b[0] - seg.a[0]),
  };
}

async function extractPlateTemplates(geometry) {
  const pos = geometry.getAttribute("position");
  const nTri = Math.floor(pos.count / 3);
  const wanted = new Set(Object.values(PLATE_TEMPLATE_SEGMENTS));
  const valuesBySegment = new Map([...wanted].map((index) => [index, []]));
  const plateReach = Math.min(2.30, (play.motion?.p || 4.7625) * 0.49);
  const outerLayer = 1.80;

  // OpenSCAD 导出的两层链板在 STL 中会各自合并成一张连通网格，不能依靠
  // 拓扑连通性拆节。也不能把拐角处的三角形按最近路径段分桶：那会把同一
  // 个链节切开。只从直线上的已知外/内链节提取一次模板，随后所有链节共享
  // 模板几何并各自以路径节为刚体运动。
  //
  // 这里还要按两个独立的条件选三角形：
  // 1. 沿直线链节自身的局部纵向范围，而不是“离哪一段路径最近”；相邻
  //    内外链板在销孔处会有重叠，最近路径归桶会把一个链节切掉。
  // 2. 原始 STL 的轴向层：外链板在 |Y-chainY| >= 1.80，内链板在里面。
  //    连接节只保留负 Y 侧的那一块普通外链板，另一侧由高亮接头提供。
  const templateSegments = Object.values(PLATE_TEMPLATE_SEGMENTS);
  const frameBySegment = new Map(templateSegments.map((segmentIndex) => {
    const seg = play.path.segs[segmentIndex];
    const tangent = normalize(sub(seg.b, seg.a));
    return [segmentIndex, { seg, tangent, normal: [-tangent[2], 0, tangent[0]] }];
  }));
  for (let t = 0; t < nTri; t += 1) {
    const offset = t * 9;
    const x = (pos.array[offset] + pos.array[offset + 3] + pos.array[offset + 6]) / 3;
    const y = (pos.array[offset + 1] + pos.array[offset + 4] + pos.array[offset + 7]) / 3;
    const z = (pos.array[offset + 2] + pos.array[offset + 5] + pos.array[offset + 8]) / 3;
    const axial = y - play.motion.chainY;
    for (const [segmentIndex, frame] of frameBySegment) {
      const delta = sub([x, y, z], frame.seg.a);
      const along = dot(delta, frame.tangent);
      const side = dot(delta, frame.normal);
      if (along < -plateReach || along > frame.seg.len + plateReach || Math.abs(side) > plateReach) {
        continue;
      }
      const isOuter = Math.abs(axial) >= outerLayer;
      const isSelected = segmentIndex === PLATE_TEMPLATE_SEGMENTS.connector
        ? axial <= -outerLayer
        : segmentIndex === PLATE_TEMPLATE_SEGMENTS.outer
          ? isOuter
          : !isOuter;
      if (!isSelected) continue;
      const values = valuesBySegment.get(segmentIndex);
      for (let k = 0; k < 9; k += 1) values.push(pos.array[offset + k]);
      break;
    }
    if (t % 2000 === 0) await yieldFrame();
  }

  const templates = {};
  for (const [kind, segmentIndex] of Object.entries(PLATE_TEMPLATE_SEGMENTS)) {
    const values = valuesBySegment.get(segmentIndex) || [];
    if (!values.length) throw new Error(`链板模板缺少路径节 ${segmentIndex}`);
    templates[kind] = makePlateTemplateGeometry(values, play.path.segs[segmentIndex]);
  }
  return templates;
}

function chainOffsetMm() {
  if (!play.path) return 0;
  const pitches = play.motorTurns * (play.motion?.driveTeeth || 12);
  return pitches * chainPitchMm();
}

function poseChainPart(part, offsetMm) {
  if (Number.isInteger(part.pinIndex)) {
    poseDiscreteChainPart(part, offsetMm);
    return;
  }
  // `along` is the authored geometry centre's longitudinal offset from the
  // path projection.  Apply it to the sampled path coordinate itself so a
  // link crossing a corner is centred and oriented around the same anchor;
  // adding it after taking the two endpoint samples mixes two different
  // tangents and is what makes a link peel away at a turn.
  const anchorS = part.s + offsetMm + (part.along || 0);
  const sample = samplePath(play.path, anchorS);
  // 链板/接头是跨越两个销的刚体。拐入齿轮时，路径是由相邻销位组成的折线，
  // 所以不能把链板中心放在折点本身：那会让两端孔偏离两根销，动画中看起来像
  // 链条被撕裂。用两端销位的真实中点放置，并用两端连线定姿态；销和滚子
  // halfSpan=0，仍只跟随各自的中心线。
  let tangent = sample.tangent;
  let center = sample.point;
  if (part.halfSpan > 1e-6) {
    const before = samplePath(play.path, anchorS - part.halfSpan).point;
    const after = samplePath(play.path, anchorS + part.halfSpan).point;
    center = [
      (before[0] + after[0]) / 2,
      (before[1] + after[1]) / 2,
      (before[2] + after[2]) / 2,
    ];
    tangent = normalize(sub(after, before));
  }
  const normal = [-tangent[2], 0, tangent[0]];
  part.group.position.set(
    center[0] + normal[0] * part.side,
    center[1] + part.lift,
    center[2] + normal[2] * part.side,
  );
  const yaw = Math.atan2(tangent[2], tangent[0]);
  part.group.rotation.y = -(yaw - part.restYaw);
}

async function bindWheelMesh(item, kind) {
  const motion = play.motion;
  if (!motion || !item.mesh?.isMesh || !playScene()) return;
  const candidates = motion.wheels.filter((wheel) => wheel.kind === kind);
  const islands = await splitIslands(item.mesh.geometry);
  const group = new THREE.Group();
  const used = new Set();
  for (const geo of islands) {
    const center = geo.boundingBox.getCenter(new THREE.Vector3());
    let best = null;
    let bestD = Infinity;
    for (const wheel of candidates) {
      if (used.has(wheel.id)) continue;
      const d =
        (center.x - wheel.x) ** 2 +
        (center.y - motion.chainY) ** 2 +
        (center.z - wheel.z) ** 2;
      if (d < bestD) {
        bestD = d;
        best = wheel;
      }
    }
    if (!best) continue;
    used.add(best.id);
    geo.translate(-best.x, -motion.chainY, -best.z);
    const pivot = new THREE.Group();
    pivot.position.set(best.x, motion.chainY, best.z);
    pivot.add(new THREE.Mesh(geo, item.mesh.material));
    group.add(pivot);
    play.wheels.push({
      group: pivot,
      teeth: best.teeth,
      sign: best.sign,
      restY: 0,
    });
  }
  replaceMesh(item, group);
}

async function bindChainBearingMesh(item) {
  const motion = play.motion;
  if (!motion || !item.mesh?.isMesh || !playScene()) return;
  const candidates = motion.wheels.filter((wheel) => wheel.kind === "idler");
  const islands = await splitIslands(item.mesh.geometry);
  const grouped = new Map(candidates.map((wheel) => [wheel.id, []]));

  // One purchase bearing is exported as separate outer/inner race islands.
  // Assign every island to its nearest solved wheel instead of consuming one
  // island per wheel; the old one-to-one matcher left the bearing races at
  // their authored coordinates and made them appear detached from the green
  // 8T wheels after the chain datum moved.
  for (const geo of islands) {
    const center = geo.boundingBox.getCenter(new THREE.Vector3());
    let best = null;
    let bestD = Infinity;
    for (const wheel of candidates) {
      const d =
        (center.x - wheel.x) ** 2
        + (center.y - motion.chainY) ** 2
        + (center.z - wheel.z) ** 2;
      if (d < bestD) {
        bestD = d;
        best = wheel;
      }
    }
    if (best) grouped.get(best.id).push(geo);
  }

  const group = new THREE.Group();
  for (const wheel of candidates) {
    const wheelIslands = grouped.get(wheel.id) || [];
    if (!wheelIslands.length) continue;
    const rotating = new THREE.Group();
    const fixed = new THREE.Group();
    rotating.position.set(wheel.x, motion.chainY, wheel.z);
    fixed.position.set(wheel.x, motion.chainY, wheel.z);
    for (const geo of wheelIslands) {
      const size = geo.boundingBox.getSize(new THREE.Vector3());
      const isOuterRaceOrSeal = Math.max(size.x, size.z) > 5.4;
      geo.translate(-wheel.x, -motion.chainY, -wheel.z);
      (isOuterRaceOrSeal ? rotating : fixed).add(
        new THREE.Mesh(geo, item.mesh.material),
      );
    }
    group.add(rotating, fixed);
    play.bearingRotaries.push({
      group: rotating,
      teeth: wheel.teeth,
      sign: wheel.sign,
      restY: 0,
    });
  }
  replaceMesh(item, group);
}

async function bindMotorShaftMesh(item) {
  const motion = play.motion;
  if (!motion || !item.mesh?.isMesh || !playScene()) return;
  const drive = motion.wheels.find((wheel) => wheel.id === "power")
    || motion.wheels.find((wheel) => wheel.id === "entry");
  if (!drive) return;

  // The assembly STL contains only the D output shaft.  Place its pivot on
  // the same X/Z axis as the power wheel; the Y coordinate can be any point
  // on that shaft line.  This keeps the motor body fixed while the visible
  // shaft rotates 1:1 with the D-shaft wheel.
  const shaftGeometry = item.mesh.geometry;
  shaftGeometry.translate(-drive.x, -motion.chainY, -drive.z);
  const pivot = new THREE.Group();
  pivot.position.set(drive.x, motion.chainY, drive.z);
  pivot.add(new THREE.Mesh(shaftGeometry, item.mesh.material));
  const group = new THREE.Group();
  group.add(pivot);
  play.motorShafts.push({ group: pivot, restY: 0 });
  replaceMesh(item, group);
}

function scheme1CandidateCenter(station, side) {
  if (side === "input") {
    return {
      x: station.x,
      y: (station.powerY + station.dogInputY) / 2,
      z: station.z,
    };
  }
  return {
    x: station.x,
    y: (station.outputY + station.dogOutputY) / 2,
    z: station.z,
  };
}

async function bindScheme1WheelMesh(item, side) {
  const motion = play.motion;
  const scheme = play.scheme1;
  if (!motion || !scheme.ready || !item.mesh?.isMesh || !playScene()) return;
  const isPower = side === "power";
  const islands = await splitIslands(item.mesh.geometry);
  const group = new THREE.Group();
  const used = new Set();
  const bound = isPower ? scheme.powerWheels : scheme.outputWheels;
  for (const geo of islands) {
    const center = geo.boundingBox.getCenter(new THREE.Vector3());
    let best = null;
    let bestD = Infinity;
    for (let index = 0; index < scheme.stations.length; index += 1) {
      if (used.has(index)) continue;
      const station = scheme.stations[index];
      const y = isPower ? station.powerY : station.outputY;
      const d =
        (center.x - station.x) ** 2 +
        (center.z - station.z) ** 2 +
        0.35 * (center.y - y) ** 2;
      if (d < bestD) {
        bestD = d;
        best = { index, station, y };
      }
    }
    if (!best) continue;
    used.add(best.index);
    // STL 坐标已经是装配坐标；把每个轮的轴心放到自己的 pivot，之后只
    // 绕世界 Y 轴转动，不再对整个 25 轮 STL 进行整体缩放或形变。
    geo.translate(-best.station.x, -best.y, -best.station.z);
    const pivot = new THREE.Group();
    pivot.position.set(best.station.x, best.y, best.station.z);
    pivot.add(new THREE.Mesh(geo, item.mesh.material));
    group.add(pivot);
    bound.push({
      group: pivot,
      teeth: 12,
      sign: 1,
      restY: 0,
      stationIndex: best.index,
    });
  }
  if (used.size !== scheme.stations.length) {
    console.warn(`方案1 ${side}轮绑定数量 ${used.size}/${scheme.stations.length}`);
  }
  replaceMesh(item, group);
}

async function bindScheme1ClutchMesh(item) {
  const motion = play.motion;
  const scheme = play.scheme1;
  if (!motion || !scheme.ready || !item.mesh?.isMesh || !playScene()) return;
  const islands = await splitIslands(item.mesh.geometry);
  const group = new THREE.Group();
  const used = new Set();
  const candidates = [];
  for (let index = 0; index < scheme.stations.length; index += 1) {
    const station = scheme.stations[index];
    const inputCenter = scheme1CandidateCenter(station, "input");
    const outputCenter = scheme1CandidateCenter(station, "output");
    candidates.push({
      index,
      side: "input",
      station,
      axisY: station.dogInputY,
      center: inputCenter,
    });
    candidates.push({
      index,
      side: "output",
      station,
      axisY: station.dogOutputY,
      center: outputCenter,
    });
  }
  for (const geo of islands) {
    const center = geo.boundingBox.getCenter(new THREE.Vector3());
    let best = null;
    let bestD = Infinity;
    for (const candidate of candidates) {
      const key = `${candidate.index}:${candidate.side}`;
      if (used.has(key)) continue;
      const d =
        (center.x - candidate.center.x) ** 2 +
        (center.z - candidate.center.z) ** 2 +
        0.55 * (center.y - candidate.center.y) ** 2;
      if (d < bestD) {
        bestD = d;
        best = { ...candidate, key };
      }
    }
    if (!best) continue;
    used.add(best.key);
    geo.translate(-best.station.x, -best.axisY, -best.station.z);
    const pivot = new THREE.Group();
    pivot.position.set(best.station.x, best.axisY, best.station.z);
    pivot.add(new THREE.Mesh(geo, item.mesh.material));
    group.add(pivot);
    scheme.clutches.push({
      group: pivot,
      stationIndex: best.index,
      side: best.side,
      baseY: best.axisY,
      openY: best.axisY,
      engagedY: best.side === "output" ? best.station.dogEngagedY : best.axisY,
      restY: 0,
    });
  }
  if (used.size !== candidates.length) {
    console.warn(`方案1离合绑定数量 ${used.size}/${candidates.length}`);
  }
  replaceMesh(item, group);
}

async function bindScheme1SelectorMesh(item) {
  const scheme = play.scheme1;
  if (!scheme.ready || !item.mesh?.isMesh || !playScene()) return;
  const geometry = item.mesh.geometry;
  geometry.computeBoundingBox();
  const center = geometry.boundingBox.getCenter(new THREE.Vector3());
  const proj = projectPoint(play.path, center.x, center.y, center.z);
  geometry.translate(-center.x, -center.y, -center.z);
  const pivot = new THREE.Group();
  pivot.position.copy(center);
  pivot.add(new THREE.Mesh(geometry, item.mesh.material));
  const group = new THREE.Group();
  group.add(pivot);
  scheme.selectorPart = {
    group: pivot,
    s: proj.s,
    along: proj.along,
    side: proj.side,
    lift: proj.lift,
    restYaw: Math.atan2(proj.tangent[2], proj.tangent[0]),
    halfSpan: 0,
  };
  replaceMesh(item, group);
  poseSelectorPart(scheme.selectorPart, scheme.selectorS - scheme.selectorPart.s);
}

function poseSelectorPart(part, deltaMm) {
  poseChainPart(part, deltaMm);
}

function initScheme1Motion() {
  const motion = play.motion;
  const scheme = motion?.scheme1;
  if (!motion || !scheme?.stations?.length || !play.path) return;
  const stations = scheme.stations;
  const stationS = stations.map((station) => projectPoint(
    play.path,
    station.x,
    motion.chainY,
    station.z,
  ).s);
  const start = Math.min(
    stations.length - 1,
    Math.max(0, Number(scheme.selectorStart) || 0),
  );
  play.scheme1.stations = stations;
  play.scheme1.stationS = stationS;
  play.scheme1.selectorS = stationS[start];
  play.scheme1.targetIndex = start;
  play.scheme1.phase = SCHEME1_PHASE.INDEX;
  play.scheme1.phaseTime = 0;
  play.scheme1.powerTurns = 0;
  play.scheme1.outputTurns = Array.from({ length: stations.length }, () => 0);
  play.scheme1.cycleSign = 1;
  play.scheme1.cycleStartPowerTurns = 0;
  play.scheme1.cycleStartOutputTurns = 0;
  play.scheme1.cycleProgressTurns = 0;
  play.scheme1.ready = true;
  if (play.centerViewRequested && snapScheme1ToCenter()) {
    scheme1Status("首件视角 · 三层柜体中心格触发基准已对准 · 开位");
  } else {
    scheme1Status(`选择指待机 · R${stations[start].row + 1}C${stations[start].col + 1}`);
  }
}

function snapScheme1ToCenter() {
  const scheme = play.scheme1;
  if (!scheme.ready || !scheme.stations.length) return false;
  const centerIndex = scheme.stations.findIndex((station) => (
    Number(station.row) === CURRENT_CLUTCH_ROW
      && Number(station.col) === CURRENT_CLUTCH_COL
  ));
  if (centerIndex < 0) return false;
  scheme.targetIndex = centerIndex;
  scheme.selectorS = scheme.stationS[centerIndex];
  scheme.phase = SCHEME1_PHASE.INDEX;
  scheme.phaseTime = 0;
  scheme.powerTurns = 0;
  scheme.outputTurns.fill(0);
  scheme.cycleSign = 1;
  scheme.cycleStartPowerTurns = 0;
  scheme.cycleStartOutputTurns = 0;
  scheme.cycleProgressTurns = 0;
  play.motorTurns = 0;
  if (scheme.selectorPart) {
    poseSelectorPart(scheme.selectorPart, scheme.selectorS - scheme.selectorPart.s);
  }
  return true;
}

function setScheme1Phase(phase) {
  const scheme = play.scheme1;
  if (phase === SCHEME1_PHASE.ENGAGE) {
    // Capture the datum only after the selector has arrived.  OPEN and CLOSE
    // will return to this exact value, so the next INDEX phase never inherits
    // a half-open drawer angle from the preceding station.
    scheme.cycleSign = play.dir || scheme.cycleSign || 1;
    scheme.cycleStartPowerTurns = scheme.powerTurns;
    scheme.cycleStartOutputTurns = scheme.outputTurns[scheme.targetIndex] || 0;
    scheme.cycleProgressTurns = 0;
  }
  scheme.phase = phase;
  scheme.phaseTime = 0;
  const stationLabel = scheme1StationLabel(scheme.targetIndex);
  const labels = {
    [SCHEME1_PHASE.INDEX]: `选择指移动 · 目标 ${stationLabel}`,
    [SCHEME1_PHASE.ENGAGE]: `停稳磁力接合 · ${stationLabel}`,
    [SCHEME1_PHASE.OPEN]: `抽屉打开中 · ${stationLabel}`,
    [SCHEME1_PHASE.CLOSE]: `抽屉关闭中 · ${stationLabel}`,
    [SCHEME1_PHASE.RELEASE]: `磁力接口释放 · ${stationLabel}`,
  };
  scheme1Status(labels[phase] || "方案1");
}

function chainPitchMm() {
  if (!play.path?.count) return Number(play.motion?.p) || 0;
  // The path is built from the authored/rounded pin positions.  Use that
  // actual per-pin arc length for both selector travel and motor turns so the
  // final frame of a station arrival cannot leave the chain one frame behind.
  return play.path.length / play.path.count;
}

function chainLinearSpeedMmPerHz() {
  return (play.motion?.driveTeeth || 12) * chainPitchMm();
}

function scheme1TransportSpeed() {
  // Selector motion and the visible snake motor now share one derived speed;
  // the old independently-authored selectorSpeed value could introduce a
  // small phase error after each station stop.
  return chainLinearSpeedMmPerHz() * play.motorHz;
}

function tickScheme1(dt) {
  const scheme = play.scheme1;
  if (!scheme.ready || !play.path || !scheme.stationS.length) return 0;
  let transportDistance = 0;

  if (play.playing) {
    scheme.phaseTime += dt;
    if (scheme.phase === SCHEME1_PHASE.INDEX) {
      // The snake selector is the only moving system in INDEX.  Keep the
      // drawer power datum frozen until the selected slot is fully stopped.
      const targetS = scheme.stationS[scheme.targetIndex];
      const remaining = pathDistance(scheme.selectorS, targetS, play.dir);
      const travel = Math.min(
        remaining,
        scheme1TransportSpeed() * dt,
      );
      if (remaining < 0.001 || travel >= remaining - 0.001) {
        transportDistance = remaining;
        scheme.selectorS = targetS;
        setScheme1Phase(SCHEME1_PHASE.ENGAGE);
      } else {
        transportDistance = travel;
        scheme.selectorS = wrapPathS(scheme.selectorS + play.dir * travel);
      }
    } else if (scheme.phase === SCHEME1_PHASE.ENGAGE
      && scheme.phaseTime >= SCHEME1_ENGAGE_SECONDS) {
      // The selector remains stopped during the complete clutch stroke.
      setScheme1Phase(SCHEME1_PHASE.OPEN);
    } else if (scheme.phase === SCHEME1_PHASE.OPEN) {
      // OPEN and CLOSE are one closed cycle.  Use a bounded progress datum so
      // a high preview speed cannot overshoot and slowly desynchronise the
      // rear gear, the 2GT belt, and the front rack pinion.
      scheme.cycleProgressTurns = Math.min(
        SCHEME1_DRAWER_TRAVEL_TURNS,
        scheme.cycleProgressTurns + play.motorHz * dt,
      );
      scheme.powerTurns = scheme.cycleStartPowerTurns
        + scheme.cycleSign * scheme.cycleProgressTurns;
      scheme.outputTurns[scheme.targetIndex] = scheme.cycleStartOutputTurns
        + scheme.cycleSign * scheme.cycleProgressTurns;
      if (scheme.cycleProgressTurns >= SCHEME1_DRAWER_TRAVEL_TURNS - 1e-6) {
        setScheme1Phase(SCHEME1_PHASE.CLOSE);
      }
    } else if (scheme.phase === SCHEME1_PHASE.CLOSE) {
      scheme.cycleProgressTurns = Math.max(
        0,
        scheme.cycleProgressTurns - play.motorHz * dt,
      );
      scheme.powerTurns = scheme.cycleStartPowerTurns
        + scheme.cycleSign * scheme.cycleProgressTurns;
      scheme.outputTurns[scheme.targetIndex] = scheme.cycleStartOutputTurns
        + scheme.cycleSign * scheme.cycleProgressTurns;
      if (scheme.cycleProgressTurns <= 1e-6) {
        // Snap the return datum once, rather than accumulating floating-point
        // error across 25 stations and repeated direction changes.
        scheme.cycleProgressTurns = 0;
        scheme.powerTurns = scheme.cycleStartPowerTurns;
        scheme.outputTurns[scheme.targetIndex] = scheme.cycleStartOutputTurns;
        setScheme1Phase(SCHEME1_PHASE.RELEASE);
      }
    } else if (scheme.phase === SCHEME1_PHASE.RELEASE
      && scheme.phaseTime >= SCHEME1_RELEASE_SECONDS) {
      const count = scheme.stations.length;
      scheme.targetIndex = (scheme.targetIndex + (play.dir > 0 ? 1 : -1) + count) % count;
      setScheme1Phase(SCHEME1_PHASE.INDEX);
    }
  }

  if (scheme.selectorPart) {
    poseSelectorPart(scheme.selectorPart, scheme.selectorS - scheme.selectorPart.s);
  }
  const powerAngle = -2 * Math.PI * scheme.powerTurns;
  for (const wheel of scheme.powerWheels) {
    wheel.group.rotation.y = wheel.restY - wheel.sign * powerAngle;
  }
  const active = scheme.phase === SCHEME1_PHASE.ENGAGE
    || scheme.phase === SCHEME1_PHASE.OPEN
    || scheme.phase === SCHEME1_PHASE.CLOSE;
  for (const wheel of scheme.outputWheels) {
    const turns = scheme.outputTurns[wheel.stationIndex] || 0;
    wheel.group.rotation.y = wheel.restY - wheel.sign * 2 * Math.PI * turns;
  }
  for (const clutch of scheme.clutches) {
    const isTarget = clutch.stationIndex === scheme.targetIndex;
    const engagement = active && isTarget
      ? scheme.phase === SCHEME1_PHASE.ENGAGE
        ? Math.min(1, scheme.phaseTime / 0.28)
        : 1
      : scheme.phase === SCHEME1_PHASE.RELEASE && isTarget
        ? Math.max(0, 1 - scheme.phaseTime / 0.24)
        : 0;
    clutch.group.position.y = clutch.baseY + (clutch.engagedY - clutch.openY) * engagement;
    const turns = clutch.side === "input"
      ? scheme.powerTurns
      : (scheme.outputTurns[clutch.stationIndex] || 0);
    clutch.group.rotation.y = clutch.restY - 2 * Math.PI * turns;
  }
  return transportDistance;
}

function smoothStep(value) {
  const t = Math.min(1, Math.max(0, value));
  return t * t * (3 - 2 * t);
}

function setCenterDemoPhase(phase) {
  const demo = play.centerDemo;
  if (demo.phase === phase) return;
  demo.phase = phase;
  updateCenterDemoStatus();
}

function tickCenterClutchDemo(dt) {
  const demo = play.centerDemo;
  if (!demo.active) return;
  demo.elapsed += Math.max(0, dt);
  const approachEnd = CENTER_DEMO_APPROACH_SECONDS;
  const engageEnd = approachEnd + CENTER_DEMO_ENGAGE_SECONDS;
  const holdEnd = engageEnd + CENTER_DEMO_HOLD_SECONDS;
  const releaseEnd = holdEnd + CENTER_DEMO_RELEASE_SECONDS;
  if (demo.elapsed < approachEnd) {
    setCenterDemoPhase("approach");
    demo.engagement = 0;
    updateCenterDemoStatus();
    return;
  }
  if (demo.elapsed < engageEnd) {
    setCenterDemoPhase("engage");
    demo.engagement = smoothStep(
      (demo.elapsed - approachEnd) / CENTER_DEMO_ENGAGE_SECONDS,
    );
    updateCenterDemoStatus();
    return;
  }
  if (demo.elapsed < holdEnd) {
    setCenterDemoPhase("hold");
    demo.engagement = 1;
    updateCenterDemoStatus();
    return;
  }
  if (demo.elapsed < releaseEnd) {
    setCenterDemoPhase("release");
    demo.engagement = 1 - smoothStep(
      (demo.elapsed - holdEnd) / CENTER_DEMO_RELEASE_SECONDS,
    );
    updateCenterDemoStatus();
    return;
  }
  demo.active = false;
  demo.engagement = 0;
  demo.elapsed = 0;
  demo.phase = "idle";
  scheme1Status(`中心离合演示完成 · 已回到开位 · 公轮轴 +Y ${centerDemoTravelText()}`);
}

function currentClutchEngagement() {
  if (play.centerDemo.active) return play.centerDemo.engagement;
  if (!currentClutchDrivesDrawer()) return 0;
  const phase = play.scheme1.phase;
  if (phase === SCHEME1_PHASE.ENGAGE) {
    return Math.min(1, play.scheme1.phaseTime / SCHEME1_ENGAGE_SECONDS);
  }
  if (phase === SCHEME1_PHASE.OPEN || phase === SCHEME1_PHASE.CLOSE) return 1;
  if (phase === SCHEME1_PHASE.RELEASE) {
    return Math.max(0, 1 - play.scheme1.phaseTime / SCHEME1_RELEASE_SECONDS);
  }
  return 0;
}

function tickCurrentClutch() {
  const contract = play.currentClutch.contract;
  if (!contract) return;
  const engagement = currentClutchEngagement();
  const turns = drawerDriveTurns();
  const angle = -2 * Math.PI * turns;
  const stroke = Number(contract.strokeMm);
  for (const part of play.currentClutch.parts) {
    // The input rotor, stepped shaft, sleeve and sleeve magnet are one moving
  // +Y assembly. The fixed LM3UU block, output rotor, and integral bearing bar stay in Y.
    part.group.position.y = part.baseY + (part.moves ? stroke * engagement : 0);
    if (part.rotates) {
      // Once engaged, input and output share the coaxial clutch rotation. The
      // output does not rotate during INDEX/RELEASE because drawerDriveTurns
      // is zero outside OPEN/CLOSE.
      part.group.rotation.y = part.restY + part.sign * angle;
    }
  }
}

function tickDrawerDrive() {
  const turns = drawerDriveTurns();
  const angle = -2 * Math.PI * turns;
  // The rear female pulley is downstream of the parallel spur mesh, so its
  // rotation is opposite to the vertical spline shaft.  The drawer belt path
  // is oriented rear-to-front on its right run; a positive pulley rotation
  // therefore advances the belt in the negative path direction.
  const phaseMm = turns * DRAWER_PULLEY_TEETH * DRAWER_BELT_PITCH_MM;
  for (const belt of play.drawerBelts) {
    poseBeltTeeth(belt, phaseMm * belt.phaseSign);
  }
  for (const rotary of play.drawerRotaries) {
    rotary.group.rotation.y = rotary.restY + rotary.sign * angle;
  }
  tickCurrentClutch();
}

function tickColumnSyncDrive() {
  const turns = drawerDriveTurns();
  const angle = -2 * Math.PI * turns;
  const phaseMm = turns * POWER_COLUMN_PULLEY_TEETH * POWER_COLUMN_BELT_PITCH_MM;
  for (const rotary of play.powerRotaries) {
    rotary.group.rotation.y = rotary.restY + rotary.sign * angle;
  }
  for (const belt of play.columnSyncBelts) {
    poseBeltTeeth(belt, phaseMm * belt.phaseSign);
  }
}

async function bindChainMesh(item) {
  if (!play.path || !item.mesh?.isMesh || !playScene()) return;
  const isPlateMesh = item.part.id.endsWith("cabinet_chain_plates");
  const isRigidChainMesh = RIGID_CHAIN_IDS.has(item.part.id);
  // 普通链板从直线段模板实例化，避免把拐角三角形切到相邻链节；接头/轴承
  // 是装配替换件，必须整体作为一个刚体移动，不能按拓扑岛分别绕拐角转动。
  const plateTemplates = isPlateMesh ? await extractPlateTemplates(item.mesh.geometry) : null;
  const islands = isPlateMesh
    ? Array.from({ length: play.path.count }, (_, i) => i)
    : (isRigidChainMesh ? [item.mesh.geometry] : await splitIslands(item.mesh.geometry));
  const group = new THREE.Group();
  const mat = item.mesh.material;
  const added = [];
  for (let i = 0; i < islands.length; i += 1) {
    const isPlate = isPlateMesh;
    const plateKind = i === PLATE_TEMPLATE_SEGMENTS.connector
      ? "connector"
      : i % 2 === 0 ? "outer" : "inner";
    const template = isPlate ? plateTemplates[plateKind] : null;
    const geo = isPlate ? template.geometry : islands[i];
    const pivot = new THREE.Group();
    pivot.add(new THREE.Mesh(geo, mat));
    group.add(pivot);
    let part;
    if (isPlate) {
      // Every instance uses the exact authored p[i] -> p[i+1] chord as its
      // logical anchor.  The template itself is already centered at its
      // straight-run chord midpoint, so no corner bbox can affect the pivot.
      const seg = play.path.segs[i];
      part = {
        group: pivot,
        s: seg.s0 + seg.len / 2,
        along: 0,
        side: 0,
        lift: 0,
        restYaw: template.restYaw,
        halfSpan: (play.motion?.p || 0) / 2,
        pinIndex: i,
        scaleAlong: true,
      };
    } else {
      const center = geo.boundingBox.getCenter(new THREE.Vector3());
      const segmentIndex = RIGID_CHAIN_SEGMENTS.get(item.part.id);
      if (Number.isInteger(segmentIndex)) {
        const seg = play.path.segs[segmentIndex];
        const anchor = [
          (seg.a[0] + seg.b[0]) / 2,
          (seg.a[1] + seg.b[1]) / 2,
          (seg.a[2] + seg.b[2]) / 2,
        ];
        geo.translate(-anchor[0], -anchor[1], -anchor[2]);
        part = {
          group: pivot,
          s: seg.s0 + seg.len / 2,
          along: 0,
          side: 0,
          lift: 0,
          restYaw: Math.atan2(seg.b[2] - seg.a[2], seg.b[0] - seg.a[0]),
          halfSpan: (play.motion?.p || 0) / 2,
          pinIndex: segmentIndex,
          scaleAlong: true,
        };
      } else {
        const proj = projectPoint(play.path, center.x, center.y, center.z);
        geo.translate(-center.x, -center.y, -center.z);
        part = {
          group: pivot,
          s: proj.s,
          along: proj.along,
          side: proj.side,
          lift: proj.lift,
          restYaw: Math.atan2(proj.tangent[2], proj.tangent[0]),
          halfSpan: isRigidChainMesh ? (play.motion?.p || 0) / 2 : 0,
          pinIndex: Math.round(proj.s / (Number(play.motion?.p) || 1))
            % play.path.count,
          scaleAlong: false,
        };
      }
    }
    added.push(part);
    play.chain.push(part);
    if (i % 80 === 0) await yieldFrame();
  }
  const offsetMm = chainOffsetMm();
  for (const part of added) poseChainPart(part, offsetMm);
  replaceMesh(item, group);
}

async function bindChainTriggerMagnetMesh(item) {
  if (!play.path || !item.mesh?.isMesh || !playScene()) return;
  const motion = play.motion;
  const trigger = motion?.chainTriggerMagnet;
  const segmentIndex = Number(trigger?.segmentIndex ?? 182);
  const seg = play.path.segs[segmentIndex];
  if (!seg) throw new Error(`触发磁铁路径节不存在: ${segmentIndex}`);

  const geometry = item.mesh.geometry;
  geometry.computeBoundingBox();
  const center = geometry.boundingBox.getCenter(new THREE.Vector3());
  const anchor = [
    (seg.a[0] + seg.b[0]) / 2,
    (seg.a[1] + seg.b[1]) / 2,
    (seg.a[2] + seg.b[2]) / 2,
  ];
  const tangent = normalize(sub(seg.b, seg.a));
  const normal = [-tangent[2], 0, tangent[0]];
  const delta = [center.x - anchor[0], center.y - anchor[1], center.z - anchor[2]];
  const side = delta[0] * normal[0] + delta[2] * normal[2];
  const geometryMaterial = item.mesh.material;
  geometry.translate(-center.x, -center.y, -center.z);

  const pivot = new THREE.Group();
  pivot.add(new THREE.Mesh(geometry, geometryMaterial));
  const group = new THREE.Group();
  group.name = "chain-clutch-trigger-magnet-animated";
  group.add(pivot);
  const part = {
    group: pivot,
    s: seg.s0 + seg.len / 2,
    along: 0,
    side,
    // The authored chain axial offset is source Y. It is intentionally kept
    // as lift here: legacyRoot maps source +Y to browser/world Z-.
    lift: delta[1],
    restYaw: Math.atan2(seg.b[2] - seg.a[2], seg.b[0] - seg.a[0]),
    halfSpan: 0,
    pinIndex: segmentIndex,
    scaleAlong: false,
  };
  group.visible = item.mesh.visible;
  play.chain.push(part);
  replaceMesh(item, group);
  poseChainPart(part, chainOffsetMm());
}

function updateHzLabel() {
  const els = play.host?.els;
  if (!els?.hzOut) return;
  const dir = play.dir > 0 ? "顺时针" : play.dir < 0 ? "逆时针" : "停止";
  const run = play.playing ? dir : "停止";
  els.hzOut.textContent = `${formatHz(play.motorHz)} Hz · ${run}`;
  els.fwd?.classList.toggle("on", play.playing && play.dir > 0);
  els.stop?.classList.toggle("on", !play.playing);
  els.rev?.classList.toggle("on", play.playing && play.dir < 0);
}

function setDir(dir) {
  play.centerDemo.active = false;
  play.centerDemo.elapsed = 0;
  play.centerDemo.engagement = 0;
  play.centerDemo.phase = "idle";
  if (dir === 0) {
    play.playing = false;
  } else {
    play.dir = dir;
    play.playing = true;
  }
  updateHzLabel();
}

function enqueueBind(task, front) {
  if (front) play.bindQueue.unshift(task);
  else play.bindQueue.push(task);
  void drainBinds();
}

async function drainBinds() {
  if (play.bindBusy) return;
  play.bindBusy = true;
  while (play.bindQueue.length) {
    const task = play.bindQueue.shift();
    await task();
  }
  play.bindBusy = false;
}
//#endregion

//#region 公开 API
export function attachCabinetChainPlay(host) {
  play.host = host;
  host.els.hzRange?.addEventListener("input", () => {
    play.motorHz = hzFromSlider(host.els.hzRange);
    updateHzLabel();
  });
  host.els.fwd?.addEventListener("click", () => setDir(1));
  host.els.stop?.addEventListener("click", () => setDir(0));
  host.els.rev?.addEventListener("click", () => setDir(-1));
  play.motorHz = hzFromSlider(host.els.hzRange);
  updateHzLabel();
  fetch(MOTION_URL, { cache: "no-cache" })
    .then((res) => {
      if (!res.ok) throw new Error(String(res.status));
      return res.json();
    })
    .then((motion) => {
      const centerClutch = validateCenterClutchContract(motion.centerClutch);
      const datum = motion.chainTopDatum;
      const trigger = motion.chainTriggerMagnet;
      if (!datum || datum.mode !== "input-sleeve-magnet-bottom"
          || !trigger
          || Number(trigger.segmentIndex) !== Number(centerClutch.snakeChainTriggerMagnetSegmentIndex)
          || Math.abs(Number(motion.chainVerticalShiftMm)
            - Number(centerClutch.snakeChainVerticalShiftMm)) > 0.001
          || Math.abs(
            Number(datum.referencePathShiftedCenterYMm)
              + Number(datum.linkTopOffsetMm)
              - Number(datum.inputSleeveMagnetOpenBottomYMm),
          ) > 0.001) {
        throw new Error("蛇链服务层高度与中心离合底部磁铁契约不一致");
      }
      play.motion = motion;
      play.currentClutch.contract = centerClutch;
      play.path = buildPath(motion);
      initScheme1Motion();
      play.ready = true;
      for (const item of host.state.items.values()) {
        if (item.mesh) void onPartLoaded(item);
      }
    })
    .catch((error) => {
      if (host.els.hzOut) host.els.hzOut.textContent = "未加载运动路径";
      if (host.els.scheme1Out) {
        host.els.scheme1Out.textContent = `运动契约错误：${error.message || error}`;
      }
    });
}

export function focusCenterClutch() {
  play.centerViewRequested = true;
  play.centerDemo.active = false;
  play.centerDemo.elapsed = 0;
  play.centerDemo.engagement = 0;
  play.centerDemo.phase = "idle";
  play.playing = false;
  const snapped = snapScheme1ToCenter();
  if (snapped) {
    scheme1Status(`首件视角 · 三层柜体中心格已对准 · 开位`);
  }
  updateHzLabel();
  return snapped;
}

export function playCenterClutchDemo() {
  play.centerViewRequested = true;
  if (!play.ready || !play.scheme1.ready || !play.currentClutch.contract) {
    scheme1Status("中心离合演示等待运动契约加载…");
    return false;
  }
  if (!snapScheme1ToCenter()) {
    scheme1Status("中心离合演示不可用：缺少三层柜体中心格站点");
    return false;
  }
  play.playing = false;
  play.centerDemo.active = true;
  play.centerDemo.elapsed = 0;
  play.centerDemo.engagement = 0;
  play.centerDemo.phase = "idle";
  setCenterDemoPhase("approach");
  updateHzLabel();
  return true;
}

export async function onPartLoaded(item) {
  const id = item.part?.id;
  if (!id || !play.path || item.playBound) return;
  if (id === SCHEME1_POWER_ID) {
    item.playBound = true;
    enqueueBind(() => bindScheme1WheelMesh(item, "power").catch((error) => {
      console.error("scheme1 power wheel bind failed", id, error);
      item.playBound = false;
    }), true);
    return;
  }
  if (id === SCHEME1_OUTPUT_ID) {
    item.playBound = true;
    enqueueBind(() => bindScheme1WheelMesh(item, "output").catch((error) => {
      console.error("scheme1 output wheel bind failed", id, error);
      item.playBound = false;
    }), true);
    return;
  }
  if (id === SCHEME1_CLUTCH_ID) {
    item.playBound = true;
    enqueueBind(() => bindScheme1ClutchMesh(item).catch((error) => {
      console.error("scheme1 clutch bind failed", id, error);
      item.playBound = false;
    }), true);
    return;
  }
  if (id === SCHEME1_SELECTOR_ID) {
    item.playBound = true;
    enqueueBind(() => bindScheme1SelectorMesh(item).catch((error) => {
      console.error("scheme1 selector bind failed", id, error);
      item.playBound = false;
    }), true);
    return;
  }
  if (id === SCHEME1_BEARING_ID) {
    // 轴承是银色的静态装配参考件；它不参与旋转驱动，避免把采购件误当
    // 成齿轮主体或在网页中拆成可形变的链节。
    item.playBound = true;
    return;
  }
  if (id === POWER_MOTOR_SHAFT_ID) {
    item.playBound = true;
    enqueueBind(() => Promise.resolve(bindWorldYAxisRotaryMesh(
      item,
      play.powerRotaries,
      "drawer-power-motor-shaft",
      1,
    )).catch((error) => {
      console.error("drawer power motor shaft bind failed", id, error);
      item.playBound = false;
    }), true);
    return;
  }
  if (id.startsWith(POWER_COLUMN_ID_PREFIX)) {
    item.playBound = true;
    enqueueBind(() => Promise.resolve(bindWorldYAxisRotaryMesh(
      item,
      play.powerRotaries,
      "drawer-power-column",
      1,
    )).catch((error) => {
      console.error("drawer power column bind failed", id, error);
      item.playBound = false;
    }), true);
    return;
  }
  if (POWER_COLUMN_SYNC_BELT_IDS.has(id)) {
    item.playBound = true;
    enqueueBind(() => Promise.resolve(bindColumnSyncBeltMesh(item)).catch((error) => {
      console.error("column sync timing belt bind failed", id, error);
      item.playBound = false;
    }), true);
    return;
  }
  if (id === POWER_COLUMN_SYNC_TENSIONER_ID) {
    item.playBound = true;
    enqueueBind(() => Promise.resolve(bindWorldYAxisRotaryMesh(
      item,
      play.powerRotaries,
      "column-sync-tensioner",
      1,
    )).catch((error) => {
      console.error("column sync tensioner bind failed", id, error);
      item.playBound = false;
    }), true);
    return;
  }
  if (id === DRAWER_BELT_ID) {
    item.playBound = true;
    enqueueBind(() => Promise.resolve(bindDrawerBeltMesh(item)).catch((error) => {
      console.error("drawer timing belt bind failed", id, error);
      item.playBound = false;
    }), true);
    return;
  }
  if (id === CHAIN_TRIGGER_MAGNET_ID) {
    item.playBound = true;
    enqueueBind(() => bindChainTriggerMagnetMesh(item).catch((error) => {
      console.error("chain trigger magnet bind failed", id, error);
      item.playBound = false;
    }));
    return;
  }
  if (id === CHAIN_BEARING_ID) {
    item.playBound = true;
    enqueueBind(() => bindChainBearingMesh(item).catch((error) => {
      console.error("chain bearing bind failed", id, error);
      item.playBound = false;
    }), true);
    return;
  }
  if (CURRENT_CLUTCH_STATIC_IDS.has(id)) {
    // Cage, fixed bearing block and the removable plate are fixed world-frame
    // hardware. They must not enter the legacy chain adapter or a rotary
    // pivot; their coordinates come directly from the native STL.
    item.playBound = true;
    return;
  }
  if (CURRENT_CLUTCH_IDS.has(id)) {
    const config = CURRENT_CLUTCH_IDS.get(id);
    item.playBound = true;
    enqueueBind(() => Promise.resolve(bindCurrentClutchMesh(item, config)).catch((error) => {
      console.error("current clutch bind failed", id, error);
      item.playBound = false;
    }), true);
    return;
  }
  if (DRAWER_ROTARY_IDS.has(id)) {
    item.playBound = true;
    enqueueBind(() => Promise.resolve(bindDrawerRotaryMesh(item, DRAWER_ROTARY_IDS.get(id))).catch((error) => {
      console.error("drawer drive rotary bind failed", id, error);
      item.playBound = false;
    }), true);
    return;
  }
  if (CHAIN_IDS.has(id)) {
    item.playBound = true;
    enqueueBind(() => bindChainMesh(item).catch((error) => {
      console.error("chain play bind failed", id, error);
      item.playBound = false;
    }));
    return;
  }
  if (WHEEL_IDS[id]) {
    item.playBound = true;
    enqueueBind(() => bindWheelMesh(item, WHEEL_IDS[id]).catch((error) => {
      console.error("chain play bind failed", id, error);
      item.playBound = false;
    }), true);
    return;
  }
  if (MOTOR_SHAFT_IDS.has(id)) {
    item.playBound = true;
    enqueueBind(() => bindMotorShaftMesh(item).catch((error) => {
      console.error("motor shaft bind failed", id, error);
      item.playBound = false;
    }), true);
  }
}

export function holdScheme1Engaged() {
  const scheme = play.scheme1;
  if (!scheme.ready || !scheme.stations.length) return;
  scheme.selectorS = scheme.stationS[scheme.targetIndex];
  scheme.cycleSign = play.dir || 1;
  scheme.cycleStartPowerTurns = scheme.powerTurns;
  scheme.cycleStartOutputTurns = scheme.outputTurns[scheme.targetIndex] || 0;
  scheme.cycleProgressTurns = 0;
  scheme.phase = SCHEME1_PHASE.ENGAGE;
  scheme.phaseTime = SCHEME1_ENGAGE_SECONDS;
  play.playing = false;
  updateHzLabel();
  scheme1Status(`磁力离合检查状态 · 已接合 ${scheme1StationLabel(scheme.targetIndex)}`);
}

export function tickPlay(dt) {
  if (!play.ready || !play.path) return;
  tickCenterClutchDemo(dt);
  // Resolve the scheme first.  If INDEX reaches its station in this frame,
  // tickScheme1 changes the phase to ENGAGE before the transport datum is
  // advanced, so the selector and the snake belt stop on the same frame with
  // no one-frame overshoot.
  const transportDistance = play.centerDemo.active ? 0 : tickScheme1(dt);
  // 方案1中，拨叉沿蛇形选择带到达目标后，选择带必须停稳；只有在
  // OPEN/CLOSE 完成并回到关闭基准、离合释放后，选择带才允许继续走位。
  // 这里用 tickScheme1 返回的“本帧实际弧长”更新电机转数，而不是再次按
  // 速度计时，确保拨叉、链节和主动轮在到站的最后一帧仍然完全重合。
  if (play.playing && transportDistance > 0) {
    play.motorTurns += play.dir * transportDistance / chainLinearSpeedMmPerHz();
  }
  const offsetMm = chainOffsetMm();
  for (const part of play.chain) poseChainPart(part, offsetMm);
  const pitches = play.motorTurns * (play.motion?.driveTeeth || 12);
  for (const wheel of play.wheels) {
    wheel.group.rotation.y = wheel.restY - wheel.sign * 2 * Math.PI * pitches / wheel.teeth;
  }
  for (const bearing of play.bearingRotaries) {
    bearing.group.rotation.y = bearing.restY
      - bearing.sign * 2 * Math.PI * pitches / bearing.teeth;
  }
  for (const shaft of play.motorShafts) {
    // This is the legacy snake-selector motor shaft.  It follows the snake
    // belt datum, not the separate drawer-power datum; therefore it stops
    // while OPEN/CLOSE runs and spins again only after RELEASE completes.
    shaft.group.rotation.y = shaft.restY + 2 * Math.PI * play.motorTurns;
  }
  // The column bus follows the same motor/power-turn datum as the drawer
  // take-off.  It is evaluated after scheme1 so a selected powered station
  // cannot leave the visible motor shaft and five columns one frame behind.
  tickColumnSyncDrive();
  tickDrawerDrive();
}
//#endregion

//#region 业务逻辑
// 正转 = 后视顺时针 = 沿销轴路径前进。1 Hz 是橙色 12T 驱动轮每秒一转。
//#endregion

//#region 方法/工具
export { HZ_STEPS, DEFAULT_HZ_INDEX };
//#endregion
