import { useCallback, useEffect, useState, type CSSProperties } from 'react';
import { ALL_DRAW_TARGETS, DrawTarget } from '../lib/bezierProfile';
import { getCachedBundle, isProfileCacheLoaded } from '../lib/profileCache';
import {
  applyBundleToEditor,
  createSnapshot,
  flushPendingSaves,
  formatStoreErrorMessage,
  formatStoreSuccessMessage,
  listSnapshots,
  reimportProjectFile,
  reloadProfilesFromServer,
  restoreSnapshotToProject,
  SnapshotMeta,
} from '../lib/bezierStorage';
import ConfirmDialog from './toast/ConfirmDialog';
import { useToast } from './toast/ToastProvider';

const TARGET_LABELS: Record<DrawTarget, string> = {
  'blade-front': '底板正视',
  'handle-front': '手柄正视',
  side: '柄侧视',
  'handle-bottom': '柄底视',
};

type ConfirmState =
  | { kind: 'reload' }
  | { kind: 'flush' }
  | { kind: 'restore'; snap: SnapshotMeta; alsoLoad: boolean }
  | null;

export default function BezierProfileStorePanel() {
  const { toast } = useToast();
  const [snapshots, setSnapshots] = useState<SnapshotMeta[]>([]);
  const [snapshotLabel, setSnapshotLabel] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<ConfirmState>(null);
  const [, tick] = useState(0);

  const refreshUi = () => tick(n => n + 1);

  const loadSnapshotList = useCallback(async () => {
    try {
      setSnapshots(await listSnapshots());
    } catch {
      setSnapshots([]);
    }
  }, []);

  useEffect(() => {
    void loadSnapshotList();
    const onLoaded = () => refreshUi();
    window.addEventListener('smartpaddle-profiles-loaded', onLoaded);
    return () => window.removeEventListener('smartpaddle-profiles-loaded', onLoaded);
  }, [loadSnapshotList]);

  const bundle = getCachedBundle();
  const keys = ALL_DRAW_TARGETS.filter(t => bundle[t] != null);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      toast(e instanceof Error ? e.message : String(e), 'error');
    } finally {
      setBusy(false);
      refreshUi();
      void loadSnapshotList();
    }
  };

  const handleReload = () => setConfirm({ kind: 'reload' });

  const handleFlush = () => setConfirm({ kind: 'flush' });

  const handleSnapshot = () => {
    void run(async () => {
      const meta = await createSnapshot(snapshotLabel);
      setSnapshotLabel('');
      toast(`快照：${meta.label}`, 'success');
    });
  };

  return (
    <section style={sectionStyle}>
      <h3 style={titleStyle}>工程存储</h3>
      <p style={hintStyle}>
        刷新页面会从<strong>服务端</strong>（SQLite）自动加载；编辑只改内存，点「保存到服务端」写入数据库并同步{' '}
        <code style={codeStyle}>userBezierProfiles.json</code>。
        {isProfileCacheLoaded() ? '' : ' （加载中…）'}
      </p>

      <p style={{ fontSize: 12, color: '#888', margin: '0 0 10px' }}>
        当前内存：{keys.length > 0 ? keys.map(k => TARGET_LABELS[k]).join('、') : '尚无数据（将用默认曲线）'}
      </p>

      <div style={rowStyle}>
        <button type="button" disabled={busy} onClick={handleReload} style={primaryBtn(false)}>
          从服务端刷新
        </button>
        <button type="button" disabled={busy} onClick={handleFlush} style={primaryBtn(busy)}>
          保存到服务端
        </button>
      </div>

      <div style={{ ...rowStyle, marginTop: 10 }}>
        <button
          type="button"
          disabled={busy}
          style={btnStyle}
          onClick={() =>
            void run(async () => {
              const result = await reimportProjectFile();
              const b = await reloadProfilesFromServer();
              applyBundleToEditor(b);
              toast(`已从 JSON 导入并刷新：${result.keys.join('、')}`, 'success');
            })
          }
        >
          从 JSON 文件导入
        </button>
      </div>
      <p style={{ fontSize: 11, color: '#666', margin: '8px 0 0', lineHeight: 1.45 }}>
        若加载/保存报 404，请先停掉旧进程再运行 <code style={codeStyle}>./dev.sh</code>（需同时有前端 5173 与 Go :8000）。
      </p>

      <hr style={hrStyle} />

      <h4 style={subTitleStyle}>快照（SQLite）</h4>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8, alignItems: 'center' }}>
        <input
          type="text"
          value={snapshotLabel}
          onChange={e => setSnapshotLabel(e.target.value)}
          placeholder="备注（可选）"
          disabled={busy}
          style={inputStyle}
        />
        <button type="button" disabled={busy} onClick={handleSnapshot} style={btnStyle}>
          创建快照
        </button>
      </div>

      {snapshots.length === 0 ? (
        <p style={{ fontSize: 11, color: '#666', margin: 0 }}>暂无快照</p>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, fontSize: 12 }}>
          {snapshots.map(snap => (
            <li key={snap.id} style={snapRowStyle}>
              <span style={{ color: '#ccc', flex: '1 1 180px' }}>
                <strong style={{ color: '#81d4fa' }}>{snap.label}</strong>
                <span style={{ color: '#666', marginLeft: 8 }}>{formatTime(snap.created_at)}</span>
              </span>
              <button
                type="button"
                disabled={busy}
                onClick={() => setConfirm({ kind: 'restore', snap, alsoLoad: false })}
                style={btnStyle}
              >
                恢复
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => setConfirm({ kind: 'restore', snap, alsoLoad: true })}
                style={primaryBtn(false)}
              >
                恢复并刷新
              </button>
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={confirm?.kind === 'reload'}
        title="从服务端刷新"
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          setConfirm(null);
          void run(async () => {
            const b = await reloadProfilesFromServer();
            applyBundleToEditor(b);
            toast('已从服务端重新加载曲线', 'success');
          });
        }}
      >
        将用数据库中的曲线覆盖当前编辑器中的内容。
      </ConfirmDialog>

      <ConfirmDialog
        open={confirm?.kind === 'flush'}
        title="保存到服务端"
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          setConfirm(null);
          void (async () => {
            setBusy(true);
            try {
              const result = await flushPendingSaves();
              toast(formatStoreSuccessMessage(result), 'success');
            } catch (e) {
              toast(formatStoreErrorMessage(e), 'error');
            } finally {
              setBusy(false);
              refreshUi();
            }
          })();
        }}
      >
        将当前内存中的曲线写入 SQLite，并同步到 userBezierProfiles.json。保存后会提示是否成功及文件路径。
      </ConfirmDialog>

      <ConfirmDialog
        open={confirm?.kind === 'restore'}
        title="恢复快照"
        danger
        confirmLabel={confirm?.kind === 'restore' && confirm.alsoLoad ? '恢复并刷新' : '恢复'}
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          if (confirm?.kind !== 'restore') return;
          const { snap, alsoLoad } = confirm;
          setConfirm(null);
          void run(async () => {
            const result = await restoreSnapshotToProject(snap.id);
            if (alsoLoad) {
              const b = await reloadProfilesFromServer();
              applyBundleToEditor(b);
            }
            toast(`已恢复快照「${result.label}」`, 'success');
          });
        }}
      >
        {confirm?.kind === 'restore'
          ? confirm.alsoLoad
            ? `恢复快照「${confirm.snap.label}」到数据库并刷新编辑器。`
            : `恢复快照「${confirm.snap.label}」到数据库（需点「从服务端刷新」才进编辑器）。`
          : null}
      </ConfirmDialog>
    </section>
  );
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false });
  } catch {
    return iso;
  }
}

const sectionStyle: CSSProperties = {
  marginBottom: 16,
  padding: 14,
  borderRadius: 8,
  border: '1px solid #2a3a4a',
  background: '#12121f',
};
const titleStyle: CSSProperties = { fontSize: 15, fontWeight: 600, color: '#81d4fa', margin: '0 0 8px' };
const subTitleStyle: CSSProperties = { fontSize: 13, fontWeight: 600, color: '#90caf9', margin: '0 0 8px' };
const hintStyle: CSSProperties = { fontSize: 12, color: '#888', margin: '0 0 10px', lineHeight: 1.5 };
const codeStyle: CSSProperties = { color: '#aaa' };
const rowStyle: CSSProperties = { display: 'flex', gap: 8, flexWrap: 'wrap' };
const hrStyle: CSSProperties = { border: 'none', borderTop: '1px solid #2a2a3a', margin: '14px 0' };
const inputStyle: CSSProperties = {
  padding: '6px 10px',
  fontSize: 12,
  border: '1px solid #444',
  borderRadius: 4,
  background: '#0c0c14',
  color: '#ddd',
  minWidth: 160,
};
const snapRowStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
  alignItems: 'center',
  flexWrap: 'wrap',
  padding: '6px 0',
  borderBottom: '1px solid #222',
};
const btnStyle: CSSProperties = {
  padding: '6px 12px',
  fontSize: 12,
  border: '1px solid #444',
  borderRadius: 4,
  background: '#1a1a28',
  color: '#ccc',
  cursor: 'pointer',
};
function primaryBtn(disabled: boolean): CSSProperties {
  return {
    ...btnStyle,
    border: '1px solid #1565c0',
    background: disabled ? '#1a1a28' : '#1e3a5f',
    color: disabled ? '#666' : '#4fc3f7',
    fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
  };
}
