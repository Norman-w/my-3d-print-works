import * as THREE from 'three';

// Selection belongs to an instance or a manifest frame, never a material group.
export function installAssemblyInteraction({ runtime, manifest, focus }) {
  const $ = (s) => document.querySelector(s);
  const canvas = runtime.renderer.domElement;
  const tree = $('#tree');
  const group = $('#group-filter');
  const search = $('#search');
  const frames = runtime.index.frames;
  const records = runtime.instances;
  const children = new Map();
  const direct = new Map();
  let selection = null;
  let hovered = null;
  let pointer = null;
  let down = null;
  let lastHoverTime = 0;
  const pointers = new Set();
  const folded = new Set();
  const raycaster = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  const meshIds = new Map([...records].map(([id, r]) => [r.mesh, id]));
  const originalEmissive = new Map([...records].map(([id, r]) => [id, {
    color: r.mesh.material.emissive.clone(), intensity: r.mesh.material.emissiveIntensity,
  }]));
  for (const frame of frames.values()) {
    if (!children.has(frame.parentFrameId)) children.set(frame.parentFrameId, []);
    children.get(frame.parentFrameId).push(frame.id);
  }
  for (const [id, r] of records) {
    if (!direct.has(r.spec.parentFrameId)) direct.set(r.spec.parentFrameId, []);
    direct.get(r.spec.parentFrameId).push(id);
  }
  const frameIds = (id) => [...(direct.get(id) || []), ...(children.get(id) || []).flatMap(frameIds)];
  const idsFor = (target) => !target ? [] : target.kind === 'instance' ? [target.id] : frameIds(target.id);
  const selectedIds = () => idsFor(selection);
  const label = (target) => target.kind === 'frame' ? frames.get(target.id).label || target.id
    : records.get(target.id).spec.name || records.get(target.id).part.name || target.id;
  const parentOf = (target) => {
    if (!target) return null;
    const id = target.kind === 'frame' ? frames.get(target.id).parentFrameId : records.get(target.id).spec.parentFrameId;
    return id === null ? null : { kind: 'frame', id };
  };
  const same = (a, b) => a?.id === b?.id && a?.kind === b?.kind;
  const visibility = (ids) => {
    const count = ids.filter((id) => records.get(id).visible).length;
    return count === 0 ? 'hidden' : count === ids.length ? 'visible' : 'mixed';
  };
  const setVisible = (ids, value) => {
    for (const id of ids) runtime.setVisible(id, value);
    refresh();
  };
  const toggle = (ids) => setVisible(ids, visibility(ids) !== 'visible');
  const button = (text, action, className = '') => {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = text; b.className = className;
    b.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); action(); });
    return b;
  };
  const eyeIcon = (state) => state === 'hidden'
    ? '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M2 12s3.5-6 10-6c2.2 0 4.1.7 5.7 1.7M22 12s-3.5 6-10 6c-2.2 0 4.1-.7 5.7-1.7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M3 3l18 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
    : '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><circle cx="12" cy="12" r="2.5" fill="currentColor"/></svg>';
  const describeToggle = (b, ids, name) => {
    const state = visibility(ids);
    const action = state === 'visible' ? '隐藏' : state === 'mixed' ? '显示全部' : '显示';
    b.innerHTML = eyeIcon(state);
    b.setAttribute('aria-label', `${action} ${name}`);
    b.setAttribute('aria-pressed', state === 'mixed' ? 'mixed' : String(state === 'visible'));
    b.dataset.visibility = state;
    b.title = `${action} ${name} · ${state === 'visible' ? '全部显示' : state === 'mixed' ? '部分隐藏' : '全部隐藏'}`;
    b.disabled = ids.length === 0;
  };
  const visibilityButton = (ids, name) => {
    const b = button('', () => toggle(ids), 'small visibility-toggle');
    describeToggle(b, ids, name); return b;
  };
  const tooltip = document.createElement('div');
  tooltip.className = 'component-tooltip'; tooltip.hidden = true; tooltip.setAttribute('role', 'tooltip');
  document.body.append(tooltip);
  const toolbar = document.createElement('aside');
  toolbar.className = 'selection-toolbar'; toolbar.hidden = true;
  toolbar.setAttribute('aria-label', '当前选中组件');
  const selectedName = document.createElement('strong'); selectedName.setAttribute('aria-live', 'polite');
  const parentButton = button('上一级', () => select(parentOf(selection)));
  parentButton.title = '选择上一级（Alt+↑）'; parentButton.setAttribute('aria-keyshortcuts', 'Alt+ArrowUp');
  const hideButton = button('', () => toggle(selectedIds()));
  hideButton.setAttribute('aria-keyshortcuts', 'Control+h');
  const clearButton = button('×', () => select(null)); clearButton.setAttribute('aria-label', '清除选择');
  toolbar.append(selectedName, parentButton, hideButton, clearButton);
  $('#canvas-panel').append(toolbar);

  function tint() {
    const ids = new Set(selectedIds());
    for (const [id, r] of records) {
      const base = originalEmissive.get(id);
      const active = ids.has(id), hover = id === hovered;
      r.mesh.material.emissive.copy(base.color);
      r.mesh.material.emissiveIntensity = base.intensity;
      if (active || hover) {
        r.mesh.material.emissive.set(active ? '#d88920' : '#5ea6d0');
        r.mesh.material.emissiveIntensity = active ? 0.33 : 0.2;
      }
    }
  }
  function select(target) {
    selection = target;
    for (let p = parentOf(target); p; p = parentOf(p)) folded.delete(p.id);
    refresh();
  }
  function inspector() {
    $('#inspector').hidden = !selection;
    toolbar.hidden = !selection;
    if (!selection) return;
    const ids = selectedIds();
    const name = label(selection);
    const state = visibility(ids);
    selectedName.textContent = `${name}${state === 'hidden' ? ' · 已隐藏' : state === 'mixed' ? ' · 部分隐藏' : ''}`;
    $('#selected-name').textContent = name;
    const crumbs = $('#selection-path'); crumbs.replaceChildren();
    const path = [];
    for (let p = selection; p; p = parentOf(p)) path.unshift(p);
    for (const p of path) {
      const b = button(label(p), () => select(p));
      b.setAttribute('aria-current', same(p, selection) ? 'true' : 'false');
      crumbs.append(b);
    }
    const record = selection.kind === 'instance' ? records.get(selection.id) : null;
    const binding = record?.part.componentBindings?.find((b) => b.id === record.spec.componentBindingId);
    $('#selected-source').textContent = record
      ? `${record.part.source.file} · ${record.part.file}${binding ? ` · ${binding.name || binding.id}` : ''}`
      : `${ids.length} 个下属实例 · ${ids.filter((id) => records.get(id).visible).length} 个显示`;
    $('#select-parent').disabled = parentButton.disabled = !parentOf(selection);
    describeToggle($('#toggle-selected'), ids, name);
    describeToggle(hideButton, ids, name);
    const values = ids.map((id) => records.get(id).opacity);
    const mixed = values.some((v) => v !== values[0]);
    $('#selected-opacity').value = String(Math.round((values[0] ?? 1) * 100));
    $('#selected-opacity-value').textContent = mixed ? '混合' : `${$('#selected-opacity').value}%`;
  }
  const matches = (id) => {
    const r = records.get(id), q = search.value.trim().toLocaleLowerCase();
    if (group.value && r.part.groupId !== group.value) return false;
    const binding = r.part.componentBindings?.find((b) => b.id === r.spec.componentBindingId);
    return !q || [r.part.name, r.part.id, r.spec.name, id, r.part.file, r.part.groupId,
      binding?.name, binding?.id, binding?.islandId].some((v) => String(v || '').toLocaleLowerCase().includes(q));
  };
  function renderFrame(id) {
    const frame = frames.get(id), target = { kind: 'frame', id };
    const details = document.createElement('details');
    details.className = 'frame'; details.open = !folded.has(id); details.dataset.frameId = id;
    details.addEventListener('toggle', () => { if (details.open) folded.delete(id); else folded.add(id); });
    const summary = document.createElement('summary');
    const expand = document.createElement('span'); expand.className = 'tree-disclosure'; expand.setAttribute('aria-hidden', 'true');
    const name = button(label(target), () => select(target), 'part-button frame-button');
    name.classList.toggle('selected', same(selection, target));
    name.setAttribute('aria-pressed', String(same(selection, target)));
    summary.append(expand, name, visibilityButton(frameIds(id), label(target))); details.append(summary);
    const nested = document.createElement('div'); nested.className = 'tree-children';
    for (const instanceId of direct.get(id) || []) {
      if (!matches(instanceId)) continue;
      const t = { kind: 'instance', id: instanceId };
      const row = document.createElement('div'); row.className = 'instance-row'; row.dataset.instanceId = instanceId;
      const b = button(label(t), () => select(t), 'part-button');
      b.style.borderLeft = `3px solid ${records.get(instanceId).part.color}`;
      b.classList.toggle('selected', same(selection, t));
      b.setAttribute('aria-pressed', String(same(selection, t))); b.title = label(t);
      row.append(b, visibilityButton([instanceId], label(t))); nested.append(row);
    }
    for (const child of children.get(id) || []) {
      if (frameIds(child).some(matches)) nested.append(renderFrame(child));
    }
    details.append(nested); return details;
  }
  const groupIds = () => [...records].filter(([, r]) => !group.value || r.part.groupId === group.value).map(([id]) => id);
  function refresh() {
    const focused = tree.contains(document.activeElement) ? {
      row: document.activeElement.closest('[data-instance-id]')?.dataset.instanceId,
      frame: document.activeElement.closest('[data-frame-id]')?.dataset.frameId,
      toggle: document.activeElement.classList.contains('visibility-toggle'),
    } : null;
    tree.replaceChildren();
    if (frameIds(runtime.index.rootId).some(matches)) tree.append(renderFrame(runtime.index.rootId));
    else tree.textContent = '没有匹配的实例';
    if (focused) {
      const row = focused.row ? tree.querySelector(`[data-instance-id="${CSS.escape(focused.row)}"]`)
        : tree.querySelector(`[data-frame-id="${CSS.escape(focused.frame)}"] > summary`);
      row?.querySelector(focused.toggle ? '.visibility-toggle' : '.part-button')?.focus({ preventScroll: true });
    }
    describeToggle($('#toggle-group'), groupIds(), group.value ? runtime.index.groups.get(group.value).label : '全部组件');
    inspector(); hovered = null; tooltip.hidden = true; tint();
  }
  $('#focus-selected').addEventListener('click', () => focus(selectedIds()));
  $('#toggle-selected').addEventListener('click', () => toggle(selectedIds()));
  $('#select-parent').addEventListener('click', () => select(parentOf(selection)));
  $('#toggle-group').addEventListener('click', () => toggle(groupIds()));
  $('#selected-opacity').addEventListener('input', (e) => {
    for (const id of selectedIds()) runtime.setOpacity(id, Number(e.target.value) / 100);
    inspector();
  });
  group.addEventListener('change', refresh); search.addEventListener('input', refresh);

  function pick(point) {
    if (runtime.axisHelper?.contains(point)) return null;
    const rect = canvas.getBoundingClientRect();
    if (point.clientX < rect.left || point.clientX > rect.right || point.clientY < rect.top || point.clientY > rect.bottom) return null;
    ndc.set((point.clientX - rect.left) / rect.width * 2 - 1, -(point.clientY - rect.top) / rect.height * 2 + 1);
    runtime.scene.updateMatrixWorld(true); runtime.camera.updateMatrixWorld(true);
    raycaster.setFromCamera(ndc, runtime.camera);
    const eligible = [...records.values()].filter((r) => {
      if (!r.visible || r.mesh.material.opacity <= 0) return false;
      for (let obj = r.mesh; obj; obj = obj.parent) if (!obj.visible) return false;
      return true;
    }).map((r) => r.mesh);
    return meshIds.get(raycaster.intersectObjects(eligible, false)[0]?.object) || null;
  }
  canvas.addEventListener('pointerdown', (e) => {
    pointers.add(e.pointerId); tooltip.hidden = true;
    if (pointers.size > 1) { if (down) down.dragged = true; return; }
    if (e.button === 0) down = { id: e.pointerId, x: e.clientX, y: e.clientY, dragged: false };
  });
  canvas.addEventListener('pointermove', (e) => {
    pointer = e.pointerType === 'touch' ? null : { clientX: e.clientX, clientY: e.clientY };
    if (down && Math.hypot(e.clientX - down.x, e.clientY - down.y) > 5) down.dragged = true;
  });
  canvas.addEventListener('pointerup', (e) => {
    if (down?.id === e.pointerId && !down.dragged && e.button === 0) {
      const id = pick(e); select(id ? { kind: 'instance', id } : null);
    }
    pointers.delete(e.pointerId); if (down?.id === e.pointerId) down = null;
  });
  canvas.addEventListener('pointercancel', (e) => { pointers.delete(e.pointerId); down = null; pointer = null; });
  canvas.addEventListener('pointerleave', () => { pointer = null; tooltip.hidden = true; hovered = null; tint(); });
  window.addEventListener('pointerup', (e) => { pointers.delete(e.pointerId); if (down?.id === e.pointerId) down = null; });
  document.addEventListener('keydown', (e) => {
    if (!selection || e.defaultPrevented || e.isComposing || e.target.isContentEditable || e.target.closest('input,textarea,select,[role="textbox"]')) return;
    if (e.ctrlKey && !e.shiftKey && !e.altKey && !e.metaKey && e.key.toLowerCase() === 'h') {
      e.preventDefault(); if (!e.repeat) setVisible(selectedIds(), false);
    } else if (e.altKey && !e.ctrlKey && e.key === 'ArrowUp') {
      e.preventDefault(); if (!e.repeat && parentOf(selection)) select(parentOf(selection));
    } else if (e.key === 'Escape') select(null);
  });
  function update(now) {
    if (now - lastHoverTime < 80) return;
    lastHoverTime = now;
    const id = pointer && pointers.size === 0 && document.elementFromPoint(pointer.clientX, pointer.clientY) === canvas ? pick(pointer) : null;
    if (id !== hovered) { hovered = id; tint(); }
    tooltip.hidden = !id;
    if (!id) return;
    tooltip.textContent = label({ kind: 'instance', id });
    tooltip.style.left = `${Math.max(4, Math.min(pointer.clientX + 14, innerWidth - tooltip.offsetWidth - 8))}px`;
    tooltip.style.top = `${Math.max(4, Math.min(pointer.clientY + 16, innerHeight - tooltip.offsetHeight - 8))}px`;
  }
  refresh();
  return { refresh, update };
}
