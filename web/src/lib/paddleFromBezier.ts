/** Build Three.js paddle geometry from hand-drawn Bezier profiles (mm, y-up). */

import * as THREE from 'three';
import { mergeVertices } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { BezierProfile, cubicAt, segmentPoints } from './bezierProfile';

const MM = 0.01;

/** Set false to preview wood + handle only (no rubber sheets). */
export const RENDER_RUBBER_LAYERS = true;

const DEFAULT_DIMS = {
  coreThicknessMm: 5.8,
  rubberThicknessMm: 1.8,
  handleThicknessMm: 25,
  handleJoinYMm: -78.5,
  handleBottomYMm: -178.5,
};

function clipOpenPolylineAtMinY(pts: { x: number; y: number }[], yMin: number): { x: number; y: number }[] {
  if (pts.length < 2) return pts;
  const out: { x: number; y: number }[] = [];
  if (pts[0].y >= yMin) out.push({ ...pts[0] });
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1];
    const b = pts[i];
    if (a.y >= yMin && b.y >= yMin) {
      out.push({ ...b });
    } else if (a.y >= yMin && b.y < yMin) {
      const t = (yMin - a.y) / (b.y - a.y);
      out.push({ x: a.x + t * (b.x - a.x), y: yMin });
    } else if (a.y < yMin && b.y >= yMin) {
      const t = (yMin - a.y) / (b.y - a.y);
      out.push({ x: a.x + t * (b.x - a.x), y: yMin });
      out.push({ ...b });
    }
  }
  return out.length >= 2 ? out : pts;
}

function handleMaterial(color = 0x1a2744): THREE.MeshPhongMaterial {
  return new THREE.MeshPhongMaterial({
    color,
    specular: 0x223355,
    shininess: 18,
    // Keep both sides visible to avoid artifacts if local loft triangles flip.
    side: THREE.DoubleSide,
    depthWrite: true,
    transparent: false,
  });
}

function roundedRectShape(w: number, h: number, r: number): THREE.Shape {
  const hw = w / 2;
  const hh = h / 2;
  r = Math.min(r, hw - 0.001, hh - 0.001);
  const s = new THREE.Shape();
  s.moveTo(-hw + r, -hh);
  s.lineTo(hw - r, -hh);
  s.quadraticCurveTo(hw, -hh, hw, -hh + r);
  s.lineTo(hw, hh - r);
  s.quadraticCurveTo(hw, hh, hw - r, hh);
  s.lineTo(-hw + r, hh);
  s.quadraticCurveTo(-hw, hh, -hw, hh - r);
  s.lineTo(-hw, -hh + r);
  s.quadraticCurveTo(-hw, -hh, -hw + r, -hh);
  return s;
}

export type PaddleProfiles = {
  blade: BezierProfile;
  handle: BezierProfile;
  side?: BezierProfile | null;
  handleBottom?: BezierProfile | null;
};

function resampleClosedRing(points: { x: number; z: number }[], count: number): { x: number; z: number }[] {
  if (points.length < 3) return points;
  const dists: number[] = [0];
  for (let i = 1; i < points.length; i++) {
    const dx = points[i].x - points[i - 1].x;
    const dz = points[i].z - points[i - 1].z;
    dists.push(dists[i - 1] + Math.hypot(dx, dz));
  }
  const closeDx = points[0].x - points[points.length - 1].x;
  const closeDz = points[0].z - points[points.length - 1].z;
  const total = dists[dists.length - 1] + Math.hypot(closeDx, closeDz);
  const out: { x: number; z: number }[] = [];
  for (let i = 0; i < count; i++) {
    const target = (i / count) * total;
    let j = 0;
    while (j < dists.length - 1 && dists[j + 1] < target) j++;
    const a = points[j];
    const b = points[(j + 1) % points.length];
    const segStart = dists[j];
    const segEnd = j < dists.length - 1 ? dists[j + 1] : total;
    const t = segEnd > segStart ? (target - segStart) / (segEnd - segStart) : 0;
    out.push({ x: a.x + (b.x - a.x) * t, z: a.z + (b.z - a.z) * t });
  }
  return out;
}

function bottomProfileExtents(bottom: BezierProfile): { baseHalfW: number; baseHalfT: number } {
  const pts = sampleProfilePoints(bottom, 48);
  return {
    baseHalfW: Math.max(1, ...pts.map(p => Math.max(p.x, 0))),
    baseHalfT: Math.max(1, ...pts.map(p => Math.abs(p.y))),
  };
}

/** Closed ring in (x=halfW, z=halfT) from butt profile right edge. */
function sampleButtCrossSectionRing(bottom: BezierProfile, ringSegments: number): { x: number; z: number }[] {
  const pts = sampleProfilePoints(bottom, 36);
  const loop: { x: number; z: number }[] = pts.map(p => ({ x: Math.max(p.x, 0), z: p.y }));
  const last = loop[loop.length - 1];
  if (last.x > 0.01) loop.push({ x: -last.x, z: last.z });
  for (let i = pts.length - 2; i >= 0; i--) {
    loop.push({ x: -Math.max(pts[i].x, 0), z: pts[i].y });
  }
  return resampleClosedRing(loop, ringSegments);
}

/**
 * Loft handle: cross-section shape from handle-bottom profile, scaled at each height
 * by handle-front (width) and side (thickness).
 */
export function createLoftedHandleGeometry(
  front: BezierProfile,
  bottom: BezierProfile,
  side: BezierProfile | null | undefined,
  slices = 56,
  ringSegments = 40,
): THREE.BufferGeometry {
  const { baseHalfW, baseHalfT } = bottomProfileExtents(bottom);
  const handlePts = sampleProfilePoints(front, 48);
  const joinY = DEFAULT_DIMS.handleJoinYMm;
  // Leave a small gap from blade neck to reduce depth-fighting / interpenetration artifacts.
  const topY = Math.min(Math.max(...handlePts.map(p => p.y)), joinY - 0.6);
  const bottomY = Math.min(...handlePts.map(p => p.y));
  const ringTemplate = sampleButtCrossSectionRing(bottom, ringSegments);
  const sliceCount = Math.max(slices, 2);

  const positions: number[] = [];
  const indices: number[] = [];

  for (let s = 0; s < sliceCount; s++) {
    const t = s / (sliceCount - 1);
    const y = bottomY + t * (topY - bottomY);
    const hw = halfWidthAtY(front, y);
    const ht = side ? halfWidthAtY(side, y) : baseHalfT * (hw / baseHalfW);
    const sx = Math.max(hw / baseHalfW, 0.05);
    const sz = Math.max(Math.max(ht, 0.5) / baseHalfT, 0.05);
    for (const p of ringTemplate) {
      positions.push(p.x * sx * MM, y * MM, p.z * sz * MM);
    }
  }

  for (let s = 0; s < sliceCount - 1; s++) {
    for (let r = 0; r < ringSegments; r++) {
      const a = s * ringSegments + r;
      const b = s * ringSegments + ((r + 1) % ringSegments);
      const c = (s + 1) * ringSegments + r;
      const d = (s + 1) * ringSegments + ((r + 1) % ringSegments);
      indices.push(a, c, b, b, c, d);
    }
  }

  // Bottom cap (outward −Y)
  const bottomCenter = positions.length / 3;
  positions.push(0, bottomY * MM, 0);
  for (let r = 0; r < ringSegments; r++) {
    const a = r;
    const b = (r + 1) % ringSegments;
    indices.push(bottomCenter, b, a);
  }

  // Top cap (outward +Y)
  const topRingStart = (sliceCount - 1) * ringSegments;
  const topCenter = positions.length / 3;
  positions.push(0, topY * MM, 0);
  for (let r = 0; r < ringSegments; r++) {
    const a = topRingStart + r;
    const b = topRingStart + ((r + 1) % ringSegments);
    indices.push(topCenter, a, b);
  }

  let geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geo.setIndex(indices);
  geo = mergeVertices(geo);
  geo.computeVertexNormals();
  geo.normalizeNormals();
  return geo;
}

export function sampleProfilePoints(profile: BezierProfile, stepsPerSeg = 32): { x: number; y: number }[] {
  const pts: { x: number; y: number }[] = [{ ...profile.start }];
  for (let i = 0; i < profile.segments.length; i++) {
    const [p0, p1, p2, p3] = segmentPoints(profile, i);
    for (let j = 1; j <= stepsPerSeg; j++) {
      pts.push(cubicAt(p0, p1, p2, p3, j / stepsPerSeg));
    }
  }
  return pts;
}

/** Right-edge half-width (mm) at given y from a front-view profile. */
export function halfWidthAtY(profile: BezierProfile, yMm: number): number {
  const pts = sampleProfilePoints(profile, 40);
  let best = Math.abs(pts[0].y - yMm);
  let x = Math.abs(pts[0].x);
  for (const p of pts) {
    const d = Math.abs(p.y - yMm);
    if (d < best) {
      best = d;
      x = Math.abs(p.x);
    }
  }
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    if ((a.y <= yMm && b.y >= yMm) || (a.y >= yMm && b.y <= yMm)) {
      const t = Math.abs(b.y - a.y) < 1e-6 ? 0.5 : (yMm - a.y) / (b.y - a.y);
      const xi = Math.abs(a.x + t * (b.x - a.x));
      if (xi > x) x = xi;
    }
  }
  return Math.max(x, 0.5);
}

/** Half thickness (mm) at y from side profile; falls back to constant. */
export function halfThicknessAtY(side: BezierProfile | null | undefined, yMm: number, fallbackMm: number): number {
  if (!side) return fallbackMm / 2;
  return halfWidthAtY(side, yMm);
}

function closeSymmetricRight(right: [number, number][]): [number, number][] {
  const out: [number, number][] = [...right];
  const last = right[right.length - 1];
  if (Math.abs(last[0]) > 0.01) out.push([-last[0], last[1]]);
  for (let i = right.length - 2; i >= 0; i--) out.push([-right[i][0], right[i][1]]);
  return out;
}

/** Closed THREE.Shape from a front-view right-edge Bezier (blade or handle outline). */
export function profileToClosedShape(profile: BezierProfile, yMin = -Infinity): THREE.Shape {
  let pts = sampleProfilePoints(profile, 48);
  if (Number.isFinite(yMin)) pts = clipOpenPolylineAtMinY(pts, yMin);
  const right: [number, number][] = pts.map(p => [Math.max(p.x, 0), p.y]);
  if (right[0][0] < 0.01 && right.length > 1) {
    // tip on centerline: skip duplicate at tip when mirroring
  }
  const closed = closeSymmetricRight(right);
  const shape = new THREE.Shape();
  shape.moveTo(closed[0][0] * MM, closed[0][1] * MM);
  for (let i = 1; i < closed.length; i++) shape.lineTo(closed[i][0] * MM, closed[i][1] * MM);
  shape.closePath();
  return shape;
}

function mergeGeometries(geos: THREE.BufferGeometry[]): THREE.BufferGeometry | null {
  if (geos.length === 0) return null;
  if (geos.length === 1) return geos[0];
  const merged = new THREE.BufferGeometry();
  let offset = 0;
  const pos: number[] = [];
  const norm: number[] = [];
  const idx: number[] = [];
  for (const g of geos) {
    g.computeVertexNormals();
    const p = g.attributes.position.array as Float32Array;
    const n = g.attributes.normal?.array as Float32Array;
    const base = offset;
    for (let i = 0; i < p.length; i += 3) {
      pos.push(p[i], p[i + 1], p[i + 2]);
      if (n) norm.push(n[i], n[i + 1], n[i + 2]);
    }
    const index = g.index?.array;
    if (index) {
      for (let i = 0; i < index.length; i++) idx.push(index[i] + base);
    } else {
      for (let i = 0; i < p.length / 3; i++) idx.push(base + i);
    }
    offset += p.length / 3;
    g.dispose();
  }
  merged.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  if (norm.length) merged.setAttribute('normal', new THREE.Float32BufferAttribute(norm, 3));
  merged.setIndex(idx);
  merged.computeVertexNormals();
  return merged;
}

/**
 * FL handle: front-view profile gives half-width vs y (top narrow, bottom wide).
 * Extrude stacked slices along handle length with uniform thickness (mm).
 */
export function createHandleFromFrontProfile(
  profile: BezierProfile,
  thicknessMm: number,
  slices = 56,
): THREE.BufferGeometry {
  const pts = sampleProfilePoints(profile, 48);
  const bottomY = Math.min(...pts.map(p => p.y));
  const topY = Math.max(...pts.map(p => p.y));
  const lengthMm = topY - bottomY;
  const geos: THREE.BufferGeometry[] = [];
  const sliceHmm = lengthMm / slices;
  const thM = thicknessMm * MM;

  for (let i = 0; i < slices; i++) {
    const y = bottomY + (i + 0.5) * sliceHmm;
    const halfW = halfWidthAtY(profile, y);
    const wMm = halfW * 2;
    const r = Math.min(2.5, wMm * 0.08, thicknessMm * 0.08);
    const shape = roundedRectShape(wMm * MM, thM, r * MM);
    const geo = new THREE.ExtrudeGeometry(shape, { depth: sliceHmm * MM + 0.00005, bevelEnabled: false });
    geo.translate(0, y * MM, -thM / 2);
    geos.push(geo);
  }
  return mergeGeometries(geos) ?? geos[0];
}

export function createPaddleFromProfiles({ blade, handle, side, handleBottom }: PaddleProfiles): THREE.Group {
  const group = new THREE.Group();
  const coreT = DEFAULT_DIMS.coreThicknessMm * MM;
  const joinY = DEFAULT_DIMS.handleJoinYMm;

  // Full blade-front profile including neck taper below 柄顶.
  const woodShape = profileToClosedShape(blade);
  const woodGeo = new THREE.ExtrudeGeometry(woodShape, {
    depth: coreT,
    bevelEnabled: true,
    bevelThickness: 0.003,
    bevelSize: 0.003,
    bevelSegments: 6,
  });
  woodGeo.translate(0, 0, -coreT / 2);
  const woodMesh = new THREE.Mesh(
    woodGeo,
    new THREE.MeshPhongMaterial({ color: 0xe2bf6e, specular: 0x221100, shininess: 25, side: THREE.FrontSide }),
  );
  woodMesh.renderOrder = 2;
  group.add(woodMesh);

  if (RENDER_RUBBER_LAYERS) {
    const rubT = DEFAULT_DIMS.rubberThicknessMm * MM;
    const rubberShape = profileToClosedShape(blade, joinY);
    const rubGeo = new THREE.ExtrudeGeometry(rubberShape, { depth: rubT, bevelEnabled: false });
    const fh = new THREE.Mesh(rubGeo, new THREE.MeshPhongMaterial({ color: 0xd42020, specular: 0x111111, shininess: 4, side: THREE.FrontSide }));
    fh.position.z = coreT / 2;
    fh.renderOrder = 2;
    group.add(fh);
    const bh = new THREE.Mesh(rubGeo.clone(), new THREE.MeshPhongMaterial({ color: 0x151515, specular: 0x222222, shininess: 4, side: THREE.FrontSide }));
    bh.position.z = -(coreT / 2 + rubT);
    bh.renderOrder = 2;
    group.add(bh);
  }

  const handleGeo = handleBottom
    ? createLoftedHandleGeometry(handle, handleBottom, side)
    : createHandleFromFrontProfile(handle, DEFAULT_DIMS.handleThicknessMm);
  const handleMat = handleMaterial();
  handleMat.polygonOffset = true;
  handleMat.polygonOffsetFactor = 1;
  handleMat.polygonOffsetUnits = 1;
  const handleMesh = new THREE.Mesh(handleGeo, handleMat);
  handleMesh.renderOrder = 1;
  group.add(handleMesh);

  return group;
}
