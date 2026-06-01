import { useCallback, useEffect, useRef, useState } from 'react';
import {
  anchorCount,
  BezierHandleKind,
  BezierHandleRef,
  BezierProfile,
  canRemoveAnchor,
  defaultProfile,
  DrawTarget,
  getHandle,
  handleRefs,
  closestOnProfile,
  insertAnchorOnSelected,
  loadProfile,
  parseProfileJson,
  profileToJson,
  removeAnchor,
  saveProfile,
  segmentPoints,
  setHandle,
  splitSegment,
  viewBoundsSide,
} from '../lib/bezierProfile';
import {
  applyRefAdjust,
  boundsToViewBox,
  BOTTOM_GRID,
  BOTTOM_REF,
  defaultGridViewport,
  defaultRefAdjust,
  loadRefAdjust,
  mmGridToSvg,
  saveRefAdjust,
  SIDE_GRID,
  SIDE_REF,
  svgGridToMm,
  refImageSvgRect,
  refImageCenterSvg,
  workspaceBounds,
  type RefGridTarget,
  type RefImageAdjust,
  type RefImageBox,
} from '../lib/refGridLayout';
import {
  loadPhotoMap,
  mmToPhotoPx,
  mmYToPhotoY,
  PhotoMapConfig,
  photoCanvasSize,
  photoImageRect,
  photoMirrorPathFromMmRight,
  photoPathFromMmRight,
  photoPxToMm,
} from '../lib/photoCoords';
import { PADDLE } from '../lib/paddleModel';

const REF_IMAGE = 'butterfly_ca_media_02.jpg';
const PREFS_KEY = 'smartpaddle-bezier-ui';

type EditorPrefs = {
  photoOpacity: number;
  /** Grid ref photo opacity (side / handle-bottom). */
  gridRefOpacity: number;
  showMirror: boolean;
  showGuides: boolean;
  zoom: number;
};

const ZOOM_MIN = 1;
const ZOOM_MAX = 8;

function loadPrefs(): EditorPrefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (raw) return { photoOpacity: 1, gridRefOpacity: 0.55, showMirror: true, showGuides: true, zoom: 1, ...JSON.parse(raw) };
  } catch {
    /* ignore */
  }
  return { photoOpacity: 1, gridRefOpacity: 0.55, showMirror: true, showGuides: true, zoom: 1 };
}

type Viewport = { cx: number; cy: number; zoom: number };
type ViewBoxRect = { x: number; y: number; w: number; h: number };

function viewBoxToString(r: ViewBoxRect): string {
  return `${r.x} ${r.y} ${r.w} ${r.h}`;
}

function viewportToViewBox(base: ViewBoxRect, vp: Viewport): ViewBoxRect {
  const w = base.w / vp.zoom;
  const h = base.h / vp.zoom;
  return { x: vp.cx - w / 2, y: vp.cy - h / 2, w, h };
}

function defaultViewport(base: ViewBoxRect, zoom = 1): Viewport {
  return { cx: base.x + base.w / 2, cy: base.y + base.h / 2, zoom };
}

function clampViewport(vp: Viewport, base: ViewBoxRect): Viewport {
  const w = base.w / vp.zoom;
  const h = base.h / vp.zoom;
  return {
    zoom: vp.zoom,
    cx: Math.min(base.x + base.w - w / 2, Math.max(base.x + w / 2, vp.cx)),
    cy: Math.min(base.y + base.h - h / 2, Math.max(base.y + h / 2, vp.cy)),
  };
}

/** Widen viewBox to match canvas aspect so meet fills the canvas (no dead letterbox zones). */
function fitViewBoxToAspect(vb: ViewBoxRect, aspect: number): ViewBoxRect {
  if (!Number.isFinite(aspect) || aspect <= 0) return vb;
  const cx = vb.x + vb.w / 2;
  const cy = vb.y + vb.h / 2;
  const vbAspect = vb.w / vb.h;
  if (vbAspect < aspect) {
    const w = vb.h * aspect;
    return { x: cx - w / 2, y: vb.y, w, h: vb.h };
  }
  const h = vb.w / aspect;
  return { x: vb.x, y: cy - h / 2, w: vb.w, h };
}

const EDGE_PAN_PX = 52;

function edgePanDelta(
  vb: ViewBoxRect,
  clientX: number,
  clientY: number,
  rect: DOMRect,
): { dcx: number; dcy: number } | null {
  let dcx = 0;
  let dcy = 0;
  if (clientX - rect.left < EDGE_PAN_PX) dcx = -vb.w * 0.06;
  else if (rect.right - clientX < EDGE_PAN_PX) dcx = vb.w * 0.06;
  if (clientY - rect.top < EDGE_PAN_PX) dcy = -vb.h * 0.06;
  else if (rect.bottom - clientY < EDGE_PAN_PX) dcy = vb.h * 0.06;
  if (!dcx && !dcy) return null;
  return { dcx, dcy };
}

function gridResetViewport(
  target: RefGridTarget,
  profile: BezierProfile,
  panBounds: ViewBoxRect,
): Viewport {
  const grid = target === 'handle-bottom' ? BOTTOM_GRID : SIDE_GRID;
  const fallback = defaultGridViewport(target, grid, 1);
  const pts = [profile.start, ...profile.segments.flatMap(s => [s.cp1, s.cp2, s.end])];
  if (pts.length < 2) {
    return { cx: fallback.cx, cy: -fallback.cy, zoom: fallback.zoom };
  }
  let x0 = Infinity;
  let x1 = -Infinity;
  let y0 = Infinity;
  let y1 = -Infinity;
  for (const p of pts) {
    x0 = Math.min(x0, p.x);
    x1 = Math.max(x1, p.x);
    y0 = Math.min(y0, p.y);
    y1 = Math.max(y1, p.y);
  }
  const pad = 20;
  const pw = x1 - x0 + pad * 2;
  const ph = y1 - y0 + pad * 2;
  const mmCx = (x0 + x1) / 2;
  const mmCy = (y0 + y1) / 2;
  const zoom = Math.min(ZOOM_MAX, Math.max(fallback.zoom, Math.min(panBounds.w / pw, panBounds.h / ph) * 0.9));
  return { cx: mmCx, cy: -mmCy, zoom };
}

function zoomViewportAt(base: ViewBoxRect, vp: Viewport, newZoom: number, focal: { x: number; y: number }): Viewport {
  const z = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, newZoom));
  if (z === vp.zoom) return vp;
  const oldW = base.w / vp.zoom;
  const oldH = base.h / vp.zoom;
  const newW = base.w / z;
  const newH = base.h / z;
  const oldX = vp.cx - oldW / 2;
  const oldY = vp.cy - oldH / 2;
  const fx = (focal.x - oldX) / oldW;
  const fy = (focal.y - oldY) / oldH;
  return clampViewport(
    { zoom: z, cx: focal.x + newW * (0.5 - fx), cy: focal.y + newH * (0.5 - fy) },
    base,
  );
}

function savePrefs(p: EditorPrefs): void {
  localStorage.setItem(PREFS_KEY, JSON.stringify(p));
}

type EditorMode = 'photo' | 'grid';

const TARGET_META: Record<
  DrawTarget,
  {
    label: string;
    stroke: string;
    mode: EditorMode;
    hint: string;
    refImage?: string;
    refImageBox?: RefImageBox;
    gridBounds?: { xMin: number; xMax: number; yMin: number; yMax: number };
  }
> = {
  'blade-front': {
    label: '底板 (+Z)',
    stroke: '#ff1744',
    mode: 'photo',
    hint: '红线 = 拍面+颈，可向下扎入手柄区。标尺线仅供参考，不限制拖拽范围。',
  },
  'handle-front': {
    label: '手柄 (+Z)',
    stroke: '#00e5ff',
    mode: 'photo',
    hint: '蓝线 = FL 柄正视。与底板同一张官图、同一 mm 坐标系，可同时看到另一条曲线。',
  },
  side: {
    label: '柄侧视 (+X)',
    stroke: '#1565c0',
    mode: 'grid',
    hint: 'x = 半厚度 · y = 沿柄长 mm。叠图对齐柄区，描外侧厚度曲线（侧面微鼓）。',
    refImage: SIDE_REF.image,
    refImageBox: SIDE_REF.box,
    gridBounds: SIDE_GRID,
  },
  'handle-bottom': {
    label: '柄底视 (−Y)',
    stroke: '#ab47bc',
    mode: 'grid',
    hint: 'x = 半宽 · y = 半厚。画柄底截面右半外轮廓；3D 按此放样，配合正视/侧视缩放。',
    refImage: BOTTOM_REF.image,
    refImageBox: BOTTOM_REF.box,
    gridBounds: BOTTOM_GRID,
  },
};

const GHOST_STROKE: Record<'blade-front' | 'handle-front', string> = {
  'blade-front': '#ff1744',
  'handle-front': '#00e5ff',
};

const KIND_COLOR: Record<BezierHandleKind, string> = {
  start: '#ff1744',
  cp1: '#ffb300',
  cp2: '#ffb300',
  end: '#4fc3f7',
};

/** On-curve anchors (deletable) vs off-curve control handles. */
function isOnCurveAnchor(kind: BezierHandleKind): boolean {
  return kind === 'start' || kind === 'end';
}

const HIT_R_PX = 12;
const ANCHOR_R_ON_PX = 5;
const ANCHOR_R_ON_SEL_PX = 6;
const ANCHOR_R_CP_PX = 3.5;
const ANCHOR_R_CP_SEL_PX = 4.5;

type MmBounds = { xMin: number; xMax: number; yMin: number; yMax: number };

function clampMmToBounds(mm: { x: number; y: number }, b: MmBounds): { x: number; y: number } {
  return {
    x: Math.min(b.xMax, Math.max(b.xMin, mm.x)),
    y: Math.min(b.yMax, Math.max(b.yMin, mm.y)),
  };
}

function sameRef(a: BezierHandleRef | null, b: BezierHandleRef | null) {
  return a && b && a.seg === b.seg && a.kind === b.kind;
}

type Props = {
  target: DrawTarget;
};

export default function BezierDrawEditor({ target }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const canvasWrapRef = useRef<HTMLDivElement>(null);
  const spaceRef = useRef(false);
  const [photoMap] = useState<PhotoMapConfig>(() => loadPhotoMap());
  const [profiles, setProfiles] = useState<Record<DrawTarget, BezierProfile>>(() => ({
    'blade-front': loadProfile('blade-front'),
    'handle-front': loadProfile('handle-front'),
    side: loadProfile('side'),
    'handle-bottom': loadProfile('handle-bottom'),
  }));
  const [prefs, setPrefs] = useState<EditorPrefs>(loadPrefs);
  const [selected, setSelected] = useState<BezierHandleRef | null>(null);
  const [drag, setDrag] = useState<BezierHandleRef | null>(null);
  const [panDrag, setPanDrag] = useState<{ startX: number; startY: number; startCx: number; startCy: number } | null>(
    null,
  );
  const [importText, setImportText] = useState('');
  const [showImport, setShowImport] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showRefCalibrate, setShowRefCalibrate] = useState(false);
  const [refAdjust, setRefAdjust] = useState<RefImageAdjust>(() =>
    onGridTarget(target) ? loadRefAdjust(target as RefGridTarget) : defaultRefAdjust('side'),
  );
  const [canvasAspect, setCanvasAspect] = useState(1.6);

  const profile = profiles[target];
  const meta = TARGET_META[target];
  const onPhoto = meta.mode === 'photo';
  const onGrid = meta.mode === 'grid';
  const sideBounds = viewBoundsSide();
  const gridBounds = meta.gridBounds ?? sideBounds;
  const canvasSize = onPhoto ? photoCanvasSize(photoMap) : null;
  const imgRect = onPhoto ? photoImageRect(photoMap) : null;
  const refImageBox =
    onGrid && meta.refImageBox ? applyRefAdjust(meta.refImageBox, refAdjust) : null;
  const refSvgRect = refImageBox ? refImageSvgRect(refImageBox) : null;
  const workspace = onGrid ? workspaceBounds(gridBounds) : gridBounds;
  const editBounds: MmBounds = onGrid
    ? workspace
    : { ...viewBoundsSide(), xMin: 0 };
  const panBounds: ViewBoxRect = onPhoto && canvasSize
    ? { x: 0, y: 0, w: canvasSize.width, h: canvasSize.height }
    : boundsToViewBox(workspace);

  const initialViewport = (): Viewport => {
    const zoom = loadPrefs().zoom;
    if (onPhoto && canvasSize) return defaultViewport({ x: 0, y: 0, w: canvasSize.width, h: canvasSize.height }, zoom);
    if (onGridTarget(target)) {
      const gv = defaultGridViewport(target as RefGridTarget, gridBounds, zoom);
      return { cx: gv.cx, cy: -gv.cy, zoom: gv.zoom };
    }
    return defaultViewport(
      { x: sideBounds.xMin, y: -sideBounds.yMax, w: sideBounds.xMax - sideBounds.xMin, h: sideBounds.yMax - sideBounds.yMin },
      zoom,
    );
  };
  const [viewport, setViewport] = useState<Viewport>(initialViewport);
  const [spaceHeld, setSpaceHeld] = useState(false);

  const updatePrefs = useCallback((patch: Partial<EditorPrefs>) => {
    setPrefs(prev => {
      const next = { ...prev, ...patch };
      savePrefs(next);
      return next;
    });
  }, []);

  const commit = useCallback((next: BezierProfile) => {
    setProfiles(prev => ({ ...prev, [next.target]: next }));
    saveProfile(next);
  }, []);

  const applyZoom = useCallback(
    (newZoom: number, clientX?: number, clientY?: number) => {
      setViewport(vp => {
        let focal = { x: vp.cx, y: vp.cy };
        if (clientX != null && clientY != null) {
          const svg = svgRef.current;
          if (svg) {
            const pt = svg.createSVGPoint();
            pt.x = clientX;
            pt.y = clientY;
            const ctm = svg.getScreenCTM();
            if (ctm) focal = pt.matrixTransform(ctm.inverse());
          }
        }
        const next = zoomViewportAt(panBounds, vp, newZoom, focal);
        updatePrefs({ zoom: next.zoom });
        return next;
      });
    },
    [panBounds, updatePrefs],
  );

  const resetViewport = useCallback(() => {
    if (onGridTarget(target)) {
      const vp = gridResetViewport(target as RefGridTarget, profile, panBounds);
      setViewport(vp);
      updatePrefs({ zoom: vp.zoom });
    } else {
      setViewport(defaultViewport(panBounds, 1));
      updatePrefs({ zoom: 1 });
    }
  }, [panBounds, profile, target, updatePrefs]);

  const updateRefAdjust = useCallback(
    (patch: Partial<RefImageAdjust>) => {
      if (!onGridTarget(target)) return;
      setRefAdjust(prev => {
        const next = { ...prev, ...patch };
        saveRefAdjust(target as RefGridTarget, next);
        return next;
      });
    },
    [target],
  );

  const resetRefAdjust = useCallback(() => {
    if (!onGridTarget(target)) return;
    const next = defaultRefAdjust(target as RefGridTarget);
    setRefAdjust(next);
    saveRefAdjust(target as RefGridTarget, next);
  }, [target]);

  useEffect(() => {
    setSelected(null);
    setPanDrag(null);
    if (onGridTarget(target)) {
      setRefAdjust(loadRefAdjust(target as RefGridTarget));
      const vp = gridResetViewport(target as RefGridTarget, profiles[target], panBounds);
      setViewport(vp);
    } else {
      setViewport(defaultViewport(panBounds, prefs.zoom));
    }
  }, [target]);

  useEffect(() => {
    const el = canvasWrapRef.current;
    if (!el) return;
    const sync = () => {
      const r = el.getBoundingClientRect();
      if (r.height > 0) setCanvasAspect(r.width / r.height);
    };
    sync();
    const ro = new ResizeObserver(sync);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasWrapRef.current;
    if (!canvas) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
      setViewport(vp => {
        let focal = { x: vp.cx, y: vp.cy };
        const svg = svgRef.current;
        if (svg) {
          const pt = svg.createSVGPoint();
          pt.x = e.clientX;
          pt.y = e.clientY;
          const ctm = svg.getScreenCTM();
          if (ctm) focal = pt.matrixTransform(ctm.inverse());
        }
        const next = zoomViewportAt(panBounds, vp, vp.zoom * factor, focal);
        updatePrefs({ zoom: next.zoom });
        return next;
      });
    };
    canvas.addEventListener('wheel', onWheel, { passive: false });
    return () => canvas.removeEventListener('wheel', onWheel);
  }, [panBounds, updatePrefs]);

  useEffect(() => {
    const tagOk = (el: EventTarget | null) => {
      const tag = (el as HTMLElement | null)?.tagName;
      return tag !== 'INPUT' && tag !== 'TEXTAREA';
    };
    const onDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && tagOk(e.target)) {
        e.preventDefault();
        spaceRef.current = true;
        setSpaceHeld(true);
      }
    };
    const onUp = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        spaceRef.current = false;
        setSpaceHeld(false);
      }
    };
    window.addEventListener('keydown', onDown);
    window.addEventListener('keyup', onUp);
    return () => {
      window.removeEventListener('keydown', onDown);
      window.removeEventListener('keyup', onUp);
    };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Delete' && e.key !== 'Backspace') return;
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      e.preventDefault();
      if (!canRemoveAnchor(profile)) return;
      commit(removeAnchor(profile, selected));
      setSelected(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selected, profile, commit]);

  const clientToPx = useCallback((clientX: number, clientY: number): { x: number; y: number } | null => {
    const svg = svgRef.current;
    if (!svg) return null;
    const pt = svg.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return null;
    return pt.matrixTransform(ctm.inverse());
  }, []);

  const pxToMm = useCallback(
    (px: { x: number; y: number }) => (onPhoto ? photoPxToMm(photoMap, px.x, px.y) : svgGridToMm(px)),
    [onPhoto, photoMap],
  );

  const mmToPx = useCallback(
    (mm: { x: number; y: number }) => (onPhoto ? mmToPhotoPx(photoMap, mm.x, mm.y) : mmGridToSvg(mm)),
    [onPhoto, photoMap],
  );

  const hitRadiusSvg = useCallback(() => {
    const scale = svgRef.current?.getScreenCTM()?.a ?? 1;
    return HIT_R_PX / scale;
  }, []);

  const pickHandle = (px: { x: number; y: number }): BezierHandleRef | null => {
    const hitR = hitRadiusSvg();
    let best: { ref: BezierHandleRef; d: number; priority: number } | null = null;
    for (const ref of handleRefs(profile)) {
      const p = mmToPx(getHandle(profile, ref));
      const d = Math.hypot(px.x - p.x, px.y - p.y);
      const priority = isOnCurveAnchor(ref.kind) ? 0 : 1;
      if (d <= hitR && (!best || priority < best.priority || (priority === best.priority && d < best.d))) {
        best = { ref, d, priority };
      }
    }
    return best?.ref ?? null;
  };

  const constrainMm = useCallback(
    (mm: { x: number; y: number }) => clampMmToBounds(mm, editBounds),
    [editBounds],
  );

  const beginHandleDrag = (ref: BezierHandleRef, e: React.PointerEvent) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    setSelected(ref);
    setDrag(ref);
    svgRef.current?.setPointerCapture(e.pointerId);
  };

  const isPanMode = (e: React.PointerEvent) =>
    e.button === 1 || (e.button === 0 && (spaceRef.current || e.altKey));

  const onPointerDown = (e: React.PointerEvent) => {
    if (isPanMode(e)) {
      e.preventDefault();
      setPanDrag({ startX: e.clientX, startY: e.clientY, startCx: viewport.cx, startCy: viewport.cy });
      svgRef.current?.setPointerCapture(e.pointerId);
      return;
    }
    if (e.button !== 0) return;
    const px = clientToPx(e.clientX, e.clientY);
    if (!px) return;
    const hit = pickHandle(px);
    if (hit) {
      beginHandleDrag(hit, e);
      return;
    }
    if (e.shiftKey) {
      const mm = constrainMm(pxToMm(px));
      const c = closestOnProfile(profile, mm);
      if (c && c.dist < 5) commit(splitSegment(profile, c.seg, c.t));
      return;
    }
    // Left-drag on blank canvas also pans viewport (all targets).
    setPanDrag({ startX: e.clientX, startY: e.clientY, startCx: viewport.cx, startCy: viewport.cy });
    svgRef.current?.setPointerCapture(e.pointerId);
    setSelected(null);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (panDrag) {
      const scale = svgRef.current?.getScreenCTM()?.a ?? 1;
      const dx = (e.clientX - panDrag.startX) / scale;
      const dy = (e.clientY - panDrag.startY) / scale;
      setViewport(vp => clampViewport({ ...vp, cx: panDrag.startCx - dx, cy: panDrag.startCy - dy }, panBounds));
      return;
    }
    if (!drag) return;
    const svg = svgRef.current;
    const px = clientToPx(e.clientX, e.clientY);
    if (!px) return;
    commit(setHandle(profile, drag, constrainMm(pxToMm(px))));
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    setViewport(vp => {
      const rawVb = viewportToViewBox(panBounds, vp);
      const vb = onGrid ? fitViewBoxToAspect(rawVb, canvasAspect) : rawVb;
      const pan = edgePanDelta(vb, e.clientX, e.clientY, rect);
      if (!pan) return vp;
      return clampViewport({ ...vp, cx: vp.cx + pan.dcx, cy: vp.cy + pan.dcy }, panBounds);
    });
  };

  const onPointerUp = (e: React.PointerEvent) => {
    if (panDrag) {
      setPanDrag(null);
      svgRef.current?.releasePointerCapture(e.pointerId);
    }
    if (drag) {
      setDrag(null);
      svgRef.current?.releasePointerCapture(e.pointerId);
    }
  };

  const renderPhotoPath = (p: BezierProfile, stroke: string, opacity: number, width: number, dash?: string) => {
    const d = photoPathFromMmRight(photoMap, p.start, p.segments);
    const md = prefs.showMirror ? photoMirrorPathFromMmRight(photoMap, p.start, p.segments) : null;
    return (
      <g opacity={opacity}>
        {md && <path d={md} fill="none" stroke={stroke} strokeWidth={width * 0.7} strokeDasharray="5 4" />}
        <path d={d} fill="none" stroke={stroke} strokeWidth={width} strokeDasharray={dash} vectorEffect="non-scaling-stroke" />
      </g>
    );
  };

  const renderHandles = (p: BezierProfile) => {
    const svgScale = svgRef.current?.getScreenCTM()?.a ?? 1;
    return handleRefs(p).map(ref => {
      const pt = mmToPx(getHandle(p, ref));
      const isSel = sameRef(selected, ref);
      const isDrag = sameRef(drag, ref);
      const onCurve = isOnCurveAnchor(ref.kind);
      const rPx = onCurve
        ? isSel || isDrag
          ? ANCHOR_R_ON_SEL_PX
          : ANCHOR_R_ON_PX
        : isSel || isDrag
          ? ANCHOR_R_CP_SEL_PX
          : ANCHOR_R_CP_PX;
      const r = rPx / svgScale;
      const strokePx = isSel || isDrag ? 2 : onCurve ? 1.5 : 1;
      return (
        <circle
          key={`${ref.seg}-${ref.kind}`}
          cx={pt.x}
          cy={pt.y}
          r={r}
          fill={KIND_COLOR[ref.kind]}
          stroke={isSel || isDrag ? '#fff' : onCurve ? '#111' : '#444'}
          strokeWidth={strokePx / svgScale}
          style={{ cursor: onCurve ? 'pointer' : 'grab' }}
          onPointerDown={e => beginHandleDrag(ref, e)}
        />
      );
    });
  };

  const renderControlLines = (p: BezierProfile) =>
    p.segments.map((_, i) => {
      const [p0, p1, p2, p3] = segmentPoints(p, i);
      const a = mmToPx(p0);
      const b = mmToPx(p1);
      const c = mmToPx(p2);
      const d = mmToPx(p3);
      return (
        <g key={`seg-${i}`}>
          <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#ffc107" strokeWidth={1} opacity={0.85} vectorEffect="non-scaling-stroke" />
          <line x1={d.x} y1={d.y} x2={c.x} y2={c.y} stroke="#ffc107" strokeWidth={1} opacity={0.85} vectorEffect="non-scaling-stroke" />
        </g>
      );
    });

  const guideLines = [
    { y: PADDLE.tipYMm, label: `拍顶 ${PADDLE.tipYMm}`, color: '#4caf50' },
    { y: PADDLE.handleJoinYMm, label: `柄顶 ${PADDLE.handleJoinYMm}（参考）`, color: '#ff9800' },
    { y: PADDLE.handleJoinYMm - PADDLE.handleLengthMm, label: `柄底 ${PADDLE.handleJoinYMm - PADDLE.handleLengthMm}`, color: '#9c27b0' },
  ];

  const renderGridPath = (p: BezierProfile, stroke: string, width: number, mirror = false) => {
    const parts = [`M ${p.start.x.toFixed(2)} ${(-p.start.y).toFixed(2)}`];
    for (const seg of p.segments) {
      parts.push(
        `C ${seg.cp1.x.toFixed(2)} ${(-seg.cp1.y).toFixed(2)}, ${seg.cp2.x.toFixed(2)} ${(-seg.cp2.y).toFixed(2)}, ${seg.end.x.toFixed(2)} ${(-seg.end.y).toFixed(2)}`,
      );
    }
    const d = parts.join(' ');
    let md: string | null = null;
    if (mirror) {
      const mp = [`M ${(-p.start.x).toFixed(2)} ${(-p.start.y).toFixed(2)}`];
      for (const seg of p.segments) {
        mp.push(
          `C ${(-seg.cp1.x).toFixed(2)} ${(-seg.cp1.y).toFixed(2)}, ${(-seg.cp2.x).toFixed(2)} ${(-seg.cp2.y).toFixed(2)}, ${(-seg.end.x).toFixed(2)} ${(-seg.end.y).toFixed(2)}`,
        );
      }
      md = mp.join(' ');
    }
    return (
      <g>
        {md && <path d={md} fill="none" stroke={stroke} strokeWidth={width * 0.75} strokeDasharray="6 4" opacity={0.55} />}
        <path d={d} fill="none" stroke={stroke} strokeWidth={width} vectorEffect="non-scaling-stroke" />
      </g>
    );
  };

  const viewBox = viewBoxToString(
    onGrid
      ? fitViewBoxToAspect(viewportToViewBox(panBounds, viewport), canvasAspect)
      : viewportToViewBox(panBounds, viewport),
  );

  const selMm = selected ? getHandle(profile, selected) : null;
  const selPx = selMm ? mmToPx(selMm) : null;

  const ghostFront: DrawTarget | null =
    target === 'blade-front' ? 'handle-front' : target === 'handle-front' ? 'blade-front' : null;

  return (
    <div style={{ background: '#14141e', borderRadius: 8, border: '1px solid #2a2a3a', padding: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: meta.stroke }}>
          正在编辑：{meta.label}
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <button type="button" onClick={() => commit(insertAnchorOnSelected(profile, selected))} style={btnStyle}>
            + 锚点
          </button>
          <button
            type="button"
            disabled={!canRemoveAnchor(profile)}
            onClick={() => {
              commit(removeAnchor(profile, selected));
              setSelected(null);
            }}
            style={{ ...btnStyle, ...(!canRemoveAnchor(profile) ? btnDisabledStyle : {}) }}
            title="删除选中锚点；未选中时删最后一个中间锚点"
          >
            − 锚点
          </button>
          <button type="button" onClick={() => commit(defaultProfile(target))} style={btnStyle}>
            重置当前
          </button>
          <button
            type="button"
            onClick={() => {
              navigator.clipboard.writeText(profileToJson(profile));
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            }}
            style={btnStyle}
          >
            {copied ? '已复制' : 'JSON'}
          </button>
          <button type="button" onClick={() => setShowImport(v => !v)} style={btnStyle}>
            导入
          </button>
        </div>
      </div>

      <p style={{ fontSize: 12, color: '#666', margin: '0 0 4px', lineHeight: 1.5 }}>{meta.hint}</p>
      <p style={{ fontSize: 11, color: '#555', margin: '0 0 8px' }}>
        锚点 {anchorCount(profile)} · 红/蓝 = 曲线锚点 · 黄 = 控制柄 · Shift+点击插锚点 · − 或 Delete 删锚点 · 滚轮缩放 · 左键拖动画布平移（或空格/中键/Alt+拖移）
        {onPhoto && ghostFront && (
          <span style={{ color: GHOST_STROKE[ghostFront as 'blade-front' | 'handle-front'] }}>
            {' '}
            · 红=底板 / 蓝=手柄（同时显示）
          </span>
        )}
      </p>

      <div style={{ display: 'flex', gap: 16, marginBottom: 8, fontSize: 12, color: '#777', flexWrap: 'wrap', alignItems: 'center' }}>
        {onPhoto && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            参考图
            <input
              type="range"
              min={20}
              max={100}
              value={prefs.photoOpacity * 100}
              onChange={e => updatePrefs({ photoOpacity: Number(e.target.value) / 100 })}
              style={{ width: 80 }}
            />
          </label>
        )}
        {onGrid && meta.refImage && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            底图透明度
            <input
              type="range"
              min={10}
              max={100}
              value={Math.round(prefs.gridRefOpacity * 100)}
              onChange={e => updatePrefs({ gridRefOpacity: Number(e.target.value) / 100 })}
              style={{ width: 88 }}
            />
            <span style={{ minWidth: 32, fontFamily: 'monospace', fontSize: 11 }}>{Math.round(prefs.gridRefOpacity * 100)}%</span>
          </label>
        )}
        {onGrid && meta.refImage && (
          <button type="button" style={btnStyle} onClick={() => setShowRefCalibrate(v => !v)}>
            {showRefCalibrate ? '收起校准' : '参考图校准'}
          </button>
        )}
        <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input type="checkbox" checked={prefs.showMirror} onChange={e => updatePrefs({ showMirror: e.target.checked })} />
          对称
        </label>
        {onPhoto && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="checkbox" checked={prefs.showGuides} onChange={e => updatePrefs({ showGuides: e.target.checked })} />
            标尺
          </label>
        )}
        <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          缩放
          <button type="button" style={btnStyle} onClick={() => applyZoom(viewport.zoom / 1.25)} title="缩小">
            −
          </button>
          <input
            type="range"
            min={100}
            max={800}
            step={10}
            value={Math.round(viewport.zoom * 100)}
            onChange={e => applyZoom(Number(e.target.value) / 100)}
            style={{ width: 88 }}
          />
          <button type="button" style={btnStyle} onClick={() => applyZoom(viewport.zoom * 1.25)} title="放大">
            +
          </button>
          <span style={{ minWidth: 40, fontFamily: 'monospace', fontSize: 11 }}>{Math.round(viewport.zoom * 100)}%</span>
          <button
            type="button"
            style={btnStyle}
            onClick={resetViewport}
            title={onGrid ? '找回曲线与参考线' : '重置缩放与位置'}
          >
            {onGrid ? '找回视图' : '适应'}
          </button>
        </label>
      </div>

      {onGrid && meta.refImage && showRefCalibrate && (
        <div
          style={{
            marginBottom: 8,
            padding: 10,
            borderRadius: 6,
            border: '1px solid #333',
            background: '#101018',
            fontSize: 12,
            color: '#888',
          }}
        >
          <div style={{ marginBottom: 8, lineHeight: 1.5 }}>
            仅旋转/平移/缩放<strong style={{ color: '#aaa' }}>底图</strong>，mm 参考线位置固定不动。请让柄的长边与竖直虚线（x=0）平行；球拍上的印刷字会随底图一起转。
          </div>
          <div style={{ marginBottom: 8, fontFamily: 'monospace', fontSize: 11, color: '#666' }}>
            当前：缩放 {Math.round(refAdjust.scale * 100)}% · 旋转 {refAdjust.rotateDeg.toFixed(1)}° · 偏移 ({refAdjust.offsetX.toFixed(1)}, {refAdjust.offsetY.toFixed(1)}) mm
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
            <RefSlider
              label="整体缩放"
              min={25}
              max={800}
              step={5}
              value={Math.round(refAdjust.scale * 100)}
              unit="%"
              onChange={v => updateRefAdjust({ scale: v / 100 })}
            />
            <RefSlider
              label="旋转（底图）"
              min={-45}
              max={45}
              step={0.2}
              value={Math.round(refAdjust.rotateDeg * 10) / 10}
              unit="°"
              onChange={v => updateRefAdjust({ rotateDeg: v })}
            />
            <RefSlider
              label="右移 X"
              min={-80}
              max={80}
              step={0.5}
              value={refAdjust.offsetX}
              unit="mm"
              onChange={v => updateRefAdjust({ offsetX: v })}
            />
            <RefSlider
              label="上移 Y"
              min={-80}
              max={80}
              step={0.5}
              value={refAdjust.offsetY}
              unit="mm"
              onChange={v => updateRefAdjust({ offsetY: v })}
            />
          </div>
          <button type="button" style={{ ...btnStyle, marginTop: 8 }} onClick={resetRefAdjust}>
            重置参考图位置
          </button>
        </div>
      )}

      {showImport && (
        <div style={{ marginBottom: 8 }}>
          <textarea value={importText} onChange={e => setImportText(e.target.value)} placeholder="粘贴 JSON…" rows={4} style={textareaStyle} />
          <button
            type="button"
            style={{ ...btnStyle, marginTop: 6 }}
            onClick={() => {
              try {
                const p = parseProfileJson(importText);
                p.target = target;
                commit(p);
                setShowImport(false);
                setImportText('');
              } catch {
                alert('JSON 无效');
              }
            }}
          >
            应用
          </button>
        </div>
      )}

      <div
        ref={canvasWrapRef}
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: onPhoto ? 560 : '100%',
          margin: onPhoto ? '0 auto' : undefined,
          aspectRatio: canvasSize ? `${canvasSize.width} / ${canvasSize.height}` : undefined,
          height: onGrid ? 520 : undefined,
          minHeight: 520,
          background: '#e8e8e4',
          borderRadius: 4,
          border: '1px solid #333',
          overflow: 'hidden',
        }}
      >
        <svg
          ref={svgRef}
          viewBox={viewBox}
          preserveAspectRatio="xMidYMid meet"
          overflow="visible"
          style={{
            display: 'block',
            width: '100%',
            height: onPhoto ? '100%' : 520,
            minHeight: onPhoto ? 520 : 520,
            touchAction: 'none',
            cursor: panDrag || drag ? 'grabbing' : spaceHeld ? 'grab' : 'crosshair',
            userSelect: 'none',
          }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
        >
          {/* workspace background */}
          {onPhoto && canvasSize && (
            <rect x={0} y={0} width={canvasSize.width} height={canvasSize.height} fill="#e8e8e4" />
          )}
          {onGrid && (
            <rect x={panBounds.x} y={panBounds.y} width={panBounds.w} height={panBounds.h} fill="#e8e8e4" />
          )}

          {onPhoto && imgRect && (
            <>
              <rect
                x={imgRect.x}
                y={imgRect.y}
                width={imgRect.width}
                height={imgRect.height}
                fill="#fff"
                stroke="#bbb"
                strokeWidth={1}
              />
              <image
                href={`/refs/${REF_IMAGE}`}
                x={imgRect.x}
                y={imgRect.y}
                width={imgRect.width}
                height={imgRect.height}
                preserveAspectRatio="none"
                opacity={prefs.photoOpacity}
              />
            </>
          )}
          {onPhoto && prefs.showGuides && imgRect && (
            <>
              <line
                x1={imgRect.x + photoMap.cx}
                x2={imgRect.x + photoMap.cx}
                y1={imgRect.y}
                y2={imgRect.y + imgRect.height}
                stroke="#000"
                strokeWidth={0.5}
                opacity={0.2}
              />
              {guideLines.map(g => (
                <g key={g.y}>
                  <line
                    x1={imgRect.x}
                    x2={imgRect.x + imgRect.width}
                    y1={mmYToPhotoY(photoMap, g.y)}
                    y2={mmYToPhotoY(photoMap, g.y)}
                    stroke={g.color}
                    strokeWidth={1}
                    strokeDasharray="6 4"
                    opacity={0.55}
                  />
                  <text x={imgRect.x + 8} y={mmYToPhotoY(photoMap, g.y) - 4} fontSize={11} fill={g.color} opacity={0.75}>
                    {g.label}
                  </text>
                </g>
              ))}
            </>
          )}

          {!onPhoto && onGrid && (
            <>
              {[0, 5, 10, 15].map(x => (
                <line
                  key={`gx-${x}`}
                  x1={x}
                  x2={x}
                  y1={-gridBounds.yMax}
                  y2={-gridBounds.yMin}
                  stroke={x === 0 || x === 10 ? '#bdbdbd' : '#d8d8d8'}
                  strokeWidth={x === 0 || x === 10 ? 0.55 : 0.35}
                />
              ))}
              {target === 'side' &&
                [-150, -100, -78.5, 0, 50, 78.5].map(y => (
                  <line
                    key={`gy-${y}`}
                    x1={gridBounds.xMin}
                    x2={gridBounds.xMax}
                    y1={-y}
                    y2={-y}
                    stroke={y === PADDLE.handleJoinYMm || y === PADDLE.handleJoinYMm - PADDLE.handleLengthMm ? '#bdbdbd' : '#d8d8d8'}
                    strokeWidth={y === PADDLE.handleJoinYMm || y === PADDLE.handleJoinYMm - PADDLE.handleLengthMm ? 0.55 : 0.35}
                  />
                ))}
              {target === 'handle-bottom' &&
                [-12, -6, 0, 6, 12].map(y => (
                  <line
                    key={`gy-${y}`}
                    x1={gridBounds.xMin}
                    x2={gridBounds.xMax}
                    y1={-y}
                    y2={-y}
                    stroke={y === 0 ? '#bdbdbd' : '#d8d8d8'}
                    strokeWidth={y === 0 ? 0.55 : 0.35}
                  />
                ))}
            </>
          )}
          {!onPhoto && onGrid && refSvgRect && refImageBox && meta.refImage && (() => {
            const center = refImageCenterSvg(refImageBox);
            const rot = refAdjust.rotateDeg;
            const tf = `rotate(${rot} ${center.x} ${center.y})`;
            const svgScale = svgRef.current?.getScreenCTM()?.a ?? 1;
            const pivotR = 4 / svgScale;
            return (
              <>
                <g transform={tf}>
                  <rect
                    x={refSvgRect.x}
                    y={refSvgRect.y}
                    width={refSvgRect.width}
                    height={refSvgRect.height}
                    fill="#fff"
                    stroke="#bbb"
                    strokeWidth={0.5}
                  />
                  <image
                    href={`/refs/${meta.refImage}?v=2`}
                    x={refSvgRect.x}
                    y={refSvgRect.y}
                    width={refSvgRect.width}
                    height={refSvgRect.height}
                    preserveAspectRatio="xMidYMid slice"
                    opacity={prefs.gridRefOpacity}
                  />
                  <rect
                    x={refSvgRect.x}
                    y={refSvgRect.y}
                    width={refSvgRect.width}
                    height={refSvgRect.height}
                    fill="none"
                    stroke="#1565c0"
                    strokeWidth={0.8}
                    strokeDasharray="5 3"
                    opacity={0.55}
                    pointerEvents="none"
                  />
                </g>
                {showRefCalibrate && (
                  <g pointerEvents="none" opacity={0.9}>
                    <line
                      x1={center.x - pivotR * 4}
                      x2={center.x + pivotR * 4}
                      y1={center.y}
                      y2={center.y}
                      stroke="#e65100"
                      strokeWidth={1.5 / svgScale}
                    />
                    <line
                      x1={center.x}
                      x2={center.x}
                      y1={center.y - pivotR * 4}
                      y2={center.y + pivotR * 4}
                      stroke="#e65100"
                      strokeWidth={1.5 / svgScale}
                    />
                    <circle cx={center.x} cy={center.y} r={pivotR} fill="#e65100" />
                  </g>
                )}
              </>
            );
          })()}
          {!onPhoto && onGrid && renderGridGuideOverlay(target, gridBounds)}
          {onGrid && target === 'handle-bottom' && prefs.showMirror && (
            <line
              x1={0}
              x2={0}
              y1={-gridBounds.yMax}
              y2={-gridBounds.yMin}
              stroke="#37474f"
              strokeWidth={1}
              strokeDasharray="5 3"
              opacity={0.75}
            />
          )}

          {/* ghost: the other front profile */}
          {onPhoto && ghostFront && renderPhotoPath(profiles[ghostFront], GHOST_STROKE[ghostFront], 0.55, 2, '6 4')}

          {/* active profile */}
          {onPhoto
            ? renderPhotoPath(profile, meta.stroke, 1, 2.5)
            : renderGridPath(profile, meta.stroke, 2.5, prefs.showMirror && (target === 'handle-bottom' || target === 'side'))}

          {renderControlLines(profile)}
          {renderHandles(profile)}
        </svg>
      </div>

      {selMm && selPx && (
        <div style={{ marginTop: 8, fontSize: 11, color: '#888', fontFamily: 'monospace' }}>
          {selected!.kind} · mm ({selMm.x.toFixed(2)}, {selMm.y.toFixed(2)})
          {onPhoto && ` · px (${selPx.x.toFixed(1)}, ${selPx.y.toFixed(1)})`}
        </div>
      )}
    </div>
  );
}

function onGridTarget(t: DrawTarget): t is RefGridTarget {
  return t === 'side' || t === 'handle-bottom';
}

function renderGridGuideOverlay(target: DrawTarget, bounds: { xMin: number; xMax: number; yMin: number; yMax: number }) {
  const handleBottomY = PADDLE.handleJoinYMm - PADDLE.handleLengthMm;
  const guides: { kind: 'h' | 'v'; pos: number; label: string; color: string; dash?: string }[] =
    target === 'side'
      ? [
          { kind: 'h', pos: PADDLE.handleJoinYMm, label: `柄顶 ${PADDLE.handleJoinYMm}`, color: '#e65100' },
          { kind: 'h', pos: handleBottomY, label: `柄底 ${handleBottomY}`, color: '#7b1fa2' },
          { kind: 'v', pos: 0, label: 'x=0 中心', color: '#263238', dash: '6 4' },
          { kind: 'v', pos: 10, label: 'x=10', color: '#455a64', dash: '4 4' },
        ]
      : [
          { kind: 'h', pos: 0, label: 'y=0 中心', color: '#263238', dash: '6 4' },
          { kind: 'v', pos: 0, label: 'x=0 对称', color: '#263238', dash: '6 4' },
          { kind: 'v', pos: 10, label: 'x=10 半宽', color: '#455a64', dash: '4 4' },
          { kind: 'h', pos: 6.25, label: 'y=6.25 半厚', color: '#455a64', dash: '4 4' },
        ];

  return (
    <g pointerEvents="none">
      {guides.map(g => {
        const svgY = -g.pos;
        const labelX = bounds.xMin + 1.2;
        const labelY = g.kind === 'h' ? svgY - 1.2 : svgY + 3.5;
        return (
          <g key={`${g.kind}-${g.pos}-${g.label}`}>
            {g.kind === 'h' ? (
              <line
                x1={bounds.xMin}
                x2={bounds.xMax}
                y1={svgY}
                y2={svgY}
                stroke={g.color}
                strokeWidth={1.4}
                strokeDasharray={g.dash}
                opacity={0.92}
              />
            ) : (
              <line
                x1={g.pos}
                x2={g.pos}
                y1={-bounds.yMax}
                y2={-bounds.yMin}
                stroke={g.color}
                strokeWidth={1.4}
                strokeDasharray={g.dash}
                opacity={0.92}
              />
            )}
            <text x={labelX} y={labelY} fontSize={10.5} fontWeight={600} fill={g.color} opacity={0.95}>
              {g.label}
            </text>
          </g>
        );
      })}
    </g>
  );
}

function RefSlider({
  label,
  min,
  max,
  step = 1,
  value,
  unit,
  onChange,
}: {
  label: string;
  min: number;
  max: number;
  step?: number;
  value: number;
  unit: string;
  onChange: (v: number) => void;
}) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span>
        {label}{' '}
        <span style={{ fontFamily: 'monospace', color: '#aaa' }}>
          {value}
          {unit}
        </span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
      />
    </label>
  );
}

const btnStyle: React.CSSProperties = {
  padding: '4px 10px',
  fontSize: 12,
  border: '1px solid #333',
  borderRadius: 4,
  background: '#1a1a28',
  color: '#aaa',
  cursor: 'pointer',
};

const btnDisabledStyle: React.CSSProperties = {
  opacity: 0.35,
  cursor: 'not-allowed',
};

const textareaStyle: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  background: '#0c0c14',
  color: '#ccc',
  border: '1px solid #333',
  borderRadius: 4,
  fontSize: 11,
  fontFamily: 'monospace',
  padding: 8,
};
