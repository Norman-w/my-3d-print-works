/** In-memory Bezier profiles; server (SQLite) is the source of truth. */

import type { BezierProfile, DrawTarget } from './bezierProfile';

const ALL_DRAW_TARGETS: DrawTarget[] = ['blade-front', 'handle-front', 'side', 'handle-bottom'];

const LEGACY_LS_KEYS = [
  'smartpaddle-bezier-ui',
  'smartpaddle-bezier-active-target',
  'smartpaddle-ref-layout',
  'smartpaddle-photo-map',
];

export type BezierProfilesBundle = Partial<Record<DrawTarget, BezierProfile>>;

let cache: BezierProfilesBundle = {};
let loaded = false;
let loadPromise: Promise<BezierProfilesBundle> | null = null;

export function isProfileCacheLoaded(): boolean {
  return loaded;
}

export function getCachedProfile(target: DrawTarget): BezierProfile | undefined {
  return cache[target];
}

export function getCachedBundle(): BezierProfilesBundle {
  return { ...cache };
}

export function setCachedProfile(profile: BezierProfile): void {
  cache[profile.target] = profile;
}

export function setCacheFromBundle(bundle: BezierProfilesBundle): void {
  cache = { ...bundle };
  loaded = true;
}

export function clearProfileCache(): void {
  cache = {};
  loaded = false;
  loadPromise = null;
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

/** Drop obsolete browser keys (curves now live on server only). */
export function purgeLegacyBezierBrowserStorage(): void {
  try {
    for (const target of ALL_DRAW_TARGETS) {
      localStorage.removeItem(`smartpaddle-bezier-${target}`);
    }
    for (const key of LEGACY_LS_KEYS) {
      localStorage.removeItem(key);
    }
  } catch {
    /* ignore */
  }
}

/** Load curves from GET /api/bezier-profiles/project (used on startup and manual refresh). */
export async function ensureProfilesLoaded(): Promise<BezierProfilesBundle> {
  if (loaded) return getCachedBundle();
  if (!loadPromise) {
    loadPromise = (async () => {
      const res = await fetch('/api/bezier-profiles/project');
      const text = await res.text();
      let data: { profiles?: Record<string, unknown>; error?: string };
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error(text || `HTTP ${res.status}`);
      }
      if (!res.ok) {
        if (res.status === 404) {
          throw new Error('API 404：请重启 Go 服务（./dev.sh）');
        }
        throw new Error(data.error || text);
      }
      const bundle = rawToBundle(data.profiles ?? {});
      setCacheFromBundle(bundle);
      purgeLegacyBezierBrowserStorage();
      window.dispatchEvent(new CustomEvent('smartpaddle-profiles-loaded'));
      return getCachedBundle();
    })().finally(() => {
      loadPromise = null;
    });
  }
  return loadPromise;
}

export function notifyProfilesUpdated(): void {
  window.dispatchEvent(new CustomEvent('smartpaddle-profiles-updated'));
}
