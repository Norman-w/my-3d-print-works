//#region 模型/类型
export interface ProcessComponent {
  id: string;
  label: string;
  path: string;
  color: string;
  kind: 'skin' | 'core' | 'monolithic' | 'assembly' | 'inspection' | 'interference';
  opacity: number;
}

export interface ProcessView {
  id: string;
  label: string;
  components: string[];
  camera?: string;
}

export interface CameraPreset {
  id: string;
  label: string;
  target: [number, number, number];
  position: [number, number, number];
}

export interface ProcessPreviewManifest {
  schemaVersion: number;
  modelVersion: string;
  generatedAt: string;
  components: ProcessComponent[];
  processSteps: ProcessView[];
  processTypes: ProcessView[];
  cameraPresets: CameraPreset[];
}
//#endregion

//#region 常量/配置
export const PROCESS_MANIFEST_URL = '/stl/preview/manifest.json';
//#endregion

//#region 公开 API
export async function loadProcessManifest(): Promise<ProcessPreviewManifest> {
  const response = await fetch(PROCESS_MANIFEST_URL, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`manifest HTTP ${response.status}`);
  }
  const manifest = await response.json() as ProcessPreviewManifest;
  if (manifest.schemaVersion !== 1 || !Array.isArray(manifest.components)) {
    throw new Error('不支持的工艺预览 manifest');
  }
  return manifest;
}
//#endregion
