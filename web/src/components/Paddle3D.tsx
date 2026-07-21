import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { createPaddleModel } from '../lib/paddleModel';
import { applyPaddleMountFrame, setPaddleQuaternionFromImu } from '../lib/imuOrientation';

function disposePaddleGroup(group: THREE.Group): void {
  group.traverse(obj => {
    if (obj instanceof THREE.Mesh) {
      obj.geometry?.dispose();
      const mat = obj.material;
      if (Array.isArray(mat)) mat.forEach(m => m.dispose());
      else mat?.dispose();
    }
  });
}

interface Props {
  imuData: {
    ax: number;
    ay: number;
    az: number;
    gx: number;
    gy: number;
    gz: number;
    qw?: number;
    qx?: number;
    qy?: number;
    qz?: number;
  }[];
  impactData: { x_mm?: number; y_mm?: number; confidence?: number }[];
}

export default function Paddle3D({ imuData, impactData }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const refs = useRef<{ scene: THREE.Scene; paddle: THREE.Group; impacts: THREE.Group; trailPts: THREE.Vector3[] } | null>(null);
  const hasImuRef = useRef(false);
  const [waitingTick, setWaitingTick] = useState(0);

  useEffect(() => {
    hasImuRef.current = imuData.length > 0;
  }, [imuData.length]);

  useEffect(() => {
    if (!containerRef.current) return;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0c0c14);
    const cam = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    cam.position.set(0, -1.1, 6.0);
    cam.lookAt(0, -1.0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    containerRef.current.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0x505078, 2.8));
    const k = new THREE.DirectionalLight(0xffffff, 3.2); k.position.set(1.5, 1, 2.5); scene.add(k);
    scene.add(new THREE.DirectionalLight(0x8899cc, 1.2)).position.set(-1, 0.3, -1);
    scene.add(new THREE.DirectionalLight(0xffeecc, 1.8)).position.set(0, -0.3, 0.5);

    const grid = new THREE.GridHelper(3, 24, 0x333355, 0x181828);
    grid.position.y = -2.2;
    scene.add(grid);

    const paddle = createPaddleModel();
    applyPaddleMountFrame(paddle);
    scene.add(paddle);

    const impacts = new THREE.Group();
    scene.add(impacts);

    const trailPts: THREE.Vector3[] = [];
    const trail = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0x4fc3f7, transparent: true, opacity: 0.7 }));
    scene.add(trail);

    refs.current = { scene, paddle, impacts, trailPts };

    const resize = () => {
      const w = containerRef.current!.clientWidth, h = containerRef.current!.clientHeight;
      renderer.setSize(w, h);
      cam.aspect = w / Math.max(h, 1);
      cam.updateProjectionMatrix();
    };
    resize();
    window.addEventListener('resize', resize);

    let id: number;
    (function loop() {
      id = requestAnimationFrame(loop);
      if (!hasImuRef.current) paddle.rotation.y += 0.005;
      if (refs.current!.trailPts.length > 1) {
        trail.geometry.dispose();
        trail.geometry = new THREE.BufferGeometry().setFromPoints(refs.current!.trailPts);
      }
      renderer.render(scene, cam);
    })();

    return () => { cancelAnimationFrame(id); window.removeEventListener('resize', resize); renderer.dispose(); containerRef.current?.removeChild(renderer.domElement); };
  }, []);

  useEffect(() => {
    const rebuild = () => {
      const r = refs.current;
      if (!r) return;
      try {
        r.scene.remove(r.paddle);
        disposePaddleGroup(r.paddle);
        r.paddle = createPaddleModel();
        applyPaddleMountFrame(r.paddle);
        r.scene.add(r.paddle);
      } catch (err) {
        console.warn('Paddle3D rebuild failed', err);
      }
    };
    window.addEventListener('smartpaddle-profiles-loaded', rebuild);
    window.addEventListener('smartpaddle-profiles-updated', rebuild);
    return () => {
      window.removeEventListener('smartpaddle-profiles-loaded', rebuild);
      window.removeEventListener('smartpaddle-profiles-updated', rebuild);
    };
  }, []);

  useEffect(() => {
    const r = refs.current;
    if (!r || imuData.length < 1) return;
    const d = imuData[imuData.length - 1];
    if (
      d.qw !== undefined &&
      d.qx !== undefined &&
      d.qy !== undefined &&
      d.qz !== undefined
    ) {
      setPaddleQuaternionFromImu(r.paddle, d.qw, d.qx, d.qy, d.qz);
    } else {
      const gs = 0.0007;
      r.paddle.rotation.x += d.gx * gs;
      r.paddle.rotation.y += d.gy * gs;
      r.paddle.rotation.z += d.gz * gs;
      r.paddle.rotation.x = Math.max(-1.2, Math.min(1.2, r.paddle.rotation.x));
      r.paddle.rotation.z = Math.max(-0.8, Math.min(0.8, r.paddle.rotation.z));
    }
    const p = new THREE.Vector3();
    r.paddle.getWorldPosition(p);
    r.trailPts.push(p);
    if (r.trailPts.length > 200) r.trailPts.shift();
  }, [imuData]);

  useEffect(() => {
    const r = refs.current; if (!r) return;
    while (r.impacts.children.length > 0) r.impacts.remove(r.impacts.children[0]);
    impactData.slice(-20).forEach(imp => {
      if (imp.x_mm === undefined || imp.y_mm === undefined) return;
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.022, 10, 10),
        new THREE.MeshBasicMaterial({ color: imp.confidence && imp.confidence > 0.8 ? 0x4caf50 : 0xff9800, transparent: true, opacity: 0.85 }));
      dot.position.set((imp.x_mm / 160) * 1.5, (imp.y_mm / 150) * 1.6, 0.05);
      r.paddle.add(dot); r.impacts.add(dot);
    });
  }, [impactData]);

  useEffect(() => {
    if (imuData.length > 0) return;
    const id = window.setInterval(() => setWaitingTick(v => (v + 1) % 4), 420);
    return () => window.clearInterval(id);
  }, [imuData.length]);

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', position: 'relative' }}>
      {imuData.length === 0 && (
        <div
          style={{
            position: 'absolute',
            top: 14,
            right: 14,
            color: '#d8e4ff',
            fontSize: 12,
            letterSpacing: 0.3,
            pointerEvents: 'none',
            background: 'linear-gradient(135deg, rgba(16,22,36,0.88), rgba(21,32,58,0.82))',
            border: '1px solid rgba(120,160,255,0.34)',
            borderRadius: 12,
            padding: '8px 11px',
            backdropFilter: 'blur(4px)',
            boxShadow: '0 6px 18px rgba(0,0,0,0.28)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: '#59b0ff',
              boxShadow: '0 0 0 4px rgba(89,176,255,0.2)',
            }}
          />
          <span style={{ fontWeight: 600 }}>
            Waiting for paddle data
            <span style={{ display: 'inline-block', width: 18, textAlign: 'left' }}>{'.'.repeat(waitingTick)}</span>
          </span>
        </div>
      )}
    </div>
  );
}
