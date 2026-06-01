/** Cubic Bezier profiles in paddle mm (y-up). */

import { PADDLE } from './paddleModel';

export type Pt = { x: number; y: number };

export type BezierSegment = { cp1: Pt; cp2: Pt; end: Pt };

/** blade-front / handle-front = CA.media.02; side = side thickness; handle-bottom = butt cross-section */
export type DrawTarget = 'blade-front' | 'handle-front' | 'side' | 'handle-bottom';

export type BezierProfile = {
  target: DrawTarget;
  start: Pt;
  segments: BezierSegment[];
};

export type BezierHandleKind = 'start' | 'cp1' | 'cp2' | 'end';

export type BezierHandleRef = { seg: number; kind: BezierHandleKind };

const STORAGE_PREFIX = 'smartpaddle-bezier-';

export function storageKey(target: DrawTarget): string {
  return `${STORAGE_PREFIX}${target}`;
}

export function loadProfile(target: DrawTarget): BezierProfile {
  try {
    const raw = localStorage.getItem(storageKey(target));
    if (raw) {
      const parsed = JSON.parse(raw) as BezierProfile;
      if (parsed.target === target && parsed.start && Array.isArray(parsed.segments)) return parsed;
    }
  } catch {
    /* ignore */
  }
  return defaultProfile(target);
}

export function saveProfile(profile: BezierProfile): void {
  localStorage.setItem(storageKey(profile.target), JSON.stringify(profile));
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('smartpaddle-profiles-updated'));
  }
}

export function defaultProfile(target: DrawTarget): BezierProfile {
  const join = PADDLE.handleJoinYMm;
  const tip = PADDLE.tipYMm;
  const bottom = join - PADDLE.handleLengthMm;

  if (target === 'blade-front') {
    return {
      target,
      start: { x: 0, y: tip },
      segments: [
        { cp1: { x: 35, y: 72 }, cp2: { x: 72, y: 35 }, end: { x: 74, y: 0 } },
        { cp1: { x: 75, y: -30 }, cp2: { x: 68, y: -58 }, end: { x: 55, y: -68 } },
        { cp1: { x: 38, y: -82 }, cp2: { x: 14, y: -92 }, end: { x: 9, y: -105 } },
      ],
    };
  }
  if (target === 'handle-front') {
    return {
      target,
      start: { x: 12, y: join },
      segments: [
        { cp1: { x: 12, y: join - 20 }, cp2: { x: 11.5, y: join - 45 }, end: { x: 12, y: join - 70 } },
        { cp1: { x: 12.5, y: join - 95 }, cp2: { x: 14, y: join - 130 }, end: { x: 15.5, y: join - 165 } },
        { cp1: { x: 16, y: bottom + 8 }, cp2: { x: 14, y: bottom + 3 }, end: { x: 12, y: bottom } },
      ],
    };
  }
  if (target === 'handle-bottom') {
    // Right-half outer edge of FL butt (mm): x = half-width, y = half-thickness
    return {
      target,
      start: { x: 0, y: 12.5 },
      segments: [
        { cp1: { x: 10, y: 12.8 }, cp2: { x: 17, y: 10.5 }, end: { x: 17, y: 4 } },
        { cp1: { x: 17, y: -2 }, cp2: { x: 17, y: -9 }, end: { x: 10, y: -12.5 } },
        { cp1: { x: 4, y: -12.5 }, cp2: { x: 0, y: -12.2 }, end: { x: 0, y: -12.5 } },
      ],
    };
  }
  const bladeHalf = (PADDLE.bladeCoreThicknessMm + PADDLE.rubberThicknessMm * 2) / 2;
  const handleHalf = PADDLE.handleThicknessMm / 2;
  return {
    target: 'side',
    start: { x: bladeHalf, y: tip },
    segments: [
      { cp1: { x: bladeHalf, y: 40 }, cp2: { x: bladeHalf, y: -20 }, end: { x: bladeHalf, y: join } },
      { cp1: { x: bladeHalf, y: join - 25 }, cp2: { x: handleHalf, y: join - 60 }, end: { x: handleHalf, y: bottom } },
    ],
  };
}

export function yRangeForTarget(target: DrawTarget): { yMin: number; yMax: number } {
  const join = PADDLE.handleJoinYMm;
  const tip = PADDLE.tipYMm;
  const bottom = join - PADDLE.handleLengthMm;
  if (target === 'blade-front') return { yMin: join, yMax: tip };
  if (target === 'handle-front') return { yMin: bottom, yMax: join };
  if (target === 'handle-bottom') return { yMin: -14, yMax: 14 };
  return { yMin: bottom, yMax: tip };
}

export function cubicAt(p0: Pt, p1: Pt, p2: Pt, p3: Pt, t: number): Pt {
  const u = 1 - t;
  return {
    x: u * u * u * p0.x + 3 * u * u * t * p1.x + 3 * u * t * t * p2.x + t * t * t * p3.x,
    y: u * u * u * p0.y + 3 * u * u * t * p1.y + 3 * u * t * t * p2.y + t * t * t * p3.y,
  };
}

export function segmentPoints(profile: BezierProfile, segIdx: number): [Pt, Pt, Pt, Pt] {
  const seg = profile.segments[segIdx];
  const start = segIdx === 0 ? profile.start : profile.segments[segIdx - 1].end;
  return [start, seg.cp1, seg.cp2, seg.end];
}

function cloneProfile(profile: BezierProfile): BezierProfile {
  return {
    target: profile.target,
    start: { ...profile.start },
    segments: profile.segments.map(s => ({ cp1: { ...s.cp1 }, cp2: { ...s.cp2 }, end: { ...s.end } })),
  };
}

export function getHandle(profile: BezierProfile, ref: BezierHandleRef): Pt {
  if (ref.kind === 'start') return profile.start;
  const seg = profile.segments[ref.seg];
  if (ref.kind === 'cp1') return seg.cp1;
  if (ref.kind === 'cp2') return seg.cp2;
  return seg.end;
}

export function setHandle(profile: BezierProfile, ref: BezierHandleRef, pt: Pt): BezierProfile {
  const next = cloneProfile(profile);
  if (ref.kind === 'start') {
    next.start = pt;
    return next;
  }
  const seg = next.segments[ref.seg];
  if (ref.kind === 'cp1') seg.cp1 = pt;
  else if (ref.kind === 'cp2') seg.cp2 = pt;
  else seg.end = pt;
  return next;
}

function lerp(a: Pt, b: Pt, t: number): Pt {
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
}

/** Split cubic segment at t (inserts anchor). */
export function splitSegment(profile: BezierProfile, segIdx: number, t = 0.5): BezierProfile {
  if (segIdx < 0 || segIdx >= profile.segments.length) return profile;
  const [p0, p1, p2, p3] = segmentPoints(profile, segIdx);
  const m01 = lerp(p0, p1, t);
  const m12 = lerp(p1, p2, t);
  const m23 = lerp(p2, p3, t);
  const m012 = lerp(m01, m12, t);
  const m123 = lerp(m12, m23, t);
  const mid = lerp(m012, m123, t);

  const next = cloneProfile(profile);
  next.segments.splice(segIdx, 1, { cp1: m01, cp2: m012, end: mid }, { cp1: m123, cp2: m23, end: p3 });
  return next;
}

export function mergeAnchorAt(profile: BezierProfile, endSegIdx: number): BezierProfile {
  if (profile.segments.length <= 1) return profile;
  if (endSegIdx < 0 || endSegIdx >= profile.segments.length - 1) return profile;
  const next = cloneProfile(profile);
  const left = next.segments[endSegIdx];
  const right = next.segments[endSegIdx + 1];
  next.segments.splice(endSegIdx, 2, { cp1: left.cp1, cp2: right.cp2, end: right.end });
  return next;
}

export function removeLastSegment(profile: BezierProfile): BezierProfile {
  if (profile.segments.length <= 1) return profile;
  const next = cloneProfile(profile);
  next.segments.pop();
  return next;
}

export function addSegment(profile: BezierProfile): BezierProfile {
  const last = profile.segments[profile.segments.length - 1]?.end ?? profile.start;
  const seg: BezierSegment = {
    cp1: { x: last.x, y: last.y - 12 },
    cp2: { x: last.x, y: last.y - 24 },
    end: { x: last.x, y: last.y - 36 },
  };
  return { ...cloneProfile(profile), segments: [...profile.segments, seg] };
}

export function anchorCount(profile: BezierProfile): number {
  return 1 + profile.segments.length;
}

/** Remove first segment; advance start to former first anchor. */
function removeStartAnchor(profile: BezierProfile): BezierProfile {
  if (profile.segments.length <= 1) return profile;
  const next = cloneProfile(profile);
  next.start = { ...next.segments[0].end };
  next.segments.shift();
  return next;
}

export function canRemoveAnchor(profile: BezierProfile): boolean {
  return profile.segments.length > 1;
}

/** Remove last interior anchor when nothing is selected. */
export function removeDefaultAnchor(profile: BezierProfile): BezierProfile {
  if (profile.segments.length <= 1) return profile;
  if (profile.segments.length === 2) return removeLastSegment(profile);
  return mergeAnchorAt(profile, profile.segments.length - 2);
}

export function removeAnchor(profile: BezierProfile, ref: BezierHandleRef | null): BezierProfile {
  if (!canRemoveAnchor(profile)) return profile;
  if (ref) return removeSelectedAnchor(profile, ref);
  return removeDefaultAnchor(profile);
}

export function removeSelectedAnchor(profile: BezierProfile, ref: BezierHandleRef | null): BezierProfile {
  if (profile.segments.length <= 1 || !ref) return profile;
  const r = ref;

  if (r.kind === 'start') return removeStartAnchor(profile);

  if (r.kind === 'cp1' || r.kind === 'cp2') {
    return removeSelectedAnchor(profile, { seg: r.seg, kind: 'end' });
  }

  if (r.kind === 'end') {
    if (r.seg < profile.segments.length - 1) return mergeAnchorAt(profile, r.seg);
    return removeLastSegment(profile);
  }

  return profile;
}

export function insertAnchorOnSelected(profile: BezierProfile, ref: BezierHandleRef | null): BezierProfile {
  if (ref?.kind === 'end' && ref.seg < profile.segments.length) return splitSegment(profile, ref.seg, 0.5);
  if (ref?.kind === 'cp1' || ref?.kind === 'cp2') return splitSegment(profile, ref.seg, 0.5);
  if (ref?.kind === 'start' && profile.segments.length > 0) return splitSegment(profile, 0, 0.5);
  return splitSegment(profile, profile.segments.length - 1, 0.5);
}

export function closestOnProfile(profile: BezierProfile, pt: Pt): { seg: number; t: number; dist: number } | null {
  let best: { seg: number; t: number; dist: number } | null = null;
  for (let i = 0; i < profile.segments.length; i++) {
    const [p0, p1, p2, p3] = segmentPoints(profile, i);
    for (let j = 0; j <= 40; j++) {
      const t = j / 40;
      const c = cubicAt(p0, p1, p2, p3, t);
      const d = Math.hypot(c.x - pt.x, c.y - pt.y);
      if (!best || d < best.dist) best = { seg: i, t, dist: d };
    }
  }
  return best;
}

export function profileToSvgPathMm(profile: BezierProfile): string {
  if (profile.segments.length === 0) return '';
  const parts = [`M ${profile.start.x.toFixed(2)} ${(-profile.start.y).toFixed(2)}`];
  for (const seg of profile.segments) {
    parts.push(
      `C ${seg.cp1.x.toFixed(2)} ${(-seg.cp1.y).toFixed(2)}, ${seg.cp2.x.toFixed(2)} ${(-seg.cp2.y).toFixed(2)}, ${seg.end.x.toFixed(2)} ${(-seg.end.y).toFixed(2)}`,
    );
  }
  return parts.join(' ');
}

export function mirroredProfilePathMm(profile: BezierProfile): string {
  const parts = [`M ${(-profile.start.x).toFixed(2)} ${(-profile.start.y).toFixed(2)}`];
  for (const seg of profile.segments) {
    parts.push(
      `C ${(-seg.cp1.x).toFixed(2)} ${(-seg.cp1.y).toFixed(2)}, ${(-seg.cp2.x).toFixed(2)} ${(-seg.cp2.y).toFixed(2)}, ${(-seg.end.x).toFixed(2)} ${(-seg.end.y).toFixed(2)}`,
    );
  }
  return parts.join(' ');
}

export function viewBoundsSide(): { xMin: number; xMax: number; yMin: number; yMax: number } {
  const bottom = PADDLE.handleJoinYMm - PADDLE.handleLengthMm;
  const pad = 15;
  return { xMin: -pad, xMax: 35, yMin: bottom - pad, yMax: PADDLE.tipYMm + pad };
}

export function viewBoundsBottom(): { xMin: number; xMax: number; yMin: number; yMax: number } {
  return { xMin: -2, xMax: 22, yMin: -16, yMax: 16 };
}

export function profileToJson(profile: BezierProfile): string {
  return JSON.stringify(profile, null, 2);
}

export function parseProfileJson(text: string): BezierProfile {
  const parsed = JSON.parse(text) as BezierProfile;
  if (!parsed.start || !Array.isArray(parsed.segments)) throw new Error('invalid profile');
  return parsed;
}

export function handleRefs(profile: BezierProfile): BezierHandleRef[] {
  const refs: BezierHandleRef[] = [{ seg: 0, kind: 'start' }];
  profile.segments.forEach((_, i) => {
    refs.push({ seg: i, kind: 'cp1' }, { seg: i, kind: 'cp2' }, { seg: i, kind: 'end' });
  });
  return refs;
}
