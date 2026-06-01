import { useEffect, useState } from 'react';
import { api } from '../lib/api';

interface Session {
  id: string;
  created_at: string;
  swings: number;
  duration_s: number;
}

export default function SessionBrowser() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/sessions')
      .then(r => r.json())
      .then(data => {
        setSessions(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div style={{ flex: 1, padding: 24, overflow: 'auto' }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Sessions</h2>

      {loading && <div style={{ color: '#888' }}>Loading...</div>}

      {!loading && sessions.length === 0 && (
        <div style={{ color: '#666', textAlign: 'center', marginTop: 80 }}>
          No sessions recorded yet. Connect your paddle to start.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {sessions.map(s => (
          <div key={s.id} style={{
            background: '#14141e',
            borderRadius: 8,
            padding: '12px 20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'monospace' }}>{s.id.slice(0, 12)}...</div>
              <div style={{ fontSize: 12, color: '#888' }}>{new Date(s.created_at).toLocaleString()}</div>
            </div>
            <div style={{ display: 'flex', gap: 24, textAlign: 'center' }}>
              <div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#4fc3f7' }}>{s.swings}</div>
                <div style={{ fontSize: 11, color: '#888' }}>swings</div>
              </div>
              <div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#ffb74d' }}>{s.duration_s}s</div>
                <div style={{ fontSize: 11, color: '#888' }}>duration</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
