//#region 导入/依赖
import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import {
  CameraPreset,
  loadProcessManifest,
  ProcessPreviewManifest,
  ProcessView,
} from '../lib/processPreview';
//#endregion

//#region 模型/类型
type BrowseMode = 'steps' | 'types' | 'components';
//#endregion

//#region 常量/配置
const PANEL: React.CSSProperties = {
  width: 310,
  padding: 14,
  overflowY: 'auto',
  borderRight: '1px solid #293244',
  background: '#111827',
};

const BUTTON: React.CSSProperties = {
  padding: '7px 9px',
  borderRadius: 6,
  border: '1px solid #374151',
  background: '#1f2937',
  color: '#dbeafe',
  cursor: 'pointer',
  textAlign: 'left',
};

const EXPLODE_Z: Record<string, number> = {
  skin_front: 12,
  core_front: 4,
  core_back: -4,
  skin_back: -12,
};
//#endregion

//#region 私有成员
function idsForDefault(manifest: ProcessPreviewManifest): Set<string> {
  const first = manifest.processSteps[0];
  return new Set(first?.components ?? manifest.components.slice(0, 1).map((item) => item.id));
}

function cameraById(
  manifest: ProcessPreviewManifest,
  id?: string,
): CameraPreset | undefined {
  return manifest.cameraPresets.find((preset) => preset.id === id);
}

function fitMeshes(
  camera: THREE.PerspectiveCamera,
  controls: OrbitControls,
  meshes: Map<string, THREE.Mesh>,
) {
  const box = new THREE.Box3();
  meshes.forEach((mesh) => {
    if (mesh.visible) box.expandByObject(mesh);
  });
  if (box.isEmpty()) return;
  const center = box.getCenter(new THREE.Vector3());
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  const radius = Math.max(sphere.radius, 1);
  const verticalFov = THREE.MathUtils.degToRad(camera.fov);
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect);
  const limitingFov = Math.max(Math.min(verticalFov, horizontalFov), 0.01);
  const distance = radius / Math.sin(limitingFov / 2) * 1.08;
  const direction = camera.position.clone().sub(controls.target);
  if (direction.lengthSq() < 0.001) direction.set(1, -1.2, 0.8);
  direction.normalize();
  controls.target.copy(center);
  camera.position.copy(center).addScaledVector(direction, distance);
  camera.near = Math.max(0.05, distance - radius * 1.5);
  camera.far = Math.max(3000, distance + radius * 4);
  camera.updateProjectionMatrix();
  controls.update();
}
//#endregion

//#region 视图层
export default function StlProcessPreview() {
  const hostRef = useRef<HTMLDivElement>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera>();
  const controlsRef = useRef<OrbitControls>();
  const meshesRef = useRef(new Map<string, THREE.Mesh>());
  const fitRef = useRef<() => void>(() => undefined);
  const visibleIdsRef = useRef<Set<string>>(new Set());
  const [manifest, setManifest] = useState<ProcessPreviewManifest>();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadedCount, setLoadedCount] = useState(0);
  const [mode, setMode] = useState<BrowseMode>('steps');
  const [activeId, setActiveId] = useState('');
  const [visibleIds, setVisibleIds] = useState<Set<string>>(new Set());
  const [transparent, setTransparent] = useState(false);
  const [exploded, setExploded] = useState(false);
  const [sectioned, setSectioned] = useState(false);

  useEffect(() => {
    loadProcessManifest()
      .then((next) => {
        const initialIds = idsForDefault(next);
        visibleIdsRef.current = initialIds;
        setManifest(next);
        setVisibleIds(initialIds);
        setActiveId(next.processSteps[0]?.id ?? '');
      })
      .catch((reason: unknown) => {
        setError(`未找到 M6 预览资产：${String(reason)}。请先运行 ./scripts/export-stl.sh`);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!manifest || !hostRef.current) return;
    const host = hostRef.current;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x090d16);
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 3000);
    camera.up.set(0, 0, 1);
    cameraRef.current = camera;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true });
    } catch (reason) {
      setError(`无法创建 WebGL 预览：${String(reason)}。请启用浏览器硬件加速后刷新。`);
      setLoading(false);
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.localClippingEnabled = true;
    renderer.domElement.addEventListener('webglcontextlost', (event) => {
      event.preventDefault();
      setError('WebGL 上下文已丢失，请刷新页面或启用浏览器硬件加速。');
    });
    host.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.zoomToCursor = false;
    controls.screenSpacePanning = true;
    controlsRef.current = controls;
    const initialPreset = cameraById(manifest, manifest.processSteps[0]?.camera)
      ?? manifest.cameraPresets[0];
    if (initialPreset) {
      controls.target.set(...initialPreset.target);
      camera.position.set(...initialPreset.position);
      controls.update();
    }

    scene.add(new THREE.HemisphereLight(0xffffff, 0x223047, 1.3));
    const key = new THREE.DirectionalLight(0xffffff, 1.4);
    key.position.set(100, -180, 220);
    scene.add(key);
    scene.add(new THREE.AxesHelper(15));
    const grid = new THREE.GridHelper(240, 24, 0x334155, 0x1f2937);
    grid.rotateX(Math.PI / 2);
    scene.add(grid);

    let disposed = false;
    fitRef.current = () => {
      fitMeshes(camera, controls, meshesRef.current);
    };
    const loader = new STLLoader();
    Promise.all(manifest.components.map(async (component) => {
      const geometry = await loader.loadAsync(component.path);
      geometry.computeVertexNormals();
      const material = new THREE.MeshStandardMaterial({
        color: component.color,
        roughness: 0.55,
        metalness: component.kind === 'fastener'
          ? 0.78
          : component.kind === 'interference' ? 0.2 : 0.05,
        transparent: true,
        opacity: component.opacity,
        side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.visible = visibleIdsRef.current.has(component.id);
      mesh.userData.component = component;
      meshesRef.current.set(component.id, mesh);
      scene.add(mesh);
      if (!disposed) {
        setLoadedCount((count) => count + 1);
      }
    })).then(() => {
      if (!disposed) {
        meshesRef.current.forEach((mesh, id) => {
          mesh.visible = visibleIdsRef.current.has(id);
        });
        if (initialPreset) {
          controls.target.set(...initialPreset.target);
          camera.position.set(...initialPreset.position);
          camera.lookAt(controls.target);
          controls.update();
          controls.saveState();
        } else {
          fitMeshes(camera, controls, meshesRef.current);
        }
        setLoading(false);
      }
    }).catch((reason: unknown) => {
      if (!disposed) {
        setError(`STL 加载失败：${String(reason)}`);
        setLoading(false);
      }
    });

    const resize = () => {
      const width = Math.max(host.clientWidth, 1);
      const height = Math.max(host.clientHeight, 1);
      renderer.setSize(width, height, false);
      renderer.domElement.style.width = `${width}px`;
      renderer.domElement.style.height = `${height}px`;
      renderer.domElement.style.display = 'block';
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();
    let frame = 0;
    const render = () => {
      controls.update();
      renderer.render(scene, camera);
      frame = requestAnimationFrame(render);
    };
    render();

    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      meshesRef.current.forEach((mesh) => {
        mesh.geometry.dispose();
        (mesh.material as THREE.Material).dispose();
      });
      meshesRef.current.clear();
      fitRef.current = () => undefined;
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [manifest]);

  useEffect(() => {
    visibleIdsRef.current = visibleIds;
    const clipping = sectioned
      ? [new THREE.Plane(new THREE.Vector3(1, 0, 0), 0)]
      : [];
    meshesRef.current.forEach((mesh, id) => {
      mesh.visible = visibleIds.has(id);
      mesh.position.z = exploded ? (EXPLODE_Z[id] ?? 0) : 0;
      const material = mesh.material as THREE.MeshStandardMaterial;
      const kind = mesh.userData.component?.kind as string | undefined;
      material.opacity = kind === 'interference'
        ? 0.82
        : transparent ? 0.28 : 1;
      material.clippingPlanes = clipping;
      material.needsUpdate = true;
    });
  }, [exploded, sectioned, transparent, visibleIds, manifest]);

  const views = useMemo<ProcessView[]>(() => {
    if (!manifest) return [];
    if (mode === 'steps') return manifest.processSteps;
    if (mode === 'types') return manifest.processTypes;
    return [];
  }, [manifest, mode]);

  const applyCamera = (preset?: CameraPreset) => {
    if (!preset || !cameraRef.current || !controlsRef.current) return;
    controlsRef.current.target.set(...preset.target);
    cameraRef.current.position.set(...preset.position);
    cameraRef.current.near = 0.1;
    cameraRef.current.far = 3000;
    cameraRef.current.updateProjectionMatrix();
    cameraRef.current.lookAt(controlsRef.current.target);
    controlsRef.current.update();
    controlsRef.current.saveState();
  };

  const selectView = (view: ProcessView) => {
    setActiveId(view.id);
    setVisibleIds(new Set(view.components));
    setExploded(view.id === 'four_layers');
    if (manifest) applyCamera(cameraById(manifest, view.camera));
  };

  const toggleComponent = (id: string) => {
    setVisibleIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div style={{ display: 'flex', flex: 1, minHeight: 0, color: '#e5e7eb' }}>
      <aside style={PANEL}>
        <h2 style={{ margin: '0 0 4px', color: '#60a5fa' }}>M6 工艺预览</h2>
        <div style={{ color: '#94a3b8', fontSize: 12, marginBottom: 12 }}>
          四层连续承力 · 头柄无缝
        </div>
        <div style={{ display: 'flex', gap: 5, marginBottom: 10 }}>
          {([
            ['steps', '按步骤'],
            ['types', '按工艺'],
            ['components', '按组件'],
          ] as const).map(([id, label]) => (
            <button
              key={id}
              type="button"
              style={{ ...BUTTON, background: mode === id ? '#1d4ed8' : '#1f2937' }}
              onClick={() => setMode(id)}
            >
              {label}
            </button>
          ))}
        </div>

        {mode !== 'components' && (
          <div style={{ display: 'grid', gap: 6 }}>
            {views.map((view) => (
              <button
                key={view.id}
                type="button"
                style={{ ...BUTTON, borderColor: activeId === view.id ? '#60a5fa' : '#374151' }}
                onClick={() => selectView(view)}
              >
                {view.label}
              </button>
            ))}
          </div>
        )}

        {mode === 'components' && manifest && (
          <div style={{ display: 'grid', gap: 6 }}>
            {manifest.components.map((component) => (
              <label key={component.id} style={{ fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={visibleIds.has(component.id)}
                  onChange={() => toggleComponent(component.id)}
                />{' '}
                {component.label}
              </label>
            ))}
          </div>
        )}

        <h3 style={{ fontSize: 14, marginBottom: 7 }}>装配效果</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          <button type="button" style={BUTTON} onClick={() => setTransparent((value) => !value)}>
            {transparent ? '取消透明' : '透明观察'}
          </button>
          <button type="button" style={BUTTON} onClick={() => setExploded((value) => !value)}>
            {exploded ? '合拢' : '爆炸'}
          </button>
          <button type="button" style={BUTTON} onClick={() => setSectioned((value) => !value)}>
            {sectioned ? '取消剖切' : 'X=0 剖切'}
          </button>
          <button type="button" style={BUTTON} onClick={() => fitRef.current()}>
            适配模型
          </button>
        </div>

        <h3 style={{ fontSize: 14, marginBottom: 7 }}>特写</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          {manifest?.cameraPresets.map((preset) => (
            <button key={preset.id} type="button" style={BUTTON} onClick={() => applyCamera(preset)}>
              {preset.label}
            </button>
          ))}
        </div>
        {error && <p style={{ color: '#fca5a5', fontSize: 12 }}>{error}</p>}
      </aside>
      <div style={{ flex: 1, minWidth: 0, position: 'relative' }}>
        <div ref={hostRef} style={{ position: 'absolute', inset: 0 }} />
        {(loading || error) && (
          <div
            style={{
              position: 'absolute',
              top: 12,
              right: 12,
              zIndex: 2,
              maxWidth: 420,
              padding: '9px 12px',
              borderRadius: 7,
              border: `1px solid ${error ? '#7f1d1d' : '#1d4ed8'}`,
              background: error ? '#2a1515ee' : '#172554ee',
              color: error ? '#fca5a5' : '#bfdbfe',
              fontSize: 12,
            }}
          >
            {error || `正在加载 STL：${loadedCount}/${manifest?.components.length ?? 0}`}
          </div>
        )}
      </div>
    </div>
  );
}
//#endregion
