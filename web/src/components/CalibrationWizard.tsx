import { useState } from 'react';

export default function CalibrationWizard() {
  const [gridSize] = useState(7);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentPoint, setCurrentPoint] = useState<{ gx: number; gy: number } | null>(null);
  const [pointsCollected, setPointsCollected] = useState(0);
  const [status, setStatus] = useState<'idle' | 'collecting' | 'complete'>('idle');
  const [rmse, setRmse] = useState<number | null>(null);
  const [lastTdoa, setLastTdoa] = useState<string>(''); // User manually enters TDOA from serial monitor

  const totalPoints = gridSize * gridSize;

  const startCalibration = async () => {
    setStatus('collecting');
    const res = await fetch('/api/calibration/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ grid_size: gridSize }),
    });
    const data = await res.json();
    setSessionId(data.id);
    // Start at first grid point
    navigateToPoint(0, 0);
  };

  const navigateToPoint = (gx: number, gy: number) => {
    const half = (gridSize - 1) / 2;
    setCurrentPoint({ gx: gx - half, gy: half - gy }); // Center-origin coords
  };

  const submitTap = async () => {
    if (!sessionId || !currentPoint) return;

    // Parse TDOA from user input: "d21,d31,d41" in ns
    const tdoaValues = lastTdoa.split(',').map(Number).filter(n => !isNaN(n));
    if (tdoaValues.length < 3) return;

    await fetch(`/api/calibration/${sessionId}/points`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        grid_x: currentPoint.gx,
        grid_y: currentPoint.gy,
        tdoa_ns: tdoaValues,
        tap_number: 1,
      }),
    });

    const newCount = pointsCollected + 1;
    setPointsCollected(newCount);

    // Move to next grid point
    const idx = newCount;
    if (idx < totalPoints) {
      const row = Math.floor(idx / gridSize);
      const col = idx % gridSize;
      navigateToPoint(col, row);
    }

    setLastTdoa('');
  };

  const completeCalibration = async () => {
    if (!sessionId) return;
    const res = await fetch(`/api/calibration/${sessionId}/complete`, { method: 'POST' });
    const data = await res.json();
    if (data.rmse !== undefined) {
      setRmse(data.rmse);
      setStatus('complete');
    }
  };

  return (
    <div style={{ flex: 1, padding: 24, overflow: 'auto' }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Calibration Wizard</h2>

      {status === 'idle' && (
        <div style={{ textAlign: 'center', marginTop: 80 }}>
          <p style={{ color: '#888', marginBottom: 24 }}>
            Print the calibration grid, tape it to your paddle blade, then start.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button onClick={startCalibration} style={{
              padding: '12px 32px',
              background: '#1e3a5f',
              color: '#4fc3f7',
              border: 'none',
              borderRadius: 8,
              fontSize: 16,
              cursor: 'pointer',
            }}>
              Start Calibration
            </button>
            <button onClick={() => window.open('/api/grids/7x7.pdf', '_blank')} style={{
              padding: '12px 32px',
              background: '#14141e',
              color: '#888',
              border: '1px solid #2a2a3a',
              borderRadius: 8,
              fontSize: 16,
              cursor: 'pointer',
            }}>
              Download Grid PDF
            </button>
          </div>
        </div>
      )}

      {status === 'collecting' && currentPoint && (
        <div>
          {/* Progress */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#888', marginBottom: 8 }}>
              <span>Progress</span>
              <span>{pointsCollected} / {totalPoints}</span>
            </div>
            <div style={{ height: 6, background: '#1a1a2e', borderRadius: 3 }}>
              <div style={{
                width: `${(pointsCollected / totalPoints) * 100}%`,
                height: '100%',
                background: '#4fc3f7',
                borderRadius: 3,
                transition: 'width 0.3s',
              }} />
            </div>
          </div>

          {/* Current tap target */}
          <div style={{
            background: '#14141e',
            borderRadius: 12,
            padding: 24,
            textAlign: 'center',
            marginBottom: 24,
          }}>
            <div style={{ fontSize: 13, color: '#888', marginBottom: 8 }}>Tap this grid position:</div>
            <div style={{ fontSize: 36, fontWeight: 700, color: '#ffb74d' }}>
              ({currentPoint.gx}, {currentPoint.gy})
            </div>
            <div style={{ fontSize: 13, color: '#666', marginTop: 8 }}>mm from center</div>
          </div>

          {/* TDOA input (from serial monitor) */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 13, color: '#888', display: 'block', marginBottom: 4 }}>
              TDOA values from serial monitor (d21,d31,d41 in ns):
            </label>
            <input
              type="text"
              value={lastTdoa}
              onChange={e => setLastTdoa(e.target.value)}
              placeholder="e.g. -1234,567,890"
              style={{
                width: '100%',
                padding: '12px',
                background: '#1a1a2e',
                border: '1px solid #2a2a3a',
                borderRadius: 8,
                color: '#e0e0e0',
                fontSize: 16,
                fontFamily: 'monospace',
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: 12 }}>
            <button onClick={submitTap} disabled={lastTdoa.length < 5} style={{
              flex: 1,
              padding: '12px',
              background: lastTdoa.length >= 5 ? '#1e3a5f' : '#14141e',
              color: lastTdoa.length >= 5 ? '#4fc3f7' : '#444',
              border: 'none',
              borderRadius: 8,
              fontSize: 16,
              cursor: lastTdoa.length >= 5 ? 'pointer' : 'not-allowed',
            }}>
              Confirm Tap
            </button>

            {pointsCollected >= 10 && (
              <button onClick={completeCalibration} style={{
                padding: '12px 24px',
                background: '#2e7d32',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                fontSize: 16,
                cursor: 'pointer',
              }}>
                Finish & Fit Model
              </button>
            )}
          </div>
        </div>
      )}

      {status === 'complete' && rmse !== null && (
        <div style={{ textAlign: 'center', marginTop: 80 }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
          <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Calibration Complete</div>
          <div style={{ fontSize: 16, color: '#888' }}>
            RMSE: <span style={{ color: rmse < 5 ? '#4caf50' : '#ff9800', fontWeight: 600 }}>{rmse.toFixed(2)} mm</span>
          </div>
          {rmse >= 5 && (
            <div style={{ color: '#ff9800', marginTop: 8, fontSize: 14 }}>
              Accuracy above 5mm — consider recalibrating problem points.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
