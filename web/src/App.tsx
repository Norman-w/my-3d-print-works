import { useState, useEffect } from 'react';
import TelemetryDashboard from './components/TelemetryDashboard';
import Paddle3D from './components/Paddle3D';
import SessionBrowser from './components/SessionBrowser';
import CalibrationWizard from './components/CalibrationWizard';
import { useWebSocket } from './hooks/useWebSocket';

import PaddleShapePreview from './components/PaddleShapePreview';

type Tab = 'live' | 'shape' | 'sessions' | 'calibrate';

const TABS: Tab[] = ['live', 'shape', 'sessions', 'calibrate'];

function tabFromUrl(): Tab {
  const q = new URLSearchParams(window.location.search).get('tab');
  if (q && TABS.includes(q as Tab)) return q as Tab;
  const h = window.location.hash.replace(/^#/, '');
  if (h && TABS.includes(h as Tab)) return h as Tab;
  return 'live';
}

export default function App() {
  const [tab, setTab] = useState<Tab>(tabFromUrl);
  const { connected, imuData, impactData, sessionId } = useWebSocket('ws://localhost:8000/ws/paddle?device_id=test');

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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <header style={{
        padding: '8px 20px',
        background: '#12121a',
        borderBottom: '1px solid #2a2a3a',
        display: 'flex',
        alignItems: 'center',
        gap: 20,
      }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, color: '#4fc3f7' }}>SmartPaddle</h1>
        <div style={{ display: 'flex', gap: 4 }}>
          {TABS.map(t => (
            <button key={t} onClick={() => selectTab(t)} style={{
              padding: '6px 16px',
              border: 'none',
              borderRadius: 6,
              background: tab === t ? '#1e3a5f' : 'transparent',
              color: tab === t ? '#4fc3f7' : '#888',
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: tab === t ? 600 : 400,
            }}>
              {t === 'live' ? 'Live' : t === 'shape' ? 'Shape' : t === 'sessions' ? 'Sessions' : 'Calibrate'}
            </button>
          ))}
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 12, alignItems: 'center', fontSize: 13 }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: connected ? '#4caf50' : '#f44336',
            display: 'inline-block',
          }} />
          <span style={{ color: '#888' }}>
            {connected ? `Connected · ${sessionId?.slice(0, 8)}...` : 'Disconnected'}
          </span>
        </div>
      </header>

      {/* Main content */}
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
        {tab === 'sessions' && <SessionBrowser />}
        {tab === 'calibrate' && <CalibrationWizard />}
      </main>
    </div>
  );
}
