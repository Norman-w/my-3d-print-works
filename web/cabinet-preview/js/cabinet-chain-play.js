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
]);
const WHEEL_IDS = {
  "cabinet-chain/cabinet_chain_sprockets": "sprocket",
  "cabinet-chain/cabinet_chain_idlers": "idler",
};
const MOTION_URL = "./models/cabinet-chain/cabinet_chain_motion.json";
//#endregion

//#region 模型/类型
/** @typedef {{a:number[], b:number[], s0:number, len:number}} PathSeg */
/** @typedef {{group:THREE.Group, s:number, along:number, side:number, lift:number, restYaw:number}} ChainPart */
/** @typedef {{group:THREE.Group, teeth:number, sign:number, restY:number}} WheelPivot */
//#endregion

//#region 私有成员
const play = {
  ready: false,
  motion: null,
  path: null,
  chain: /** @type {ChainPart[]} */ ([]),
  wheels: /** @type {WheelPivot[]} */ ([]),
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
    if (s > seg.s0 + seg.len) lo = mid + 1;
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

function playScene() {
  return play.host?.state?.scene ?? null;
}

function replaceMesh(item, group) {
  const scene = playScene();
  if (!scene || !item.mesh) return;
  group.visible = item.mesh.visible;
  scene.remove(item.mesh);
  scene.add(group);
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

async function splitByPath(geometry, path) {
  const pos = geometry.getAttribute("position");
  const arr = pos.array;
  const nTri = Math.floor(pos.count / 3);
  const buckets = new Map();
  for (let t = 0; t < nTri; t += 1) {
    const i = t * 9;
    const cx = (arr[i] + arr[i + 3] + arr[i + 6]) / 3;
    const cy = (arr[i + 1] + arr[i + 4] + arr[i + 7]) / 3;
    const cz = (arr[i + 2] + arr[i + 5] + arr[i + 8]) / 3;
    const proj = projectPoint(path, cx, cy, cz);
    const key = proj.seg * 2 + (proj.side >= 0 ? 1 : 0);
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(t);
    if (t % 8000 === 0) await yieldFrame();
  }
  const geos = [];
  let built = 0;
  for (const tris of buckets.values()) {
    const out = new Float32Array(tris.length * 9);
    let w = 0;
    for (const t of tris) {
      for (let k = 0; k < 9; k += 1) out[w++] = arr[t * 9 + k];
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(out, 3));
    geo.computeVertexNormals();
    geo.computeBoundingBox();
    geos.push(geo);
    built += 1;
    if (built % 40 === 0) await yieldFrame();
  }
  return geos;
}

function chainOffsetMm() {
  if (!play.path) return 0;
  const pitches = play.motorTurns * (play.motion?.driveTeeth || 12);
  return pitches * (play.path.length / play.path.count);
}

function poseChainPart(part, offsetMm) {
  const sample = samplePath(play.path, part.s + offsetMm);
  part.group.position.set(
    sample.point[0] + sample.tangent[0] * part.along + sample.normal[0] * part.side,
    sample.point[1] + part.lift,
    sample.point[2] + sample.tangent[2] * part.along + sample.normal[2] * part.side,
  );
  const yaw = Math.atan2(sample.tangent[2], sample.tangent[0]);
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

async function bindChainMesh(item) {
  if (!play.path || !item.mesh?.isMesh || !playScene()) return;
  const islands = await splitByPath(item.mesh.geometry, play.path);
  const group = new THREE.Group();
  const mat = item.mesh.material;
  const added = [];
  for (let i = 0; i < islands.length; i += 1) {
    const geo = islands[i];
    const center = geo.boundingBox.getCenter(new THREE.Vector3());
    const proj = projectPoint(play.path, center.x, center.y, center.z);
    geo.translate(-center.x, -center.y, -center.z);
    const pivot = new THREE.Group();
    pivot.add(new THREE.Mesh(geo, mat));
    group.add(pivot);
    const part = {
      group: pivot,
      s: proj.s,
      along: proj.along,
      side: proj.side,
      lift: proj.lift,
      restYaw: Math.atan2(proj.tangent[2], proj.tangent[0]),
    };
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
  }
}

export function tickPlay(dt) {
  if (!play.ready || !play.path || !play.wheels.length) return;
  if (play.playing) play.motorTurns += play.dir * play.motorHz * dt;
  const offsetMm = chainOffsetMm();
  for (const part of play.chain) poseChainPart(part, offsetMm);
  const pitches = play.motorTurns * (play.motion?.driveTeeth || 12);
  for (const wheel of play.wheels) {
    wheel.group.rotation.y = wheel.restY - wheel.sign * 2 * Math.PI * pitches / wheel.teeth;
  }
}
//#endregion

//#region 业务逻辑
// 正转 = 后视顺时针 = 沿销轴路径前进。1 Hz 是橙色 12T 驱动轮每秒一转。
//#endregion

//#region 方法/工具
export { HZ_STEPS, DEFAULT_HZ_INDEX };
//#endregion
