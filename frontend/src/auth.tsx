import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { resetRunKeys } from './api';
import { readSim, replaceSim, type LevelProgress } from './progress';
import { BASE_URL } from './site';

/** Account state for the protected area (/app). Backed by the Pages Functions in functions/api. */
export interface AccountUser { email: string; name: string | null; provider: 'google' | 'email' | string; plan: 'free' | 'pro'; pro_until: string | null; created_at: string }

interface AuthState {
  /** null until the first /api/me answer arrives */
  ready: boolean;
  /** false when the deployment has no account backend configured (local dev, preview) */
  configured: boolean;
  user: AccountUser | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
  /** Push the simulator progress to the account (no-op without session). */
  saveProgress: (progress: Record<string, LevelProgress>) => void;
}

const AuthContext = createContext<AuthState>({ ready: false, configured: false, user: null, refresh: async () => undefined, logout: async () => undefined, saveProgress: () => undefined });

/** Merge browser progress into account progress: keep the best score and the latest note per level. */
function mergeProgress(local: Record<string, LevelProgress>, remote: Record<string, LevelProgress>): Record<string, LevelProgress> {
  const out: Record<string, LevelProgress> = { ...remote };
  for (const [level, l] of Object.entries(local)) {
    const r = out[level];
    if (!r) { out[level] = l; continue; }
    const score = !r.score ? l.score : !l.score ? r.score : (l.score.ok > r.score.ok ? l.score : r.score);
    const note = l.note && (!r.note || (l.score?.at ?? '') > (r.score?.at ?? '')) ? l.note : r.note;
    out[level] = { score, note, completed: Boolean(r.completed || l.completed) };
  }
  return out;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{ ready: boolean; configured: boolean; user: AccountUser | null }>({ ready: false, configured: false, user: null });

  const refresh = useCallback(async () => {
    try {
      const response = await fetch(`${BASE_URL}api/me`, { credentials: 'same-origin', cache: 'no-store' });
      const data = (await response.json()) as { user: AccountUser | null; configured: boolean; progress?: Record<string, LevelProgress> };
      if (data.user) {
        // First visit with a session: import what the browser already had, then keep both in sync.
        const merged = mergeProgress(readSim(), data.progress ?? {});
        replaceSim(merged);
        if (JSON.stringify(merged) !== JSON.stringify(data.progress ?? {})) {
          fetch(`${BASE_URL}api/me`, { method: 'PUT', credentials: 'same-origin', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ progress: merged }) }).catch(() => undefined);
        }
      }
      setState({ ready: true, configured: data.configured, user: data.user });
      resetRunKeys();
    } catch {
      setState({ ready: true, configured: false, user: null });
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const logout = useCallback(async () => {
    try { await fetch(`${BASE_URL}api/auth/logout`, { method: 'POST', credentials: 'same-origin' }); } catch { /* offline */ }
    setState((s) => ({ ...s, user: null }));
  }, []);

  const saveProgress = useCallback((progress: Record<string, LevelProgress>) => {
    if (!state.user) return;
    fetch(`${BASE_URL}api/me`, { method: 'PUT', credentials: 'same-origin', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ progress }) }).catch(() => undefined);
  }, [state.user]);

  return <AuthContext.Provider value={{ ...state, refresh, logout, saveProgress }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

export const isPro = (user: AccountUser | null) => user?.plan === 'pro';
