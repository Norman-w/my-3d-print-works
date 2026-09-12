//#region 导入/依赖
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
//#endregion

//#region 常量/配置
const PITCH_MM = 4.7625;
const CENTER_DISTANCE_MM = 200;
const TANGENT_PITCHES = 42;
const LEFT_WRAP_PITCHES = 6;
const RIGHT_WRAP_PITCHES = 12;
const N_LEFT = 12;
const N_RIGHT = 24;
const HZ_STEPS = [0.1, 0.5, 1, 2, 5, 10];
const DEFAULT_HZ_INDEX = 2;
const CLOCKWISE = -1;
const MODEL_FILES = {
  sprocket1x: "ch1_03c_drive_sprocket_1x.stl",
  sprocket2x: "ch1_03c_drive_sprocket_2x.stl",
  plates: "ch1_03c_drive_plates.stl",
  rollers: "ch1_03c_drive_rollers.stl",
  pins: "ch1_03c_drive_pins.stl",
};
const MODEL_BASES = ["./models/sprocket-drive/", "./assets/stl/drive/"];
//#endregion

//#region 模型/类型
/** @typedef {{a:number[], b:number[], s0:number, len:number}} PathSeg */
/** @typedef {{pins:number[][], segs:PathSeg[], length:number}} DrivePath */
/** @typedef {{mesh:THREE.Mesh, rest:Float32Array, s:Float32Array, along:Float32Array, side:Float32Array, lift:Float32Array}} ChainPart */
//#endregion

//#region 私有成员
const BAKE_CHUNK = 1800;
const els = {
  meta: document.getElementById("meta"),
  status: document.getElementById("status"),
  hzOut: document.getElementById("hz-out"),
  play: document.getElementById("play"),
  pause: document.getElementById("pause"),
  fit: document.getElementById("fit"),
  top: document.getElementById("top-view"),
  hzRange: document.getElementById("hz-range"),
  stage: document.getElementById("stage"),
  loading: document.getElementById("loading"),
  loadingStep: document.getElementById("loading-step"),
  loadingBar: document.getElementById("loading-bar"),
};

const state = {
  scene: null,
  camera: null,
  renderer: null,
  controls: null,
  path: /** @type {DrivePath|null} */ (null),
  motor: /** @type {THREE.Group|null} */ (null),
  driven: /** @type {THREE.Group|null} */ (null),
  chain: /** @type {ChainPart[]} */ ([]),
  playing: true,
  ready: false,
  motorHz: HZ_STEPS[DEFAULT_HZ_INDEX],
  motorTurns: 0,
  lastMs: 0,
  modelBase: MODEL_BASES[0],
};

function yieldFrame() {
  return new Promise((resolve) => requestAnimationFrame(() => resolve()));
}

function setLoading(text, ratio) {
  if (els.status) els.status.textContent = text;
  if (els.loadingStep) els.loadingStep.textContent = text;
  if (els.loadingBar) els.loadingBar.style.width = `${Math.round(Math.min(1, Math.max(0, ratio)) * 100)}%`;
}

async function announce(text, ratio) {
  setLoading(text, ratio);
  await yieldFrame();
}

function revealScene() {
  state.ready = true;
  els.stage?.classList.add("is-ready");
  for (const control of [els.play, els.pause, els.fit, els.top, els.hzRange]) {
    if (control) control.disabled = false;
  }
}

function formatHz(hz) {
  return Number.isInteger(hz) ? String(hz) : String(hz);
}

function hzFromSlider() {
  const index = Number(els.hzRange?.value ?? DEFAULT_HZ_INDEX);
  return HZ_STEPS[Math.min(HZ_STEPS.length - 1, Math.max(0, index))] ?? HZ_STEPS[DEFAULT_HZ_INDEX];
}

function updateHzLabel() {
  const motor = state.motorHz;
  const driven = motor * (N_LEFT / N_RIGHT);
  if (els.hzOut) {
    els.hzOut.textContent = `${formatHz(motor)} Hz · 2x ${formatHz(driven)} Hz · 顺时针`;
  }
}

function showLoadError(message) {
  if (els.loading) els.loading.classList.add("is-error");
  setLoading(message, 0);
}

function polar(cx, cy, r, angle) {
  return [cx + r * Math.cos(angle), cy + r * Math.sin(angle), 0];
}

function lerp(a, b, t) {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
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

function wrapCwOpen(cx, cy, r, teeth, steps, startAngle) {
  const step = (2 * Math.PI) / teeth;
  const pts = [];
  for (let k = 1; k <= steps; k += 1) pts.push(polar(cx, cy, r, startAngle - k * step));
  return pts;
}

function lerpOpen(a, b, n) {
  const pts = [];
  for (let j = 1; j <= n - 1; j += 1) pts.push(lerp(a, b, j / n));
  return pts;
}

function buildDrivePath() {
  const rLeft = PITCH_MM / (2 * Math.sin(Math.PI / N_LEFT));
  const rRight = PITCH_MM / (2 * Math.sin(Math.PI / N_RIGHT));
  const alpha = Math.asin((rRight - rLeft) / CENTER_DISTANCE_MM);
  const leftRot = Math.PI / 2 + alpha;
  const rightRot = Math.PI / 2 + alpha;
  const leftUpper = polar(0, 0, rLeft, leftRot);
  const rightUpper = polar(CENTER_DISTANCE_MM, 0, rRight, rightRot);
  const leftLower = polar(0, 0, rLeft, leftRot - LEFT_WRAP_PITCHES * ((2 * Math.PI) / N_LEFT));
  const rightLower = polar(
    CENTER_DISTANCE_MM,
    0,
    rRight,
    rightRot - RIGHT_WRAP_PITCHES * ((2 * Math.PI) / N_RIGHT),
  );
  const pins = [
    leftUpper,
    ...lerpOpen(leftUpper, rightUpper, TANGENT_PITCHES),
    rightUpper,
    ...wrapCwOpen(CENTER_DISTANCE_MM, 0, rRight, N_RIGHT, RIGHT_WRAP_PITCHES, rightRot),
    ...lerpOpen(rightLower, leftLower, TANGENT_PITCHES),
    leftLower,
    ...wrapCwOpen(0, 0, rLeft, N_LEFT, LEFT_WRAP_PITCHES - 1, leftRot - LEFT_WRAP_PITCHES * ((2 * Math.PI) / N_LEFT)),
  ];
  const segs = [];
  let total = 0;
  for (let i = 0; i < pins.length; i += 1) {
    const a = pins[i];
    const b = pins[(i + 1) % pins.length];
    const len = length3(sub(b, a));
    segs.push({ a, b, s0: total, len });
    total += len;
  }
  return { pins, segs, length: total, rLeft, rRight, alpha };
}

function samplePath(path, sRaw) {
  const length = path.length;
  let s = ((sRaw % length) + length) % length;
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
  const normal = [-tangent[1], tangent[0], 0];
  return {
    point: lerp(seg.a, seg.b, t),
    tangent,
    normal,
  };
}

function projectPoint(path, x, y, z) {
  let bestD = Infinity;
  let bestS = 0;
  let bestQ = [x, y, z];
  let bestT = [1, 0, 0];
  for (const seg of path.segs) {
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
    }
  }
  const normal = [-bestT[1], bestT[0], 0];
  const delta = [x - bestQ[0], y - bestQ[1], z - bestQ[2]];
  return {
    s: bestS,
    along: dot(delta, bestT),
    side: dot(delta, normal),
    lift: delta[2],
  };
}

async function bakeChain(geometry, path, label, startRatio, endRatio) {
  const attr = geometry.getAttribute("position");
  const rest = new Float32Array(attr.array);
  const count = attr.count;
  const s = new Float32Array(count);
  const along = new Float32Array(count);
  const side = new Float32Array(count);
  const lift = new Float32Array(count);
  for (let i = 0; i < count; i += 1) {
    const baked = projectPoint(path, rest[i * 3], rest[i * 3 + 1], rest[i * 3 + 2]);
    s[i] = baked.s;
    along[i] = baked.along;
    side[i] = baked.side;
    lift[i] = baked.lift;
    if (i % BAKE_CHUNK === 0) {
      const t = count <= 1 ? 1 : i / (count - 1);
      await announce(`${label} ${Math.round(t * 100)}%`, startRatio + (endRatio - startRatio) * t);
    }
  }
  return { rest, s, along, side, lift };
}

function slideChain(part, path, offsetMm) {
  const attr = part.mesh.geometry.getAttribute("position");
  const arr = attr.array;
  for (let i = 0; i < part.s.length; i += 1) {
    const sample = samplePath(path, part.s[i] + offsetMm);
    arr[i * 3] = sample.point[0] + sample.tangent[0] * part.along[i] + sample.normal[0] * part.side[i];
    arr[i * 3 + 1] = sample.point[1] + sample.tangent[1] * part.along[i] + sample.normal[1] * part.side[i];
    arr[i * 3 + 2] = sample.point[2] + part.lift[i];
  }
  attr.needsUpdate = true;
}

function toColor(hex) {
  try {
    return new THREE.Color(hex);
  } catch {
    return new THREE.Color("#8b93a7");
  }
}

async function resolveModelBase() {
  for (const base of MODEL_BASES) {
    try {
      const response = await fetch(`${base}${MODEL_FILES.sprocket1x}`, { cache: "no-cache" });
      if (response.ok) return base;
    } catch {
      // 尝试下一个候选目录
    }
  }
  throw new Error("找不到传动 STL，请先运行 scripts/export_ch1_03c_sprocket_drive.sh");
}

function loadGeometry(url) {
  const loader = new STLLoader();
  return new Promise((resolve, reject) => {
    loader.load(url, resolve, undefined, reject);
  });
}

function makePivotGroup(geometry, pivot, color) {
  geometry.translate(-pivot[0], -pivot[1], -pivot[2]);
  geometry.computeVertexNormals();
  const mesh = new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({
      color: toColor(color),
      roughness: 0.42,
      metalness: 0.18,
    }),
  );
  const group = new THREE.Group();
  group.position.set(pivot[0], pivot[1], pivot[2]);
  group.add(mesh);
  return group;
}

function fitCamera(kind) {
  if (!state.camera || !state.controls) return;
  const center = new THREE.Vector3(CENTER_DISTANCE_MM / 2, 0, 0);
  state.controls.target.copy(center);
  if (kind === "top") {
    state.camera.up.set(0, 1, 0);
    state.camera.position.set(center.x, 0, 280);
  } else {
    state.camera.up.set(0, 0, 1);
    state.camera.position.set(center.x + 90, -210, 140);
  }
  state.camera.near = 0.2;
  state.camera.far = 4000;
  state.camera.updateProjectionMatrix();
  state.controls.update();
}

function applyMotion(dt) {
  if (!state.ready || !state.path || !state.motor || !state.driven) return;
  if (state.playing) state.motorTurns += state.motorHz * dt;
  const pitches = state.motorTurns * N_LEFT;
  const offsetMm = pitches * (state.path.length / state.path.pins.length);
  const motorAngle = CLOCKWISE * 2 * Math.PI * state.motorTurns;
  const drivenAngle = motorAngle * (N_LEFT / N_RIGHT);
  state.motor.rotation.z = motorAngle;
  state.driven.rotation.z = drivenAngle;
  for (const part of state.chain) slideChain(part, state.path, offsetMm);
  updateHzLabel();
}
//#endregion

//#region 公开 API
function initScene() {
  const canvas = document.getElementById("c");
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0d12);
  const camera = new THREE.PerspectiveCamera(42, 1, 0.2, 4000);
  camera.up.set(0, 0, 1);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  scene.add(new THREE.AmbientLight(0xffffff, 0.7));
  const key = new THREE.DirectionalLight(0xffffff, 1.1);
  key.position.set(40, -80, 90);
  scene.add(key);
  scene.add(new THREE.HemisphereLight(0xbfdcff, 0x111a20, 0.45));
  state.scene = scene;
  state.camera = camera;
  state.renderer = renderer;
  state.controls = controls;
  function resize() {
    camera.aspect = canvas.clientWidth / Math.max(1, canvas.clientHeight);
    camera.updateProjectionMatrix();
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
  }
  window.addEventListener("resize", resize);
  state.resize = resize;
  function tick(now) {
    if (!state.ready) {
      requestAnimationFrame(tick);
      return;
    }
    const dt = state.lastMs ? Math.min(0.05, (now - state.lastMs) / 1000) : 0;
    state.lastMs = now;
    applyMotion(dt);
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

async function loadDrive() {
  await announce("正在定位模型目录…", 0.04);
  state.modelBase = await resolveModelBase();
  await announce("正在构建销轴路径…", 0.08);
  state.path = buildDrivePath();
  if (state.path.pins.length !== 102) {
    throw new Error(`销轴路径应为 102，实际 ${state.path.pins.length}`);
  }
  const stamp = Date.now();
  await announce("正在加载 1x 链轮…", 0.12);
  const sprocket1x = await loadGeometry(`${state.modelBase}${MODEL_FILES.sprocket1x}?v=${stamp}`);
  await announce("正在加载 2x 链轮…", 0.18);
  const sprocket2x = await loadGeometry(`${state.modelBase}${MODEL_FILES.sprocket2x}?v=${stamp}`);
  state.motor = makePivotGroup(sprocket1x, [0, 0, 0], "#5b9fd6");
  state.driven = makePivotGroup(sprocket2x, [CENTER_DISTANCE_MM, 0, 0], "#e0c07a");
  state.scene.add(state.motor, state.driven);

  const chainFiles = [
    [MODEL_FILES.plates, "#8A919C", 0.22, 0.55],
    [MODEL_FILES.rollers, "#E8EDF2", 0.55, 0.78],
    [MODEL_FILES.pins, "#B08D57", 0.78, 0.96],
  ];
  state.chain = [];
  for (const [file, color, startRatio, endRatio] of chainFiles) {
    const label = `正在烘焙链条路径：${file}`;
    await announce(`正在加载 ${file}…`, startRatio);
    const geometry = await loadGeometry(`${state.modelBase}${file}?v=${stamp}`);
    geometry.computeVertexNormals();
    const baked = await bakeChain(geometry, state.path, label, startRatio, endRatio);
    const mesh = new THREE.Mesh(
      geometry,
      new THREE.MeshStandardMaterial({
        color: toColor(color),
        roughness: 0.46,
        metalness: 0.22,
      }),
    );
    mesh.visible = false;
    state.scene.add(mesh);
    state.chain.push({ mesh, ...baked });
  }
  if (els.meta) {
    els.meta.textContent =
      `1x 电机 0.1–10 Hz 顺时针 · 2x 半速同向 · 中心距 ${CENTER_DISTANCE_MM} mm · 102 节`;
  }
  for (const part of state.chain) part.mesh.visible = true;
  await announce("正在打开三维场景…", 1);
  revealScene();
  state.resize?.();
  fitCamera("iso");
  setLoading("已按 1x=电机、顺时针运行。", 1);
}

function bindControls() {
  els.play?.addEventListener("click", () => {
    state.playing = true;
  });
  els.pause?.addEventListener("click", () => {
    state.playing = false;
  });
  els.fit?.addEventListener("click", () => fitCamera("iso"));
  els.top?.addEventListener("click", () => fitCamera("top"));
  els.hzRange?.addEventListener("input", () => {
    state.motorHz = hzFromSlider();
    updateHzLabel();
  });
}
//#endregion

//#region 视图层
// 画布与按钮在 sprocket-drive-viewer.html。
//#endregion

//#region 业务逻辑
// 链传动同向：ω2 = ω1 * 12/24。路径前进方向与 1x 顺时针一致（上边向右）。
//#endregion

//#region 方法/工具
if (window.location.protocol === "file:") {
  showLoadError("请用 HTTP 打开，不要用 file://");
} else {
  initScene();
  bindControls();
  loadDrive().catch((error) => {
    showLoadError(`加载失败：${error.message || error}`);
  });
}
//#endregion
