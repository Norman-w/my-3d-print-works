import { AssemblyScene } from "./assembly-scene.mjs";
import { installFloatingPanels } from "./floating-panels.mjs";

const $ = (selector) => document.querySelector(selector);
const clamp = (value, minimum, maximum) => Math.min(Math.max(value, minimum), maximum);
const button = (label, action, className = "") => {
  const element = document.createElement("button");
  element.type = "button";
  element.textContent = label;
  element.className = className;
  element.addEventListener("click", action);
  return element;
};

const DEFAULT_INSTRUCTIONS = [
  "拖动模型：等轴旋转；滚轮：缩放。",
  "顶部 Tab 只切换风机接口方案；相机、爆炸比例、全局透明度、搜索和面板布局属于公共状态。",
];

async function readJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

function finiteVector(value) {
  return Array.isArray(value) && value.length === 3 && value.every(Number.isFinite);
}

async function main() {
  if (location.protocol === "file:") {
    throw new Error("请从 HTTP 服务打开预览，不要用 file://");
  }

  const rootManifest = await readJson("./manifest.json");
  const catalog = rootManifest.variantCatalog || {
    defaultId: "default",
    variants: [{ id: "default", label: rootManifest.title || "装配方案", manifest: "./manifest.json" }],
  };
  if (!Array.isArray(catalog.variants) || !catalog.variants.length) {
    throw new Error("variantCatalog.variants 不能为空");
  }
  const variants = new Map();
  for (const entry of catalog.variants) {
    if (!entry?.id || variants.has(entry.id)) throw new Error(`重复的风机方案 ID: ${entry?.id}`);
    variants.set(entry.id, {
      id: entry.id,
      label: entry.label || entry.id,
      manifest: entry.manifest || "./manifest.json",
    });
  }
  const defaultVariantId = variants.has(catalog.defaultId)
    ? catalog.defaultId : variants.keys().next().value;
  const requestedVariantId = location.hash.slice(1) ||
    new URL(location.href).searchParams.get("variant");
  const initialVariantId = variants.has(requestedVariantId)
    ? requestedVariantId : defaultVariantId;
  const manifestCache = new Map([["./manifest.json", rootManifest]]);

  installFloatingPanels($("#canvas-panel"), {
    persist: rootManifest.ui?.persistPanelState === true,
  });

  const stateKey = `scad-assembly-web-preview:shared-state:${location.pathname}`;
  let persisted = {};
  try { persisted = JSON.parse(localStorage.getItem(stateKey) || "{}"); }
  catch { persisted = {}; }
  const persistedCommon = persisted.common || {};
  const common = {
    search: typeof persistedCommon.search === "string" ? persistedCommon.search : "",
    group: typeof persistedCommon.group === "string" ? persistedCommon.group : "",
    explosion: Number.isFinite(persistedCommon.explosion)
      ? clamp(persistedCommon.explosion, 0, 1) : 0,
    globalOpacity: Number.isFinite(persistedCommon.globalOpacity)
      ? clamp(persistedCommon.globalOpacity, 0, 1) : 1,
    camera: persistedCommon.camera && finiteVector(persistedCommon.camera.direction)
      ? {
        direction: persistedCommon.camera.direction,
        zoom: Number.isFinite(persistedCommon.camera.zoom)
          ? clamp(persistedCommon.camera.zoom, 0.2, 8) : 1,
      } : null,
  };
  const variantState = persisted.variants && typeof persisted.variants === "object"
    ? persisted.variants : {};

  const canvas = $("#viewport");
  const status = (message) => { $("#status").textContent = message; };
  const groupSelect = $("#group-filter");
  const stageSelect = $("#stage");
  const tabContainer = $("#variant-tabs");
  let runtime = null;
  let activeManifest = null;
  let activeVariantId = null;
  let activeFocusIds = null;
  let activeDirection = [1, 0.75, 1];
  let selectedId = null;
  let switchToken = 0;

  const resizeViewport = () => {
    if (!runtime) return;
    runtime.resize(
      Math.max(1, canvas.clientWidth),
      Math.max(1, canvas.clientHeight),
    );
  };
  if (typeof ResizeObserver === "function") {
    new ResizeObserver(resizeViewport).observe(canvas);
  }
  window.addEventListener("resize", resizeViewport);

  const saveState = () => {
    try {
      localStorage.setItem(stateKey, JSON.stringify({ common, variants: variantState }));
    } catch { /* Storage may be disabled; in-page state still works. */ }
  };

  const captureCommonState = () => {
    common.search = $("#search").value;
    common.group = groupSelect.value;
    common.explosion = Number($("#explode").value) / 100;
    common.globalOpacity = Number($("#global-opacity").value) / 100;
    if (runtime) {
      const offset = runtime.camera.position.clone().sub(runtime.controls.target);
      const distance = offset.length();
      const fit = runtime.fitDistance();
      if (distance > 0 && fit) {
        common.camera = {
          direction: offset.normalize().toArray(),
          zoom: clamp(distance / fit, 0.2, 8),
        };
      }
    }
    if (activeVariantId) {
      variantState[activeVariantId] = {
        ...(variantState[activeVariantId] || {}),
        stage: stageSelect.value || undefined,
        travel: runtime?.motionValues[activeManifest?.screwMotion?.frameId],
        nozzle: $("#nozzle").value || undefined,
      };
    }
    saveState();
  };

  const renderTabs = (busy = false) => {
    tabContainer.replaceChildren();
    for (const entry of variants.values()) {
      const tab = button(entry.label, () => switchVariant(entry.id), "variant-tab");
      tab.dataset.variantId = entry.id;
      tab.setAttribute("aria-selected", String(entry.id === activeVariantId));
      tab.setAttribute("aria-busy", String(busy));
      tab.disabled = busy;
      tabContainer.append(tab);
    }
  };

  const updateScrewReadout = () => {
    if (!runtime || !activeManifest?.screwMotion) return;
    const screw = activeManifest.screwMotion;
    const value = runtime.motionValues[screw.frameId] ?? 0;
    $("#travel").value = String(value);
    $("#travel-value").textContent = `${value.toFixed(2)} / ${screw.travelMm} mm`;
    $("#travel-note").textContent = `P${screw.pitchMm} · ${(value / screw.pitchMm).toFixed(2)} 圈；嘴端超出主体 ${(screw.tipProtrusionAtZeroMm + value).toFixed(2)} mm（Y内安全范围待实测）`;
  };

  const updateNozzleReadout = () => {
    if (!runtime) return;
    const selected = activeManifest.nozzleOptions.find(({ instanceId }) => runtime.instances.get(instanceId)?.visible);
    $("#nozzle").value = selected?.instanceId || "";
    const download = $("#download-core");
    download.hidden = !selected;
    if (selected) download.href = runtime.instances.get(selected.instanceId).part.file;
  };

  const renderInstructions = (manifest) => {
    const container = $("#instructions");
    const instructions = Array.isArray(manifest.instructions) && manifest.instructions.length
      ? manifest.instructions : DEFAULT_INSTRUCTIONS;
    container.replaceChildren(...instructions.map((text) => {
      const paragraph = document.createElement("p");
      paragraph.textContent = text;
      return paragraph;
    }));
  };

  const focus = (ids, direction = activeDirection) => {
    activeFocusIds = ids || null;
    activeDirection = direction;
    runtime?.focus(activeFocusIds, activeDirection);
    captureCommonState();
  };

  const renderInspector = () => {
    const inspector = $("#inspector");
    const record = runtime?.instances.get(selectedId);
    if (!record) {
      selectedId = null;
      inspector.hidden = true;
      return;
    }
    inspector.hidden = false;
    $("#selected-name").textContent = record.spec.name || record.part.name || selectedId;
    const binding = record.part.componentBindings?.find((item) =>
      item.id === record.spec.componentBindingId);
    $("#selected-source").textContent = `${record.part.source.file} · ${record.part.file}` +
      (binding ? ` · ${binding.name || binding.id} (${binding.islandId})` : "");
    $("#selected-opacity").value = String(Math.round(record.opacity * 100));
    $("#selected-opacity-value").textContent = `${$("#selected-opacity").value}%`;
  };

  const renderTree = () => {
    const tree = $("#tree");
    tree.replaceChildren();
    if (!runtime || !activeManifest) return;
    const byParent = new Map();
    for (const frame of activeManifest.assembly.frames) {
      if (!byParent.has(frame.parentFrameId)) byParent.set(frame.parentFrameId, []);
      byParent.get(frame.parentFrameId).push(frame);
    }
    const recordsByFrame = new Map();
    for (const [instanceId, record] of runtime.instances) {
      const frameId = record.spec.parentFrameId;
      if (!recordsByFrame.has(frameId)) recordsByFrame.set(frameId, []);
      recordsByFrame.get(frameId).push([instanceId, record]);
    }
    const matches = (record) => {
      const group = groupSelect.value;
      const query = $("#search").value.trim().toLocaleLowerCase();
      if (group && record.part.groupId !== group) return false;
      if (!query) return true;
      const binding = record.part.componentBindings?.find((item) =>
        item.id === record.spec.componentBindingId);
      return [record.part.name, record.part.id, record.spec.name, record.spec.id,
        record.part.file, record.part.groupId, binding?.id, binding?.name, binding?.islandId].some((value) =>
        String(value || "").toLocaleLowerCase().includes(query));
    };
    const frameMatches = (frameId) =>
      (recordsByFrame.get(frameId) || []).some(([, record]) => matches(record)) ||
      (byParent.get(frameId) || []).some((child) => frameMatches(child.id));
    const renderFrame = (frame) => {
      const details = document.createElement("details");
      details.open = true;
      details.className = "frame";
      const summary = document.createElement("summary");
      const label = document.createElement("span");
      label.textContent = frame.label || frame.id;
      summary.append(label);
      const actions = document.createElement("span");
      actions.className = "inline-actions";
      const click = (fn) => (event) => {
        event.preventDefault();
        event.stopPropagation();
        fn();
        renderTree();
      };
      actions.append(button("显", click(() => runtime.setFrameVisible(frame.id, true)), "small"));
      actions.append(button("隐", click(() => runtime.setFrameVisible(frame.id, false)), "small"));
      summary.append(actions);
      details.append(summary);
      const children = document.createElement("div");
      children.className = "tree-children";
      for (const [instanceId, record] of recordsByFrame.get(frame.id) || []) {
        if (!matches(record)) continue;
        const row = document.createElement("div");
        row.className = "instance-row";
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = record.visible;
        checkbox.setAttribute("aria-label", `显示 ${instanceId}`);
        checkbox.addEventListener("change", () => runtime.setVisible(instanceId, checkbox.checked));
        const name = record.spec.name || record.part.name || instanceId;
        const inspect = button(name, () => {
          selectedId = instanceId;
          renderInspector();
          focus([instanceId]);
          renderTree();
        }, selectedId === instanceId ? "selected part-button" : "part-button");
        row.append(checkbox, inspect);
        children.append(row);
      }
      for (const child of byParent.get(frame.id) || []) {
        if (frameMatches(child.id)) children.append(renderFrame(child));
      }
      details.append(children);
      return details;
    };
    const root = runtime.index.frames.get(runtime.index.rootId);
    if (root && frameMatches(root.id)) tree.append(renderFrame(root));
    else tree.textContent = "没有匹配的实例";
  };

  const configureControls = (manifest) => {
    groupSelect.replaceChildren(new Option("全部分组", ""));
    for (const group of runtime.index.groups.values()) {
      groupSelect.append(new Option(group.label, group.id));
    }
    groupSelect.value = runtime.index.groups.has(common.group) ? common.group : "";
    const showSearch = manifest.ui?.showSearch !== false;
    const showGroups = manifest.ui?.showGroups !== false && runtime.index.groups.size > 0;
    $("#search").hidden = !showSearch;
    groupSelect.hidden = !showGroups;
    $("#group-actions").hidden = !showGroups;
    $("#filters").hidden = !showSearch && !showGroups;
    $("#filters").classList.toggle("single-control", !showSearch || !showGroups);
    $("#search").value = common.search;

    stageSelect.replaceChildren();
    stageSelect.append(new Option("手动调节", ""));
    for (const stage of runtime.index.stages.values()) {
      stageSelect.append(new Option(stage.label || stage.id, stage.id));
    }
    $("#stage-controls").hidden = !runtime.index.stages.size;
    $("#play").hidden = !manifest.playback;
    if (runtime.index.stages.size) {
      const savedStage = variantState[activeVariantId]?.stage;
      const stageId = runtime.index.stages.has(savedStage)
        ? savedStage : runtime.index.stages.keys().next().value;
      stageSelect.value = stageId;
      runtime.setStage(stageId);
    }

    const saved = variantState[activeVariantId] || {};
    const screw = manifest.screwMotion;
    $("#travel").max = String(screw.travelMm);
    if (Number.isFinite(saved.travel) && saved.travel >= 0 && saved.travel <= screw.travelMm) {
      runtime.applyMotionValues({ [screw.frameId]: saved.travel });
      stageSelect.value = [...runtime.index.stages.values()].find(
        stage => stage.values[screw.frameId] === saved.travel)?.id || "";
    }
    $("#nozzle").replaceChildren(new Option("隐藏所有气嘴", ""));
    for (const option of manifest.nozzleOptions) {
      $("#nozzle").append(new Option(`Ø${option.diameterMm} mm`, option.instanceId));
    }
    const nozzleId = manifest.nozzleOptions.some(option => option.instanceId === saved.nozzle)
      ? saved.nozzle : manifest.defaultNozzleId;
    runtime.setVisible(nozzleId, true);
    $("#download-body").href = runtime.instances.get("body").part.file;
    updateNozzleReadout();
    updateScrewReadout();

    $("#axis-views").replaceChildren();
    for (const [label, direction] of [
      ["+X", [1, 0, 0]], ["−X", [-1, 0, 0]],
      ["+Y", [0, 1, 0]], ["−Y", [0, -1, 0]],
      ["+Z", [0, 0, 1]], ["−Z", [0, 0, -1]],
    ]) {
      $("#axis-views").append(button(label, () => {
        runtime.orientToAxis(direction);
        activeDirection = direction;
        captureCommonState();
      }));
    }

    $("#views").replaceChildren();
    for (const view of runtime.index.views.values()) {
      $("#views").append(button(view.label || view.id, () =>
        focus(view.focusInstanceIds, view.direction)));
    }
    if (!runtime.index.views.size) $("#views").append(button("全局", () => focus(null)));

    const firstView = manifest.views?.[0];
    if (common.camera) {
      activeFocusIds = null;
      activeDirection = common.camera.direction;
      const fitted = runtime.focus(null, activeDirection);
      if (fitted) {
        const distance = fitted.distance * common.camera.zoom;
        const direction = runtime.camera.position.clone().sub(runtime.controls.target).normalize();
        runtime.camera.position.copy(runtime.controls.target).addScaledVector(direction, distance);
        runtime.controls.update();
      }
    } else {
      activeFocusIds = firstView?.focusInstanceIds || null;
      activeDirection = firstView?.direction || [1, 0.75, 1];
      runtime.focus(activeFocusIds, activeDirection);
    }
    runtime.setExplosion(common.explosion);
    runtime.setGlobalOpacity(common.globalOpacity);
    $("#explode").value = String(Math.round(common.explosion * 100));
    $("#explode-value").textContent = `${$("#explode").value}%`;
    $("#global-opacity").value = String(Math.round(common.globalOpacity * 100));
    $("#global-opacity-value").textContent = `${$("#global-opacity").value}%`;
  };

  const loadVariantManifest = async (entry) => {
    if (manifestCache.has(entry.manifest)) return manifestCache.get(entry.manifest);
    const manifest = await readJson(entry.manifest);
    manifestCache.set(entry.manifest, manifest);
    return manifest;
  };

  const mountVariant = async (variantId, manifest) => {
    if (runtime) {
      captureCommonState();
      runtime.dispose();
      runtime = null;
    }
    activeVariantId = variantId;
    activeManifest = manifest;
    activeFocusIds = null;
    selectedId = null;
    const next = new AssemblyScene(canvas, manifest);
    runtime = next;
    resizeViewport();
    try {
      await next.load();
      if (manifest.motionAdapterModule) {
        const module = await import(new URL(manifest.motionAdapterModule, import.meta.url));
        if (typeof module.createMotionAdapter !== "function") {
          throw new Error("motion adapter must export createMotionAdapter(runtime, manifest)");
        }
        next.setMotionAdapter(module.createMotionAdapter(next, manifest));
      }
    } catch (error) {
      next.dispose();
      runtime = null;
      throw error;
    }
    $("#title").textContent = manifest.title || "装配预览";
    const release = manifest.release;
    $("#release").textContent = `${release.id} · P${release.pitchMm} · 行程 ${release.travelMm} mm · 原始 STL`;
    $("#release").dataset.revision = release.id;
    renderInstructions(manifest);
    next.onAxisView = (direction) => { activeDirection = direction; };
    next.onPlaybackUpdate = (stageId, playing) => {
      $("#play").textContent = playing ? "暂停" : "播放";
      if (stageId) stageSelect.value = stageId;
    };
    configureControls(manifest);
    next.onVisibilityUpdate = () => {
      updateNozzleReadout();
      renderTree();
      captureCommonState();
    };
    renderTree();
    renderInspector();
    status(`${next.index.parts.size} 种几何 · ${next.instances.size} 个实例 · ${next.index.frames.size} 个 frame`);
    renderTabs(false);
  };

  const switchVariant = async (variantId) => {
    if (variantId === activeVariantId) return;
    const entry = variants.get(variantId);
    if (!entry) return;
    const token = ++switchToken;
    captureCommonState();
    renderTabs(true);
    status(`正在切换到：${entry.label}`);
    try {
      const manifest = await loadVariantManifest(entry);
      if (token !== switchToken) return;
      await mountVariant(variantId, manifest);
      if (token !== switchToken) return;
      history.replaceState(null, "", `#${variantId}`);
    } catch (error) {
      status(`切换失败：${error.message}`);
      console.error(error);
    } finally {
      if (token === switchToken) {
        switchToken = 0;
        renderTabs(false);
      }
    }
  };

  $("#stage").addEventListener("change", () => {
    if (!runtime || !stageSelect.value) return;
    runtime.setStage(stageSelect.value);
    updateScrewReadout();
    captureCommonState();
  });
  $("#travel").addEventListener("input", event => {
    if (!runtime) return;
    runtime.pause();
    runtime.playInitialized = false;
    runtime.applyMotionValues({ [activeManifest.screwMotion.frameId]: Number(event.target.value) });
    stageSelect.value = "";
    updateScrewReadout();
    captureCommonState();
  });
  $("#nozzle").addEventListener("change", event => {
    if (!runtime) return;
    const id = event.target.value;
    if (id) runtime.setVisible(id, true);
    else for (const option of activeManifest.nozzleOptions) runtime.setVisible(option.instanceId, false);
    updateNozzleReadout();
    renderTree();
    captureCommonState();
  });
  $("#play").addEventListener("click", () => {
    if (!runtime) return;
    if (runtime.playing) runtime.pause();
    else {
      if (activeFocusIds) focus(null, activeDirection);
      runtime.play();
    }
  });
  $("#explode").addEventListener("input", (event) => {
    common.explosion = Number(event.target.value) / 100;
    $("#explode-value").textContent = `${event.target.value}%`;
    runtime?.setExplosion(common.explosion);
    saveState();
  });
  $("#global-opacity").addEventListener("input", (event) => {
    common.globalOpacity = Number(event.target.value) / 100;
    $("#global-opacity-value").textContent = `${event.target.value}%`;
    runtime?.setGlobalOpacity(common.globalOpacity);
    saveState();
  });
  $("#selected-opacity").addEventListener("input", (event) => {
    runtime?.setOpacity(selectedId, Number(event.target.value) / 100);
    $("#selected-opacity-value").textContent = `${event.target.value}%`;
  });
  $("#focus-selected").addEventListener("click", () => {
    if (selectedId) focus([selectedId]);
  });
  $("#show-selected").addEventListener("click", () => {
    if (selectedId) runtime?.setVisible(selectedId, true);
    renderTree();
  });
  $("#hide-selected").addEventListener("click", () => {
    if (selectedId) runtime?.setVisible(selectedId, false);
    renderTree();
  });
  $("#search").addEventListener("input", () => {
    common.search = $("#search").value;
    renderTree();
    saveState();
  });
  groupSelect.addEventListener("change", () => {
    common.group = groupSelect.value;
    renderTree();
    saveState();
  });
  $("#show-group").addEventListener("click", () => {
    if (groupSelect.value) runtime?.setGroupVisible(groupSelect.value, true);
    else if (runtime) for (const instanceId of runtime.instances.keys()) runtime.setVisible(instanceId, true);
    renderTree();
  });
  $("#hide-group").addEventListener("click", () => {
    if (groupSelect.value) runtime?.setGroupVisible(groupSelect.value, false);
    else if (runtime) for (const instanceId of runtime.instances.keys()) runtime.setVisible(instanceId, false);
    renderTree();
  });

  renderTabs(true);
  await mountVariant(initialVariantId, await loadVariantManifest(variants.get(initialVariantId)));
  renderTabs(false);
  let last = performance.now();
  const tick = (now) => {
    const delta = (now - last) / 1000;
    last = now;
    runtime?.tick(delta);
    updateScrewReadout();
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

main().catch((error) => {
  $("#status").textContent = `加载失败：${error.message}`;
  console.error(error);
});
