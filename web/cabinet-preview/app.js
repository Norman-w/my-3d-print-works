//#region 导入/依赖
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { attachCabinetChainPlay, onPartLoaded, tickPlay } from "./js/cabinet-chain-play.js";
//#endregion

//#region 常量/配置
const ROLE_FALLBACK_OPACITY = {
  printed: 1,
  purchased: 0.72,
  diagnostic: 0.45,
};
const AUTO_EXPLODE_SCALE = 0.55;
const AUTOLOAD_MAX = 12;
const SEARCH_DELAY_MS = 160;
//#endregion

//#region 模型/类型
/** @typedef {{id:string,name:string,file:string,group?:string,role?:string,color?:string,opacity?:number,visible?:boolean,explosion?:number[],bytes?:number}} PreviewPart */
/** @typedef {{title?:string,units?:string,up?:string,count?:number,totalCount?:number,groups?:{id:string,name:string,count:number}[],parts:PreviewPart[]}} PreviewListing */
//#endregion

//#region 私有成员
const els = {
  title: document.getElementById("title"),
  meta: document.getElementById("meta"),
  parts: document.getElementById("parts"),
  explodeRange: document.getElementById("explode-range"),
  explodeOut: document.getElementById("explode-out"),
  modeSimple: document.getElementById("mode-simple"),
  modeExplode: document.getElementById("mode-explode"),
  fit: document.getElementById("fit"),
  assemble: document.getElementById("assemble"),
  explode: document.getElementById("explode"),
  search: document.getElementById("part-search"),
  groupFilter: document.getElementById("group-filter"),
  roleFilter: document.getElementById("role-filter"),
  loadFiltered: document.getElementById("load-filtered"),
  hideFiltered: document.getElementById("hide-filtered"),
  hzRange: document.getElementById("hz-range"),
  hzOut: document.getElementById("hz-out"),
  fwd: document.getElementById("fwd"),
  stop: document.getElementById("stop"),
  rev: document.getElementById("rev"),
};

const state = {
  mode: "simple",
  explode: 0,
  units: "mm",
  listing: /** @type {PreviewListing|null} */ (null),
  items: /** @type {Map<string, any>} */ (new Map()),
  visibleIds: new Set(),
  camera: null,
  controls: null,
  scene: null,
  searchTimer: 0,
  lastMs: 0,
};

function setMeta(text) {
  els.meta.textContent = text;
}

function itemStatus(item) {
  if (item.error) return "失败";
  if (item.loading) return "加载中";
  if (item.mesh) return "已加载";
  return "未加载";
}

function renderGroupOptions(groups) {
  const current = els.groupFilter.value;
  els.groupFilter.innerHTML = '<option value="">全部分组</option>';
  for (const group of groups || []) {
    const option = document.createElement("option");
    option.value = group.id;
    option.textContent = `${group.name} (${group.count})`;
    els.groupFilter.appendChild(option);
  }
  if ([...els.groupFilter.options].some((option) => option.value === current)) {
    els.groupFilter.value = current;
  }
}

function renderPartList() {
  els.parts.innerHTML = "";
  const listing = state.listing;
  if (!listing) return;
  const grouped = new Map();
  for (const part of listing.parts || []) {
    const groupId = part.group || "ungrouped";
    if (!grouped.has(groupId)) grouped.set(groupId, []);
    grouped.get(groupId).push(part);
  }
  for (const [groupId, parts] of grouped) {
    const section = document.createElement("section");
    section.className = "group";
    const heading = document.createElement("h2");
    heading.innerHTML = `<span>${groupId}</span><span>${parts.length}</span>`;
    section.appendChild(heading);
    for (const part of parts) {
      const item = state.items.get(part.id);
      const line = document.createElement("label");
      line.className = "part";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = state.visibleIds.has(part.id);
      checkbox.addEventListener("change", () => {
        void setPartVisible(part.id, checkbox.checked);
      });
      const mark = document.createElement("span");
      mark.style.width = "10px";
      mark.style.height = "10px";
      mark.style.borderRadius = "50%";
      mark.style.background = part.color || "#8b93a7";
      const name = document.createElement("span");
      name.className = "name";
      name.textContent = part.name || part.id;
      name.title = part.file;
      name.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        void isolatePart(part.id);
      });
      const status = document.createElement("span");
      status.className = "status";
      status.textContent = itemStatus(item);
      line.append(checkbox, mark, name, status);
      section.appendChild(line);
    }
    els.parts.appendChild(section);
  }
  refreshMeta();
}

function refreshMeta() {
  const total = state.listing?.totalCount ?? state.items.size;
  const listed = state.listing?.parts?.length ?? 0;
  const loaded = [...state.items.values()].filter((item) => item.mesh).length;
  const visible = [...state.items.values()].filter((item) => item.mesh && item.mesh.visible).length;
  setMeta(`${listed}/${total} 件清单 · ${loaded} 已加载 · ${visible} 显示中 · ${state.units}`);
}

function initScene() {
  const canvas = document.getElementById("c");
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0d12);
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 4000);
  camera.up.set(0, 0, 1);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  scene.add(new THREE.AmbientLight(0xffffff, 0.7));
  const key = new THREE.DirectionalLight(0xffffff, 1.1);
  key.position.set(40, -80, 60);
  scene.add(key);
  scene.add(new THREE.HemisphereLight(0xbfdcff, 0x111a20, 0.45));
  state.scene = scene;
  state.camera = camera;
  state.controls = controls;
  function resize() {
    camera.aspect = canvas.clientWidth / Math.max(1, canvas.clientHeight);
    camera.updateProjectionMatrix();
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
  }
  window.addEventListener("resize", resize);
  resize();
  function tick(now) {
    const dt = state.lastMs ? Math.min(0.05, (now - state.lastMs) / 1000) : 0;
    state.lastMs = now;
    tickPlay(dt);
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
//#endregion

//#region 公开 API
async function fetchListing() {
  const params = new URLSearchParams();
  const query = els.search.value.trim();
  const group = els.groupFilter.value;
  const role = els.roleFilter.value;
  if (query) params.set("q", query);
  if (group) params.set("group", group);
  if (role) params.set("role", role);
  const queryText = params.toString();
  const response = await fetch(queryText ? `./api/parts?${queryText}` : "./api/parts", {
    cache: "no-cache",
  });
  if (response.ok) return response.json();
  const fallback = await fetch("./manifest.json", { cache: "no-cache" });
  if (!fallback.ok) throw new Error(`零件清单 ${response.status}`);
  const manifest = await fallback.json();
  return {
    ...manifest,
    totalCount: (manifest.parts || []).length,
    count: (manifest.parts || []).length,
  };
}

async function refreshListing({ autoload = false } = {}) {
  const listing = await fetchListing();
  state.listing = listing;
  state.units = listing.units || "mm";
  els.title.textContent = listing.title || "STL 预览";
  renderGroupOptions(listing.groups || []);
  for (const part of listing.parts || []) {
    if (!state.items.has(part.id)) {
      state.items.set(part.id, {
        part,
        mesh: null,
        box: null,
        base: new THREE.Vector3(0, 0, 0),
        explosion: new THREE.Vector3(0, 0, 0),
        loading: false,
        error: "",
      });
    } else {
      state.items.get(part.id).part = part;
    }
  }
  renderPartList();
  if (autoload) {
    const targets = (listing.parts || [])
      .filter((part) => part.visible !== false)
      .sort((a, b) => (a.bytes || 0) - (b.bytes || 0))
      .slice(0, AUTOLOAD_MAX);
    await Promise.all(targets.map((part) => setPartVisible(part.id, true)));
    fitCamera();
  }
}

async function setPartVisible(partId, visible) {
  const item = state.items.get(partId);
  if (!item) return;
  if (visible) {
    state.visibleIds.add(partId);
    await loadPart(item);
    if (item.mesh) item.mesh.visible = true;
  } else {
    state.visibleIds.delete(partId);
    if (item.mesh) item.mesh.visible = false;
  }
  renderPartList();
  applyExplode();
}

async function isolatePart(partId) {
  const ids = [...state.items.keys()];
  await Promise.all(ids.map((id) => setPartVisible(id, id === partId)));
  fitCamera();
}

async function setFilteredVisible(visible) {
  const parts = state.listing?.parts || [];
  await Promise.all(parts.map((part) => setPartVisible(part.id, visible)));
  if (visible) fitCamera();
}
//#endregion

//#region 视图层
function bindPreviewControls() {
  els.modeSimple.addEventListener("click", () => setMode("simple"));
  els.modeExplode.addEventListener("click", () => setMode("explode"));
  els.fit.addEventListener("click", fitCamera);
  els.assemble.addEventListener("click", () => {
    state.explode = 0;
    setMode("simple");
  });
  els.explode.addEventListener("click", () => {
    state.explode = 1;
    setMode("explode");
  });
  els.explodeRange.addEventListener("input", () => {
    state.explode = Number(els.explodeRange.value) / 100;
    setMode("explode");
  });
  els.search.addEventListener("input", () => {
    window.clearTimeout(state.searchTimer);
    state.searchTimer = window.setTimeout(() => {
      void refreshListing();
    }, SEARCH_DELAY_MS);
  });
  els.groupFilter.addEventListener("change", () => {
    void refreshListing();
  });
  els.roleFilter.addEventListener("change", () => {
    void refreshListing();
  });
  els.loadFiltered.addEventListener("click", () => {
    void setFilteredVisible(true);
  });
  els.hideFiltered.addEventListener("click", () => {
    void setFilteredVisible(false);
  });
}

if (window.location.protocol === "file:") {
  document.body.classList.add("file");
} else {
  initScene();
  bindPreviewControls();
  attachCabinetChainPlay({ state, els });
  refreshListing({ autoload: true }).catch((error) => {
    setMeta(`加载失败：${error.message || error}`);
  });
}
//#endregion

//#region 业务逻辑
function ensureExplosion(item, centroid, span, index, count) {
  if (Array.isArray(item.part.explosion) && item.part.explosion.length === 3) {
    return new THREE.Vector3(...item.part.explosion);
  }
  const center = item.box.getCenter(new THREE.Vector3());
  const dir = center.sub(centroid);
  if (dir.lengthSq() < 1e-6) {
    const offset = index - (count - 1) / 2;
    dir.set(0, 0, offset === 0 ? span * 0.15 : offset);
  }
  dir.normalize().multiplyScalar(span * AUTO_EXPLODE_SCALE);
  return dir;
}

function recomputeExplosions() {
  const loaded = [...state.items.values()].filter((item) => item.box);
  if (!loaded.length) return;
  const union = new THREE.Box3();
  for (const item of loaded) union.union(item.box);
  const centroid = union.getCenter(new THREE.Vector3());
  const span = Math.max(...union.getSize(new THREE.Vector3()).toArray(), 1);
  loaded.forEach((item, index) => {
    item.explosion = ensureExplosion(item, centroid, span, index, loaded.length);
  });
}

function applyExplode() {
  const amount = state.mode === "explode" ? state.explode : 0;
  for (const item of state.items.values()) {
    if (!item.mesh) continue;
    item.mesh.position.copy(item.base).addScaledVector(item.explosion, amount);
  }
  els.explodeRange.value = String(Math.round(amount * 100));
  els.explodeOut.textContent = String(Math.round(amount * 100));
}

function setMode(mode) {
  state.mode = mode;
  els.modeSimple.classList.toggle("on", mode === "simple");
  els.modeExplode.classList.toggle("on", mode === "explode");
  if (mode === "explode" && state.explode === 0) state.explode = 1;
  if (mode === "simple") state.explode = 0;
  applyExplode();
}

async function loadPart(item) {
  if (item.mesh || item.loading) return;
  item.loading = true;
  item.error = "";
  renderPartList();
  try {
    const geometry = await loadGeometry(`${item.part.file}?v=${item.part.mtime || Date.now()}`);
    geometry.computeVertexNormals();
    geometry.computeBoundingBox();
    const material = new THREE.MeshStandardMaterial({
      color: toColor(item.part.color),
      roughness: 0.5,
      metalness: 0.08,
      transparent: partOpacity(item.part) < 0.999,
      opacity: partOpacity(item.part),
      side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.visible = state.visibleIds.has(item.part.id);
    state.scene.add(mesh);
    item.mesh = mesh;
    item.box = geometry.boundingBox.clone();
    try {
      await onPartLoaded(item);
    } catch (playError) {
      console.error("chain play bind failed", item.part?.id, playError);
    }
    recomputeExplosions();
    applyExplode();
  } catch (error) {
    item.error = error.message || String(error);
  } finally {
    item.loading = false;
    renderPartList();
  }
}
//#endregion

//#region 方法/工具
function partOpacity(part) {
  if (typeof part.opacity === "number") return part.opacity;
  return ROLE_FALLBACK_OPACITY[part.role] ?? 1;
}

function toColor(value) {
  try {
    return new THREE.Color(value || "#8b93a7");
  } catch {
    return new THREE.Color("#8b93a7");
  }
}

function fitCamera() {
  const box = new THREE.Box3();
  let has = false;
  for (const item of state.items.values()) {
    if (!item.mesh || !item.mesh.visible) continue;
    box.expandByObject(item.mesh);
    has = true;
  }
  if (!has || !state.camera || !state.controls) return;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const radius = Math.max(size.x, size.y, size.z, 1) * 0.9;
  state.controls.target.copy(center);
  state.camera.up.set(0, 0, 1);
  state.camera.position.set(
    center.x + radius * 0.15,
    center.y + radius * 2.1,
    center.z + radius * 0.35,
  );
  state.camera.near = Math.max(0.01, radius / 100);
  state.camera.far = Math.max(500, radius * 40);
  state.camera.updateProjectionMatrix();
  state.controls.update();
}

async function loadGeometry(url) {
  const loader = new STLLoader();
  return new Promise((resolve, reject) => {
    loader.load(url, resolve, undefined, reject);
  });
}
//#endregion
