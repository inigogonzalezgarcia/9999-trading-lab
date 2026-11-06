import { useState } from 'react';
import { isPro, useAuth } from '../auth';
import { useT } from '../i18n';
import { Link, useRoute } from '../router';
import { BASE_URL, GUMROAD_LIBRARY, GUMROAD_SUBSCRIPTIONS, PRO_OPEN, PRO_URLS } from '../site';

const REASON: Record<string, { es: string; en: string }> = {
  not_found: { es: 'Esa clave no corresponde a ningún producto Lab Pro. Cópiala entera desde el correo de Gumroad o desde tu biblioteca.', en: 'That key does not belong to any Lab Pro product. Copy it whole from the Gumroad email or your library.' },
  refunded: { es: 'Esa compra fue reembolsada o disputada; la clave ya no es válida.', en: 'That purchase was refunded or disputed; the key is no longer valid.' },
  subscription_ended: { es: 'La suscripción de esa clave terminó o el cobro falló. Renueva en Gumroad y vuelve a pegarla.', en: 'The subscription for that key ended or its payment failed. Renew on Gumroad and paste it again.' },
  invalid_format: { es: 'El formato no es el de una clave de Gumroad (XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX).', en: 'Not the format of a Gumroad key (XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX).' },
  rate_limited: { es: 'Demasiados intentos; espera unos minutos.', en: 'Too many attempts; wait a few minutes.' },
};

/** /app/cuenta — plan, licence activation, Gumroad links, sign out and account deletion. */
export function AccountPage() {
  const { lang } = useT();
  const es = lang === 'es';
  const { user, refresh, logout } = useAuth();
  const { navigate } = useRoute();
  const [key, setKey] = useState('');
  const [state, setState] = useState<{ kind: 'idle' | 'busy' | 'ok' | 'error'; text?: string }>({ kind: 'idle' });
  const [confirmDelete, setConfirmDelete] = useState(false);
  if (!user) return <main className="prose"><p className="muted">…</p></main>;
  const pro = isPro(user);
  const activate = async (event: React.FormEvent) => {
    event.preventDefault();
    setState({ kind: 'busy' });
    try {
      const response = await fetch(`${BASE_URL}api/license`, { method: 'POST', credentials: 'same-origin', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ key }) });
      const data = (await response.json()) as { ok?: boolean; reason?: string; error?: string; lifetime?: boolean };
      if (data.ok) { setState({ kind: 'ok', text: data.lifetime ? (es ? 'Lab Pro de por vida activado.' : 'Lab Pro lifetime activated.') : (es ? 'Lab Pro activado. Se renueva mientras la suscripción siga activa en Gumroad.' : 'Lab Pro activated. It renews while the subscription stays active on Gumroad.') }); await refresh(); }
      else setState({ kind: 'error', text: (REASON[data.reason ?? data.error ?? 'not_found'] ?? REASON.not_found)[lang] });
    } catch {
      setState({ kind: 'error', text: es ? 'No se pudo comprobar la clave. Inténtalo de nuevo.' : 'Could not check the key. Try again.' });
    }
  };
  const remove = async () => {
    const response = await fetch(`${BASE_URL}api/me`, { method: 'DELETE', credentials: 'same-origin' });
    if (response.ok) { await logout(); navigate('/'); }
  };
  return (
    <main className="prose account">
      <p className="kicker">{es ? 'Tu cuenta' : 'Your account'}</p>
      <h1 className="page-title">{user.email}</h1>
      <div className="tiles">
        <div className="tile"><div className="tile-label">{es ? 'Plan' : 'Plan'}</div><div className="tile-value">{pro ? 'Lab Pro' : (es ? 'Gratis' : 'Free')}</div><div className="tile-hint">{pro ? (user.pro_until ? (es ? `comprobado hasta ${user.pro_until.slice(0, 10)}` : `verified until ${user.pro_until.slice(0, 10)}`) : (es ? 'de por vida' : 'lifetime')) : (es ? 'niveles 0–2' : 'levels 0–2')}</div></div>
        <div className="tile"><div className="tile-label">{es ? 'Acceso' : 'Sign-in'}</div><div className="tile-value">{user.provider === 'google' ? 'Google' : (es ? 'Correo' : 'Email')}</div><div className="tile-hint">{es ? 'desde' : 'since'} {user.created_at.slice(0, 10)}</div></div>
      </div>

      <section>
        <h2>{pro ? (es ? 'Clave de licencia' : 'Licence key') : (es ? 'Activar Lab Pro' : 'Activate Lab Pro')}</h2>
        <p className="muted">{es ? 'Tras comprar Lab Pro en Gumroad recibes una clave por correo (también en tu biblioteca de Gumroad). Pégala aquí.' : 'After buying Lab Pro on Gumroad you receive a key by email (also in your Gumroad library). Paste it here.'}</p>
        <form onSubmit={activate} className="subscribe-form">
          <input className="mono" value={key} onChange={(e) => { setKey(e.target.value); setState({ kind: 'idle' }); }} placeholder="XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX" spellCheck={false} autoComplete="off" />
          <button type="submit" disabled={state.kind === 'busy' || key.trim().length < 20}>{state.kind === 'busy' ? '…' : (es ? 'Activar' : 'Activate')}</button>
        </form>
        {state.kind === 'ok' && <p className="good">{state.text}</p>}
        {state.kind === 'error' && <p className="bad">{state.text}</p>}
        {!pro && (PRO_OPEN
          ? <p className="row-actions"><a className="button" href={PRO_URLS.membership} target="_blank" rel="noopener">{es ? 'Suscribirme · 12 €/mes o 89 €/año' : 'Subscribe · 12 €/month or 89 €/year'}</a><a className="button ghost" href={PRO_URLS.lifetime} target="_blank" rel="noopener">{es ? 'De por vida · 149 €' : 'Lifetime · 149 €'}</a></p>
          : <p className="muted small">{es ? 'Lab Pro abre el 23 de noviembre. ' : 'Lab Pro opens on 23 November. '}<Link to="/planes">{es ? 'Ver planes y apuntarme al aviso' : 'See plans and join the waitlist'}</Link></p>)}
        {pro && <p className="muted small"><a href={GUMROAD_SUBSCRIPTIONS} target="_blank" rel="noopener">{es ? 'Gestionar la suscripción' : 'Manage the subscription'}</a> · <a href={GUMROAD_LIBRARY} target="_blank" rel="noopener">{es ? 'Facturas y descargas (kit) en Gumroad' : 'Invoices and downloads (kit) on Gumroad'}</a></p>}
      </section>

      <section>
        <h2>{es ? 'Sesión y datos' : 'Session and data'}</h2>
        <div className="row-actions">
          <button type="button" className="ghost" onClick={async () => { await logout(); navigate('/'); }}>{es ? 'Cerrar sesión' : 'Sign out'}</button>
          {!confirmDelete
            ? <button type="button" className="ghost danger" onClick={() => setConfirmDelete(true)}>{es ? 'Borrar mi cuenta' : 'Delete my account'}</button>
            : <><span className="bad small">{es ? 'Se borran cuenta, progreso y notas; no hay vuelta atrás. La suscripción de Gumroad se cancela en Gumroad.' : 'Account, progress and notes are erased; no way back. A Gumroad subscription is cancelled on Gumroad.'}</span><button type="button" className="danger" onClick={remove}>{es ? 'Sí, borrar' : 'Yes, delete'}</button><button type="button" className="ghost" onClick={() => setConfirmDelete(false)}>{es ? 'No' : 'No'}</button></>}
        </div>
        <p className="muted small">{es ? 'Guardamos tu correo, el proveedor de acceso, tu progreso y, si activas Lab Pro, el estado de la licencia. ' : 'We store your email, sign-in provider, your progress and, with Lab Pro, the licence status. '}<Link to="/legal/privacidad">{es ? 'Privacidad' : 'Privacy'}</Link></p>
      </section>
    </main>
  );
}
