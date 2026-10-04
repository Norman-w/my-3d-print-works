//#region 导入/依赖
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
//#endregion

//#region 常量/配置
const ROLE_FALLBACK_OPACITY = {
  printed: 1,
  purchased: 0.72,
  diagnostic: 0.45,
};
const AUTO_EXPLODE_SCALE = 0.55;
const AUTOLOAD_MAX = 40;
const SEARCH_DELAY_MS = 160;
const ORIGINAL_BEAM_ID = "feeder/beam-grip";
const TRIGGER_LEVER_ID = "feeder/trigger-lever";
const TRIGGER_SCENE_FILE = "./trigger-candidate/scene.json";
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
  viewAssembly: document.getElementById("view-assembly"),
  toggleTrigger: document.getElementById("toggle-trigger"),
  focusTrigger: document.getElementById("focus-trigger"),
  triggerRange: document.getElementById("trigger-range"),
  triggerOut: document.getElementById("trigger-out"),
  sceneNote: document.getElementById("scene-note"),
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
  trigger: {
    enabled: false,
    loading: false,
    group: null,
    leverPivot: null,
    spring: null,
    sceneData: null,
  },
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
      status.textContent = (part.id === ORIGINAL_BEAM_ID || part.id === TRIGGER_LEVER_ID)
        && state.trigger.enabled ? "动态场景显示中" : itemStatus(item);
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
  const visible = [...state.items.values()].filter((item) => item.mesh && item.mesh.visible).length
    + (state.trigger.enabled && state.trigger.group?.visible ? 2 : 0);
  const candidate = state.trigger.enabled ? " · 显示已选电子扳机动态场景" : "";
  setMeta(`${listed}/${total} 件清单 · ${loaded} 已加载 · ${visible} 显示中 · ${state.units}${candidate}`);
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
  function tick() {
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(tick);
  }
  tick();
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
    const targets = (listing.parts || []).slice(0, AUTOLOAD_MAX);
    await Promise.all(targets.map((part) => setPartVisible(part.id, true)));
    fitCamera();
  }
}

async function setPartVisible(partId, visible) {
  const item = state.items.get(partId);
  if (!item) return;
  if ((partId === ORIGINAL_BEAM_ID || partId === TRIGGER_LEVER_ID)
      && visible && state.trigger.enabled) {
    await setTriggerEnabled(false, { restoreOriginal: false });
  }
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
  if (state.trigger.enabled) {
    await setTriggerEnabled(false, { restoreOriginal: false });
  }
  const ids = [...state.items.keys()];
  await Promise.all(ids.map((id) => setPartVisible(id, id === partId)));
  fitCamera();
}

async function setFilteredVisible(visible) {
  const parts = state.listing?.parts || [];
  await Promise.all(parts.map((part) => setPartVisible(part.id, visible)));
  if (visible) fitCamera();
}

async function showDefinedAssembly({ candidate = state.trigger.enabled } = {}) {
  els.search.value = "";
  els.groupFilter.value = "";
  els.roleFilter.value = "";
  await refreshListing();
  const targets = (state.listing?.parts || []).filter((part) => part.group !== "hold");
  const ids = new Set(targets.map((part) => part.id));
  if (candidate) {
    ids.delete(ORIGINAL_BEAM_ID);
    ids.delete(TRIGGER_LEVER_ID);
  }
  state.visibleIds = ids;
  await Promise.all(targets.filter((part) => ids.has(part.id))
    .map((part) => loadPart(state.items.get(part.id))));
  for (const item of state.items.values()) {
    if (item.mesh) item.mesh.visible = ids.has(item.part.id);
  }
  renderPartList();
  applyExplode();
  fitCamera();
  els.sceneNote.textContent = candidate
    ? "结构全览：已选替换背梁与杠杆在动态场景中显示；开关、弹簧和转轴是尺寸代理，电机与传动未装入。"
    : "当前显示 49 件已定义结构，其中电子扳机处于松开位置；电机与传动未装入。";
}
//#endregion

//#region 视图层
function bindPreviewControls() {
  els.viewAssembly.addEventListener("click", () => {
    void showDefinedAssembly().catch((error) => {
      els.sceneNote.textContent = `结构加载失败：${error.message || error}`;
    });
  });
  els.toggleTrigger.addEventListener("click", () => {
    void setTriggerEnabled(!state.trigger.enabled);
  });
  els.focusTrigger.addEventListener("click", focusTrigger);
  els.triggerRange.addEventListener("input", () => {
    setTriggerFraction(Number(els.triggerRange.value) / 100);
  });
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
    void (async () => {
      if (state.trigger.enabled) await setTriggerEnabled(false, { restoreOriginal: false });
      await Promise.all([...state.items.keys()].map(id => setPartVisible(id, false)));
      await refreshListing({ autoload: true });
    })();
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
  (async () => {
    await refreshListing();
    const params = new URLSearchParams(location.search);
    if (params.get("trigger") === "1") {
      await setTriggerEnabled(true);
    } else {
      els.groupFilter.value = params.get("group") || "feeder";
      await refreshListing({ autoload: true });
    }
  })().catch((error) => {
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
  if (state.trigger.group) {
    state.trigger.group.position.set(30 * amount, -10 * amount, 0);
    const pivot = state.trigger.sceneData.geometry.pivot_mm;
    state.trigger.leverPivot.position.set(
      pivot[0] + 20 * amount, pivot[1] - 10 * amount, pivot[2]);
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
  fitCamera();
}

function triggerMaterial(color, opacity = 1, metalness = 0.08) {
  return new THREE.MeshStandardMaterial({
    color,
    roughness: 0.5,
    metalness,
    transparent: opacity < 1,
    opacity,
    side: THREE.DoubleSide,
  });
}

function addReferenceBox(group, x, y, z, width, depth, height, material) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, depth, height), material);
  mesh.position.set(x, y, z);
  group.add(mesh);
}

async function loadTriggerCandidate() {
  if (state.trigger.group) return;
  const response = await fetch(TRIGGER_SCENE_FILE, { cache: "no-cache" });
  if (!response.ok) throw new Error(`电子扳机场景 ${response.status}`);
  const data = await response.json();
  if (data.status !== "NOMINAL_TRIGGER_CANDIDATE_VIEW_ONLY"
      || data.replacement_for !== ORIGINAL_BEAM_ID
      || data.selected_inventory_promoted !== true
      || data.real_switch_spring_and_motor_verified !== false) {
    throw new Error("电子扳机场景状态与当前清单不一致");
  }
  const [beamGeometry, leverGeometry] = await Promise.all([
    loadGeometry(`${data.meshes.beam.file}?v=${data.meshes.beam.sha256.slice(0, 12)}`),
    loadGeometry(`${data.meshes.lever.file}?v=${data.meshes.lever.sha256.slice(0, 12)}`),
  ]);
  beamGeometry.computeVertexNormals();
  leverGeometry.computeVertexNormals();
  const g = data.geometry;
  const pivot = new THREE.Vector3(...g.pivot_mm);
  const group = new THREE.Group();
  group.name = "已选电子扳机 · 动态显示";
  const beam = new THREE.Mesh(beamGeometry, triggerMaterial("#4583a9"));
  beam.name = "替换背梁（已选）";
  group.add(beam);
  leverGeometry.translate(-pivot.x, -pivot.y, -pivot.z);
  const leverPivot = new THREE.Group();
  leverPivot.position.copy(pivot);
  const lever = new THREE.Mesh(leverGeometry, triggerMaterial("#ff841f"));
  lever.name = "朝握把勾扣的信号杠杆（已选）";
  leverPivot.add(lever);
  group.add(leverPivot);

  const switchMaterial = triggerMaterial("#191c23", 0.92);
  const silver = triggerMaterial("#c2ccd2", 1, 0.42);
  const switchX = g.et_switch_x;
  const switchY = g.et_switch_y;
  const switchZ = g.et_switch_z;
  addReferenceBox(group,
    switchX + g.et_switch_case_depth_x / 2,
    switchY + g.et_switch_case_depth_y / 2,
    switchZ + g.switch_case_height_z_mm / 2,
    g.et_switch_case_depth_x, g.et_switch_case_depth_y,
    g.switch_case_height_z_mm, switchMaterial);
  for (let index = 0; index < 3; index += 1) {
    addReferenceBox(group,
      switchX - g.et_switch_terminal_length_x / 2,
      switchY + g.et_switch_case_depth_y / 2,
      switchZ + g.et_switch_terminal_first_z_offset
        + index * g.et_switch_terminal_pitch_z,
      g.et_switch_terminal_length_x, g.et_switch_terminal_thickness_y,
      g.et_switch_terminal_width_z, silver);
  }
  const target = new THREE.Mesh(
    new THREE.SphereGeometry(0.45, 12, 8), triggerMaterial("#ec3e36"));
  target.position.set(switchX + g.et_switch_actuator_op,
    pivot.y, g.et_switch_actuator_z);
  group.add(target);
  const spacer = new THREE.Mesh(new THREE.CylinderGeometry(
    g.et_pivot_spacer_od / 2, g.et_pivot_spacer_od / 2,
    g.et_pivot_spacer_length, 24), silver);
  spacer.position.copy(pivot);
  group.add(spacer);
  const bolt = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.5, 18, 20), silver);
  bolt.position.copy(pivot);
  group.add(bolt);
  const spring = new THREE.Mesh(
    new THREE.CylinderGeometry(g.et_spring_od / 2, g.et_spring_od / 2, 1, 24),
    triggerMaterial("#e7bc4e", 0.68, 0.25));
  spring.rotation.z = Math.PI / 2;
  group.add(spring);
  group.visible = false;
  state.scene.add(group);
  state.trigger.group = group;
  state.trigger.leverPivot = leverPivot;
  state.trigger.spring = spring;
  state.trigger.sceneData = data;
}

function setTriggerFraction(fraction) {
  const data = state.trigger.sceneData;
  if (!data) return;
  const t = Math.max(0, Math.min(1, fraction));
  const angle = data.pull_angle_deg * t;
  const radians = THREE.MathUtils.degToRad(angle);
  const g = data.geometry;
  state.trigger.leverPivot.rotation.y = radians;
  const movingX = g.pivot_mm[0]
    + (g.et_spring_moving_seat_x - g.pivot_mm[0]) * Math.cos(radians)
    + (g.et_spring_center_z - g.pivot_mm[2]) * Math.sin(radians);
  const springLength = g.et_spring_fixed_seat_x - movingX;
  state.trigger.spring.scale.y = springLength;
  state.trigger.spring.position.set((g.et_spring_fixed_seat_x + movingX) / 2,
    g.et_spring_center_y, g.et_spring_center_z);
  els.triggerOut.textContent = `${angle.toFixed(1)}° · ${t === 0 ? "松开" : t === 1 ? "扣到底" : "勾扣中"}`;
}

function focusTrigger() {
  if (!state.trigger.enabled) return;
  // Keep the selected parts loaded, but hide them to expose the lever behind
  // the feeder housing. The full-assembly button restores their visibility.
  state.visibleIds.clear();
  for (const item of state.items.values()) {
    if (item.mesh) item.mesh.visible = false;
  }
  renderPartList();
  state.controls.target.set(56, -52, -16);
  state.camera.position.set(105, 75, 25);
  state.camera.near = 0.1;
  state.camera.far = 1000;
  state.camera.updateProjectionMatrix();
  state.controls.update();
  els.sceneNote.textContent = "局部视角：已加载的其他结构暂时隐藏，点“已定义结构全览”可恢复。橙色杠杆向握把勾扣；开关、弹簧和转轴是尺寸代理。";
}

async function setTriggerEnabled(enabled, { restoreOriginal = true } = {}) {
  if (state.trigger.loading || enabled === state.trigger.enabled) return;
  state.trigger.loading = true;
  els.toggleTrigger.disabled = true;
  try {
    if (enabled) {
      els.sceneNote.textContent = "正在加载同一坐标系中的总装与扳机动态场景…";
      await showDefinedAssembly({ candidate: true });
      await loadTriggerCandidate();
      state.trigger.enabled = true;
      state.trigger.group.visible = true;
      els.triggerRange.disabled = false;
      els.focusTrigger.disabled = false;
      els.toggleTrigger.classList.add("on");
      els.toggleTrigger.setAttribute("aria-pressed", "true");
      els.toggleTrigger.textContent = "隐藏扳机动态场景";
      setTriggerFraction(Number(els.triggerRange.value) / 100);
      applyExplode();
      fitCamera();
    } else {
      state.trigger.enabled = false;
      state.trigger.group.visible = false;
      els.triggerRange.disabled = true;
      els.triggerRange.value = "0";
      setTriggerFraction(0);
      els.focusTrigger.disabled = true;
      els.toggleTrigger.classList.remove("on");
      els.toggleTrigger.setAttribute("aria-pressed", "false");
      els.toggleTrigger.textContent = "加载扳机动态场景";
      if (restoreOriginal) await showDefinedAssembly({ candidate: false });
      els.sceneNote.textContent = "当前显示 49 件已定义结构；电子扳机已选但未实物验收。";
      fitCamera();
    }
  } catch (error) {
    if (enabled) {
      state.trigger.enabled = false;
      if (state.trigger.group) state.trigger.group.visible = false;
      await setPartVisible(ORIGINAL_BEAM_ID, true);
      await setPartVisible(TRIGGER_LEVER_ID, true);
    }
    els.sceneNote.textContent = `扳机动态场景加载失败：${error.message || error}`;
  } finally {
    state.trigger.loading = false;
    els.toggleTrigger.disabled = false;
    renderPartList();
  }
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
  if (state.trigger.enabled && state.trigger.group?.visible) {
    box.expandByObject(state.trigger.group);
    has = true;
  }
  if (!has || !state.camera || !state.controls) return;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const radius = Math.max(size.x, size.y, size.z, 1) * 0.9;
  state.controls.target.copy(center);
  state.camera.up.set(0, 0, 1);
  state.camera.position.set(
    center.x + radius * 1.4,
    center.y - radius * 1.6,
    center.z + radius * 0.9,
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
