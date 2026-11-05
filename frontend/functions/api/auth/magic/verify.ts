import { ensureSchema, sessionCookie, sessionSecret, sha256, siteUrl, type PagesContext, upsertUser } from '../../../_lib';

/** GET /api/auth/magic/verify?t=token&next=/app → consumes the token and opens a session. */
export const onRequestGet = async ({ request, env }: PagesContext): Promise<Response> => {
  const origin = siteUrl(request, env);
  const fail = (reason: string) => new Response(null, { status: 302, headers: { location: `${origin}/entrar?error=${reason}`, 'cache-control': 'no-store' } });
  if (!env.DB || !sessionSecret(env)) return fail('not_configured');
  const url = new URL(request.url);
  const token = url.searchParams.get('t');
  const next = (url.searchParams.get('next') ?? '/app').replace(/[^a-zA-Z0-9/_-]/g, '').slice(0, 100) || '/app';
  if (!token) return fail('link');
  await ensureSchema(env.DB);
  const hash = await sha256(token);
  const row = await env.DB.prepare('SELECT email, lang, expires_at, used_at FROM magic_tokens WHERE hash = ?').bind(hash).first<{ email: string; lang: string; expires_at: string; used_at: string | null }>();
  if (!row || row.used_at || new Date(row.expires_at).getTime() < Date.now()) return fail('expired');
  await env.DB.prepare('UPDATE magic_tokens SET used_at = ? WHERE hash = ?').bind(new Date().toISOString(), hash).run();
  const user = await upsertUser(env, row.email, 'email', null, row.lang);
  return new Response(null, { status: 302, headers: { location: `${origin}${next}`, 'set-cookie': await sessionCookie(env, user.id), 'cache-control': 'no-store' } });
};
