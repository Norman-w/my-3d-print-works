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
  // These are straight, ordinary links in the canonical 5x5 path.  Taking
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
const MOTOR_SHAFT_IDS = new Set([
  "cabinet-chain/cabinet_chain_motor_shaft",
]);
const SCHEME1_POWER_ID = "cabinet-chain/cabinet_chain_scheme1_power_wheels";
const SCHEME1_OUTPUT_ID = "cabinet-chain/cabinet_chain_scheme1_output_wheels";
const SCHEME1_CLUTCH_ID = "cabinet-chain/cabinet_chain_scheme1_clutch_faces";
const SCHEME1_BEARING_ID = "cabinet-chain/cabinet_chain_scheme1_bearings";
const SCHEME1_SELECTOR_ID = "cabinet-chain/cabinet_chain_scheme1_selector";
const DRAWER_BELT_ID = "cabinet-clutch/13_drawer_timing_belt_reference";
const DRAWER_ROTARY_IDS = new Map([
  ["cabinet-clutch/09_rear_takeoff_timing_pulley_candidate", 1],
  ["cabinet-clutch/14_front_timing_pulley_candidate", 1],
  ["cabinet-clutch/15_front_pinion_candidate", 1],
]);
// This is the default center station's mating pulley tooth count, not the
// total teeth in the closed belt. One pulley revolution advances the 2GT belt
// by 12 * 2 mm; using the belt's total 80 teeth would move it by one whole
// loop and make it appear stationary in the preview.
const DRAWER_PULLEY_TEETH = 12;
const DRAWER_BELT_PITCH_MM = 2;
const SCHEME1_PHASE = {
  INDEX: "INDEX",
  ENGAGE: "ENGAGE",
  DRIVE: "DRIVE",
  RELEASE: "RELEASE",
};
const MOTION_URL = "./models/cabinet-chain/cabinet_chain_motion.json";
//#endregion

//#region 模型/类型
/** @typedef {{a:number[], b:number[], s0:number, len:number}} PathSeg */
/** @typedef {{group:THREE.Group, s:number, along:number, side:number, lift:number, restYaw:number, halfSpan:number}} ChainPart */
/** @typedef {{group:THREE.Group, teeth:number, sign:number, restY:number}} WheelPivot */
/** @typedef {{group:THREE.Group, restY:number}} MotorShaftPivot */
/** @typedef {{group:THREE.Group, stationIndex:number, side:string, baseY:number, openY:number, engagedY:number, restY:number}} ClutchPivot */
//#endregion

//#region 私有成员
const play = {
  ready: false,
  motion: null,
  path: null,
  chain: /** @type {ChainPart[]} */ ([]),
  wheels: /** @type {WheelPivot[]} */ ([]),
  motorShafts: /** @type {MotorShaftPivot[]} */ ([]),
  drawerBelts: /** @type {Array<{mesh:THREE.Mesh,path:any,s:number[],radial:number[],yOffset:number[],lastPhase:number}>} */ ([]),
  drawerRotaries: /** @type {Array<{group:THREE.Group, sign:number, restY:number}>} */ ([]),
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
  },
  playing: true,
  dir: 1,
  motorHz: HZ_STEPS[DEFAULT_HZ_INDEX],
  motorTurns: 0,
  host: null,
  bindQueue: /** @type {Array<() => Promise<void>>} */ ([]),
  bindBusy: false,
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

function playScene() {
  return play.host?.state?.legacyRoot ?? play.host?.state?.scene ?? null;
}

function replaceMesh(item, group, parent = playScene()) {
  if (!parent || !item.mesh) return;
  group.visible = item.mesh.visible;
  item.mesh.parent?.remove(item.mesh);
  parent.add(group);
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
  const pitchRadius = Math.max(1, outerRadius - DRAWER_BELT_PITCH_MM * 0.6);
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

function drawerDriveTurns() {
  if (play.scheme1.ready) return play.scheme1.powerTurns;
  return play.motorTurns;
}

function drawerPathNormal(sample) {
  // Path coordinates are X/Z while the belt's axial width is Y.  This is the
  // in-plane normal used to preserve the original belt cross-section as the
  // whole connected STL is advected around the two pulley wraps.
  return [-sample.tangent[2], sample.tangent[0]];
}

function buildDrawerBeltVertexMap(geometry, path) {
  const position = geometry.getAttribute("position");
  const s = new Float32Array(position.count);
  const radial = new Float32Array(position.count);
  const yOffset = new Float32Array(position.count);
  for (let i = 0; i < position.count; i += 1) {
    const x = position.getX(i);
    const y = position.getY(i);
    const z = position.getZ(i);
    const projected = projectDrawerBeltPoint(path, x, z);
    const sample = sampleDrawerBeltPath(path, projected);
    const normal = drawerPathNormal(sample);
    s[i] = projected;
    radial[i] = (x - sample.point[0]) * normal[0] + (z - sample.point[2]) * normal[1];
    yOffset[i] = y - path.y;
  }
  return { s, radial, yOffset };
}

function poseDrawerBelt(belt, phaseMm) {
  if (Number.isFinite(belt.lastPhase) && Math.abs(belt.lastPhase - phaseMm) < 1e-6) return;
  const position = belt.mesh.geometry.getAttribute("position");
  const { s, radial, yOffset } = belt;
  for (let i = 0; i < position.count; i += 1) {
    const sample = sampleDrawerBeltPath(belt.path, s[i] + phaseMm);
    const normal = drawerPathNormal(sample);
    position.setXYZ(
      i,
      sample.point[0] + normal[0] * radial[i],
      sample.point[1] + yOffset[i],
      sample.point[2] + normal[1] * radial[i],
    );
  }
  position.needsUpdate = true;
  belt.mesh.geometry.computeVertexNormals();
  belt.mesh.geometry.computeBoundingBox();
  belt.lastPhase = phaseMm;
}

function bindDrawerBeltMesh(item) {
  if (!item.mesh?.isMesh || !play.host?.state?.scene) return;
  const geometry = item.mesh.geometry;
  const path = buildDrawerBeltPath(geometry);
  const vertexMap = buildDrawerBeltVertexMap(geometry, path);
  play.drawerBelts.push({
    mesh: item.mesh,
    path,
    s: vertexMap.s,
    radial: vertexMap.radial,
    yOffset: vertexMap.yOffset,
    lastPhase: Number.NaN,
  });
  // Preserve the authored SCAD pose at phase zero, then move every belt
  // vertex—including the connected tooth geometry—along the same pitch path.
  poseDrawerBelt(play.drawerBelts[play.drawerBelts.length - 1], 0);
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
  return pitches * (play.path.length / play.path.count);
}

function poseChainPart(part, offsetMm) {
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
  poseChainPart(scheme.selectorPart, scheme.selectorS - scheme.selectorPart.s);
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
  play.scheme1.ready = true;
  scheme1Status(`拨叉待机 · R${stations[start].row + 1}C${stations[start].col + 1}`);
}

function setScheme1Phase(phase) {
  play.scheme1.phase = phase;
  play.scheme1.phaseTime = 0;
  const stationLabel = scheme1StationLabel(play.scheme1.targetIndex);
  const labels = {
    [SCHEME1_PHASE.INDEX]: `拨叉移动 · 目标 ${stationLabel}`,
    [SCHEME1_PHASE.ENGAGE]: `停稳合闸 · ${stationLabel}`,
    [SCHEME1_PHASE.DRIVE]: `方案1传动中 · ${stationLabel}`,
    [SCHEME1_PHASE.RELEASE]: `断开离合 · ${stationLabel}`,
  };
  scheme1Status(labels[phase] || "方案1");
}

function scheme1TransportSpeed() {
  const base = Number(play.motion?.scheme1?.selectorSpeed);
  const fallback = (play.motion?.driveTeeth || 12) * (play.motion?.p || 0);
  return (Number.isFinite(base) && base > 0 ? base : fallback) * play.motorHz;
}

function tickScheme1(dt) {
  const scheme = play.scheme1;
  if (!scheme.ready || !play.path || !scheme.stationS.length) return;

  // 输入侧永远由动力轮带动；输出侧只有 DRIVE 阶段的目标站转动。
  if (play.playing) {
    scheme.powerTurns += play.dir * play.motorHz * dt;
  }

  if (play.playing) {
    scheme.phaseTime += dt;
    if (scheme.phase === SCHEME1_PHASE.INDEX) {
      const targetS = scheme.stationS[scheme.targetIndex];
      const remaining = pathDistance(scheme.selectorS, targetS, play.dir);
      const travel = Math.min(
        remaining,
        scheme1TransportSpeed() * dt,
      );
      if (remaining < 0.001 || travel >= remaining - 0.001) {
        scheme.selectorS = targetS;
        setScheme1Phase(SCHEME1_PHASE.ENGAGE);
      } else {
        scheme.selectorS = wrapPathS(scheme.selectorS + play.dir * travel);
      }
    } else if (scheme.phase === SCHEME1_PHASE.ENGAGE && scheme.phaseTime >= 0.28) {
      setScheme1Phase(SCHEME1_PHASE.DRIVE);
    } else if (scheme.phase === SCHEME1_PHASE.DRIVE) {
      scheme.outputTurns[scheme.targetIndex] += play.dir * play.motorHz * dt;
      if (scheme.phaseTime >= 0.90) setScheme1Phase(SCHEME1_PHASE.RELEASE);
    } else if (scheme.phase === SCHEME1_PHASE.RELEASE && scheme.phaseTime >= 0.24) {
      const count = scheme.stations.length;
      scheme.targetIndex = (scheme.targetIndex + (play.dir > 0 ? 1 : -1) + count) % count;
      setScheme1Phase(SCHEME1_PHASE.INDEX);
    }
  }

  if (scheme.selectorPart) {
    poseChainPart(scheme.selectorPart, scheme.selectorS - scheme.selectorPart.s);
  }
  const powerAngle = -2 * Math.PI * scheme.powerTurns;
  for (const wheel of scheme.powerWheels) {
    wheel.group.rotation.y = wheel.restY - wheel.sign * powerAngle;
  }
  const active = scheme.phase === SCHEME1_PHASE.ENGAGE || scheme.phase === SCHEME1_PHASE.DRIVE;
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
}

function tickDrawerDrive() {
  const turns = drawerDriveTurns();
  const angle = -2 * Math.PI * turns;
  const phaseMm = turns * DRAWER_PULLEY_TEETH * DRAWER_BELT_PITCH_MM;
  for (const belt of play.drawerBelts) {
    poseDrawerBelt(belt, phaseMm);
  }
  for (const rotary of play.drawerRotaries) {
    rotary.group.rotation.y = rotary.restY + rotary.sign * angle;
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
      play.motion = motion;
      play.path = buildPath(motion);
      initScheme1Motion();
      play.ready = true;
      for (const item of host.state.items.values()) {
        if (item.mesh) void onPartLoaded(item);
      }
    })
    .catch(() => {
      if (host.els.hzOut) host.els.hzOut.textContent = "未加载运动路径";
    });
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
  if (id === DRAWER_BELT_ID) {
    item.playBound = true;
    enqueueBind(() => Promise.resolve(bindDrawerBeltMesh(item)).catch((error) => {
      console.error("drawer timing belt bind failed", id, error);
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
  scheme.phase = SCHEME1_PHASE.ENGAGE;
  scheme.phaseTime = 0.28;
  play.playing = false;
  updateHzLabel();
  scheme1Status(`方案1检查状态 · 已合闸 ${scheme1StationLabel(scheme.targetIndex)}`);
}

export function tickPlay(dt) {
  if (!play.ready || !play.path) return;
  // 方案1中，拨叉沿链条到达目标后，运输链停住，先完成合闸和动力传递；
  // 这样不会出现拨叉停在一个抽屉而链条继续把它拖走的假动作。
  const transportMoving = !play.scheme1.ready || play.scheme1.phase === SCHEME1_PHASE.INDEX;
  if (play.playing && transportMoving) play.motorTurns += play.dir * play.motorHz * dt;
  const offsetMm = chainOffsetMm();
  for (const part of play.chain) poseChainPart(part, offsetMm);
  const pitches = play.motorTurns * (play.motion?.driveTeeth || 12);
  for (const wheel of play.wheels) {
    wheel.group.rotation.y = wheel.restY - wheel.sign * 2 * Math.PI * pitches / wheel.teeth;
  }
  for (const shaft of play.motorShafts) {
    const motorTurns = play.scheme1.ready ? play.scheme1.powerTurns : play.motorTurns;
    shaft.group.rotation.y = shaft.restY + 2 * Math.PI * motorTurns;
  }
  tickScheme1(dt);
  tickDrawerDrive();
}
//#endregion

//#region 业务逻辑
// 正转 = 后视顺时针 = 沿销轴路径前进。1 Hz 是橙色 12T 驱动轮每秒一转。
//#endregion

//#region 方法/工具
export { HZ_STEPS, DEFAULT_HZ_INDEX };
//#endregion
