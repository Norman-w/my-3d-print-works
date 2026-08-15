//#region 导入/依赖
import {
  buildDeviceWsUrl,
  parseDeviceImuBinary,
  type DeviceImuFrame,
} from './deviceImuProtocol';
//#endregion

//#region 常量/配置
const RECONNECT_MS = 2500;
const UI_FLUSH_MS = 50;
//#endregion

//#region 模型/类型
export type DeviceWsStatus = {
  connected: boolean;
  lastError: string | null;
  sessionId: string | null;
};

export type PowerTelemetry = {
  batteryMv: number;
  batteryPercent: number;
  percentIsEstimate: boolean;
  adcCalibrated: boolean;
};

export type DeviceWsHandlers = {
  onStatus?: (s: DeviceWsStatus) => void;
  onImu?: (frame: DeviceImuFrame) => void;
  onImpact?: (evt: {
    ts: number;
    tdoa_ns: number[];
    first_ch?: number;
    hits?: { ch: number; dt_ns: number; edges: number }[];
    x_mm?: number;
    y_mm?: number;
    confidence?: number;
  }) => void;
  onPower?: (power: PowerTelemetry) => void;
};
//#endregion

//#region 私有成员
type Subscriber = { id: number; handlers: DeviceWsHandlers };

let nextSubId = 1;
let subscribers = new Map<number, Subscriber>();
let ws: WebSocket | null = null;
let activeUrl = '';
let reconnectTimer: number | null = null;
let intentionalClose = false;
let pendingImu: DeviceImuFrame | null = null;
let flushTimer: number | null = null;
let status: DeviceWsStatus = {
  connected: false,
  lastError: null,
  sessionId: null,
};

function broadcastStatus() {
  for (const sub of subscribers.values()) {
    sub.handlers.onStatus?.(status);
  }
}

function setStatus(patch: Partial<DeviceWsStatus>) {
  status = { ...status, ...patch };
  broadcastStatus();
}

function clearReconnect() {
  if (reconnectTimer != null) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

function flushImu() {
  flushTimer = null;
  const frame = pendingImu;
  if (!frame) return;
  pendingImu = null;
  for (const sub of subscribers.values()) {
    sub.handlers.onImu?.(frame);
  }
}

function queueImu(frame: DeviceImuFrame) {
  pendingImu = frame;
  if (flushTimer == null) {
    flushTimer = window.setTimeout(flushImu, UI_FLUSH_MS);
  }
}

function attach(socket: WebSocket, url: string) {
  socket.binaryType = 'arraybuffer';

  socket.onopen = () => {
    if (ws !== socket) return;
    setStatus({ connected: true, lastError: null, sessionId: url });
  };

  socket.onmessage = (event) => {
    if (ws !== socket) return;

    if (event.data instanceof ArrayBuffer) {
      const frame = parseDeviceImuBinary(event.data);
      if (frame) queueImu(frame);
      return;
    }

    if (event.data instanceof Blob) {
      void event.data.arrayBuffer().then((buf) => {
        if (ws !== socket) return;
        const frame = parseDeviceImuBinary(buf);
        if (frame) queueImu(frame);
      });
      return;
    }

    try {
      const msg = JSON.parse(event.data as string);
      switch (msg.type) {
        case 'hello':
          setStatus({ sessionId: msg.session_id ?? url });
          break;
        case 'impact_ack':
        case 'impact': {
          const hits = Array.isArray(msg.hits)
            ? msg.hits.map(
                (h: { ch?: number; dt_ns?: number; edges?: number }) => ({
                  ch: Number(h.ch ?? 0),
                  dt_ns: Number(h.dt_ns ?? 0),
                  edges: Number(h.edges ?? 0),
                }),
              )
            : [];
          const tdoa =
            msg.tdoa_ns ??
            hits.map((h: { dt_ns: number }) => h.dt_ns);
          for (const sub of subscribers.values()) {
            sub.handlers.onImpact?.({
              ts: msg.ts ?? msg.ts_base ?? Date.now(),
              tdoa_ns: tdoa,
              first_ch:
                msg.first !== undefined ? Number(msg.first) : hits[0]?.ch,
              hits,
              x_mm: msg.x_mm,
              y_mm: msg.y_mm,
              confidence: msg.confidence,
            });
          }
          break;
        }
        case 'power': {
          const power: PowerTelemetry = {
            batteryMv: Number(msg.battery_mv),
            batteryPercent: Math.max(
              0,
              Math.min(100, Number(msg.battery_percent)),
            ),
            percentIsEstimate: msg.percent_is_estimate === true,
            adcCalibrated: msg.adc_calibrated === true,
          };
          if (
            Number.isFinite(power.batteryMv) &&
            Number.isFinite(power.batteryPercent)
          ) {
            for (const sub of subscribers.values()) {
              sub.handlers.onPower?.(power);
            }
          }
          break;
        }
        default:
          break;
      }
    } catch {
      /* ignore */
    }
  };

  socket.onerror = () => {
    if (ws !== socket) return;
    setStatus({
      lastError: `WebSocket 失败: ${url}（请确认与板子同一 WiFi，或刷新后重试）`,
    });
  };

  socket.onclose = (ev) => {
    if (ws === socket) {
      ws = null;
      const hint =
        ev.code !== 1000 && ev.reason
          ? `${ev.code}: ${ev.reason}`
          : ev.code !== 1000
            ? `code ${ev.code}`
            : null;
      setStatus({
        connected: false,
        lastError: hint ? `连接关闭 (${hint})` : status.lastError,
      });
    }
    if (intentionalClose || subscribers.size === 0) return;
    clearReconnect();
    reconnectTimer = window.setTimeout(() => {
      if (subscribers.size === 0 || intentionalClose) return;
      openSocket(activeUrl);
    }, RECONNECT_MS);
  };
}

function openSocket(url: string) {
  if (
    ws &&
    activeUrl === url &&
    (ws.readyState === WebSocket.OPEN ||
      ws.readyState === WebSocket.CONNECTING)
  ) {
    return;
  }

  clearReconnect();
  intentionalClose = false;
  activeUrl = url;

  if (ws) {
    const prev = ws;
    // 避免旧 socket 的 onclose 再排一次重连
    prev.onclose = null;
    prev.onopen = null;
    prev.onmessage = null;
    prev.onerror = null;
    try {
      prev.close();
    } catch {
      /* ignore */
    }
    ws = null;
  }

  const next = new WebSocket(url);
  ws = next;
  attach(next, url);
}

function ensureConnected(hostOrUrl: string) {
  const url = buildDeviceWsUrl(hostOrUrl);
  if (ws && activeUrl === url) {
    const state = ws.readyState;
    if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) {
      return;
    }
  }
  openSocket(url);
}
//#endregion

//#region 公开 API

export function subscribeDeviceWs(
  hostOrUrl: string,
  handlers: DeviceWsHandlers,
): () => void {
  const id = nextSubId++;
  subscribers.set(id, { id, handlers });
  const url = buildDeviceWsUrl(hostOrUrl);
  if (url !== activeUrl || !ws || ws.readyState === WebSocket.CLOSED) {
    openSocket(url);
  } else if (ws.readyState === WebSocket.OPEN) {
    activeUrl = url;
  } else {
    activeUrl = url;
    ensureConnected(hostOrUrl);
  }
  handlers.onStatus?.(status);

  return () => {
    subscribers.delete(id);
    // 不在 unmount 时关 WebSocket：StrictMode 会双挂载，关连接会把板子单例 WS 踢掉
  };
}

export function retargetDeviceWs(hostOrUrl: string) {
  const url = buildDeviceWsUrl(hostOrUrl);
  if (url === activeUrl && ws) {
    const state = ws.readyState;
    if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) return;
  }
  if (subscribers.size === 0) {
    activeUrl = url;
    return;
  }
  openSocket(url);
}

export function getDeviceWsStatus(): DeviceWsStatus {
  return status;
}

export function reconnectDeviceWs(hostOrUrl: string): void {
  const url = buildDeviceWsUrl(hostOrUrl);
  intentionalClose = true;
  clearReconnect();
  if (ws) {
    const prev = ws;
    prev.onclose = null;
    prev.onopen = null;
    prev.onmessage = null;
    prev.onerror = null;
    try {
      prev.close();
    } catch {
      /* ignore */
    }
    ws = null;
  }
  intentionalClose = false;
  activeUrl = url;
  setStatus({ connected: false, lastError: null, sessionId: null });
  if (subscribers.size > 0) {
    openSocket(url);
  }
}

export function disconnectDeviceWs(): void {
  intentionalClose = true;
  clearReconnect();
  if (flushTimer != null) {
    window.clearTimeout(flushTimer);
    flushTimer = null;
  }
  pendingImu = null;
  if (ws) {
    const sock = ws;
    sock.onclose = null;
    sock.onopen = null;
    sock.onmessage = null;
    sock.onerror = null;
    try {
      sock.close();
    } catch {
      /* ignore */
    }
    ws = null;
  }
  setStatus({ connected: false, sessionId: null, lastError: null });
  intentionalClose = false;
}

if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    disconnectDeviceWs();
  });
}
//#endregion
