import type { CSSProperties, ReactNode } from 'react';

type Props = {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export default function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel = '确认',
  cancelLabel = '取消',
  danger,
  onConfirm,
  onCancel,
}: Props) {
  if (!open) return null;
  return (
    <div style={backdropStyle} onClick={onCancel}>
      <div style={panelStyle} onClick={e => e.stopPropagation()} role="dialog" aria-modal="true">
        <h4 style={{ margin: '0 0 10px', color: '#e3f2fd', fontSize: 15 }}>{title}</h4>
        <div style={{ fontSize: 13, color: '#bbb', lineHeight: 1.5, marginBottom: 16 }}>{children}</div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onCancel} style={btnStyle}>
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            style={{
              ...btnStyle,
              borderColor: danger ? '#c62828' : '#1565c0',
              background: danger ? '#4a1515' : '#1e3a5f',
              color: danger ? '#ffcdd2' : '#4fc3f7',
              fontWeight: 600,
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

const backdropStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 10001,
  background: 'rgba(0,0,0,0.55)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 20,
};

const panelStyle: CSSProperties = {
  background: '#1a1a28',
  border: '1px solid #444',
  borderRadius: 10,
  padding: 18,
  maxWidth: 420,
  width: '100%',
};

const btnStyle: CSSProperties = {
  padding: '8px 14px',
  fontSize: 13,
  border: '1px solid #444',
  borderRadius: 6,
  background: '#12121f',
  color: '#ccc',
  cursor: 'pointer',
};
