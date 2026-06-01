import * as THREE from 'three';
import { BezierProfile, loadProfile } from './bezierProfile';
import { createPaddleFromProfiles, PaddleProfiles, RENDER_RUBBER_LAYERS } from './paddleFromBezier';
import savedProfiles from '../data/userBezierProfiles.json';

// Butterfly Timo Boll ALC FL — 157×150 mm blade, handle 100×25×34 mm
// Face = photo-fitted ellipse (CA.media.02 rubber); tang + FL handle are separate pieces
export const PADDLE = {
  bladeWidthMm: 150,
  handleLengthMm: 100,
  handleNeckWMm: 24,
  handleButtWMm: 34,
  handleThicknessMm: 25,
  bladeCoreThicknessMm: 5.8,
  rubberThicknessMm: 1.8,
  tipYMm: 78.5,
  /** Rubber / face bottom (shoulder line, mm y-up) */
  faceBottomYMm: -71.7,
  faceEllipseA: 75,
  faceEllipseCy: -10,
  faceEllipseB: 88,
  handleJoinYMm: -78.5,
  tangHalfWMm: 9,
  tangEndYMm: -93,
} as const;

const MM = 0.01;

/** Shoulder: tang → face ellipse (from traced blade, x remapped to tang→ellipse width). */
const SHOULDER_RIGHT: [number, number][] = [
  [9.0, -78.5], [19.5, -78.55], [24.0, -76.84], [28.8, -75.14], [33.9, -73.43], [39.2, -71.72],
];

/** FL handle outer edge traced from CA.media.02 wood (right half, mm). */
const HANDLE_RIGHT: [number, number][] = [
  [12.0, -78.5], [13.4, -90.0], [13.2, -100.0], [12.3, -110.0], [12.1, -120.0], [12.5, -130.0],
  [12.8, -140.0], [13.4, -150.0], [14.5, -160.0], [15.5, -170.0], [14.0, -176.0], [12.0, -178.5],
];

function smoothstep(t: number): number {
  return t * t * (3 - 2 * t);
}

export function flHandleHalfWidth(t: number): number {
  const neck = PADDLE.handleNeckWMm / 2;
  const butt = PADDLE.handleButtWMm / 2;
  const waistT = 0.32;
  if (t <= waistT) {
    const u = t / waistT;
    return neck * (1 - 0.06 * Math.sin(u * Math.PI * 0.5));
  }
  const u = (t - waistT) / (1 - waistT);
  return neck * 0.96 + (butt - neck * 0.96) * smoothstep(u);
}

function ellipseHalfX(yMm: number): number {
  const { faceEllipseA, faceEllipseCy, faceEllipseB } = PADDLE;
  const t = (yMm - faceEllipseCy) / faceEllipseB;
  if (Math.abs(t) >= 1) return 0;
  return faceEllipseA * Math.sqrt(1 - t * t);
}

/** Right edge: face ellipse from shoulder top → tip. */
function faceRightHalf(): [number, number][] {
  const { faceBottomYMm, tipYMm } = PADDLE;
  const pts: [number, number][] = [];
  for (let y = faceBottomYMm; y <= tipYMm; y += 2.5) {
    pts.push([ellipseHalfX(y), y]);
  }
  if (pts[pts.length - 1][1] < tipYMm) pts.push([0, tipYMm]);
  return pts;
}

function bladeKeyholeRightHalf(): [number, number][] {
  const { tangHalfWMm, tangEndYMm, handleJoinYMm } = PADDLE;
  const shoulderTop = SHOULDER_RIGHT[SHOULDER_RIGHT.length - 1];
  const face = faceRightHalf();
  if (face.length && Math.abs(face[0][1] - shoulderTop[1]) < 0.5) face.shift();
  return [
    [tangHalfWMm, tangEndYMm],
    [tangHalfWMm, handleJoinYMm],
    ...SHOULDER_RIGHT.slice(1),
    ...face,
  ];
}

function handleRightHalf(): [number, number][] {
  return HANDLE_RIGHT;
}

function toSvgY(yMm: number): number {
  return -yMm;
}

function svgPathFromRight(right: [number, number][]): string {
  const parts = [`M ${right[0][0].toFixed(2)} ${toSvgY(right[0][1]).toFixed(2)}`];
  for (let i = 1; i < right.length; i++) {
    parts.push(`L ${right[i][0].toFixed(2)} ${toSvgY(right[i][1]).toFixed(2)}`);
  }
  const last = right[right.length - 1];
  if (last[0] > 0.01) parts.push(`L ${(-last[0]).toFixed(2)} ${toSvgY(last[1]).toFixed(2)}`);
  for (let i = right.length - 2; i >= 0; i--) {
    parts.push(`L ${(-right[i][0]).toFixed(2)} ${toSvgY(right[i][1]).toFixed(2)}`);
  }
  parts.push('Z');
  return parts.join(' ');
}

function tangRectPath(): string {
  const { tangHalfWMm, faceBottomYMm, tangEndYMm } = PADDLE;
  const x = tangHalfWMm;
  return `M ${-x} ${toSvgY(faceBottomYMm)} L ${x} ${toSvgY(faceBottomYMm)} L ${x} ${toSvgY(tangEndYMm)} L ${-x} ${toSvgY(tangEndYMm)} Z`;
}

export function bladeFrontSvgPath(): string {
  return svgPathFromRight(bladeKeyholeRightHalf());
}

export function handleFrontSvgPath(): string {
  return svgPathFromRight(handleRightHalf());
}

function shoulderRightHalf(): [number, number][] {
  return SHOULDER_RIGHT;
}

function shoulderOpenPath(): string {
  const right = shoulderRightHalf();
  const parts = [`M ${right[0][0].toFixed(2)} ${toSvgY(right[0][1]).toFixed(2)}`];
  for (let i = 1; i < right.length; i++) {
    parts.push(`L ${right[i][0].toFixed(2)} ${toSvgY(right[i][1]).toFixed(2)}`);
  }
  parts.push(`L ${(-right[right.length - 1][0]).toFixed(2)} ${toSvgY(right[right.length - 1][1]).toFixed(2)}`);
  for (let i = right.length - 2; i >= 0; i--) {
    parts.push(`L ${(-right[i][0]).toFixed(2)} ${toSvgY(right[i][1]).toFixed(2)}`);
  }
  return parts.join(' ');
}

function photoShoulderPath(): string {
  const right = shoulderRightHalf();
  const [x0, y0] = mmToPhotoPx(right[0][0], right[0][1]);
  const parts = [`M ${x0.toFixed(1)} ${y0.toFixed(1)}`];
  for (let i = 1; i < right.length; i++) {
    const [x, y] = mmToPhotoPx(right[i][0], right[i][1]);
    parts.push(`L ${x.toFixed(1)} ${y.toFixed(1)}`);
  }
  const last = right[right.length - 1];
  const [xl, yl] = mmToPhotoPx(-last[0], last[1]);
  parts.push(`L ${xl.toFixed(1)} ${yl.toFixed(1)}`);
  for (let i = right.length - 2; i >= 0; i--) {
    const [x, y] = mmToPhotoPx(-right[i][0], right[i][1]);
    parts.push(`L ${x.toFixed(1)} ${y.toFixed(1)}`);
  }
  return parts.join(' ');
}

export type FrontSilhouette = { blade: string; handle: string; face: string; tang: string; shoulder: string };

export function frontSilhouettePaths(): FrontSilhouette {
  return {
    blade: bladeFrontSvgPath(),
    handle: handleFrontSvgPath(),
    face: svgPathFromRight(faceRightHalf()),
    tang: tangRectPath(),
    shoulder: shoulderOpenPath(),
  };
}

function closeSymmetric(right: [number, number][]): [number, number][] {
  const out = [...right];
  const last = right[right.length - 1];
  if (last[0] > 0.01) out.push([-last[0], last[1]]);
  for (let i = right.length - 2; i >= 0; i--) out.push([-right[i][0], right[i][1]]);
  return out;
}

function shapeFromRight(right: [number, number][]): THREE.Shape {
  const closed = closeSymmetric(right);
  const shape = new THREE.Shape();
  shape.moveTo(closed[0][0] * MM, closed[0][1] * MM);
  for (let i = 1; i < closed.length; i++) shape.lineTo(closed[i][0] * MM, closed[i][1] * MM);
  shape.closePath();
  return shape;
}

export function bladeShape(): THREE.Shape {
  return shapeFromRight(bladeKeyholeRightHalf());
}

export function rubberFaceShape(): THREE.Shape {
  return shapeFromRight(faceRightHalf());
}

export function roundedRectShape(w: number, h: number, r: number): THREE.Shape {
  const hw = w / 2, hh = h / 2;
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

function mergeGeometries(geos: THREE.BufferGeometry[]): THREE.BufferGeometry | null {
  if (geos.length === 0) return null;
  if (geos.length === 1) return geos[0];
  const merged = new THREE.BufferGeometry();
  let offset = 0;
  const pos: number[] = [], norm: number[] = [], idx: number[] = [];
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

export function createFlHandleGeometry(length: number, thickness: number, slices = 48): THREE.BufferGeometry {
  const geos: THREE.BufferGeometry[] = [];
  const sliceH = length / slices;
  for (let i = 0; i < slices; i++) {
    const t = (i + 0.5) / slices;
    const w = flHandleHalfWidth(t) * 2;
    const shape = roundedRectShape(w, thickness, Math.min(0.012, w * 0.08, thickness * 0.08));
    const geo = new THREE.ExtrudeGeometry(shape, { depth: sliceH + 0.0001, bevelEnabled: false });
    geo.translate(0, 0, length / 2 - (i + 0.5) * sliceH);
    geos.push(geo);
  }
  return mergeGeometries(geos) ?? geos[0];
}

export const PADDLE_BOTTOM_Y = PADDLE.handleJoinYMm - PADDLE.handleLengthMm;
export const PADDLE_TOTAL_HEIGHT = PADDLE.tipYMm - PADDLE_BOTTOM_Y;
export const PADDLE_CENTER_Y = ((PADDLE.tipYMm + PADDLE_BOTTOM_Y) / 2) * MM;

export function loadUserProfiles(): PaddleProfiles {
  if (typeof localStorage !== 'undefined') {
    try {
      const blade = loadProfile('blade-front');
      const handle = loadProfile('handle-front');
      let side: BezierProfile | null = null;
      let handleBottom: BezierProfile | null = null;
      try {
        const raw = localStorage.getItem('smartpaddle-bezier-side');
        if (raw) side = loadProfile('side');
      } catch {
        /* default side */
      }
      try {
        const raw = localStorage.getItem('smartpaddle-bezier-handle-bottom');
        if (raw) handleBottom = loadProfile('handle-bottom');
      } catch {
        /* default */
      }
      if (blade.segments.length > 0 && handle.segments.length > 0) {
        return { blade, handle, side, handleBottom: handleBottom ?? loadProfile('handle-bottom') };
      }
    } catch {
      /* fall through */
    }
  }
  const s = savedProfiles as {
    'blade-front': BezierProfile;
    'handle-front': BezierProfile;
    'handle-bottom'?: BezierProfile;
  };
  return {
    blade: s['blade-front'],
    handle: s['handle-front'],
    side: null,
    handleBottom: s['handle-bottom'] ?? loadProfile('handle-bottom'),
  };
}

export function createPaddleModel(profiles?: PaddleProfiles): THREE.Group {
  try {
    return createPaddleFromProfiles(profiles ?? loadUserProfiles());
  } catch (err) {
    console.warn('Bezier paddle build failed, using legacy model', err);
  }

  return createLegacyPaddleModel();
}

function createLegacyPaddleModel(): THREE.Group {
  const group = new THREE.Group();
  const bt = PADDLE.bladeCoreThicknessMm * MM;
  const joinY = PADDLE.handleJoinYMm * MM;
  const hl = PADDLE.handleLengthMm * MM;
  const hDepth = PADDLE.handleThicknessMm * MM;

  const woodGeo = new THREE.ExtrudeGeometry(bladeShape(), {
    depth: bt, bevelEnabled: true, bevelThickness: 0.003, bevelSize: 0.003, bevelSegments: 8,
  });
  woodGeo.translate(0, 0, -bt / 2);
  group.add(new THREE.Mesh(woodGeo, new THREE.MeshPhongMaterial({ color: 0xe2bf6e, specular: 0x221100, shininess: 25 })));

  if (RENDER_RUBBER_LAYERS) {
    const rubGeo = new THREE.ExtrudeGeometry(rubberFaceShape(), { depth: PADDLE.rubberThicknessMm * MM, bevelEnabled: false });
    const fh = new THREE.Mesh(rubGeo, new THREE.MeshPhongMaterial({ color: 0xd42020, specular: 0x111111, shininess: 4 }));
    fh.position.z = bt / 2;
    group.add(fh);
    const bh = new THREE.Mesh(rubGeo.clone(), new THREE.MeshPhongMaterial({ color: 0x151515, specular: 0x222222, shininess: 4 }));
    bh.position.z = -(bt / 2 + PADDLE.rubberThicknessMm * MM);
    group.add(bh);
  }

  const handleGeo = createFlHandleGeometry(hl, hDepth);
  handleGeo.rotateX(Math.PI / 2);
  handleGeo.translate(0, joinY - hl / 2, 0);
  group.add(new THREE.Mesh(handleGeo, new THREE.MeshPhongMaterial({ color: 0x1a2744, specular: 0x223355, shininess: 18 })));

  return group;
}

/** CA.media.02 — paddle fills frame; tip≈y0 bottom≈y1199 */
export const REF_PHOTO = {
  width: 695,
  height: 1200,
  cx: 347.5,
  tipY: 0,
  pxPerMm: 4.665,
} as const;

function mmToPhotoPx(xMm: number, yMm: number): [number, number] {
  return [REF_PHOTO.cx + xMm * REF_PHOTO.pxPerMm, REF_PHOTO.tipY + (PADDLE.tipYMm - yMm) * REF_PHOTO.pxPerMm];
}

function photoPathFromRight(right: [number, number][]): string {
  const [x0, y0] = mmToPhotoPx(right[0][0], right[0][1]);
  const parts = [`M ${x0.toFixed(1)} ${y0.toFixed(1)}`];
  for (let i = 1; i < right.length; i++) {
    const [x, y] = mmToPhotoPx(right[i][0], right[i][1]);
    parts.push(`L ${x.toFixed(1)} ${y.toFixed(1)}`);
  }
  const last = right[right.length - 1];
  if (last[0] > 0.01) {
    const [x, y] = mmToPhotoPx(-last[0], last[1]);
    parts.push(`L ${x.toFixed(1)} ${y.toFixed(1)}`);
  }
  for (let i = right.length - 2; i >= 0; i--) {
    const [x, y] = mmToPhotoPx(-right[i][0], right[i][1]);
    parts.push(`L ${x.toFixed(1)} ${y.toFixed(1)}`);
  }
  parts.push('Z');
  return parts.join(' ');
}

function photoRect(x0: number, y0mm: number, x1: number, y1mm: number): string {
  const [px0, py0] = mmToPhotoPx(x0, y0mm);
  const [px1, py1] = mmToPhotoPx(x1, y1mm);
  return `M ${px0.toFixed(1)} ${py0.toFixed(1)} L ${px1.toFixed(1)} ${py0.toFixed(1)} L ${px1.toFixed(1)} ${py1.toFixed(1)} L ${px0.toFixed(1)} ${py1.toFixed(1)} Z`;
}

export function frontSilhouettePhotoPaths(): FrontSilhouette {
  const th = PADDLE.tangHalfWMm;
  const fb = PADDLE.faceBottomYMm;
  const te = PADDLE.tangEndYMm;
  return {
    blade: photoPathFromRight(bladeKeyholeRightHalf()),
    handle: photoPathFromRight(handleRightHalf()),
    face: photoPathFromRight(faceRightHalf()),
    tang: photoRect(-th, fb, th, te),
    shoulder: photoShoulderPath(),
  };
}
