/** mm grid editors (side / handle-bottom) with optional reference photo overlay. */

export type GridBounds = { xMin: number; xMax: number; yMin: number; yMax: number };

/** Full image rect in mm (y-up): x right, y up. */
export type RefImageBox = { x0: number; y0: number; x1: number; y1: number };

export type RefGridTarget = 'side' | 'handle-bottom';

export type RefImageAdjust = {
  offsetX: number;
  offsetY: number;
  /** Uniform scale around box center (aspect ratio preserved). */
  scale: number;
  /** Degrees, clockwise in screen space; pivot = box center. */
  rotateDeg: number;
};

const REF_LAYOUT_KEY = 'smartpaddle-ref-layout';

export const DEFAULT_REF_ADJUST: RefImageAdjust = { offsetX: 0, offsetY: 0, scale: 1, rotateDeg: 0 };

export function defaultRefAdjust(target: RefGridTarget): RefImageAdjust {
  // Phone photos include lots of background; start enlarged so the handle fills the mm grid.
  if (target === 'side') return { offsetX: 0, offsetY: 0, scale: 5, rotateDeg: 0 };
  if (target === 'handle-bottom') return { offsetX: 0, offsetY: 0, scale: 8, rotateDeg: 0 };
  return { ...DEFAULT_REF_ADJUST };
}

export function loadRefAdjust(target: RefGridTarget): RefImageAdjust {
  try {
    const raw = localStorage.getItem(REF_LAYOUT_KEY);
    if (raw) {
      const all = JSON.parse(raw) as Partial<Record<RefGridTarget, RefImageAdjust>>;
      const a = all[target];
      if (a && typeof a.scale === 'number') {
        const merged = { ...DEFAULT_REF_ADJUST, ...a };
        // Old UI capped scale at 112%; bump tiny saved values to usable defaults.
        if (merged.scale <= 1.12) merged.scale = defaultRefAdjust(target).scale;
        return merged;
      }
      // migrate legacy scaleX / scaleY
      const leg = a as unknown as { offsetX?: number; offsetY?: number; scaleX?: number; scaleY?: number };
      if (typeof leg.scaleX === 'number') {
        const s = leg.scaleY != null ? (leg.scaleX + leg.scaleY) / 2 : leg.scaleX;
        return { offsetX: leg.offsetX ?? 0, offsetY: leg.offsetY ?? 0, scale: s, rotateDeg: 0 };
      }
    }
  } catch {
    /* ignore */
  }
  return defaultRefAdjust(target);
}

export function saveRefAdjust(target: RefGridTarget, adjust: RefImageAdjust): void {
  try {
    const raw = localStorage.getItem(REF_LAYOUT_KEY);
    const all = raw ? (JSON.parse(raw) as Partial<Record<RefGridTarget, RefImageAdjust>>) : {};
    all[target] = adjust;
    localStorage.setItem(REF_LAYOUT_KEY, JSON.stringify(all));
  } catch {
    /* ignore */
  }
}

export function applyRefAdjust(base: RefImageBox, adj: RefImageAdjust): RefImageBox {
  const cx = (base.x0 + base.x1) / 2 + adj.offsetX;
  const cy = (base.y0 + base.y1) / 2 + adj.offsetY;
  const hw = ((base.x1 - base.x0) / 2) * adj.scale;
  const hh = ((base.y1 - base.y0) / 2) * adj.scale;
  return { x0: cx - hw, y0: cy - hh, x1: cx + hw, y1: cy + hh };
}

export function gridViewBoxString(b: GridBounds): string {
  const w = b.xMax - b.xMin;
  const h = b.yMax - b.yMin;
  return `${b.xMin} ${-b.yMax} ${w} ${h}`;
}

export function mmGridToSvg(mm: { x: number; y: number }): { x: number; y: number } {
  return { x: mm.x, y: -mm.y };
}

export function svgGridToMm(px: { x: number; y: number }): { x: number; y: number } {
  return { x: px.x, y: -px.y };
}

export function refImageCenterSvg(box: RefImageBox): { x: number; y: number } {
  return mmGridToSvg({ x: (box.x0 + box.x1) / 2, y: (box.y0 + box.y1) / 2 });
}

export function refImageSvgRect(box: RefImageBox): { x: number; y: number; width: number; height: number } {
  const a = mmGridToSvg({ x: box.x0, y: box.y0 });
  const b = mmGridToSvg({ x: box.x1, y: box.y1 });
  return {
    x: Math.min(a.x, b.x),
    y: Math.min(a.y, b.y),
    width: Math.abs(b.x - a.x),
    height: Math.abs(b.y - a.y),
  };
}

/** Side profile: x = half-thickness, y = paddle axis (tip +78.5 → butt -178.5). */
export const SIDE_GRID: GridBounds = { xMin: -4, xMax: 24, yMin: -190, yMax: 90 };

/** Default viewport focus for handle region on side tab. */
export const SIDE_HANDLE_FOCUS = { cx: 10, cy: -128, zoom: 3.2 };

export const SIDE_REF = {
  image: 'handle_side_ref.jpg',
  /** Photo: handle side; x ≈ thickness 0–18 mm, y ≈ handle -180 – -75 mm */
  box: { x0: -0.5, y0: -181, x1: 19.5, y1: -74 } satisfies RefImageBox,
};

/** Butt cross-section: x = half-width, y = half-thickness (FL bottom ≈ 17 × 12.5 mm). */
export const BOTTOM_GRID: GridBounds = { xMin: -2, xMax: 22, yMin: -16, yMax: 16 };

export const BOTTOM_FOCUS = { cx: 10, cy: 0, zoom: 2.8 };

export const BOTTOM_REF = {
  image: 'handle_butt_ref.jpg',
  box: { x0: -0.5, y0: -13.5, x1: 18.5, y1: 13.5 } satisfies RefImageBox,
};

export function workspaceBounds(grid: GridBounds, _refBox?: RefImageBox | null, padMm = 60): GridBounds {
  return {
    xMin: grid.xMin - padMm,
    xMax: grid.xMax + padMm,
    yMin: grid.yMin - padMm,
    yMax: grid.yMax + padMm,
  };
}

export function boundsToViewBox(b: GridBounds): { x: number; y: number; w: number; h: number } {
  return { x: b.xMin, y: -b.yMax, w: b.xMax - b.xMin, h: b.yMax - b.yMin };
}

export function defaultGridViewport(target: RefGridTarget, bounds: GridBounds, zoomPref = 1): {
  cx: number;
  cy: number;
  zoom: number;
} {
  if (target === 'side') return { ...SIDE_HANDLE_FOCUS, zoom: SIDE_HANDLE_FOCUS.zoom * zoomPref };
  if (target === 'handle-bottom') return { ...BOTTOM_FOCUS, zoom: BOTTOM_FOCUS.zoom * zoomPref };
  return { cx: (bounds.xMin + bounds.xMax) / 2, cy: (bounds.yMin + bounds.yMax) / 2, zoom: zoomPref };
}
