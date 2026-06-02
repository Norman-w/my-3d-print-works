import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { RENDER_RUBBER_LAYERS } from '../lib/paddleFromBezier';
import { createPaddleModel, PADDLE, PADDLE_BOTTOM_Y, PADDLE_TOTAL_HEIGHT } from '../lib/paddleModel';
import BezierDrawEditor from './BezierDrawEditor';
import BezierProfileStorePanel from './BezierProfileStorePanel';
import { DrawTarget } from '../lib/bezierProfile';

type ViewKind = 'front' | 'side';

function setupOrthoScene(view: ViewKind) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf4f4ef);
  scene.add(new THREE.AmbientLight(0xffffff, 1.0));
  const key = new THREE.DirectionalLight(0xffffff, 0.85);
  key.position.set(view === 'front' ? 0 : 5, 2, view === 'front' ? 5 : 0);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 0.35);
  fill.position.set(view === 'front' ? -3 : 0, -1, view === 'front' ? 2 : 5);
  scene.add(fill);
  return scene;
}

function fitOrthoCamera(cam: THREE.OrthographicCamera, view: ViewKind, aspect: number) {
  const pad = 1.12;
  const centerY = (PADDLE.tipYMm + PADDLE_BOTTOM_Y) / 2 * 0.01;
  const halfY = (PADDLE_TOTAL_HEIGHT / 2) * 0.01 * pad;
  let halfW: number;
  let halfH = halfY;
  if (view === 'front') halfW = (PADDLE.bladeWidthMm / 2) * 0.01 * pad;
  else {
    const bladeZ = PADDLE.bladeCoreThicknessMm + (RENDER_RUBBER_LAYERS ? PADDLE.rubberThicknessMm * 2 : 0);
    halfW = ((bladeZ + PADDLE.handleThicknessMm) / 2) * 0.01 * pad;
  }
  if (halfW / halfH > aspect) halfH = halfW / aspect;
  else halfW = halfH * aspect;
  cam.left = -halfW;
  cam.right = halfW;
  cam.top = halfH;
  cam.bottom = -halfH;
  cam.near = 0.1;
  cam.far = 50;
  cam.position.set(view === 'side' ? 8 : 0, centerY, view === 'front' ? 8 : 0);
  cam.lookAt(0, centerY, 0);
  cam.up.set(0, 1, 0);
  cam.updateProjectionMatrix();
}

function OrthoPanel({ view, label, profileRev }: { view: ViewKind; label: string; profileRev: number }) {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    const paddle = createPaddleModel();
    const scene = setupOrthoScene(view);
    scene.add(paddle);

    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.domElement.style.display = 'block';
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    host.appendChild(renderer.domElement);

    const render = () => {
      const rect = host.getBoundingClientRect();
      const w = Math.floor(rect.width);
      const h = Math.floor(rect.height);
      if (w < 8 || h < 8 || h > 4096) return;
      renderer.setSize(w, h, false);
      const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 50);
      fitOrthoCamera(cam, view, w / h);
      renderer.render(scene, cam);
    };

    render();
    const ro = new ResizeObserver(render);
    ro.observe(host);
    return () => {
      ro.disconnect();
      renderer.dispose();
      host.removeChild(renderer.domElement);
    };
  }, [view, profileRev]);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      <div style={{ padding: '8px 12px', fontSize: 13, fontWeight: 600, color: '#555', borderBottom: '1px solid #ddd' }}>
        {label}
      </div>
      <div ref={hostRef} style={{ flex: 1, height: 0, minHeight: 0, background: '#f4f4ef' }} />
    </div>
  );
}

function loadTarget(): DrawTarget {
  const q = new URLSearchParams(window.location.search).get('target');
  if (q === 'blade-front' || q === 'handle-front' || q === 'side' || q === 'handle-bottom') return q;
  return 'blade-front';
}

export default function PaddleShapePreview() {
  const [drawTarget, setDrawTarget] = useState<DrawTarget>(loadTarget);
  const [profileRev, setProfileRev] = useState(0);
  const bezierRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const bump = () => setProfileRev(v => v + 1);
    window.addEventListener('smartpaddle-profiles-loaded', bump);
    window.addEventListener('smartpaddle-profiles-updated', bump);
    return () => {
      window.removeEventListener('smartpaddle-profiles-loaded', bump);
      window.removeEventListener('smartpaddle-profiles-updated', bump);
    };
  }, []);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get('section') === 'bezier') {
      const scroll = () => bezierRef.current?.scrollIntoView({ block: 'start', behavior: 'instant' as ScrollBehavior });
      scroll();
      requestAnimationFrame(scroll);
    }
  }, []);

  const setTarget = (target: DrawTarget) => {
    setDrawTarget(target);
    const url = new URL(window.location.href);
    url.searchParams.set('target', target);
    url.searchParams.set('section', 'bezier');
    window.history.replaceState(null, '', url);
  };

  return (
    <div style={{ flex: 1, width: '100%', overflow: 'auto', padding: 16, background: '#0c0c14', color: '#ccc' }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#4fc3f7', marginBottom: 6 }}>球拍形状 · 贝塞尔绘制</h2>
        <p style={{ fontSize: 13, color: '#888', lineHeight: 1.5 }}>
          底板/手柄正视在官图上绘制；柄侧视、柄底视叠参考照片描轮廓。底视截面沿柄长放样，生成圆润 FL 握感。
        </p>
      </div>

      <BezierProfileStorePanel />

      <div ref={bezierRef} id="shape-bezier" data-bezier style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 4, marginBottom: 10, flexWrap: 'wrap' }}>
          {(
            [
              ['blade-front', '底板正视', '#ff1744'],
              ['handle-front', '手柄正视', '#00e5ff'],
              ['side', '柄侧视', '#1565c0'],
              ['handle-bottom', '柄底视', '#ab47bc'],
            ] as const
          ).map(([id, label, color]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTarget(id)}
              style={{
                padding: '6px 14px',
                fontSize: 13,
                border: `1px solid ${drawTarget === id ? color : '#333'}`,
                borderRadius: 4,
                background: drawTarget === id ? '#1e3a5f' : '#1a1a28',
                color: drawTarget === id ? color : '#888',
                cursor: 'pointer',
                fontWeight: drawTarget === id ? 600 : 400,
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <BezierDrawEditor target={drawTarget} />
      </div>

      <div style={{ display: 'flex', gap: 12, height: 360 }}>
        <div style={{ flex: 1, display: 'flex', border: '1px solid #333', borderRadius: 8, overflow: 'hidden', background: '#111' }}>
          <OrthoPanel view="front" label="3D 正视（贝塞尔放样）" profileRev={profileRev} />
          <div style={{ width: 1, background: '#333' }} />
          <OrthoPanel view="side" label="3D 侧视" profileRev={profileRev} />
        </div>
      </div>
    </div>
  );
}
