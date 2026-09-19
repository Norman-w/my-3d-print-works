//#region 导入/依赖
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { ViewHelper } from "three/addons/helpers/ViewHelper.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import {
  attachCabinetChainPlay,
  focusCenterClutch,
  playCenterClutchDemo,
  onPartLoaded,
  tickPlay,
} from "./js/cabinet-chain-play.js?v=cabinet-frame-view-13";
//#endregion

//#region 常量/配置
const ROLE_FALLBACK_OPACITY = {
  printed: 1,
  purchased: 0.72,
  diagnostic: 0.45,
};
const AUTO_EXPLODE_SCALE = 0.55;
const SEARCH_DELAY_MS = 160;
const TREE_COLLAPSED_KEY = "smartpartsdrawer.preview.tree.collapsed-groups";
const TREE_PANEL_COLLAPSED_KEY = "smartpartsdrawer.preview.tree.collapsed";
const TREE_POSITION_KEY = "smartpartsdrawer.preview.tree.position";
const VIEWS_COLLAPSED_KEY = "smartpartsdrawer.preview.views.collapsed";
const VIEWS_POSITION_KEY = "smartpartsdrawer.preview.views.position";
const CABINET_TRANSPARENCY_KEY = "smartpartsdrawer.preview.cabinet.transparency";
const FLOATING_PANEL_MARGIN = 12;
const VIEW_HELPER_SIZE = 128;
const LEGACY_ASSEMBLY_WIDTH = 260;
const CABINET_TRANSPARENCY_CONTROLS = Object.freeze([
  {
    partId: "cabinet-clutch/cabinet_clutch_cabinet_frame",
    inputId: "cabinet-shell-transparency",
    outputId: "cabinet-shell-transparency-out",
    fallbackOpacity: 0.30,
  },
]);
const CABINET_CONTROL_BY_PART_ID = new Map(
  CABINET_TRANSPARENCY_CONTROLS.map((control) => [control.partId, control]),
);
const DEFAULT_HIDDEN_PART_IDS = new Set([
  "cabinet/cabinet_back_panel",
  // Retired center candidate names are kept only for explicit legacy
  // diagnostics. The active center station is role-named input/output.
  "cabinet-clutch/06_upper_axis_y_spur_candidate",
  "cabinet-clutch/06_upper_axis_z_spur_candidate",
  "cabinet-clutch/07_upper_downward_dog_candidate",
  "cabinet-clutch/08_lower_upward_dog_candidate",
  "cabinet-clutch/09_rear_takeoff_timing_pulley_candidate",
  "cabinet-clutch/10_clutch_spring_reference",
  "cabinet-clutch/11_t_countersunk_screw_reference",
  "cabinet-clutch/12_clutch_fork_candidate",
  // Retired coincident cabinet meshes; the canonical frame is the only
  // cabinet object published by the root preview.
  "cabinet-clutch/cabinet_clutch_cabinet",
  "cabinet-clutch/cabinet_clutch_cabinet_context",
]);
const LEGACY_COORDINATE_GROUPS = new Set([
  "cabinet",
  "cabinet-chain",
]);
const CAMERA_VIEWS = {
  // 世界坐标：X=横向宽度，Y=竖直高度，Z=柜体深度；柜体正面为 +Z。
  front: { direction: [0, 0, 1], up: [0, 1, 0] },
  left: { direction: [-1, 0, 0], up: [0, 1, 0] },
  rear: { direction: [0, 0, -1], up: [0, 1, 0] },
  iso: { direction: [1.15, 0.82, -1.45], up: [0, 1, 0] },
  snake: { direction: [0.42, 0.62, -1.55], up: [0, 1, 0] },
  "drawer-drive": { direction: [0.68, 0.52, -1.48], up: [0, 1, 0] },
  "upper-tensioner": { direction: [-1.35, 0.62, -1.08], up: [0, 1, 0] },
  "lower-tensioner": { direction: [-0.68, 0.58, -1.55], up: [0, 1, 0] },
  "center-clutch": { direction: [0.78, 0.42, -1.20], up: [0, 1, 0] },
  "cabinet-frame": { direction: [1.15, 0.82, -1.45], up: [0, 1, 0] },
  "cabinet-partition": { direction: [0, 0, -1], up: [0, 1, 0] },
};
const DRAWER_DRIVE_TAILS = new Set([
  "cabinet_clutch_power_motor_body",
  "cabinet_clutch_power_motor_shaft",
  "cabinet_clutch_power_column_0",
  "cabinet_clutch_power_column_1",
  "cabinet_clutch_power_column_2",
  "cabinet_clutch_power_column_3",
  "cabinet_clutch_power_column_4",
  "cabinet_clutch_column_sync_belt_bottom",
  "cabinet_clutch_column_sync_belt_top",
  "cabinet_clutch_column_sync_tensioner",
  "00_tensioner_t_solid_reference",
  "04_right_round_axis_reference",
  "05_top_bottom_bus_belts_reference",
  "center_input_rotor",
  "center_output_rotor",
  "center_input_shaft_reference",
  "center_input_sleeve",
  "center_input_sleeve_magnet_reference",
  "center_linear_bearings_reference",
  "center_mechanism_plate",
  "center_output_shaft_reference",
  "center_output_bearings_reference",
  "13_drawer_timing_belt_reference",
  "14_front_timing_pulley_candidate",
  "15_front_pinion_candidate",
  "16_drawer_linear_rack_candidate",
  "24_center_station_kit_template",
]);
const LEGACY_SCHEME1_TAILS = new Set([
  "cabinet_chain_scheme1_power_wheels",
  "cabinet_chain_scheme1_output_wheels",
  "cabinet_chain_scheme1_clutch_faces",
  "cabinet_chain_scheme1_bearings",
  "cabinet_chain_scheme1_selector",
]);
const CENTER_CLUTCH_FOCUS_IDS = new Set([
  "cabinet-clutch/center_input_rotor",
  "cabinet-clutch/center_output_rotor",
  "cabinet-clutch/center_input_shaft_reference",
  "cabinet-clutch/center_input_sleeve",
  "cabinet-clutch/center_input_sleeve_magnet_reference",
  "cabinet-clutch/center_linear_bearings_reference",
  "cabinet-clutch/center_mechanism_plate",
  "cabinet-clutch/center_output_bearings_reference",
  "cabinet-clutch/center_output_shaft_reference",
]);
const CENTER_CLUTCH_FRAME_IDS = new Set([
  ...CENTER_CLUTCH_FOCUS_IDS,
]);
const CENTER_CLUTCH_CONTEXT_IDS = new Set([
  // Keep the first-article view readable: the full cabinet/grid is a useful
  // assembly context in the normal rear view, but its translucent wall faces
  // hide the very mechanism being checked. Only the real neighboring drive
  // datums remain as low-opacity context here.
  "cabinet-clutch/cabinet_clutch_power_column_2",
  "cabinet-clutch/13_drawer_timing_belt_reference",
  "cabinet-clutch/14_front_timing_pulley_candidate",
  "cabinet-clutch/15_front_pinion_candidate",
  "cabinet-clutch/16_drawer_linear_rack_candidate",
  // Keep the authored snake-chain assets available as a low-opacity spatial
  // reference for the center mechanism.
  "cabinet-chain/cabinet_chain_plates",
  "cabinet-chain/cabinet_chain_rollers",
  "cabinet-chain/cabinet_chain_pins",
  "cabinet-chain/cabinet_chain_connector",
  "cabinet-chain/cabinet_chain_clutch_connector",
  "cabinet-chain/cabinet_chain_clutch_bearing",
  "cabinet-chain/cabinet_chain_clutch_trigger_magnet",
]);
const LEGACY_MOTOR_TENSIONER_ID = "cabinet-chain/cabinet_chain_motor_tensioner";
const UPPER_TENSIONER_TAILS = new Set([
  "00_tensioner_t_solid_reference",
  "cabinet_clutch_column_sync_tensioner",
  "00_cabinet_tensioner_receiver_candidate",
  "00_left_d_axis_candidate",
  "00_tensioner_adjust_screw_reference",
  "00_tensioner_base_candidate",
  "00_tensioner_carriage_candidate",
  "00_tensioner_slide_assembly_reference",
  "00_tensioner_spring_reference",
]);
//#endregion

//#region 模型/类型
/** @typedef {{id:string,name:string,file:string,group?:string,role?:string,color?:string,opacity?:number,visible?:boolean,explosion?:number[],bytes?:number,instanceMode?:string,instanceCount?:number,instances?:Array<{id?:string,position?:number[],rotation?:number[],scale?:number[]}>}} PreviewPart */
/** @typedef {{title?:string,units?:string,up?:string,count?:number,totalCount?:number,groups?:{id:string,name:string,count:number}[],parts:PreviewPart[]}} PreviewListing */
//#endregion

//#region 私有成员
const els = {
  title: document.getElementById("title"),
  meta: document.getElementById("meta"),
  parts: document.getElementById("parts"),
  explodeRange: document.getElementById("explode-range"),
  explodeOut: document.getElementById("explode-out"),
  cabinetShellTransparency: document.getElementById("cabinet-shell-transparency"),
  cabinetShellTransparencyOut: document.getElementById("cabinet-shell-transparency-out"),
  cabinetTransparencyReset: document.getElementById("cabinet-opacity-reset"),
  search: document.getElementById("part-search"),
  groupFilter: document.getElementById("group-filter"),
  roleFilter: document.getElementById("role-filter"),
  loadFiltered: document.getElementById("load-filtered"),
  hideFiltered: document.getElementById("hide-filtered"),
  hzRange: document.getElementById("hz-range"),
  hzOut: document.getElementById("hz-out"),
  scheme1Out: document.getElementById("scheme1-status"),
  centerClutchDemo: document.getElementById("center-clutch-demo"),
  fwd: document.getElementById("fwd"),
  stop: document.getElementById("stop"),
  rev: document.getElementById("rev"),
  previewApp: document.getElementById("preview-app"),
  treePanel: document.getElementById("tree-panel"),
  treeHeader: document.querySelector("#tree-panel .tree-header"),
  treeCollapse: document.getElementById("tree-collapse"),
  viewPanel: document.getElementById("view-panel"),
  viewHeader: document.querySelector("#view-panel .view-panel-header"),
  viewsToggle: document.getElementById("views-toggle"),
  viewsChevron: document.getElementById("views-chevron"),
  viewButtons: [...document.querySelectorAll("[data-view]")],
};

const state = {
  explode: 0,
  units: "mm",
  listing: /** @type {PreviewListing|null} */ (null),
  items: /** @type {Map<string, any>} */ (new Map()),
  visibleIds: new Set(),
  camera: null,
  controls: null,
  scene: null,
  legacyRoot: null,
  legacyTensionerRoot: null,
  viewHelper: null,
  searchTimer: 0,
  lastMs: 0,
  collapsedGroups: loadCollapsedGroups(),
  treeCollapsed: loadTreeCollapsed(),
  treePosition: loadTreePosition(),
  treeDrag: null,
  viewsCollapsed: loadViewsCollapsed(),
  viewsPosition: loadViewsPosition(),
  viewsDrag: null,
  activeView: "rear",
  viewProfile: null,
  viewRequest: 0,
  cabinetTransparency: loadCabinetTransparency(),
};

function clampCabinetTransparency(value) {
  return Math.min(100, Math.max(0, Math.round(Number(value))));
}

function loadCabinetTransparency() {
  try {
    const saved = JSON.parse(localStorage.getItem(CABINET_TRANSPARENCY_KEY) || "null");
    const result = new Map();
    for (const control of CABINET_TRANSPARENCY_CONTROLS) {
      const value = Number(saved?.[control.partId]);
      if (Number.isFinite(value)) result.set(control.partId, clampCabinetTransparency(value));
    }
    return result;
  } catch {
    return new Map();
  }
}

function saveCabinetTransparency() {
  try {
    const values = Object.fromEntries(state.cabinetTransparency.entries());
    localStorage.setItem(CABINET_TRANSPARENCY_KEY, JSON.stringify(values));
  } catch {
    // Private browsing can deny localStorage; the controls still work for this load.
  }
}

function loadCollapsedGroups() {
  try {
    const saved = JSON.parse(localStorage.getItem(TREE_COLLAPSED_KEY) || "[]");
    return new Set(Array.isArray(saved) ? saved : []);
  } catch {
    return new Set();
  }
}

function saveCollapsedGroups() {
  try {
    localStorage.setItem(TREE_COLLAPSED_KEY, JSON.stringify([...state.collapsedGroups]));
  } catch {
    // Private browsing can deny localStorage; the tree still works for this load.
  }
}

function loadTreeCollapsed() {
  try {
    return localStorage.getItem(TREE_PANEL_COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

function saveTreeCollapsed() {
  try {
    localStorage.setItem(TREE_PANEL_COLLAPSED_KEY, state.treeCollapsed ? "1" : "0");
  } catch {
    // Private browsing can deny localStorage; the tree still works for this load.
  }
}

function loadFloatingPosition(storageKey, fallback) {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || "null");
    if (Number.isFinite(saved?.left) && Number.isFinite(saved?.top)) {
      return { left: saved.left, top: saved.top };
    }
  } catch {
    // Private browsing can deny localStorage; use the default position.
  }
  return { ...fallback };
}

function saveFloatingPosition(storageKey, position) {
  try {
    localStorage.setItem(storageKey, JSON.stringify(position));
  } catch {
    // Private browsing can deny localStorage; the panel still moves for this load.
  }
}

function loadViewsCollapsed() {
  try {
    return localStorage.getItem(VIEWS_COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

function saveViewsCollapsed() {
  try {
    localStorage.setItem(VIEWS_COLLAPSED_KEY, state.viewsCollapsed ? "1" : "0");
  } catch {
    // Private browsing can deny localStorage; the view section still works for this load.
  }
}

function loadTreePosition() {
  return loadFloatingPosition(TREE_POSITION_KEY, { left: 16, top: 16 });
}

function saveTreePosition(position = state.treePosition) {
  saveFloatingPosition(TREE_POSITION_KEY, position);
}

function loadViewsPosition() {
  return loadFloatingPosition(VIEWS_POSITION_KEY, { left: 368, top: 16 });
}

function saveViewsPosition(position = state.viewsPosition) {
  saveFloatingPosition(VIEWS_POSITION_KEY, position);
}

function clampFloatingPosition(panel, left, top) {
  if (!panel) return { left, top };
  const width = panel.offsetWidth || 340;
  const height = panel.offsetHeight || Math.max(44, window.innerHeight - 32);
  const maxLeft = Math.max(FLOATING_PANEL_MARGIN, window.innerWidth - width - FLOATING_PANEL_MARGIN);
  const maxTop = Math.max(FLOATING_PANEL_MARGIN, window.innerHeight - height - FLOATING_PANEL_MARGIN);
  return {
    left: Math.min(Math.max(left, FLOATING_PANEL_MARGIN), maxLeft),
    top: Math.min(Math.max(top, FLOATING_PANEL_MARGIN), maxTop),
  };
}

function applyFloatingPosition(panel, position, save, { persist = false } = {}) {
  const next = clampFloatingPosition(panel, position.left, position.top);
  if (panel) {
    panel.style.left = `${next.left}px`;
    panel.style.top = `${next.top}px`;
  }
  if (persist) save(next);
  return next;
}

function applyTreePosition({ persist = false } = {}) {
  state.treePosition = applyFloatingPosition(els.treePanel, state.treePosition, saveTreePosition, { persist });
}

function applyViewsPosition({ persist = false } = {}) {
  state.viewsPosition = applyFloatingPosition(els.viewPanel, state.viewsPosition, saveViewsPosition, { persist });
}

function placeCenterClutchViewPanel() {
  if (!els.viewPanel) return;
  const width = els.viewPanel.offsetWidth || 280;
  state.viewsPosition = clampFloatingPosition(
    els.viewPanel,
    window.innerWidth - width - FLOATING_PANEL_MARGIN,
    FLOATING_PANEL_MARGIN,
  );
  applyViewsPosition();
}

function setMeta(text) {
  els.meta.textContent = text;
}

function applyTreeCollapsed() {
  els.treePanel?.classList.toggle("collapsed", state.treeCollapsed);
  els.previewApp?.classList.toggle("tree-collapsed", state.treeCollapsed);
  if (els.treeCollapse) {
    els.treeCollapse.textContent = state.treeCollapsed ? "›" : "‹";
    els.treeCollapse.setAttribute("aria-label", state.treeCollapsed ? "展开器件树" : "折叠器件树");
    els.treeCollapse.title = state.treeCollapsed ? "展开器件树" : "折叠器件树";
  }
  applyTreePosition();
}

function applyViewsCollapsed() {
  els.viewPanel?.classList.toggle("collapsed", state.viewsCollapsed);
  els.viewsToggle?.setAttribute("aria-expanded", String(!state.viewsCollapsed));
  if (els.viewsToggle) {
    const label = state.viewsCollapsed ? "展开视角" : "折叠视角";
    els.viewsToggle.setAttribute("aria-label", label);
    els.viewsToggle.title = label;
  }
  if (els.viewsChevron) els.viewsChevron.textContent = state.viewsCollapsed ? "›" : "‹";
}

function bindFloatingPanelDrag({ panel, handle, getPosition, setPosition, save }) {
  if (!handle || !panel) return;

  let drag = null;

  const finishDrag = (event) => {
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (handle.hasPointerCapture?.(event.pointerId)) {
      handle.releasePointerCapture(event.pointerId);
    }
    handle.classList.remove("dragging");
    panel.classList.remove("dragging");
    drag = null;
    const position = applyFloatingPosition(panel, getPosition(), save, { persist: true });
    setPosition(position);
  };

  handle.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    const target = event.target;
    if (target instanceof Element && target.closest("button, input, select, a")) return;
    const rect = panel.getBoundingClientRect();
    drag = {
      pointerId: event.pointerId,
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
    };
    handle.setPointerCapture?.(event.pointerId);
    handle.classList.add("dragging");
    panel.classList.add("dragging");
    event.preventDefault();
  });

  handle.addEventListener("pointermove", (event) => {
    if (!drag || drag.pointerId !== event.pointerId) return;
    const position = clampFloatingPosition(panel,
      event.clientX - drag.offsetX,
      event.clientY - drag.offsetY,
    );
    setPosition(position);
    panel.style.left = `${position.left}px`;
    panel.style.top = `${position.top}px`;
    event.preventDefault();
  });

  handle.addEventListener("pointerup", finishDrag);
  handle.addEventListener("pointercancel", finishDrag);
  window.addEventListener("resize", () => {
    const position = applyFloatingPosition(panel, getPosition(), save, { persist: true });
    setPosition(position);
  });
  const position = applyFloatingPosition(panel, getPosition(), save);
  setPosition(position);
}

function bindTreeDrag() {
  bindFloatingPanelDrag({
    panel: els.treePanel,
    handle: els.treeHeader,
    getPosition: () => state.treePosition,
    setPosition: (position) => { state.treePosition = position; },
    save: saveTreePosition,
  });
}

function bindViewsDrag() {
  bindFloatingPanelDrag({
    panel: els.viewPanel,
    handle: els.viewHeader,
    getPosition: () => state.viewsPosition,
    setPosition: (position) => { state.viewsPosition = position; },
    save: saveViewsPosition,
  });
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

function fallbackTree(listing) {
  const grouped = new Map();
  for (const part of listing?.parts || []) {
    const groupId = part.group || "ungrouped";
    if (!grouped.has(groupId)) {
      const group = listing.groups?.find((item) => item.id === groupId);
      grouped.set(groupId, {
        id: groupId,
        kind: "folder",
        groupId,
        name: group?.name || groupId,
        children: [],
      });
    }
    grouped.get(groupId).children.push({
      id: `part:${part.id}`,
      kind: "part",
      partId: part.id,
      name: part.name || part.id,
    });
  }
  return [...grouped.values()];
}

function treeRoots(listing = state.listing) {
  return Array.isArray(listing?.tree) && listing.tree.length
    ? listing.tree
    : fallbackTree(listing);
}

function visibleTreeRoots(listing = state.listing) {
  const allowed = new Set((listing?.parts || []).map((part) => part.id));
  const prune = (node) => {
    if (node.partId && !allowed.has(node.partId)) return null;
    const children = Array.isArray(node.children)
      ? node.children.map(prune).filter(Boolean)
      : [];
    if (!node.partId && node.kind !== "call" && !children.length) return null;
    return { ...node, children };
  };
  return treeRoots(listing).map(prune).filter(Boolean);
}

function treePartIds(node, ids = new Set()) {
  if (node?.partId && state.listing?.parts?.some((part) => part.id === node.partId)) {
    ids.add(node.partId);
  }
  for (const child of node?.children || []) treePartIds(child, ids);
  return ids;
}

function treePartNodes(node, result = []) {
  if (node?.partId && state.listing?.parts?.some((part) => part.id === node.partId)) {
    result.push(node);
  }
  for (const child of node?.children || []) treePartNodes(child, result);
  return result;
}

function allTreePartNodes() {
  return visibleTreeRoots().flatMap((node) => treePartNodes(node));
}

function findTreePartNode(partId) {
  return allTreePartNodes().find((node) => node.partId === partId) || null;
}

function nodeExclusiveGroups(node) {
  return Array.isArray(node?.exclusiveGroups) ? node.exclusiveGroups : [];
}

function groupVisibility(node) {
  const ids = [...treePartIds(node)];
  const visibleCount = ids.filter((id) => state.visibleIds.has(id)).length;
  if (visibleCount === 0) return "off";
  if (visibleCount === ids.length) return "on";
  return "mixed";
}

function preferredPartIds(node) {
  const nodes = treePartNodes(node);
  const selected = new Set([...treePartIds(node)]);
  const byExclusiveGroup = new Map();
  for (const child of nodes) {
    for (const group of nodeExclusiveGroups(child)) {
      if (!byExclusiveGroup.has(group)) byExclusiveGroup.set(group, []);
      byExclusiveGroup.get(group).push(child);
    }
  }
  for (const candidates of byExclusiveGroup.values()) {
    if (candidates.length < 2) continue;
    const winner = candidates.find((candidate) => candidate.displayMode === "assembly")
      || candidates[0];
    for (const candidate of candidates) {
      if (candidate !== winner) selected.delete(candidate.partId);
    }
  }
  return selected;
}

function preferredVisiblePartIds() {
  const selected = new Set();
  for (const node of visibleTreeRoots()) {
    for (const partId of preferredPartIds(node)) selected.add(partId);
  }
  return selected;
}

async function setTreeNodeVisible(node, visible) {
  const ids = [...treePartIds(node)];
  const selected = visible ? preferredPartIds(node) : new Set();
  for (const id of ids) {
    if (selected.has(id)) {
      state.visibleIds.add(id);
    } else {
      state.visibleIds.delete(id);
      const item = state.items.get(id);
      if (item?.mesh) item.mesh.visible = false;
    }
  }
  await Promise.all([...selected].map(async (id) => {
    const item = state.items.get(id);
    if (!item) return;
    await loadPart(item);
    if (item.mesh) item.mesh.visible = true;
  }));
  renderPartList();
  applyExplode();
}

async function setGroupVisible(groupId, visible) {
  const node = visibleTreeRoots().find((item) => item.id === groupId);
  if (node) await setTreeNodeVisible(node, visible);
}

function toggleTreeNode(nodeId) {
  if (state.collapsedGroups.has(nodeId)) state.collapsedGroups.delete(nodeId);
  else state.collapsedGroups.add(nodeId);
  saveCollapsedGroups();
  renderPartList();
}

function makeDisclosure(node, collapsed, label) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "node-disclosure";
  button.textContent = collapsed ? "›" : "⌄";
  button.setAttribute("aria-expanded", String(!collapsed));
  button.setAttribute("aria-label", `${collapsed ? "展开" : "折叠"}${label}`);
  button.title = collapsed ? "展开" : "折叠";
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleTreeNode(node.id);
  });
  return button;
}

function makePartLine(part) {
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
  return line;
}

function renderTreePartNode(node) {
  const part = state.listing?.parts?.find((item) => item.id === node.partId);
  if (!part) return null;
  const wrapper = document.createElement("div");
  wrapper.className = "tree-part-node";
  const children = node.children || [];
  const collapsed = children.length > 0 && state.collapsedGroups.has(node.id);
  const row = document.createElement("div");
  row.className = "tree-part-row";
  row.append(
    children.length
      ? makeDisclosure(node, collapsed, part.name || part.id)
      : Object.assign(document.createElement("span"), { className: "node-spacer" }),
    makePartLine(part),
  );
  wrapper.appendChild(row);
  if (children.length) {
    const childBox = document.createElement("div");
    childBox.className = "tree-children";
    childBox.hidden = collapsed;
    for (const child of children) {
      const rendered = renderTreeChild(child);
      if (rendered) childBox.appendChild(rendered);
    }
    wrapper.appendChild(childBox);
  }
  return wrapper;
}

function renderTreeInfoNode(node) {
  const wrapper = document.createElement("div");
  wrapper.className = "tree-info-node";
  const children = node.children || [];
  const collapsed = children.length > 0 && state.collapsedGroups.has(node.id);
  const row = document.createElement("div");
  row.className = "tree-info-row";
  row.append(
    children.length
      ? makeDisclosure(node, collapsed, node.name || "调用节点")
      : Object.assign(document.createElement("span"), { className: "node-spacer" }),
  );
  const title = document.createElement("span");
  title.className = "tree-info-name";
  title.textContent = node.name || node.id;
  title.title = node.description || node.id;
  row.appendChild(title);
  if (node.kind === "call") {
    const kind = document.createElement("span");
    kind.className = "tree-info-kind";
    kind.textContent = "内含";
    row.appendChild(kind);
  }
  wrapper.appendChild(row);
  if (children.length) {
    const childBox = document.createElement("div");
    childBox.className = "tree-children";
    childBox.hidden = collapsed;
    for (const child of children) {
      const rendered = renderTreeChild(child);
      if (rendered) childBox.appendChild(rendered);
    }
    wrapper.appendChild(childBox);
  }
  return wrapper;
}

function renderTreeChild(node) {
  return node?.partId ? renderTreePartNode(node) : renderTreeInfoNode(node);
}

function renderTreeFolder(node) {
  const section = document.createElement("section");
  section.className = "group tree-folder-node";
  const collapsed = state.collapsedGroups.has(node.id);
  section.classList.toggle("collapsed", collapsed);
  const heading = document.createElement("h2");
  const label = node.name || node.id;
  const visibility = groupVisibility(node);
  const visibilityToggle = document.createElement("button");
  visibilityToggle.type = "button";
  visibilityToggle.className = "group-visibility";
  visibilityToggle.dataset.state = visibility;
  visibilityToggle.setAttribute("aria-pressed", String(visibility === "on"));
  visibilityToggle.setAttribute("aria-label", visibility === "on" ? `隐藏${label}` : `显示${label}`);
  visibilityToggle.title = visibility === "on" ? "隐藏本组" : "显示本组";
  visibilityToggle.textContent = visibility === "on" ? "●" : visibility === "mixed" ? "◐" : "○";
  visibilityToggle.addEventListener("click", (event) => {
    event.stopPropagation();
    void setTreeNodeVisible(node, visibility !== "on");
  });
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "group-toggle";
  toggle.setAttribute("aria-expanded", String(!collapsed));
  toggle.setAttribute("aria-label", `${label} (${treePartIds(node).size})`);
  const chevron = document.createElement("span");
  chevron.className = "chevron";
  chevron.textContent = collapsed ? "›" : "⌄";
  const name = document.createElement("span");
  name.className = "name";
  name.textContent = label;
  const count = document.createElement("span");
  count.textContent = String(treePartIds(node).size);
  toggle.append(chevron, name, count);
  toggle.addEventListener("click", () => toggleTreeNode(node.id));
  heading.append(visibilityToggle, toggle);
  section.appendChild(heading);
  const children = document.createElement("div");
  children.className = "group-items tree-children";
  children.hidden = collapsed;
  for (const child of node.children || []) {
    const rendered = renderTreeChild(child);
    if (rendered) children.appendChild(rendered);
  }
  section.appendChild(children);
  return section;
}

function renderPartList() {
  els.parts.innerHTML = "";
  if (!state.listing) return;
  for (const node of visibleTreeRoots()) {
    const rendered = node.kind === "folder" || node.groupId
      ? renderTreeFolder(node)
      : renderTreeChild(node);
    if (rendered) els.parts.appendChild(rendered);
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
  // 早期蛇形链条 STL 以 X=宽、Y=深、Z=高导出。把这批旧坐标整体旋转到
  // 当前世界：X=宽、Y=高、Z=深；离合/滑台 STL 已经使用当前世界坐标，直接
  // 挂在 scene 下。这样相机、轨道控制和右上角轴向都只面对一个世界。
  const legacyRoot = new THREE.Group();
  legacyRoot.name = "legacy-coordinate-adapter";
  legacyRoot.rotation.x = -Math.PI / 2;
  scene.add(legacyRoot);
  const legacyTensionerRoot = new THREE.Group();
  legacyTensionerRoot.name = "legacy-tensioner-coordinate-adapter";
  // The detailed slide STL predates the canonical SCAD frame: old X=width,
  // Y=depth (rear +Y), Z=height, with the tensioner on old high-X. Mirror X
  // as well while bringing it into the current X=width, Y=height, Z=depth
  // world, so the detailed reference lands on the current low-X rear side.
  legacyTensionerRoot.position.x = LEGACY_ASSEMBLY_WIDTH;
  legacyTensionerRoot.scale.x = -1;
  legacyTensionerRoot.rotation.x = -Math.PI / 2;
  scene.add(legacyTensionerRoot);
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 4000);
  camera.up.set(0, 1, 0);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  // OrbitControls 的默认滚轮倍率在已经放大的 STL 上会显得过慢；提高倍率并
  // 让缩放围绕光标位置进行，便于直接钻进拨叉、销槽和轴承座检查。
  controls.zoomSpeed = 2.4;
  controls.zoomToCursor = true;
  scene.add(new THREE.AmbientLight(0xffffff, 0.7));
  const key = new THREE.DirectionalLight(0xffffff, 1.1);
  key.position.set(40, -80, 60);
  scene.add(key);
  scene.add(new THREE.HemisphereLight(0xbfdcff, 0x111a20, 0.45));
  // 参考 SelfJackDemountableCamper：ViewHelper 固定在视口右上角，点击轴端
  // 快速切换正交视角。此处直接使用当前世界轴：X 红、Y 绿、Z 蓝。
  const viewHelper = new ViewHelper(camera, canvas);
  viewHelper.location.top = 16;
  viewHelper.location.right = 16;
  viewHelper.setLabels("X", "Y", "Z");
  remapViewHelperWorldColors(viewHelper);
  // ViewHelper is drawn into the canvas' upper-right viewport instead of a
  // DOM element. OrbitControls would otherwise receive the same pointerdown
  // first, call setPointerCapture() on the canvas, and begin a camera drag
  // before the helper's later click handler can decide whether the axis was
  // hit. Reserve only the helper viewport during pointerdown so the rest of
  // the canvas keeps the normal orbit/pan/zoom behavior.
  const isViewHelperPointer = (event) => {
    const rect = canvas.getBoundingClientRect();
    const left = viewHelper.location.left !== null
      ? rect.left + viewHelper.location.left
      : rect.left + canvas.offsetWidth - VIEW_HELPER_SIZE - viewHelper.location.right;
    const top = viewHelper.location.top !== null
      ? rect.top + viewHelper.location.top
      : rect.top + canvas.offsetHeight - VIEW_HELPER_SIZE - viewHelper.location.bottom;
    return event.clientX >= left
      && event.clientX <= left + VIEW_HELPER_SIZE
      && event.clientY >= top
      && event.clientY <= top + VIEW_HELPER_SIZE;
  };
  const onViewHelperPointerDown = (event) => {
    if (!isViewHelperPointer(event)) return;
    event.stopImmediatePropagation();
  };
  const onViewHelperClick = (event) => {
    if (viewHelper.handleClick(event)) {
      event.stopImmediatePropagation();
    }
  };
  canvas.addEventListener("pointerdown", onViewHelperPointerDown, true);
  canvas.addEventListener("click", onViewHelperClick, true);
  state.scene = scene;
  state.legacyRoot = legacyRoot;
  state.legacyTensionerRoot = legacyTensionerRoot;
  state.camera = camera;
  state.controls = controls;
  state.viewHelper = viewHelper;
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
    viewHelper.center.copy(controls.target);
    if (viewHelper.animating) viewHelper.update(dt);
    renderer.render(scene, camera);
    const previousClear = {
      autoClear: renderer.autoClear,
      autoClearColor: renderer.autoClearColor,
      autoClearDepth: renderer.autoClearDepth,
    };
    try {
      renderer.autoClear = false;
      renderer.autoClearColor = false;
      renderer.autoClearDepth = false;
      viewHelper.render(renderer);
    } finally {
      renderer.autoClear = previousClear.autoClear;
      renderer.autoClearColor = previousClear.autoClearColor;
      renderer.autoClearDepth = previousClear.autoClearDepth;
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function remapViewHelperWorldColors(viewHelper) {
  // ViewHelper 的 children 顺序为 X/Y/Z 轴，再后面是 X/Y/Z 标签。
  const [xAxis, yAxis, zAxis] = viewHelper.children;
  xAxis?.material?.color?.set?.("#ff4466");
  yAxis?.material?.color?.set?.("#88ff44");
  zAxis?.material?.color?.set?.("#4488ff");
  repaintViewHelperLabel(viewHelper.children[3], "#ff4466", "X");
  repaintViewHelperLabel(viewHelper.children[4], "#88ff44", "Y");
  repaintViewHelperLabel(viewHelper.children[5], "#4488ff", "Z");
}

function repaintViewHelperLabel(sprite, color, label) {
  const canvas = sprite?.material?.map?.image;
  const context = canvas?.getContext?.("2d");
  if (!context) return;
  const width = canvas.width || 64;
  const height = canvas.height || 64;
  context.clearRect(0, 0, width, height);
  context.beginPath();
  context.arc(width / 2, height / 2, (14 / 64) * width, 0, 2 * Math.PI);
  context.closePath();
  context.fillStyle = color;
  context.fill();
  context.font = "24px Arial";
  context.textAlign = "center";
  context.fillStyle = "#000000";
  context.fillText(label, width / 2, 41);
  sprite.material.map.needsUpdate = true;
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
  if (response.ok) {
    const listing = await response.json();
    // The preview API intentionally returns only the filtered part list. Read
    // the full manifest as well so the nested call tree remains available
    // while search/group filters are active.
    try {
      const manifestResponse = await fetch("./manifest.json", { cache: "no-cache" });
      if (manifestResponse.ok) {
        const manifest = await manifestResponse.json();
        listing.tree = manifest.tree;
        listing.treeVersion = manifest.treeVersion;
      }
    } catch {
      // The flat API result is still usable through the fallback tree.
    }
    return listing;
  }
  const fallback = await fetch("./manifest.json", { cache: "no-cache" });
  if (!fallback.ok) throw new Error(`零件清单 ${response.status}`);
  const manifest = await fallback.json();
  const allParts = manifest.parts || [];
  const queryValue = query.toLowerCase();
  const parts = allParts.filter((part) => {
    const haystack = [part.id, part.name, part.file, part.group, part.role]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return (!queryValue || haystack.includes(queryValue))
      && (!group || part.group === group)
      && (!role || part.role === role);
  });
  return {
    ...manifest,
    parts,
    totalCount: allParts.length,
    count: parts.length,
  };
}

async function refreshListing({ autoload = false } = {}) {
  const listing = await fetchListing();
  state.listing = listing;
  state.units = listing.units || "mm";
  syncCabinetTransparencyControls();
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
    // 全局默认视图要能直接看到完整动画；柜体/背板由清单中的 visible=false
    // 排除，用户仍可通过清单勾选它们来恢复背景。
    const targets = (listing.parts || [])
      .filter(isDefaultVisiblePart)
      .sort((a, b) => (a.bytes || 0) - (b.bytes || 0));
    await Promise.all(targets.map((part) => setPartVisible(part.id, true)));
    fitCamera();
  }
}

function exclusivePeerIds(partId) {
  const node = findTreePartNode(partId);
  const groups = new Set(nodeExclusiveGroups(node));
  if (!groups.size) return [];
  return allTreePartNodes()
    .filter((candidate) => candidate.partId !== partId)
    .filter((candidate) => nodeExclusiveGroups(candidate).some((group) => groups.has(group)))
    .map((candidate) => candidate.partId);
}

async function setPartVisible(partId, visible, { enforceExclusivity = true } = {}) {
  const item = state.items.get(partId);
  if (!item) return;
  if (visible) {
    if (enforceExclusivity) {
      for (const peerId of exclusivePeerIds(partId)) {
        state.visibleIds.delete(peerId);
        const peer = state.items.get(peerId);
        if (peer?.mesh) peer.mesh.visible = false;
      }
    }
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
  if (!visible) {
    await Promise.all(parts.map((part) => setPartVisible(part.id, false)));
    return;
  }
  const selected = preferredVisiblePartIds();
  // The filtered listing is a view of the full manifest. Hide already-loaded
  // items that are outside that view as well; otherwise a static preview can
  // report 12 filtered parts while still rendering the previous 40 meshes.
  for (const item of state.items.values()) {
    if (selected.has(item.part.id)) continue;
    state.visibleIds.delete(item.part.id);
    if (item?.mesh) item.mesh.visible = false;
  }
  await Promise.all([...selected].map(async (partId) => {
    const item = state.items.get(partId);
    if (!item) return;
    state.visibleIds.add(partId);
    await loadPart(item);
    if (item.mesh) item.mesh.visible = true;
  }));
  renderPartList();
  applyExplode();
  fitCamera();
}

function partTail(part) {
  return String(part?.id || "").split("/").pop().toLowerCase();
}

function usesLegacyCoordinates(part) {
  return part?.coordinateFrame === "legacy-tensioner"
    || LEGACY_COORDINATE_GROUPS.has(part?.group)
    || String(part?.id || "").startsWith("cabinet/");
}

function coordinateParent(part) {
  if (part?.coordinateFrame === "legacy-tensioner") {
    return state.legacyTensionerRoot || state.scene;
  }
  return usesLegacyCoordinates(part)
    ? (state.legacyRoot || state.scene)
    : state.scene;
}

function isCabinetContext(part) {
  if (DEFAULT_HIDDEN_PART_IDS.has(part?.id)) return false;
  return part?.id === "cabinet-clutch/cabinet_clutch_cabinet_frame";
}

function isCabinetFramePart(part) {
  return part?.id === "cabinet-clutch/cabinet_clutch_cabinet_frame";
}

function isCabinetPartitionPart(part) {
  return part?.id === "cabinet-clutch/cabinet_clutch_partition";
}

function defaultCabinetTransparency(partId) {
  const control = CABINET_CONTROL_BY_PART_ID.get(partId);
  if (!control) return 0;
  const part = state.listing?.parts?.find((item) => item.id === partId);
  const opacity = part ? rawPartOpacity(part) : control.fallbackOpacity;
  return clampCabinetTransparency((1 - opacity) * 100);
}

function cabinetTransparencyForPart(part) {
  const configured = state.cabinetTransparency.get(part?.id);
  return Number.isFinite(configured)
    ? clampCabinetTransparency(configured)
    : defaultCabinetTransparency(part?.id);
}

function cabinetOpacityForPart(part) {
  return 1 - cabinetTransparencyForPart(part) / 100;
}

function syncCabinetTransparencyControls() {
  for (const control of CABINET_TRANSPARENCY_CONTROLS) {
    const value = cabinetTransparencyForPart({ id: control.partId });
    const input = document.getElementById(control.inputId);
    const output = document.getElementById(control.outputId);
    if (input) input.value = String(value);
    if (output) output.textContent = `${value}%`;
  }
}

function setCabinetTransparency(partId, value) {
  if (!CABINET_CONTROL_BY_PART_ID.has(partId)) return;
  state.cabinetTransparency.set(partId, clampCabinetTransparency(value));
  saveCabinetTransparency();
  syncCabinetTransparencyControls();
  applyCabinetTransparency();
}

function resetCabinetTransparency() {
  state.cabinetTransparency.clear();
  saveCabinetTransparency();
  syncCabinetTransparencyControls();
  applyCabinetTransparency();
}

function isDefaultVisiblePart(part) {
  return part?.visible !== false && !DEFAULT_HIDDEN_PART_IDS.has(part?.id);
}

function isSnakePart(part) {
  return part?.group === "cabinet-chain"
    && part?.id !== LEGACY_MOTOR_TENSIONER_ID
    && !LEGACY_SCHEME1_TAILS.has(partTail(part));
}

function isNativeClutchPart(part) {
  return part?.group === "cabinet-clutch"
    || String(part?.id || "").startsWith("cabinet-clutch/");
}

function isDrawerDrivePart(part) {
  return isNativeClutchPart(part) && DRAWER_DRIVE_TAILS.has(partTail(part));
}

function isUpperTensionerPart(part) {
  return isNativeClutchPart(part) && UPPER_TENSIONER_TAILS.has(partTail(part));
}

function isLowerTensionerPart(part) {
  return part?.group === "cabinet-chain"
    && part?.id !== LEGACY_MOTOR_TENSIONER_ID
    && !LEGACY_SCHEME1_TAILS.has(partTail(part));
}

function isCenterClutchPart(part) {
  return CENTER_CLUTCH_FOCUS_IDS.has(part?.id);
}

function isCenterClutchContext(part) {
  return CENTER_CLUTCH_CONTEXT_IDS.has(part?.id);
}

function isCenterClutchFramePart(part) {
  return CENTER_CLUTCH_FRAME_IDS.has(part?.id);
}

const VIEW_PROFILES = {
  snake: {
    focus: isSnakePart,
    context: isCabinetContext,
  },
  "drawer-drive": {
    focus: isDrawerDrivePart,
    context: isCabinetContext,
  },
  "upper-tensioner": {
    focus: isUpperTensionerPart,
    context: isCabinetContext,
  },
  "lower-tensioner": {
    focus: isLowerTensionerPart,
    context: isCabinetContext,
  },
  "center-clutch": {
    focus: isCenterClutchPart,
    context: isCenterClutchContext,
    frame: isCenterClutchFramePart,
  },
  "cabinet-frame": {
    focus: isCabinetFramePart,
  },
  "cabinet-partition": {
    focus: isCabinetPartitionPart,
  },
};

function updateActiveViewButton() {
  for (const button of els.viewButtons) {
    const active = button.dataset.view === state.activeView;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  }
}

function setObjectOpacity(root, opacity) {
  const animatedBelt = root?.userData?.animatedBelt === true;
  // Animated belts stay opaque in the normal assembly, but a belt loaded as
  // low-opacity focus context must not hide the clutch interface that is being
  // inspected. The animation code only updates vertices; it does not require
  // an opaque material, so let the view profile decide here.
  const targetOpacity = animatedBelt && opacity >= 0.999 ? 1 : opacity;
  root?.traverse?.((object) => {
    if (!object.isMesh) return;
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    for (const material of materials) {
      if (!material) continue;
      // Double-sidedness is configured when the belt is built; it must not be
      // used as a reason to bypass the depth buffer. Context belts are
      // translucent with depth writing off, so the real clutch remains legible.
      material.transparent = targetOpacity < 0.999;
      material.opacity = targetOpacity;
      material.depthWrite = targetOpacity >= 0.999;
      material.depthTest = true;
      material.needsUpdate = true;
    }
  });
}

function applyCabinetTransparency() {
  const profile = state.viewProfile ? VIEW_PROFILES[state.viewProfile] : null;
  for (const item of state.items.values()) {
    if (!item.mesh || !isCabinetContext(item.part)) continue;
    const baseOpacity = cabinetOpacityForPart(item.part);
    const opacity = profile?.context?.(item.part)
      ? Math.min(0.08, baseOpacity)
      : baseOpacity;
    setObjectOpacity(item.mesh, opacity);
  }
}

function viewBox(ids = null) {
  if (!state.scene) return null;
  state.scene.updateMatrixWorld(true);
  const box = new THREE.Box3();
  let has = false;
  for (const item of state.items.values()) {
    if (!item.mesh || !item.mesh.visible) continue;
    if (ids && !ids.has(item.part.id)) continue;
    box.expandByObject(item.mesh);
    has = true;
  }
  return has ? box : null;
}

function frameBox(box, viewName) {
  if (!box || !state.camera || !state.controls) return;
  const view = CAMERA_VIEWS[viewName] || CAMERA_VIEWS.rear;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const direction = new THREE.Vector3(...view.direction).normalize();
  const up = new THREE.Vector3(...view.up).normalize();
  const aspect = Math.max(0.25, state.camera.aspect || 1);
  const vertical = Math.max(size.y, 1);
  const horizontal = Math.max(size.x, size.z, 1) / aspect;
  const span = Math.max(vertical, horizontal, 1);
  const fov = THREE.MathUtils.degToRad(state.camera.fov);
  const distance = Math.max(2, (span * 1.28) / (2 * Math.tan(fov / 2)));
  state.controls.target.copy(center);
  state.camera.up.copy(up);
  state.camera.position.copy(center).addScaledVector(direction, distance);
  state.camera.near = Math.max(0.01, distance / 100);
  state.camera.far = Math.max(500, distance * 40);
  state.camera.lookAt(center);
  state.camera.updateProjectionMatrix();
  state.controls.update();
}

async function applyViewVisibility(focusIds, contextIds, request, restorePartOpacity = false) {
  const desiredIds = new Set([...focusIds, ...contextIds]);
  state.visibleIds.clear();
  for (const item of state.items.values()) {
    if (item.mesh) item.mesh.visible = false;
  }
  for (const id of desiredIds) state.visibleIds.add(id);

  const targets = [...state.items.values()].filter((item) => desiredIds.has(item.part.id));
  await Promise.all(targets.map(async (item) => {
    await loadPart(item);
    if (request !== state.viewRequest) return;
    if (item.mesh) item.mesh.visible = true;
  }));
  if (request !== state.viewRequest) return false;

  for (const item of targets) {
    if (!item.mesh) continue;
    const opacity = restorePartOpacity
      ? partOpacity(item.part)
      : focusIds.has(item.part.id)
        ? 1
        : Math.min(0.08, partOpacity(item.part));
    setObjectOpacity(item.mesh, opacity);
  }
  applyExplode();
  renderPartList();
  return true;
}

async function applyViewPreset(name) {
  const viewName = CAMERA_VIEWS[name] ? name : "rear";
  const request = ++state.viewRequest;
  state.activeView = viewName;
  updateActiveViewButton();
  if (viewName === "center-clutch") focusCenterClutch();

  const listingParts = state.listing?.parts || [];
  const profile = VIEW_PROFILES[viewName];
  let focusIds = new Set();
  let contextIds = new Set();
  if (profile) {
    for (const part of listingParts) {
      if (profile.focus(part)) focusIds.add(part.id);
      else if (profile.context(part)) contextIds.add(part.id);
    }
    // 当前清单被搜索过滤时，特写也必须保证有可取景对象；空特写回到该清单
    // 的默认可见件，避免相机被送到原点。
    if (!focusIds.size) {
      focusIds = new Set(listingParts.filter(isDefaultVisiblePart).map((part) => part.id));
      contextIds = new Set();
    }
  } else {
    focusIds = new Set(listingParts.filter(isDefaultVisiblePart).map((part) => part.id));
  }

  const applied = await applyViewVisibility(focusIds, contextIds, request, !profile);
  if (!applied || request !== state.viewRequest) return;
  state.viewProfile = profile ? viewName : null;
  const frameIds = profile?.frame
    ? new Set(listingParts.filter(profile.frame).map((part) => part.id))
    : focusIds;
  const focusBox = profile ? viewBox(frameIds.size ? frameIds : focusIds) : null;
  frameBox(focusBox || viewBox(), viewName);
  if (viewName === "center-clutch") placeCenterClutchViewPanel();
}
//#endregion

//#region 视图层
function bindPreviewControls() {
  els.explodeRange.addEventListener("input", () => {
    state.explode = Number(els.explodeRange.value) / 100;
    applyExplode();
  });
  for (const control of CABINET_TRANSPARENCY_CONTROLS) {
    const input = document.getElementById(control.inputId);
    input?.addEventListener("input", () => {
      setCabinetTransparency(control.partId, input.value);
    });
  }
  els.cabinetTransparencyReset?.addEventListener("click", resetCabinetTransparency);
  syncCabinetTransparencyControls();
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
  els.viewsToggle?.addEventListener("click", () => {
    state.viewsCollapsed = !state.viewsCollapsed;
    saveViewsCollapsed();
    applyViewsCollapsed();
  });
  for (const button of els.viewButtons) {
    button.addEventListener("click", () => {
      void applyViewPreset(button.dataset.view);
    });
  }
  els.centerClutchDemo?.addEventListener("click", async () => {
    // A demo request is also a request for the center first-article view. If
    // the user is currently looking at the full snake structure, starting the
    // hidden center animation only changes a status label and appears broken.
    await applyViewPreset("center-clutch");
    playCenterClutchDemo();
  });
  els.treeCollapse?.addEventListener("click", () => {
    state.treeCollapsed = !state.treeCollapsed;
    saveTreeCollapsed();
    applyTreeCollapsed();
  });
  bindTreeDrag();
  bindViewsDrag();
  applyTreeCollapsed();
  applyViewsCollapsed();
  updateActiveViewButton();
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
  const amount = state.explode;
  for (const item of state.items.values()) {
    if (!item.mesh) continue;
    item.mesh.position.copy(item.base).addScaledVector(item.explosion, amount);
  }
  els.explodeRange.value = String(Math.round(amount * 100));
  els.explodeOut.textContent = String(Math.round(amount * 100));
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
    const parent = coordinateParent(item.part);
    const instances = Array.isArray(item.part.instances) && item.part.instances.length
      ? item.part.instances
      : null;
    if (instances) {
      // A manifest instance is a placement reference, not a copied STL. Keep
      // one BufferGeometry/material source and create lightweight Three.js
      // mesh nodes at the authored world datums. This is the CAD equivalent
      // of new DrawerStation() for every non-center cell.
      const group = new THREE.Group();
      group.name = `stl-template-instances:${item.part.id}`;
      for (const instance of instances) {
        const mesh = new THREE.Mesh(geometry, material);
        const position = Array.isArray(instance.position)
          ? instance.position
          : [0, 0, 0];
        const rotation = Array.isArray(instance.rotation)
          ? instance.rotation
          : [0, 0, 0];
        const scale = Array.isArray(instance.scale)
          ? instance.scale
          : [1, 1, 1];
        mesh.position.set(
          Number(position[0]) || 0,
          Number(position[1]) || 0,
          Number(position[2]) || 0,
        );
        mesh.rotation.set(
          Number(rotation[0]) || 0,
          Number(rotation[1]) || 0,
          Number(rotation[2]) || 0,
        );
        mesh.scale.set(
          Number(scale[0]) || 1,
          Number(scale[1]) || 1,
          Number(scale[2]) || 1,
        );
        mesh.userData.instanceId = instance.id || "";
        group.add(mesh);
      }
      group.visible = state.visibleIds.has(item.part.id);
      parent.add(group);
      item.mesh = group;
      group.updateMatrixWorld(true);
      item.box = new THREE.Box3().setFromObject(group);
    } else {
      const mesh = new THREE.Mesh(geometry, material);
      mesh.visible = state.visibleIds.has(item.part.id);
      parent.add(mesh);
      item.mesh = mesh;
      item.box = geometry.boundingBox.clone();
    }
    try {
      await onPartLoaded(item);
    } catch (playError) {
      console.error("chain play bind failed", item.part?.id, playError);
    }
    if (isCabinetContext(item.part)) applyCabinetTransparency();
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
  if (isCabinetContext(part)) return cabinetOpacityForPart(part);
  return rawPartOpacity(part);
}

function rawPartOpacity(part) {
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
  frameBox(viewBox(), state.activeView || "rear");
}

async function loadGeometry(url) {
  const loader = new STLLoader();
  return new Promise((resolve, reject) => {
    loader.load(url, resolve, undefined, reject);
  });
}
//#endregion
