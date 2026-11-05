import { useEffect, useState } from 'react';
import { useAuth } from '../auth';
import { useT } from '../i18n';
import { Link, useRoute } from '../router';
import { BASE_URL } from '../site';

const ERRORS: Record<string, { es: string; en: string }> = {
  expired: { es: 'Ese enlace ha caducado o ya se usó. Pide uno nuevo.', en: 'That link has expired or was already used. Request a new one.' },
  link: { es: 'El enlace no es válido. Pide uno nuevo.', en: 'The link is not valid. Request a new one.' },
  state: { es: 'La sesión de Google no coincidía (¿ventana antigua?). Vuelve a intentarlo.', en: 'The Google session did not match (old window?). Try again.' },
  token: { es: 'Google no aceptó la autorización. Vuelve a intentarlo.', en: 'Google did not accept the authorisation. Try again.' },
  userinfo: { es: 'No se pudo leer tu correo de Google.', en: 'Could not read your email from Google.' },
  email: { es: 'Google no devolvió un correo verificado.', en: 'Google did not return a verified email.' },
  not_configured: { es: 'Las cuentas todavía no están activadas en este despliegue.', en: 'Accounts are not enabled on this deployment yet.' },
};

/** /entrar — sign in or create an account: Google, or a single-use link by email. Nothing else to fill in. */
export function LoginPage() {
  const { lang } = useT();
  const es = lang === 'es';
  const { ready, configured, user } = useAuth();
  const { navigate } = useRoute();
  const [email, setEmail] = useState('');
  const [state, setState] = useState<'idle' | 'busy' | 'sent' | 'invalid' | 'error' | 'rate'>('idle');
  const params = new URLSearchParams(window.location.search);
  const next = (params.get('next') ?? '/app').replace(/[^a-zA-Z0-9/_-]/g, '') || '/app';
  const error = params.get('error');

  useEffect(() => { if (ready && user) navigate(next); }, [ready, user, next, navigate]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setState('invalid'); return; }
    setState('busy');
    try {
      const response = await fetch(`${BASE_URL}api/auth/magic/request`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ email, lang, next }) });
      if (response.status === 429) setState('rate');
      else setState(response.ok ? 'sent' : 'error');
    } catch {
      setState('error');
    }
  };

  return (
    <main className="prose login">
      <p className="kicker">{es ? 'Tu cuenta' : 'Your account'}</p>
      <h1 className="page-title">{es ? 'Entra o crea tu cuenta' : 'Sign in or create your account'}</h1>
      <p className="lead">{es ? 'Gratis. Sirve para guardar tu progreso en el simulador en cualquier dispositivo y, cuando quieras, activar Lab Pro. Sin contraseña: con Google o con un enlace que te enviamos al correo.' : 'Free. It saves your simulator progress on any device and, when you want, activates Lab Pro. No password: with Google or a link we email you.'}</p>
      {error && <p className="bad">{(ERRORS[error] ?? ERRORS.link)[lang]}</p>}
      {ready && !configured && <p className="notice">{ERRORS.not_configured[lang]}</p>}
      <div className="login-grid">
        <section className="login-card">
          <h2>{es ? 'Con Google' : 'With Google'}</h2>
          <p className="muted small">{es ? 'Solo leemos tu correo y tu nombre. No publicamos nada ni accedemos a nada más.' : 'We only read your email and name. We post nothing and access nothing else.'}</p>
          <a className="button google" href={`${BASE_URL}api/auth/google/start?lang=${lang}&next=${encodeURIComponent(next)}`}>
            <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.5l6.7-6.7C35.6 2.5 30.2 0 24 0 14.6 0 6.5 5.4 2.6 13.3l7.8 6C12.3 13.6 17.7 9.5 24 9.5z"/><path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17.5z"/><path fill="#FBBC05" d="M10.4 28.7A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.8-4.7l-7.8-6A24 24 0 0 0 0 24c0 3.9.9 7.5 2.6 10.7l7.8-6z"/><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.5-5.8c-2.1 1.4-4.9 2.3-8.4 2.3-6.3 0-11.7-4.1-13.6-9.9l-7.8 6C6.5 42.6 14.6 48 24 48z"/></svg>
            {es ? 'Continuar con Google' : 'Continue with Google'}
          </a>
        </section>
        <section className="login-card">
          <h2>{es ? 'Con tu correo' : 'With your email'}</h2>
          {state === 'sent' ? (
            <p className="good">{es ? `Enviado a ${email}. Abre el enlace del correo (caduca en 20 minutos). Si no llega, mira en spam.` : `Sent to ${email}. Open the link in the email (expires in 20 minutes). Check spam if it does not arrive.`}</p>
          ) : (
            <form onSubmit={submit} className="subscribe-form">
              <label className="sr-only" htmlFor="login-email">{es ? 'Correo' : 'Email'}</label>
              <input id="login-email" type="email" autoComplete="email" placeholder={es ? 'tu@correo.com' : 'you@example.com'} value={email} onChange={(e) => { setEmail(e.target.value); setState('idle'); }} required />
              <button type="submit" disabled={state === 'busy'}>{state === 'busy' ? '…' : (es ? 'Enviarme el enlace' : 'Email me the link')}</button>
              {state === 'invalid' && <p className="bad small">{es ? 'Revisa el correo.' : 'Check the address.'}</p>}
              {state === 'rate' && <p className="bad small">{es ? 'Demasiados intentos; espera unos minutos.' : 'Too many attempts; wait a few minutes.'}</p>}
              {state === 'error' && <p className="bad small">{es ? 'No se pudo enviar. Prueba con Google o inténtalo más tarde.' : 'Could not send. Try Google or come back later.'}</p>}
            </form>
          )}
          <p className="muted small">{es ? 'Sin contraseña: cada vez que entres te enviamos un enlace nuevo.' : 'No password: each time you sign in we send a fresh link.'}</p>
        </section>
      </div>
      <p className="muted small">{es ? 'Al entrar aceptas las ' : 'By signing in you accept the '}<Link to="/legal/condiciones">{es ? 'condiciones' : 'terms'}</Link>{es ? ' y la ' : ' and the '}<Link to="/legal/privacidad">{es ? 'política de privacidad' : 'privacy policy'}</Link>. {es ? 'Guardamos tu correo, el proveedor de acceso y tu progreso; nada más.' : 'We store your email, the sign-in provider and your progress; nothing else.'}</p>
    </main>
  );
}
