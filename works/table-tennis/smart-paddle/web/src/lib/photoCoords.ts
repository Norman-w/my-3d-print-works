import { PADDLE, REF_PHOTO } from './paddleModel';

export type PhotoMapConfig = {
  width: number;
  height: number;
  cx: number;
  tipY: number;
  pxPerMm: number;
  tipYMm: number;
  handleJoinYMm: number;
  bottomYMm: number;
};

/** Margin around reference image (mm) — extra drag space for control handles. */
export const CANVAS_PAD_MM = 40;

export function canvasPadPx(map: PhotoMapConfig): number {
  return CANVAS_PAD_MM * map.pxPerMm;
}

export function photoCanvasSize(map: PhotoMapConfig): { width: number; height: number } {
  const pad = canvasPadPx(map);
  return { width: map.width + pad * 2, height: map.height + pad * 2 };
}

export function photoImageRect(map: PhotoMapConfig): { x: number; y: number; width: number; height: number } {
  const pad = canvasPadPx(map);
  return { x: pad, y: pad, width: map.width, height: map.height };
}

export function defaultPhotoMap(): PhotoMapConfig {
  return {
    width: REF_PHOTO.width,
    height: REF_PHOTO.height,
    cx: REF_PHOTO.cx,
    tipY: REF_PHOTO.tipY,
    pxPerMm: REF_PHOTO.pxPerMm,
    tipYMm: PADDLE.tipYMm,
    handleJoinYMm: PADDLE.handleJoinYMm,
    bottomYMm: PADDLE.handleJoinYMm - PADDLE.handleLengthMm,
  };
}

export function loadPhotoMap(): PhotoMapConfig {
  return defaultPhotoMap();
}

export function mmToPhotoPx(map: PhotoMapConfig, xMm: number, yMm: number): { x: number; y: number } {
  const pad = canvasPadPx(map);
  return {
    x: pad + map.cx + xMm * map.pxPerMm,
    y: pad + map.tipY + (map.tipYMm - yMm) * map.pxPerMm,
  };
}

export function photoPxToMm(map: PhotoMapConfig, xPx: number, yPx: number): { x: number; y: number } {
  const pad = canvasPadPx(map);
  return {
    x: (xPx - pad - map.cx) / map.pxPerMm,
    y: map.tipYMm - (yPx - pad - map.tipY) / map.pxPerMm,
  };
}

export function mmYToPhotoY(map: PhotoMapConfig, yMm: number): number {
  const pad = canvasPadPx(map);
  return pad + map.tipY + (map.tipYMm - yMm) * map.pxPerMm;
}

export function photoPathFromMmRight(
  map: PhotoMapConfig,
  start: { x: number; y: number },
  segments: { cp1: { x: number; y: number }; cp2: { x: number; y: number }; end: { x: number; y: number } }[],
): string {
  const s = mmToPhotoPx(map, start.x, start.y);
  const parts = [`M ${s.x.toFixed(1)} ${s.y.toFixed(1)}`];
  for (const seg of segments) {
    const a = mmToPhotoPx(map, seg.cp1.x, seg.cp1.y);
    const b = mmToPhotoPx(map, seg.cp2.x, seg.cp2.y);
    const e = mmToPhotoPx(map, seg.end.x, seg.end.y);
    parts.push(`C ${a.x.toFixed(1)} ${a.y.toFixed(1)}, ${b.x.toFixed(1)} ${b.y.toFixed(1)}, ${e.x.toFixed(1)} ${e.y.toFixed(1)}`);
  }
  return parts.join(' ');
}

export function photoMirrorPathFromMmRight(
  map: PhotoMapConfig,
  start: { x: number; y: number },
  segments: { cp1: { x: number; y: number }; cp2: { x: number; y: number }; end: { x: number; y: number } }[],
): string {
  const s = mmToPhotoPx(map, -start.x, start.y);
  const parts = [`M ${s.x.toFixed(1)} ${s.y.toFixed(1)}`];
  for (const seg of segments) {
    const a = mmToPhotoPx(map, -seg.cp1.x, seg.cp1.y);
    const b = mmToPhotoPx(map, -seg.cp2.x, seg.cp2.y);
    const e = mmToPhotoPx(map, -seg.end.x, seg.end.y);
    parts.push(`C ${a.x.toFixed(1)} ${a.y.toFixed(1)}, ${b.x.toFixed(1)} ${b.y.toFixed(1)}, ${e.x.toFixed(1)} ${e.y.toFixed(1)}`);
  }
  return parts.join(' ');
}

/** @deprecated use loadPhotoMap() */
export const PHOTO_MAP = defaultPhotoMap();
