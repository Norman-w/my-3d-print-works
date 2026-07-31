//#region 导入/依赖
import * as THREE from 'three';
//#endregion

//#region 常量/配置
const MM = 0.01;

/** M5：满截面尾板（无电池匣） */
export const M5 = {
  datumAY: -178.1,
  outerW: 40,
  outerT: 30,
  tailLen: 70,
  wallT: 2,
  board: { w: 29.7, h: 19.3, t: 1, yFromButt: 5.8 },
} as const;

export type M5AssemblyState = 'shell' | 'board_focus' | 'section_z';

export const M5_STATE_LABELS: Record<M5AssemblyState, string> = {
  shell: '拍柄尾段',
  board_focus: '尾板焦点',
  section_z: 'Z 剖面',
};
//#endregion

//#region 模型/类型
export interface M5Motion {
  boardHighlight: boolean;
}
//#endregion

//#region 业务逻辑
export function motionForState(state: M5AssemblyState): M5Motion {
  return { boardHighlight: state === 'board_focus' };
}
//#endregion

//#region 方法/工具
function box(
  sx: number,
  sy: number,
  sz: number,
  color: number,
  opacity = 1,
): THREE.Mesh {
  const geo = new THREE.BoxGeometry(sx * MM, sy * MM, sz * MM);
  const mat = new THREE.MeshStandardMaterial({
    color,
    transparent: opacity < 1,
    opacity,
    roughness: 0.55,
    metalness: 0.15,
  });
  return new THREE.Mesh(geo, mat);
}

function stadiumBoard(color: number, opacity: number): THREE.Mesh {
  const shape = new THREE.Shape();
  const w = M5.board.w * MM;
  const h = M5.board.h * MM;
  const r = Math.min(w, h) * 0.45;
  shape.moveTo(-w / 2 + r, -h / 2);
  shape.lineTo(w / 2 - r, -h / 2);
  shape.absarc(w / 2 - r, 0, r, -Math.PI / 2, Math.PI / 2, false);
  shape.lineTo(-w / 2 + r, h / 2);
  shape.absarc(-w / 2 + r, 0, r, Math.PI / 2, -Math.PI / 2, false);
  const geo = new THREE.ExtrudeGeometry(shape, {
    depth: M5.board.t * MM,
    bevelEnabled: false,
  });
  geo.rotateX(-Math.PI / 2);
  geo.translate(0, (-M5.board.t * MM) / 2, 0);
  const mat = new THREE.MeshStandardMaterial({
    color,
    transparent: opacity < 1,
    opacity,
    roughness: 0.4,
    metalness: 0.2,
  });
  return new THREE.Mesh(geo, mat);
}
//#endregion

//#region 公开 API
export function createM5TailAssembly(state: M5AssemblyState): THREE.Group {
  const root = new THREE.Group();
  const y0 = M5.datumAY * MM;
  const shell = box(M5.outerW, M5.tailLen, M5.outerT, 0x8b93a7, state === 'section_z' ? 0.35 : 0.55);
  shell.position.set(0, y0 + (M5.tailLen * MM) / 2, 0);
  root.add(shell);

  const board = stadiumBoard(0x22c55e, motionForState(state).boardHighlight ? 0.95 : 0.7);
  board.position.set(0, (M5.datumAY + M5.board.yFromButt) * MM, 0);
  root.add(board);

  // Type-C / 按钮示意（相对板心，与当前 pcb-tail 大致方位）
  const usb = box(3.3, 6.2, 9.3, 0xc0c4cc, 0.9);
  usb.position.set(-6.86 * MM, (M5.datumAY + 2.5) * MM, -0.38 * MM);
  root.add(usb);

  const btn = new THREE.Mesh(
    new THREE.CylinderGeometry(1.45 * MM, 1.45 * MM, 3 * MM, 24),
    new THREE.MeshStandardMaterial({ color: 0x222226 }),
  );
  btn.rotation.x = Math.PI / 2;
  btn.position.set(-1.65 * MM, (M5.datumAY + 1.5) * MM, -5.46 * MM);
  root.add(btn);

  return root;
}
//#endregion
