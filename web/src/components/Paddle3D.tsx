import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { createPaddleModel } from '../lib/paddleModel';

interface Props {
  imuData: { ax: number; ay: number; az: number; gx: number; gy: number; gz: number }[];
  impactData: { x_mm?: number; y_mm?: number; confidence?: number }[];
}

export default function Paddle3D({ imuData, impactData }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const refs = useRef<{ scene: THREE.Scene; paddle: THREE.Group; impacts: THREE.Group; trailPts: THREE.Vector3[] } | null>(null);

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
      if (imuData.length < 8) paddle.rotation.y += 0.005;
      if (refs.current!.trailPts.length > 1) {
        trail.geometry.dispose();
        trail.geometry = new THREE.BufferGeometry().setFromPoints(refs.current!.trailPts);
      }
      renderer.render(scene, cam);
    })();

    return () => { cancelAnimationFrame(id); window.removeEventListener('resize', resize); renderer.dispose(); containerRef.current?.removeChild(renderer.domElement); };
  }, []);

  useEffect(() => {
    const r = refs.current; if (!r || imuData.length < 1) return;
    const d = imuData[imuData.length - 1], gs = 0.0007;
    r.paddle.rotation.x += d.gx * gs; r.paddle.rotation.y += d.gy * gs; r.paddle.rotation.z += d.gz * gs;
    r.paddle.rotation.x = Math.max(-1.2, Math.min(1.2, r.paddle.rotation.x));
    r.paddle.rotation.z = Math.max(-0.8, Math.min(0.8, r.paddle.rotation.z));
    const p = new THREE.Vector3(); r.paddle.getWorldPosition(p);
    r.trailPts.push(p); if (r.trailPts.length > 200) r.trailPts.shift();
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

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', position: 'relative' }}>
      {imuData.length === 0 && (
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', color: '#555', fontSize: 16, textAlign: 'center', pointerEvents: 'none' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🏓</div>
          Waiting for paddle data...
        </div>
      )}
    </div>
  );
}
