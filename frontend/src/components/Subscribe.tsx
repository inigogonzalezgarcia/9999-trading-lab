import { useEffect, useRef, useState } from 'react';
import { useT } from '../i18n';
import { Link } from '../router';
import { BASE_URL, STATIC_MODE, TURNSTILE_SITE_KEY } from '../site';

declare global {
  interface Window {
    turnstile?: { render: (el: HTMLElement, options: Record<string, unknown>) => string; reset: (id?: string) => void };
  }
}

/** Mailing-list opt-in. Posts to the Pages Function /api/subscribe (Turnstile + KV); see functions/api/subscribe.ts. */
export function Subscribe() {
  const { t, lang } = useT();
  const [email, setEmail] = useState('');
  const [consent, setConsent] = useState(false);
  const [state, setState] = useState<'idle' | 'busy' | 'ok' | 'error' | 'invalid'>('idle');
  const [token, setToken] = useState('');
  const widget = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!TURNSTILE_SITE_KEY || !widget.current) return;
    const render = () => {
      if (window.turnstile && widget.current && !widget.current.hasChildNodes()) {
        window.turnstile.render(widget.current, { sitekey: TURNSTILE_SITE_KEY, language: lang, callback: (value: string) => setToken(value), 'expired-callback': () => setToken('') });
      }
    };
    if (window.turnstile) render();
    else {
      const script = document.createElement('script');
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      script.async = true;
      script.onload = render;
      document.head.appendChild(script);
    }
  }, [lang]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setState('invalid'); return; }
    if (!STATIC_MODE) { setState('error'); return; }
    setState('busy');
    try {
      const response = await fetch(`${BASE_URL}api/subscribe`, {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ email, lang, consent, token, source: window.location.pathname }),
      });
      setState(response.ok ? 'ok' : 'error');
      if (response.ok) setEmail('');
    } catch {
      setState('error');
    }
  };

  return (
    <section className="subscribe">
      <h2>{t('home.subscribeTitle')}</h2>
      <p className="muted">{t('home.subscribeLead')}</p>
      {state === 'ok' ? <p className="good">{t('sub.ok')}</p> : (
        <form onSubmit={submit} className="subscribe-form">
          <label>
            {t('sub.email')}
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          </label>
          <label className="check small">
            <input type="checkbox" required checked={consent} onChange={(e) => setConsent(e.target.checked)} /> <span>{t('sub.consent')} <Link to="/legal/privacidad">{lang === 'es' ? 'Política de privacidad' : 'Privacy policy'}</Link></span>
          </label>
          {TURNSTILE_SITE_KEY && <div ref={widget} className="turnstile" />}
          <button disabled={state === 'busy' || !consent || (Boolean(TURNSTILE_SITE_KEY) && !token)}>{t('sub.button')}</button>
          {state === 'invalid' && <p className="error">{t('sub.invalid')}</p>}
          {state === 'error' && <p className="error">{STATIC_MODE ? t('sub.error') : t('sub.offline')}</p>}
        </form>
      )}
    </section>
  );
}
