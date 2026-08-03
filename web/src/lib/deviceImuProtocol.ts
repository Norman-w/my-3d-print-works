//#region 常量/配置

/** 与 firmware `Im948ReportTag` / `ws_data_send_imu_frame` 写入顺序一致 */
export const DEVICE_TAG = {
  ACCEL_NO_GRAVITY: 0x0001,
  ACCEL_WITH_GRAVITY: 0x0002,
  ANGULAR_VELOCITY: 0x0004,
  MAGNETIC: 0x0008,
  TEMP_PRESSURE_HEIGHT: 0x0010,
  QUATERNION: 0x0020,
  EULER_ANGLES: 0x0040,
  DISPLACEMENT: 0x0080,
  ACCEL_NAV_FRAME: 0x0200,
} as const;

/** C4 配网后当前 LAN 地址（DHCP 可能变；mDNS 见 DEFAULT_DEVICE_MDNS） */
export const DEFAULT_DEVICE_HOST = '192.168.7.90';
export const DEFAULT_DEVICE_MDNS = 'SP-346C.local';
export const DEVICE_HOST_STORAGE_KEY = 'smartpaddle.deviceHost';

const LEGACY_DEVICE_HOSTS = ['192.168.7.52', '192.168.7.80'] as const;

//#endregion

//#region 模型/类型

export interface DeviceImuFrame {
  ts: number;
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
  roll?: number;
  pitch?: number;
  yaw?: number;
}

//#endregion

//#region 私有成员

function readBe16(view: DataView, offset: number): number {
  return view.getUint16(offset, false);
}

function readBe32(view: DataView, offset: number): number {
  return view.getUint32(offset, false);
}

function readF32Le(view: DataView, offset: number): number {
  return view.getFloat32(offset, true);
}

function normalizeDeviceHost(hostOrUrl: string): string {
  const raw = hostOrUrl.trim();
  if (!raw) return DEFAULT_DEVICE_HOST;
  if (/^wss?:\/\//i.test(raw)) {
    try {
      return new URL(raw).host;
    } catch {
      return DEFAULT_DEVICE_HOST;
    }
  }
  return raw
    .replace(/^https?:\/\//i, '')
    .replace(/\/+$/, '')
    .split('/')[0];
}

//#endregion

//#region 公开 API

function isLanDeviceHost(host: string): boolean {
  return (
    /^(192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)/.test(host) ||
    host.endsWith('.local') ||
    /^SP-/i.test(host)
  );
}

/** 把用户输入规范成 WebSocket URL（开发环境经 Vite 同源代理到板子） */
export function buildDeviceWsUrl(hostOrUrl: string): string {
  const raw = hostOrUrl.trim();
  if (/^wss?:\/\//i.test(raw)) return raw;

  const deviceHost = normalizeDeviceHost(raw || DEFAULT_DEVICE_HOST);

  if (import.meta.env.DEV && typeof window !== 'undefined') {
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    if (isLanDeviceHost(deviceHost)) {
      return `${wsProto}//${window.location.host}/device/ws`;
    }
  }

  const path = deviceHost.includes('/') ? '' : '/ws';
  return `ws://${deviceHost}${path}`;
}

export function loadSavedDeviceHost(): string {
  try {
    const saved = localStorage.getItem(DEVICE_HOST_STORAGE_KEY);
    if (saved && saved.trim()) {
      const trimmed = saved.trim();
      if (
        (LEGACY_DEVICE_HOSTS as readonly string[]).includes(trimmed)
      ) {
        saveDeviceHost(DEFAULT_DEVICE_HOST);
        return DEFAULT_DEVICE_HOST;
      }
      return trimmed;
    }
  } catch {
    /* ignore */
  }
  return DEFAULT_DEVICE_HOST;
}

/** URL `?device=` 优先，否则 localStorage（含旧默认迁移） */
export function resolveInitialDeviceHost(): string {
  try {
    const fromUrl = new URLSearchParams(window.location.search)
      .get('device')
      ?.trim();
    if (fromUrl) {
      saveDeviceHost(fromUrl);
      return fromUrl;
    }
  } catch {
    /* ignore */
  }
  return loadSavedDeviceHost();
}

export function saveDeviceHost(host: string): void {
  try {
    localStorage.setItem(DEVICE_HOST_STORAGE_KEY, host.trim());
  } catch {
    /* ignore */
  }
}

/**
 * 解析设备端二进制 IMU 帧（帧头大端，float 小端，与 ESP32 memcpy 一致）。
 * 仅按固件实际写出的 tag 顺序读字段（忽略 ACTIVITY/ADC/GPIO 位）。
 */
export function parseDeviceImuBinary(buf: ArrayBuffer): DeviceImuFrame | null {
  if (buf.byteLength < 16) return null;
  const view = new DataView(buf);
  if (view.getUint8(0) !== 0x49) return null; // 'I'

  const ts = readBe32(view, 1);
  const tags = readBe16(view, 13);
  const flags = view.getUint8(15);
  if ((flags & 0x01) === 0) return null;

  let pos = 16;
  const need = (n: number) => pos + n <= buf.byteLength;
  const take3 = (): [number, number, number] | null => {
    if (!need(12)) return null;
    const a = readF32Le(view, pos);
    const b = readF32Le(view, pos + 4);
    const c = readF32Le(view, pos + 8);
    pos += 12;
    return [a, b, c];
  };
  const take4 = (): [number, number, number, number] | null => {
    if (!need(16)) return null;
    const a = readF32Le(view, pos);
    const b = readF32Le(view, pos + 4);
    const c = readF32Le(view, pos + 8);
    const d = readF32Le(view, pos + 12);
    pos += 16;
    return [a, b, c, d];
  };

  let ax = 0;
  let ay = 0;
  let az = 0;
  let gx = 0;
  let gy = 0;
  let gz = 0;
  let qw: number | undefined;
  let qx: number | undefined;
  let qy: number | undefined;
  let qz: number | undefined;
  let roll: number | undefined;
  let pitch: number | undefined;
  let yaw: number | undefined;

  if (tags & DEVICE_TAG.ACCEL_NO_GRAVITY) {
    const v = take3();
    if (!v) return null;
    [ax, ay, az] = v;
  }
  if (tags & DEVICE_TAG.ACCEL_WITH_GRAVITY) {
    const v = take3();
    if (!v) return null;
    [ax, ay, az] = v;
  }
  if (tags & DEVICE_TAG.ANGULAR_VELOCITY) {
    const v = take3();
    if (!v) return null;
    [gx, gy, gz] = v;
  }
  if (tags & DEVICE_TAG.MAGNETIC) {
    if (!take3()) return null;
  }
  if (tags & DEVICE_TAG.TEMP_PRESSURE_HEIGHT) {
    if (!take3()) return null;
  }
  if (tags & DEVICE_TAG.QUATERNION) {
    const v = take4();
    if (!v) return null;
    [qw, qx, qy, qz] = v;
  }
  if (tags & DEVICE_TAG.EULER_ANGLES) {
    const v = take3();
    if (!v) return null;
    [roll, pitch, yaw] = v;
  }
  if (tags & DEVICE_TAG.DISPLACEMENT) {
    if (!take3()) return null;
  }
  if (tags & DEVICE_TAG.ACCEL_NAV_FRAME) {
    if (!take3()) return null;
  }

  return { ts, ax, ay, az, gx, gy, gz, qw, qx, qy, qz, roll, pitch, yaw };
}

//#endregion
