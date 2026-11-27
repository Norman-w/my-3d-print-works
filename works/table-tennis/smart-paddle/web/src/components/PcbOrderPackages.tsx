import { useCallback, useEffect, useState } from 'react';
import { useToast } from './toast/ToastProvider';

type Target = 'main' | 'tail' | 'separate' | 'panel';

type OrderFile = {
  name: string;
  path: string;
  download_url: string;
  size: number;
  modified_at: string;
};

type ListResponse = { files: OrderFile[] };

const targetCards: Array<{ target: Target; title: string; note: string }> = [
  { target: 'main', title: '只导出主板', note: '2 层 / 0.8 mm / ENIG；严格制造门禁。' },
  { target: 'tail', title: '只导出尾板', note: '2 层 / 1.0 mm；实验样板，尚未实物验证。' },
  { target: 'separate', title: '主板 + 尾板（推荐）', note: '生成两个独立上传 ZIP，不混成一个订单。' },
  { target: 'panel', title: '正式拼板', note: '当前无拼板工程，会明确报告阻塞。' },
];

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export default function PcbOrderPackages() {
  const [files, setFiles] = useState<OrderFile[]>([]);
  const [busy, setBusy] = useState<Target | null>(null);
  const [details, setDetails] = useState('');
  const { toast } = useToast();

  const refresh = useCallback(async () => {
    const response = await fetch('/api/pcb-orders');
    if (!response.ok) throw new Error(await response.text());
    const data = (await response.json()) as ListResponse;
    setFiles(data.files ?? []);
  }, []);

  useEffect(() => {
    refresh().catch(error => toast(`读取下单资料失败：${String(error)}`, 'error'));
  }, [refresh, toast]);

  const generate = async (target: Target) => {
    setBusy(target);
    setDetails('');
    try {
      const response = await fetch('/api/pcb-orders/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target }),
      });
      const data = await response.json();
      setDetails(data.output || data.error || '');
      if (!response.ok || !data.ok) throw new Error(data.error || '导出被制造门禁阻止');
      setFiles(data.files ?? []);
      toast('下单资料已生成；请下载 upload ZIP，review bundle 用于核对。', 'success');
    } catch (error) {
      toast(`导出失败：${String(error)}`, 'error');
      await refresh().catch(() => undefined);
    } finally {
      setBusy(null);
    }
  };

  const copyPath = async (path: string) => {
    await navigator.clipboard.writeText(path);
    toast('已复制本地路径', 'success');
  };

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: 24, background: '#0b0b12', color: '#e8eefc' }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <h2 style={{ marginTop: 0, color: '#4fc3f7' }}>嘉立创 PCB 下单资料</h2>
        <p style={{ color: '#9aa4b2', lineHeight: 1.6 }}>
          点击后由当前 KiCad 文件重新运行 DRC 并导出。名称含 <code>jlcpcb</code> 的 ZIP 上传嘉立创；
          <code>review_bundle</code> 用于查看工艺说明、DRC、制造图和主板↔尾板线序。
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 12 }}>
          {targetCards.map(card => (
            <div key={card.target} style={{ border: '1px solid #293245', borderRadius: 10, padding: 16, background: '#121722' }}>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>{card.title}</div>
              <div style={{ color: '#9aa4b2', fontSize: 13, minHeight: 40, lineHeight: 1.5 }}>{card.note}</div>
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => generate(card.target)}
                style={{ marginTop: 14, width: '100%', padding: '9px 12px', border: 0, borderRadius: 7, cursor: busy ? 'wait' : 'pointer', background: card.target === 'separate' ? '#1565c0' : '#26364d', color: '#fff' }}
              >
                {busy === card.target ? '正在运行 DRC / 导出…' : '生成资料'}
              </button>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', marginTop: 28, gap: 12 }}>
          <h3 style={{ margin: 0 }}>已生成文件</h3>
          <button type="button" onClick={() => refresh()} style={{ padding: '6px 10px', borderRadius: 6, border: '1px solid #34425a', background: 'transparent', color: '#a9c7ef', cursor: 'pointer' }}>刷新</button>
        </div>

        <div style={{ marginTop: 12, border: '1px solid #293245', borderRadius: 10, overflow: 'hidden' }}>
          {files.length === 0 ? (
            <div style={{ padding: 20, color: '#7f8a9b' }}>还没有资料包。建议先点“主板 + 尾板（推荐）”。</div>
          ) : files.map((file, index) => {
            const upload = file.name.includes('jlcpcb') && !file.name.includes('review');
            return (
              <div key={file.path} style={{ padding: '12px 14px', display: 'grid', gridTemplateColumns: 'minmax(260px, 1fr) auto auto', alignItems: 'center', gap: 10, borderTop: index ? '1px solid #20293a' : 'none', background: upload ? '#102318' : '#10141d' }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ color: upload ? '#8ee6a2' : '#d7e3f4', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis' }}>{upload ? '上传包 · ' : '审阅/索引 · '}{file.name}</div>
                  <div style={{ color: '#718096', fontSize: 12, marginTop: 4 }}>{formatBytes(file.size)} · {new Date(file.modified_at).toLocaleString()}</div>
                </div>
                <button type="button" onClick={() => copyPath(file.path)} style={{ padding: '7px 10px', border: '1px solid #34425a', borderRadius: 6, background: 'transparent', color: '#a9c7ef', cursor: 'pointer' }}>复制路径</button>
                <a href={file.download_url} download style={{ padding: '8px 12px', borderRadius: 6, background: upload ? '#20753a' : '#26364d', color: '#fff', textDecoration: 'none', textAlign: 'center' }}>下载</a>
              </div>
            );
          })}
        </div>

        {details && <details style={{ marginTop: 18 }}><summary style={{ cursor: 'pointer', color: '#9dbce5' }}>查看导出日志</summary><pre style={{ whiteSpace: 'pre-wrap', background: '#090c12', padding: 12, borderRadius: 8, maxHeight: 320, overflow: 'auto', fontSize: 12 }}>{details}</pre></details>}
      </div>
    </div>
  );
}
