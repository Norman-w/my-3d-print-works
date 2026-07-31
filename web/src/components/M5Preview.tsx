//#region 导入/依赖
import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import {
  createM5TailAssembly,
  M5,
  M5_STATE_LABELS,
  M5AssemblyState,
} from '../lib/m5TailModel';
//#endregion

//#region 常量/配置
const STATES: M5AssemblyState[] = ['shell', 'board_focus', 'section_z'];
//#endregion

//#region 公开 API / 视图层
export default function M5Preview() {
  const hostRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<M5AssemblyState>('board_focus');

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0c0c14);

    const cam = new THREE.PerspectiveCamera(40, 1, 0.05, 40);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    host.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0x606080, 2.4));
    const key = new THREE.DirectionalLight(0xffffff, 2.8);
    key.position.set(2, 1, 3);
    scene.add(key);

    const pivot = new THREE.Group();
    scene.add(pivot);
    let assembly = createM5TailAssembly(state);
    pivot.add(assembly);

    let dragging = false;
    let lastX = 0;
    let lastY = 0;
    let yaw = 0.55;
    let pitch = -0.35;

    const applyOrbit = () => {
      const r = 2.15;
      const target = new THREE.Vector3(0, (M5.datumAY + 30) * 0.01, 0);
      cam.position.set(
        target.x + r * Math.cos(pitch) * Math.sin(yaw),
        target.y + r * Math.sin(pitch),
        target.z + r * Math.cos(pitch) * Math.cos(yaw),
      );
      cam.lookAt(target);
    };
    applyOrbit();

    const onDown = (e: PointerEvent) => {
      dragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
      host.setPointerCapture(e.pointerId);
    };
    const onMove = (e: PointerEvent) => {
      if (!dragging) return;
      yaw += (e.clientX - lastX) * 0.008;
      pitch = Math.max(-1.2, Math.min(1.2, pitch + (e.clientY - lastY) * 0.006));
      lastX = e.clientX;
      lastY = e.clientY;
    };
    const onUp = (e: PointerEvent) => {
      dragging = false;
      host.releasePointerCapture(e.pointerId);
    };
    host.addEventListener('pointerdown', onDown);
    host.addEventListener('pointermove', onMove);
    host.addEventListener('pointerup', onUp);

    const resize = () => {
      const w = Math.floor(host.clientWidth);
      const h = Math.floor(host.clientHeight);
      if (w < 8 || h < 8 || w > 4096 || h > 4096) return;
      renderer.setSize(w, h, false);
      cam.aspect = w / Math.max(h, 1);
      cam.updateProjectionMatrix();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(host);

    let frame = 0;
    const loop = () => {
      frame = requestAnimationFrame(loop);
      applyOrbit();
      renderer.render(scene, cam);
    };
    loop();

    const rebuild = (s: M5AssemblyState) => {
      pivot.remove(assembly);
      assembly.traverse((o) => {
        if (o instanceof THREE.Mesh) {
          o.geometry.dispose();
          const m = o.material;
          if (Array.isArray(m)) m.forEach((x) => x.dispose());
          else m.dispose();
        }
      });
      assembly = createM5TailAssembly(s);
      pivot.add(assembly);
    };
    (host as HTMLDivElement & { __m5Rebuild?: (s: M5AssemblyState) => void }).__m5Rebuild =
      rebuild;

    return () => {
      cancelAnimationFrame(frame);
      ro.disconnect();
      host.removeEventListener('pointerdown', onDown);
      host.removeEventListener('pointermove', onMove);
      host.removeEventListener('pointerup', onUp);
      renderer.dispose();
      host.removeChild(renderer.domElement);
    };
  }, []);

  useEffect(() => {
    const host = hostRef.current as
      | (HTMLDivElement & { __m5Rebuild?: (s: M5AssemblyState) => void })
      | null;
    host?.__m5Rebuild?.(state);
  }, [state]);

  return (
    <div style={{ display: 'flex', flex: 1, minHeight: 0, minWidth: 0, background: '#0c0c14' }}>
      <div ref={hostRef} style={{ flex: 1, minWidth: 0, minHeight: 0, cursor: 'grab' }} />
      <aside
        style={{
          width: 320,
          flexShrink: 0,
          borderLeft: '1px solid #2a2a3a',
          padding: 16,
          overflow: 'auto',
          color: '#d8dee9',
          fontSize: 13,
          lineHeight: 1.45,
        }}
      >
        <h2 style={{ margin: '0 0 8px', color: '#4fc3f7', fontSize: 18 }}>M5 尾板</h2>
        <p style={{ margin: '0 0 12px', color: '#889' }}>
          满截面自研尾板卡环槽；无电池匣。充电/USB/按键在 pcb-tail。
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 16 }}>
          {STATES.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setState(s)}
              style={{
                textAlign: 'left',
                padding: '8px 10px',
                borderRadius: 6,
                border: '1px solid #2a2a3a',
                background: state === s ? '#1e3a5f' : '#14141e',
                color: state === s ? '#4fc3f7' : '#c5ccd8',
                cursor: 'pointer',
              }}
            >
              {M5_STATE_LABELS[s]}
            </button>
          ))}
        </div>
        <ul style={{ margin: 0, paddingLeft: 18, color: '#b7c0ce' }}>
          <li>
            板约 {M5.board.w}×{M5.board.h}×{M5.board.t} mm
          </li>
          <li>Y_pcb = butt + {M5.board.yFromButt} mm</li>
          <li>Step6：KiCad 外形/器件干涉开孔</li>
        </ul>
      </aside>
    </div>
  );
}
//#endregion
