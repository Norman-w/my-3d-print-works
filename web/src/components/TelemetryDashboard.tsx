interface Props {
  imuData: { ax: number; ay: number; az: number; gx: number; gy: number; gz: number }[];
  impactData: { x_mm?: number; y_mm?: number; confidence?: number; ts?: number }[];
}

export default function TelemetryDashboard({ imuData, impactData }: Props) {
  const last = imuData.length > 0 ? imuData[imuData.length - 1] : null;

  // Compute approximate speed magnitude from accelerometer
  const accelMag = last
    ? Math.sqrt(last.ax * last.ax + last.ay * last.ay + last.az * last.az)
    : 0;

  const gyroMag = last
    ? Math.sqrt(last.gx * last.gx + last.gy * last.gy + last.gz * last.gz)
    : 0;

  const lastImpact = impactData.length > 0 ? impactData[impactData.length - 1] : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <h3 style={{ fontSize: 16, color: '#888', fontWeight: 600 }}>Telemetry</h3>

      {/* Accelerometer */}
      <MetricCard label="Accel Magnitude" value={accelMag.toFixed(1)} unit="mg" color="#4fc3f7" />
      {last && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
          <MiniMetric label="AX" value={last.ax} color="#e57373" />
          <MiniMetric label="AY" value={last.ay} color="#81c784" />
          <MiniMetric label="AZ" value={last.az} color="#64b5f6" />
        </div>
      )}

      {/* Gyroscope */}
      <MetricCard label="Gyro Magnitude" value={gyroMag.toFixed(0)} unit="dps" color="#ffb74d" />
      {last && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
          <MiniMetric label="GX" value={last.gx} color="#ffab91" />
          <MiniMetric label="GY" value={last.gy} color="#a5d6a7" />
          <MiniMetric label="GZ" value={last.gz} color="#90caf9" />
        </div>
      )}

      {/* Impact */}
      <div style={{ borderTop: '1px solid #2a2a3a', paddingTop: 16 }}>
        <h3 style={{ fontSize: 16, color: '#888', fontWeight: 600, marginBottom: 8 }}>Last Impact</h3>
        {lastImpact?.x_mm !== undefined ? (
          <>
            <MetricCard label="Position" value={`(${lastImpact.x_mm?.toFixed(1)}, ${lastImpact.y_mm?.toFixed(1)})`} unit="mm" color="#4caf50" />
            <MetricCard label="Confidence" value={(lastImpact.confidence || 0).toFixed(2)} unit="" color="#ff9800" />
          </>
        ) : (
          <div style={{ color: '#666', fontSize: 14 }}>No impacts detected yet</div>
        )}
      </div>

      {/* Recent impacts list */}
      {impactData.length > 0 && (
        <div style={{ borderTop: '1px solid #2a2a3a', paddingTop: 16 }}>
          <h3 style={{ fontSize: 16, color: '#888', fontWeight: 600, marginBottom: 8 }}>
            Recent ({impactData.length})
          </h3>
          <div style={{ maxHeight: 150, overflowY: 'auto', fontSize: 12 }}>
            {[...impactData].reverse().slice(0, 10).map((imp, i) => (
              <div key={i} style={{
                padding: '4px 8px',
                background: i % 2 === 0 ? '#14141e' : 'transparent',
                borderRadius: 4,
                display: 'flex',
                justifyContent: 'space-between',
                color: '#aaa',
              }}>
                <span>({imp.x_mm?.toFixed(1)}, {imp.y_mm?.toFixed(1)})</span>
                <span style={{ color: imp.confidence && imp.confidence > 0.8 ? '#4caf50' : '#888' }}>
                  {(imp.confidence || 0).toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, unit, color }: { label: string; value: string; unit: string; color: string }) {
  return (
    <div style={{
      background: '#14141e',
      borderRadius: 8,
      padding: '12px 16px',
      borderLeft: `3px solid ${color}`,
    }}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 700, color }}>
        {value}
        <span style={{ fontSize: 13, fontWeight: 400, marginLeft: 4, opacity: 0.6 }}>{unit}</span>
      </div>
    </div>
  );
}

function MiniMetric({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{
      background: '#14141e',
      borderRadius: 6,
      padding: '6px 10px',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 10, color: '#888' }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 600, color }}>{value}</div>
    </div>
  );
}
