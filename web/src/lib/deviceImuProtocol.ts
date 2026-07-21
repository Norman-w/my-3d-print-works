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

export const DEFAULT_DEVICE_HOST = '192.168.7.80';
export const DEVICE_HOST_STORAGE_KEY = 'smartpaddle.deviceHost';

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

//#endregion

//#region 公开 API

/** 把用户输入规范成 `ws://host/ws`（已是完整 ws URL 则原样返回） */
export function buildDeviceWsUrl(hostOrUrl: string): string {
  const raw = hostOrUrl.trim();
  if (!raw) return `ws://${DEFAULT_DEVICE_HOST}/ws`;
  if (/^wss?:\/\//i.test(raw)) return raw;
  const withoutScheme = raw.replace(/^https?:\/\//i, '');
  const host = withoutScheme.replace(/\/+$/, '');
  const path = host.includes('/') ? '' : '/ws';
  return `ws://${host}${path}`;
}

export function loadSavedDeviceHost(): string {
  try {
    const saved = localStorage.getItem(DEVICE_HOST_STORAGE_KEY);
    if (saved && saved.trim()) return saved.trim();
  } catch {
    /* ignore */
  }
  return DEFAULT_DEVICE_HOST;
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
