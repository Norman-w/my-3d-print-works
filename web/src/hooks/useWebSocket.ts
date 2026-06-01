import { useState, useEffect, useRef, useCallback } from 'react';

interface IMUFrame {
  ts: number;
  ax: number; ay: number; az: number;
  gx: number; gy: number; gz: number;
}

interface ImpactEvent {
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
}

export function useWebSocket(url: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [state, setState] = useState<WebSocketState>({
    connected: false,
    imuData: [],
    impactData: [],
    sessionId: null,
  });

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setState(s => ({ ...s, connected: true }));
    };

    ws.onmessage = (event) => {
      if (event.data instanceof Blob) {
        // Binary: IMU batch
        const reader = new FileReader();
        reader.onload = () => {
          try {
            const data = JSON.parse(reader.result as string);
            const frames = data.frames || [];
            setState(s => ({
              ...s,
              imuData: [...s.imuData.slice(-500), ...frames], // Keep last 500 samples
            }));
          } catch { /* binary parse error - ignore */ }
        };
        reader.readAsText(event.data);
        return;
      }

      // Text: JSON message
      try {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
          case 'hello':
            setState(s => ({ ...s, sessionId: msg.session_id }));
            break;
          case 'impact_ack':
            setState(s => ({
              ...s,
              impactData: [...s.impactData.slice(-50), {
                ts: Date.now(),
                tdoa_ns: [],
                x_mm: msg.x_mm,
                y_mm: msg.y_mm,
                confidence: msg.confidence,
              }],
            }));
            break;
          case 'impact':
            setState(s => ({
              ...s,
              impactData: [...s.impactData.slice(-50), msg as ImpactEvent],
            }));
            break;
        }
      } catch { /* parse error */ }
    };

    ws.onclose = () => {
      setState(s => ({ ...s, connected: false }));
      // Reconnect after 2s
      setTimeout(() => {
        if (wsRef.current === ws) {
          wsRef.current = new WebSocket(url);
        }
      }, 2000);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [url]);

  const sendImpact = useCallback((tdoaNs: number[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'impact',
        ts: Date.now() * 1000,
        tdoa_ns: tdoaNs,
        amplitude: [1, 1, 1, 1],
      }));
    }
  }, []);

  return { ...state, sendImpact };
}
