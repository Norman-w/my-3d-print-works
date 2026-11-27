import { useEffect, useState } from 'react';
import StlProcessPreview from './StlProcessPreview';
import { loadProcessManifest, ProcessPreviewManifest } from '../lib/processPreview';

const LIGHTBOARD_MANIFEST_URL = '/stl/lightboard/preview/lightboard_manifest.json';

function downloadName(path: string, fallback: string): string {
  const name = path.split('/').filter(Boolean).pop()?.split('?')[0];
  return name || fallback;
}

const BUTTON: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  minWidth: 74,
  padding: '7px 11px',
  borderRadius: 6,
  border: '1px solid #35527a',
  background: '#16345f',
  color: '#dbeafe',
  textDecoration: 'none',
  fontSize: 12,
  fontWeight: 600,
};

export default function LightBoardPrint() {
  const [manifest, setManifest] = useState<ProcessPreviewManifest>();
  const [error, setError] = useState('');

  useEffect(() => {
    loadProcessManifest(LIGHTBOARD_MANIFEST_URL)
      .then(setManifest)
      .catch((reason: unknown) => setError(String(reason)));
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, background: '#090d16', color: '#e8eefc' }}>
      <div style={{ display: 'flex', flex: 1, minHeight: 360, minWidth: 0, overflow: 'hidden' }}>
        <StlProcessPreview manifestUrl={LIGHTBOARD_MANIFEST_URL} minimal />
      </div>

      <section
        aria-label="M7-LB1 导出"
        style={{
          flex: '0 0 auto',
          padding: '12px 18px 14px',
          borderTop: '1px solid #293244',
          background: '#0f1420',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 9, flexWrap: 'wrap' }}>
          <strong style={{ color: '#dbeafe' }}>{manifest?.modelVersion ?? 'M7-LB1'} 光板版</strong>
          <span style={{ color: '#94a3b8', fontSize: 12 }}>SCAD → STL → 3MF · 拍面/肩颈实心 · 拍柄下段内腔 · TPU95A 把套</span>
          {error && <span style={{ color: '#fca5a5', fontSize: 12 }}>导出清单未加载：{error}</span>}
        </div>

        <div style={{ display: 'grid', gap: 6 }}>
          {(manifest?.printPlates ?? []).map((plate) => (
            <div
              key={plate.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
                padding: '7px 9px',
                border: '1px solid #253149',
                borderRadius: 6,
                background: '#111827',
              }}
            >
              <span style={{ color: '#cbd5e1', fontSize: 13 }}>{plate.label}</span>
              <div style={{ display: 'flex', gap: 6 }}>
                <a href={plate.path} download={downloadName(plate.path, `${plate.id}.stl`)} style={BUTTON}>STL</a>
                {plate.threeMfPath && (
                  <a href={plate.threeMfPath} download={downloadName(plate.threeMfPath, `${plate.id}.3mf`)} style={{ ...BUTTON, background: '#1e5b43', borderColor: '#347b5c' }}>3MF</a>
                )}
              </div>
            </div>
          ))}
          {!manifest && !error && <span style={{ color: '#93c5fd', fontSize: 12 }}>正在读取导出清单…</span>}
          {manifest && manifest.printPlates?.length === 0 && <span style={{ color: '#fcd34d', fontSize: 12 }}>暂无可下载拼板。</span>}
        </div>
      </section>
    </div>
  );
}
