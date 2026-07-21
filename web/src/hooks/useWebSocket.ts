//#region 导入/依赖
import { useState, useEffect, useRef, useCallback } from 'react';
import {
  buildDeviceWsUrl,
  parseDeviceImuBinary,
  type DeviceImuFrame,
} from '../lib/deviceImuProtocol';
//#endregion

//#region 常量/配置
const UI_FLUSH_MS = 50; // ~20Hz 刷新 React，避免 250Hz 打爆 UI
const RECONNECT_MS = 2000;
//#endregion

//#region 模型/类型
export type IMUFrame = DeviceImuFrame;

export interface ImpactEvent {
  ts: number;
  tdoa_ns: number[];
  x_mm?: number;
  y_mm?: number;
  confidence?: number;
}

interface WebSocketState {
  connected: boolean;
  imuData: IMUFrame[];
  impactData: ImpactEvent[];
  sessionId: string | null;
  lastError: string | null;
}
//#endregion

//#region 公开 API

export function useWebSocket(hostOrUrl: string, enabled = true) {
  const wsRef = useRef<WebSocket | null>(null);
  const urlRef = useRef(buildDeviceWsUrl(hostOrUrl));
  const pendingImuRef = useRef<IMUFrame | null>(null);
  const flushTimerRef = useRef<number | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const disposedRef = useRef(false);

  const [state, setState] = useState<WebSocketState>({
    connected: false,
    imuData: [],
    impactData: [],
    sessionId: null,
    lastError: null,
  });

  const flushPendingImu = useCallback(() => {
    flushTimerRef.current = null;
    const frame = pendingImuRef.current;
    if (!frame) return;
    pendingImuRef.current = null;
    setState((s) => ({
      ...s,
      imuData: [...s.imuData.slice(-500), frame],
    }));
  }, []);

  const queueImu = useCallback(
    (frame: IMUFrame) => {
      pendingImuRef.current = frame;
      if (flushTimerRef.current == null) {
        flushTimerRef.current = window.setTimeout(flushPendingImu, UI_FLUSH_MS);
      }
    },
    [flushPendingImu],
  );

  useEffect(() => {
    disposedRef.current = false;
    const url = buildDeviceWsUrl(hostOrUrl);
    urlRef.current = url;

    const clearReconnect = () => {
      if (reconnectTimerRef.current != null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    const attach = (ws: WebSocket) => {
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        if (disposedRef.current || wsRef.current !== ws) return;
        setState((s) => ({
          ...s,
          connected: true,
          lastError: null,
          sessionId: url,
        }));
      };

      ws.onmessage = (event) => {
        if (disposedRef.current || wsRef.current !== ws) return;

        if (event.data instanceof ArrayBuffer) {
          const frame = parseDeviceImuBinary(event.data);
          if (frame) queueImu(frame);
          return;
        }

        if (event.data instanceof Blob) {
          void event.data.arrayBuffer().then((buf) => {
            if (disposedRef.current || wsRef.current !== ws) return;
            const frame = parseDeviceImuBinary(buf);
            if (frame) queueImu(frame);
          });
          return;
        }

        try {
          const msg = JSON.parse(event.data as string);
          switch (msg.type) {
            case 'hello':
              setState((s) => ({ ...s, sessionId: msg.session_id ?? url }));
              break;
            case 'impact_ack':
            case 'impact':
              setState((s) => ({
                ...s,
                impactData: [
                  ...s.impactData.slice(-50),
                  {
                    ts: msg.ts ?? Date.now(),
                    tdoa_ns: msg.tdoa_ns ?? [],
                    x_mm: msg.x_mm,
                    y_mm: msg.y_mm,
                    confidence: msg.confidence,
                  },
                ],
              }));
              break;
            default:
              break;
          }
        } catch {
          /* ignore non-json text */
        }
      };

      ws.onerror = () => {
        if (disposedRef.current || wsRef.current !== ws) return;
        setState((s) => ({
          ...s,
          lastError: `连接失败: ${url}`,
        }));
      };

      ws.onclose = () => {
        if (disposedRef.current) return;
        if (wsRef.current === ws) {
          wsRef.current = null;
          setState((s) => ({ ...s, connected: false }));
          if (enabled) {
            clearReconnect();
            reconnectTimerRef.current = window.setTimeout(() => {
              if (disposedRef.current || !enabled) return;
              const next = new WebSocket(urlRef.current);
              wsRef.current = next;
              attach(next);
            }, RECONNECT_MS);
          }
        }
      };
    };

    if (!enabled) {
      setState((s) => ({ ...s, connected: false }));
      return () => {
        disposedRef.current = true;
      };
    }

    clearReconnect();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const ws = new WebSocket(url);
    wsRef.current = ws;
    attach(ws);

    return () => {
      disposedRef.current = true;
      clearReconnect();
      if (flushTimerRef.current != null) {
        window.clearTimeout(flushTimerRef.current);
        flushTimerRef.current = null;
      }
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;
      ws.close();
      if (wsRef.current === ws) wsRef.current = null;
    };
  }, [hostOrUrl, enabled, queueImu]);

  const sendImpact = useCallback((tdoaNs: number[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'impact',
          ts: Date.now() * 1000,
          tdoa_ns: tdoaNs,
          amplitude: [1, 1, 1, 1],
        }),
      );
    }
  }, []);

  return { ...state, sendImpact };
}

//#endregion
