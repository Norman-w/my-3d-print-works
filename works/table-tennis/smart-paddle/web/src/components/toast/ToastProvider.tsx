import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react';

export type ToastKind = 'info' | 'success' | 'error';

export type ToastItem = {
  id: number;
  message: string;
  kind: ToastKind;
};

type ToastContextValue = {
  toast: (message: string, kind?: ToastKind) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const toast = useCallback((message: string, kind: ToastKind = 'info') => {
    const id = nextId++;
    setItems(prev => [...prev, { id, message, kind }]);
    window.setTimeout(() => {
      setItems(prev => prev.filter(t => t.id !== id));
    }, 4500);
  }, []);

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div style={hostStyle} aria-live="polite">
        {items.map(t => (
          <div key={t.id} style={{ ...toastStyle, ...kindStyle[t.kind] }}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

const hostStyle: CSSProperties = {
  position: 'fixed',
  bottom: 20,
  right: 20,
  zIndex: 10000,
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  maxWidth: 360,
  pointerEvents: 'none',
};

const toastStyle: CSSProperties = {
  padding: '10px 14px',
  borderRadius: 8,
  fontSize: 13,
  lineHeight: 1.45,
  whiteSpace: 'pre-wrap',
  boxShadow: '0 4px 20px rgba(0,0,0,0.35)',
  pointerEvents: 'auto',
};

const kindStyle: Record<ToastKind, CSSProperties> = {
  info: { background: '#1e3a5f', color: '#e3f2fd', border: '1px solid #1565c0' },
  success: { background: '#1b3d1f', color: '#c8e6c9', border: '1px solid #2e7d32' },
  error: { background: '#3d1a1a', color: '#ffcdd2', border: '1px solid #c62828' },
};
