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

export type DeviceWsHandlers = {
  onStatus?: (s: DeviceWsStatus) => void;
  onImu?: (frame: DeviceImuFrame) => void;
  onImpact?: (evt: {
    ts: number;
    tdoa_ns: number[];
    x_mm?: number;
    y_mm?: number;
    confidence?: number;
  }) => void;
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
        case 'impact':
          for (const sub of subscribers.values()) {
            sub.handlers.onImpact?.({
              ts: msg.ts ?? Date.now(),
              tdoa_ns: msg.tdoa_ns ?? [],
              x_mm: msg.x_mm,
              y_mm: msg.y_mm,
              confidence: msg.confidence,
            });
          }
          break;
        default:
          break;
      }
    } catch {
      /* ignore */
    }
  };

  socket.onerror = () => {
    if (ws !== socket) return;
    setStatus({ lastError: `连接失败: ${url}` });
  };

  socket.onclose = () => {
    if (ws === socket) {
      ws = null;
      setStatus({ connected: false });
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
  ensureConnected(hostOrUrl);
  // 立刻同步当前状态给新订阅者
  handlers.onStatus?.(status);

  return () => {
    subscribers.delete(id);
    if (subscribers.size > 0) return;

    // 最后一个订阅者离开：延迟关闭，躲开 React StrictMode 双挂载
    window.setTimeout(() => {
      if (subscribers.size > 0) return;
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
      setStatus({ connected: false, sessionId: null });
    }, 300);
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
//#endregion
