import { createContext, useContext, useEffect, useState, type CSSProperties, type ReactNode } from 'react';
import { ALL_DRAW_TARGETS } from '../lib/bezierProfile';
import { labelTargets } from '../lib/bezierStorage';
import { ensureProfilesLoaded, isProfileCacheLoaded } from '../lib/profileCache';
import { useToast } from '../components/toast/ToastProvider';

type ProfilesReadyContextValue = {
  ready: boolean;
};

const ProfilesReadyContext = createContext<ProfilesReadyContextValue>({ ready: false });

export function useProfilesReady(): ProfilesReadyContextValue {
  return useContext(ProfilesReadyContext);
}

/** Block the app until Bezier profiles are loaded from the server (no default-curve flash). */
export default function ProfilesReadyProvider({ children }: { children: ReactNode }) {
  const { toast } = useToast();
  const [ready, setReady] = useState(isProfileCacheLoaded());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ready) return;
    void ensureProfilesLoaded()
      .then(bundle => {
        const keys = ALL_DRAW_TARGETS.filter(t => bundle[t] != null);
        if (keys.length > 0) {
          toast(`已从服务端加载：${labelTargets(keys)}`, 'info');
        }
        setReady(true);
      })
      .catch(err => {
        setError(err instanceof Error ? err.message : String(err));
      });
  }, [ready, toast]);

  if (error) {
    return (
      <div style={gateStyle}>
        <p style={{ color: '#ffcdd2', margin: '0 0 12px', lineHeight: 1.5 }}>曲线加载失败：{error}</p>
        <p style={{ color: '#888', margin: 0, fontSize: 13 }}>
          请确认已运行 <code style={codeStyle}>./dev.sh</code>（Go :8000 + 前端 5173），然后刷新页面。
        </p>
      </div>
    );
  }

  if (!ready) {
    return (
      <div style={gateStyle}>
        <p style={{ color: '#90caf9', margin: 0, fontSize: 15 }}>正在从服务端加载曲线…</p>
      </div>
    );
  }

  return <ProfilesReadyContext.Provider value={{ ready: true }}>{children}</ProfilesReadyContext.Provider>;
}

const gateStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100vh',
  background: '#0c0c14',
  padding: 24,
  textAlign: 'center',
};

const codeStyle: CSSProperties = { color: '#aaa' };
