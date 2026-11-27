//#region 导入/依赖
import { useState, useEffect, useCallback } from 'react';
import type { DeviceImuFrame } from '../lib/deviceImuProtocol';
import {
  subscribeDeviceWs,
  type PowerTelemetry,
} from '../lib/deviceWsSingleton';
//#endregion

//#region 模型/类型
export type IMUFrame = DeviceImuFrame;

export interface ImpactEvent {
  ts: number;
  tdoa_ns: number[];
  first_ch?: number;
  hits?: { ch: number; dt_ns: number; edges: number }[];
  x_mm?: number;
  y_mm?: number;
  confidence?: number;
}

interface WebSocketState {
  connected: boolean;
  imuData: IMUFrame[];
  impactData: ImpactEvent[];
  power: PowerTelemetry | null;
  sessionId: string | null;
  lastError: string | null;
}
//#endregion

//#region 公开 API

export function useWebSocket(hostOrUrl: string, enabled = true) {
  const [state, setState] = useState<WebSocketState>({
    connected: false,
    imuData: [],
    impactData: [],
    power: null,
    sessionId: null,
    lastError: null,
  });

  useEffect(() => {
    if (!enabled) {
      setState((s) => ({ ...s, connected: false }));
      return;
    }

    const unsubscribe = subscribeDeviceWs(hostOrUrl, {
      onStatus: (s) => {
        setState((prev) => ({
          ...prev,
          connected: s.connected,
          lastError: s.lastError,
          sessionId: s.sessionId,
        }));
      },
      onImu: (frame) => {
        setState((prev) => ({
          ...prev,
          imuData: [...prev.imuData.slice(-500), frame],
        }));
      },
      onImpact: (evt) => {
        setState((prev) => ({
          ...prev,
          impactData: [...prev.impactData.slice(-50), evt],
        }));
      },
      onPower: (power) => {
        setState((prev) => ({ ...prev, power }));
      },
    });

    return unsubscribe;
  }, [hostOrUrl, enabled]);

  const sendImpact = useCallback((_tdoaNs: number[]) => {
    // 设备端当前为单向推送，保留 API 兼容
  }, []);

  return { ...state, sendImpact };
}

//#endregion
