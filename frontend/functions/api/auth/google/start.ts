import { json, randomToken, siteUrl, type PagesContext } from '../../../_lib';

/** GET /api/auth/google/start?lang=es&next=/app → redirect to Google's consent screen (scopes: email, profile). */
export const onRequestGet = async ({ request, env }: PagesContext): Promise<Response> => {
  if (!env.GOOGLE_CLIENT_ID) return json({ error: 'google_not_configured' }, 503);
  const url = new URL(request.url);
  const lang = url.searchParams.get('lang') === 'en' ? 'en' : 'es';
  const next = (url.searchParams.get('next') ?? '/app').replace(/[^a-zA-Z0-9/_-]/g, '').slice(0, 100) || '/app';
  const state = randomToken(24);
  const params = new URLSearchParams({
    client_id: env.GOOGLE_CLIENT_ID, redirect_uri: `${siteUrl(request, env)}/api/auth/google/callback`, response_type: 'code',
    scope: 'openid email profile', state, prompt: 'select_account', access_type: 'online',
  });
  const stateCookie = `fxlab_oauth=${state}.${lang}.${encodeURIComponent(next)}; Path=/api/auth/google; HttpOnly; Secure; SameSite=Lax; Max-Age=600`;
  return new Response(null, { status: 302, headers: { location: `https://accounts.google.com/o/oauth2/v2/auth?${params}`, 'set-cookie': stateCookie, 'cache-control': 'no-store' } });
};
