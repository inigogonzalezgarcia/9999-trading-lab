import { createContext, useCallback, useContext, useEffect, useState, type MouseEvent, type ReactNode } from 'react';
import { BASE_URL } from './site';

/** Minimal history-API router: no dependency, enough for a handful of routes. */
const RouteContext = createContext<{ path: string; navigate: (to: string) => void }>({ path: '/', navigate: () => undefined });

function stripBase(pathname: string): string {
  const base = BASE_URL.replace(/\/$/, '');
  const path = base && pathname.startsWith(base) ? pathname.slice(base.length) : pathname;
  return path.replace(/\/+$/, '') || '/';
}

export function withBase(to: string): string {
  const base = BASE_URL.replace(/\/$/, '');
  return `${base}${to.startsWith('/') ? to : `/${to}`}`;
}

export function RouterProvider({ children }: { children: ReactNode }) {
  const [path, setPath] = useState(() => stripBase(window.location.pathname));
  useEffect(() => {
    const onPop = () => setPath(stripBase(window.location.pathname));
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);
  const navigate = useCallback((to: string) => {
    window.history.pushState(null, '', withBase(to));
    setPath(stripBase(window.location.pathname));
    window.scrollTo({ top: 0 });
  }, []);
  return <RouteContext.Provider value={{ path, navigate }}>{children}</RouteContext.Provider>;
}

export function useRoute() {
  return useContext(RouteContext);
}

/** Match "/lessons/:slug" style patterns; returns params or null. */
export function matchRoute(pattern: string, path: string): Record<string, string> | null {
  const a = pattern.split('/').filter(Boolean);
  const b = path.split('/').filter(Boolean);
  if (a.length !== b.length) return null;
  const params: Record<string, string> = {};
  for (let i = 0; i < a.length; i += 1) {
    if (a[i].startsWith(':')) params[a[i].slice(1)] = decodeURIComponent(b[i]);
    else if (a[i] !== b[i]) return null;
  }
  return params;
}

export function Link({ to, children, className, onClick }: { to: string; children: ReactNode; className?: string; onClick?: () => void }) {
  const { navigate, path } = useRoute();
  const handle = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    event.preventDefault();
    onClick?.();
    navigate(to);
  };
  const active = path === to || (to !== '/' && path.startsWith(`${to}/`));
  return (
    <a href={withBase(to)} onClick={handle} className={`${className ?? ''}${active ? ' active' : ''}`.trim()} aria-current={active ? 'page' : undefined}>
      {children}
    </a>
  );
}
