import { useEffect, useState, type ReactNode } from 'react';
import { api } from '../api';
import { useT } from '../i18n';
import { Link } from '../router';
import { AUTHOR_SITE, REPO_URL, SITE_NAME, STATIC_MODE } from '../site';
import type { Notice } from '../types';

export function Shell({ children }: { children: ReactNode }) {
  const { t, lang, setLang } = useT();
  const [version, setVersion] = useState<string>('');
  const [notice, setNotice] = useState<Notice | null>(null);
  const [menu, setMenu] = useState(false);
  useEffect(() => {
    api.health().then((h) => setVersion(h.version)).catch(() => setVersion(''));
    api.notice().then(setNotice).catch(() => setNotice(null));
  }, []);
  return (
    <div className="app">
      <header className="masthead">
        <div>
          <small>{t('shell.tagline')}</small>
          <h1><Link to="/">{SITE_NAME}</Link></h1>
        </div>
        <button type="button" className="ghost menu-toggle" aria-expanded={menu} onClick={() => setMenu(!menu)}>☰</button>
        <nav className={`site-nav ${menu ? 'open' : ''}`} aria-label="main">
          <Link to="/" onClick={() => setMenu(false)}>{t('nav.home')}</Link>
          <Link to="/lab" onClick={() => setMenu(false)}>{t('nav.lab')}</Link>
          <Link to="/lessons" onClick={() => setMenu(false)}>{t('nav.lessons')}</Link>
          <Link to="/method" onClick={() => setMenu(false)}>{t('nav.method')}</Link>
          <div className="segmented lang">
            <button type="button" className={lang === 'es' ? 'active' : ''} onClick={() => setLang('es')}>ES</button>
            <button type="button" className={lang === 'en' ? 'active' : ''} onClick={() => setLang('en')}>EN</button>
          </div>
        </nav>
        <div className="masthead-right">
          <span className="badge">{t('badge.noLive')}</span>
          <span className="badge soft">{t('badge.edu')}</span>
          {version && <span className="muted small">v{version}</span>}
        </div>
      </header>
      <aside className="notice" role="note">
        <strong>{t('notice.title')}.</strong> {t('notice.short')}
      </aside>
      {children}
      <footer className="site-footer muted small">
        <div>
          <Link to="/legal/aviso">{lang === 'es' ? 'Aviso legal' : 'Legal notice'}</Link> · <Link to="/legal/privacidad">{lang === 'es' ? 'Privacidad' : 'Privacy'}</Link> · <Link to="/legal/cookies">Cookies</Link> · <Link to="/legal/condiciones">{lang === 'es' ? 'Condiciones' : 'Terms'}</Link>
          {' · '}<a href={REPO_URL} target="_blank" rel="noreferrer">{t('footer.source')}</a>
          {' · '}<a href={AUTHOR_SITE} target="_blank" rel="noreferrer">{t('footer.author')}</a>
        </div>
        <div>{notice ? notice.lines[notice.lines.length - 1] : t('notice.short')} {t('footer.hash')}{STATIC_MODE ? '' : ''}</div>
      </footer>
    </div>
  );
}
