//#region 导入/依赖
import { useState, useEffect } from 'react';
import TelemetryDashboard from './components/TelemetryDashboard';
import Paddle3D from './components/Paddle3D';
import SessionBrowser from './components/SessionBrowser';
import CalibrationWizard from './components/CalibrationWizard';
import { useWebSocket } from './hooks/useWebSocket';
import PaddleShapePreview from './components/PaddleShapePreview';
import StlProcessPreview from './components/StlProcessPreview';
import PcbOrderPackages from './components/PcbOrderPackages';
import {
  DEFAULT_DEVICE_HOST,
  loadSavedDeviceHost,
  saveDeviceHost,
} from './lib/deviceImuProtocol';
//#endregion

//#region 模型/类型
type Tab = 'live' | 'shape' | 'process' | 'pcb' | 'sessions' | 'calibrate';
//#endregion

//#region 常量/配置
const TABS: Tab[] = ['live', 'shape', 'process', 'pcb', 'sessions', 'calibrate'];
//#endregion

//#region 私有成员
function tabFromUrl(): Tab {
  const q = new URLSearchParams(window.location.search).get('tab');
  if (q && TABS.includes(q as Tab)) return q as Tab;
  const h = window.location.hash.replace(/^#/, '');
  if (h && TABS.includes(h as Tab)) return h as Tab;
  return 'live';
}
//#endregion

//#region 公开 API / 视图层
export default function App() {
  const [tab, setTab] = useState<Tab>(tabFromUrl);
  const [hostDraft, setHostDraft] = useState(() => loadSavedDeviceHost());
  const [activeHost, setActiveHost] = useState(() => loadSavedDeviceHost());
  const { connected, imuData, impactData, lastError } = useWebSocket(
    activeHost,
    true,
  );

  useEffect(() => {
    const onPop = () => setTab(tabFromUrl());
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const selectTab = (t: Tab) => {
    setTab(t);
    const url = new URL(window.location.href);
    url.searchParams.set('tab', t);
    window.history.replaceState(null, '', url);
  };

  const applyHost = (value?: string) => {
    const next = (value ?? hostDraft).trim() || DEFAULT_DEVICE_HOST;
    setHostDraft(next);
    saveDeviceHost(next);
    setActiveHost(next);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <header
        style={{
          padding: '8px 20px',
          background: '#12121a',
          borderBottom: '1px solid #2a2a3a',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          flexWrap: 'wrap',
        }}
      >
        <h1 style={{ fontSize: 20, fontWeight: 700, color: '#4fc3f7', margin: 0 }}>
          SmartPaddle
        </h1>
        <div style={{ display: 'flex', gap: 4 }}>
          {TABS.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => selectTab(t)}
              style={{
                padding: '6px 16px',
                border: 'none',
                borderRadius: 6,
                background: tab === t ? '#1e3a5f' : 'transparent',
                color: tab === t ? '#4fc3f7' : '#888',
                cursor: 'pointer',
                fontSize: 14,
                fontWeight: tab === t ? 600 : 400,
              }}
            >
              {t === 'live'
                ? 'Live'
                : t === 'shape'
                  ? 'Shape'
                  : t === 'process'
                    ? '工艺预览'
                  : t === 'pcb'
                    ? 'PCB 下单'
                  : t === 'sessions'
                    ? 'Sessions'
                    : 'Calibrate'}
            </button>
          ))}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            applyHost();
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginLeft: 'auto',
            flexWrap: 'wrap',
          }}
        >
          <label style={{ fontSize: 12, color: '#888' }} htmlFor="device-host">
            设备
          </label>
          <input
            id="device-host"
            value={hostDraft}
            onChange={(e) => setHostDraft(e.target.value)}
            placeholder={DEFAULT_DEVICE_HOST}
            list="device-host-suggestions"
            style={{
              width: 180,
              padding: '6px 10px',
              borderRadius: 6,
              border: '1px solid #2a2a3a',
              background: '#0c0c14',
              color: '#e8eefc',
              fontSize: 13,
            }}
          />
          <datalist id="device-host-suggestions">
            <option value={DEFAULT_DEVICE_HOST} />
            <option value="192.168.7.52" />
            <option value="192.168.7.80" />
            <option value="SP-FE9C.local" />
            <option value="192.168.4.1" />
          </datalist>
          <button
            type="submit"
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              border: 'none',
              background: '#1e3a5f',
              color: '#4fc3f7',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            连接
          </button>
          <div
            style={{
              display: 'flex',
              gap: 8,
              alignItems: 'center',
              fontSize: 13,
              minWidth: 140,
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: connected ? '#4caf50' : '#f44336',
                display: 'inline-block',
              }}
            />
            <span style={{ color: '#888' }}>
              {connected
                ? `已连接 · ${activeHost} · IMU ${imuData.length}`
                : lastError
                  ? '重连中…'
                  : '未连接'}
            </span>
          </div>
        </form>
      </header>

      {lastError && !connected && (
        <div
          style={{
            padding: '6px 20px',
            background: '#2a1515',
            color: '#ffab91',
            fontSize: 12,
            borderBottom: '1px solid #3a2020',
          }}
        >
          {lastError}（将自动重试；也可改 IP 后点连接）
        </div>
      )}

      <main style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {tab === 'live' && (
          <div style={{ display: 'flex', flex: 1, gap: 0 }}>
            <div style={{ flex: 1 }}>
              <Paddle3D imuData={imuData} impactData={impactData} />
            </div>
            <div style={{ width: 340, borderLeft: '1px solid #2a2a3a', padding: 16 }}>
              <TelemetryDashboard imuData={imuData} impactData={impactData} />
            </div>
          </div>
        )}
        {tab === 'shape' && <PaddleShapePreview />}
        {tab === 'process' && <StlProcessPreview />}
        {tab === 'pcb' && <PcbOrderPackages />}
        {tab === 'sessions' && <SessionBrowser />}
        {tab === 'calibrate' && <CalibrationWizard />}
      </main>
    </div>
  );
}
//#endregion
