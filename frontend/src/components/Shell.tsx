import { useEffect, useState, type ReactNode } from 'react';
import { api } from '../api';
import { useAuth } from '../auth';
import { useT } from '../i18n';
import { Link, useRoute } from '../router';
import { AUTHOR_SITE, REPO_URL, SITE_NAME } from '../site';
import type { Notice } from '../types';

export function Shell({ children }: { children: ReactNode }) {
  const { t, lang, setLang } = useT();
  const { path } = useRoute();
  const { user } = useAuth();
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
          <div><Link to="/" className="brand"><span className="brand-mark" aria-hidden="true" />{SITE_NAME}</Link></div>
        </div>
        <button type="button" className="ghost menu-toggle" aria-expanded={menu} onClick={() => setMenu(!menu)}>☰</button>
        <nav className={`site-nav ${menu ? 'open' : ''}`} aria-label="main">
          <Link to="/" onClick={() => setMenu(false)}>{t('nav.home')}</Link>
          <Link to="/tour" onClick={() => setMenu(false)}>{t('nav.tour')}</Link>
          <Link to="/app" onClick={() => setMenu(false)}>{t('nav.app')}</Link>
          <Link to="/lab" onClick={() => setMenu(false)}>{t('nav.lab')}</Link>
          <Link to="/lessons" onClick={() => setMenu(false)}>{t('nav.lessons')}</Link>
          <Link to="/planes" onClick={() => setMenu(false)}>{t('nav.plans')}</Link>
          {user
            ? <Link to="/app/cuenta" className="nav-account" onClick={() => setMenu(false)}>{user.plan === 'pro' ? 'Pro · ' : ''}{t('nav.account')}</Link>
            : <Link to="/entrar" className="nav-account" onClick={() => setMenu(false)}>{t('nav.login')}</Link>}
          <Link to="/method" onClick={() => setMenu(false)}>{t('nav.method')}</Link>
          <div className="segmented lang">
            <button type="button" className={lang === 'es' ? 'active' : ''} onClick={() => setLang('es')}>ES</button>
            <button type="button" className={lang === 'en' ? 'active' : ''} onClick={() => setLang('en')}>EN</button>
          </div>
        </nav>
      </header>
      <aside className="notice-strip" role="note">
        <span className="notice-dot" aria-hidden="true" />
        <span><strong>{t('notice.title')}.</strong> {t('notice.short')}</span>
        <Link to="/legal/aviso" className="notice-more">{lang === 'es' ? 'Más' : 'More'}</Link>
      </aside>
      <div className="page" key={path.split('/')[1] ?? ''}>{children}</div>
      <footer className="site-footer small">
        <div className="footer-grid">
          <div className="footer-brand">
            <Link to="/" className="brand"><span className="brand-mark" aria-hidden="true" />{SITE_NAME}</Link>
            <p className="muted">{t('shell.tagline').toLowerCase()}</p>
            <div className="footer-badges"><span className="badge">{t('badge.noLive')}</span><span className="badge soft">{t('badge.edu')}</span>{version && <span className="muted mono">v{version}</span>}</div>
          </div>
          <nav className="footer-col" aria-label="site">
            <span className="footer-head">{lang === 'es' ? 'Explorar' : 'Explore'}</span>
            <Link to="/tour">{t('nav.tour')}</Link><Link to="/app">{t('nav.app')}</Link><Link to="/lab">{t('nav.lab')}</Link><Link to="/lessons">{t('nav.lessons')}</Link><Link to="/planes">{t('nav.plans')}</Link><Link to="/method">{t('nav.method')}</Link>
          </nav>
          <nav className="footer-col" aria-label="legal">
            <span className="footer-head">Legal</span>
            <Link to="/legal/aviso">{lang === 'es' ? 'Aviso legal' : 'Legal notice'}</Link><Link to="/legal/privacidad">{lang === 'es' ? 'Privacidad' : 'Privacy'}</Link><Link to="/legal/cookies">Cookies</Link><Link to="/legal/condiciones">{lang === 'es' ? 'Condiciones' : 'Terms'}</Link>
          </nav>
          <div className="footer-col">
            <span className="footer-head">{lang === 'es' ? 'Proyecto' : 'Project'}</span>
            <a href={REPO_URL} target="_blank" rel="noreferrer">{t('footer.source')}</a>
            <a href={AUTHOR_SITE} target="_blank" rel="noreferrer">{t('footer.author')}</a>
          </div>
        </div>
        <p className="muted footer-note">{notice ? notice.lines[notice.lines.length - 1] : t('notice.short')} {t('footer.hash')}</p>
      </footer>
    </div>
  );
}
