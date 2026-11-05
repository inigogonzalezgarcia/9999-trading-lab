import { ensureSchema, sessionCookie, sessionSecret, siteUrl, type PagesContext, upsertUser } from '../../../_lib';

/** GET /api/auth/google/callback?code&state → exchange the code, read the verified email, open a session. */
export const onRequestGet = async ({ request, env }: PagesContext): Promise<Response> => {
  const origin = siteUrl(request, env);
  const fail = (reason: string) => new Response(null, { status: 302, headers: { location: `${origin}/entrar?error=${reason}`, 'cache-control': 'no-store' } });
  if (!env.DB || !sessionSecret(env) || !env.GOOGLE_CLIENT_ID || !env.GOOGLE_CLIENT_SECRET) return fail('not_configured');
  const url = new URL(request.url);
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  const cookie = (request.headers.get('cookie') ?? '').split(';').map((c) => c.trim()).find((c) => c.startsWith('fxlab_oauth='))?.slice('fxlab_oauth='.length);
  if (!code || !state || !cookie) return fail('state');
  const [savedState, lang, nextRaw] = cookie.split('.');
  if (savedState !== state) return fail('state');
  const next = decodeURIComponent(nextRaw ?? '/app');

  const tokenResponse = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ code, client_id: env.GOOGLE_CLIENT_ID, client_secret: env.GOOGLE_CLIENT_SECRET, redirect_uri: `${origin}/api/auth/google/callback`, grant_type: 'authorization_code' }),
  });
  if (!tokenResponse.ok) return fail('token');
  const token = (await tokenResponse.json()) as { access_token?: string };
  if (!token.access_token) return fail('token');
  const infoResponse = await fetch('https://openidconnect.googleapis.com/v1/userinfo', { headers: { authorization: `Bearer ${token.access_token}` } });
  if (!infoResponse.ok) return fail('userinfo');
  const info = (await infoResponse.json()) as { email?: string; email_verified?: boolean; name?: string };
  if (!info.email || info.email_verified === false) return fail('email');

  await ensureSchema(env.DB);
  const user = await upsertUser(env, info.email, 'google', info.name ?? null, lang ?? 'es');
  const headers = new Headers({ location: `${origin}${next.startsWith('/') ? next : '/app'}`, 'cache-control': 'no-store' });
  headers.append('set-cookie', await sessionCookie(env, user.id));
  headers.append('set-cookie', 'fxlab_oauth=; Path=/api/auth/google; HttpOnly; Secure; SameSite=Lax; Max-Age=0');
  return new Response(null, { status: 302, headers });
};
