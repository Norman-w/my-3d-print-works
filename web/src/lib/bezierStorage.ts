/**
 * Bezier persistence: server SQLite + userBezierProfiles.json (manual save).
 */

import { ALL_DRAW_TARGETS, BezierProfile, DrawTarget } from './bezierProfile';
import {
  clearProfileCache,
  ensureProfilesLoaded,
  getCachedBundle,
  setCacheFromBundle,
  type BezierProfilesBundle,
} from './profileCache';

export type { BezierProfilesBundle };

export type StoreProfilesResult = {
  path: string;
  saved_keys: string[];
  merged_from_disk: string[];
  stored_at: string;
};

export type ProjectProfilesResult = {
  path: string;
  profiles: BezierProfilesBundle;
  keys: string[];
  storage?: string;
};

export type SnapshotMeta = {
  id: string;
  label: string;
  created_at: string;
  keys: string[];
};

export type RestoreSnapshotResult = {
  restored_id: string;
  label: string;
  path: string;
  keys: string[];
  stored_at: string;
};

async function parseJsonResponse<T>(res: Response): Promise<T> {
  const text = await res.text();
  let data: T & { error?: string };
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(text || `HTTP ${res.status}`);
  }
  if (!res.ok) throw new Error((data as { error?: string }).error || text || `HTTP ${res.status}`);
  return data;
}

function rawToBundle(profiles: Record<string, unknown>): BezierProfilesBundle {
  const bundle: BezierProfilesBundle = {};
  for (const target of ALL_DRAW_TARGETS) {
    const p = profiles[target];
    if (p && typeof p === 'object') {
      const prof = p as BezierProfile;
      if (prof.target === target && prof.start && Array.isArray(prof.segments)) {
        bundle[target] = prof;
      }
    }
  }
  return bundle;
}

const TARGET_LABELS: Record<DrawTarget, string> = {
  'blade-front': '底板正视',
  'handle-front': '手柄正视',
  side: '柄侧视',
  'handle-bottom': '柄底视',
};

export function labelTargets(targets: DrawTarget[]): string {
  return targets.map(t => TARGET_LABELS[t]).join('、');
}

export function formatStoreSuccessMessage(result: StoreProfilesResult): string {
  const lines = [
    '保存成功',
    `曲线：${result.saved_keys.length > 0 ? labelTargets(result.saved_keys as DrawTarget[]) : '（无）'}`,
    `SQLite + JSON：${result.path}`,
    `时间：${result.stored_at}`,
  ];
  if (result.merged_from_disk?.length) {
    lines.splice(2, 0, `与磁盘合并保留：${result.merged_from_disk.join('、')}`);
  }
  return lines.join('\n');
}

export function formatStoreErrorMessage(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err);
  if (msg.includes('404')) {
    return `保存失败：后端 API 不可用（404）。请先运行 ./dev.sh 启动 Go 服务。\n${msg}`;
  }
  return `保存失败：${msg}`;
}

export async function flushPendingSaves(): Promise<StoreProfilesResult> {
  const bundle = getCachedBundle();
  const result = await storeProfilesToProject(bundle);
  return result;
}

export function bundleToDownloadJson(bundle: BezierProfilesBundle): string {
  return JSON.stringify(bundle, null, 2);
}

export function downloadBundleAsFile(bundle: BezierProfilesBundle, filename = 'userBezierProfiles.json'): void {
  const blob = new Blob([bundleToDownloadJson(bundle)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function fetchProjectProfiles(): Promise<ProjectProfilesResult> {
  const res = await fetch('/api/bezier-profiles/project');
  const data = await parseJsonResponse<{
    path: string;
    profiles: Record<string, unknown>;
    keys: string[];
    storage?: string;
  }>(res);
  return {
    path: data.path,
    keys: data.keys,
    storage: data.storage,
    profiles: rawToBundle(data.profiles),
  };
}

export async function reimportProjectFile(): Promise<{ keys: string[]; path: string }> {
  const res = await fetch('/api/bezier-profiles/reimport-file', { method: 'POST' });
  return parseJsonResponse(res);
}

export async function reloadProfilesFromServer(): Promise<BezierProfilesBundle> {
  clearProfileCache();
  return ensureProfilesLoaded();
}

export function applyBundleToEditor(bundle: BezierProfilesBundle): DrawTarget[] {
  setCacheFromBundle(bundle);
  const applied: DrawTarget[] = [];
  for (const target of ALL_DRAW_TARGETS) {
    if (bundle[target]) applied.push(target);
  }
  window.dispatchEvent(new CustomEvent('smartpaddle-profiles-loaded'));
  window.dispatchEvent(new CustomEvent('smartpaddle-profiles-updated'));
  return applied;
}

export async function storeProfilesToProject(bundle: BezierProfilesBundle): Promise<StoreProfilesResult> {
  const res = await fetch('/api/bezier-profiles/store', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profiles: bundle }),
  });
  const result = await parseJsonResponse<StoreProfilesResult>(res);
  setCacheFromBundle({ ...getCachedBundle(), ...bundle });
  return result;
}

export async function listSnapshots(): Promise<SnapshotMeta[]> {
  const res = await fetch('/api/bezier-profiles/snapshots');
  const data = await parseJsonResponse<{ snapshots: SnapshotMeta[] }>(res);
  return data.snapshots ?? [];
}

export async function createSnapshot(label?: string): Promise<SnapshotMeta> {
  const res = await fetch('/api/bezier-profiles/snapshots', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label: label?.trim() || undefined }),
  });
  return parseJsonResponse(res);
}

export async function restoreSnapshotToProject(id: string): Promise<RestoreSnapshotResult> {
  const res = await fetch(`/api/bezier-profiles/snapshots/${encodeURIComponent(id)}/restore`, {
    method: 'POST',
  });
  return parseJsonResponse(res);
}
