import { EMAIL, ensureSchema, json, randomToken, sendMagicLink, sessionSecret, sha256, siteUrl, tooManyRequests, type PagesContext } from '../../../_lib';

/** POST /api/auth/magic/request {email, lang, next} → emails a single-use sign-in link. Always answers ok to not leak accounts. */
export const onRequestPost = async ({ request, env }: PagesContext): Promise<Response> => {
  if (!env.DB || !sessionSecret(env)) return json({ error: 'not_configured' }, 503);
  if (!env.BREVO_API_KEY || !env.MAIL_FROM) return json({ error: 'mail_not_configured' }, 503);
  let body: { email?: string; lang?: string; next?: string };
  try { body = (await request.json()) as typeof body; } catch { return json({ error: 'bad_json' }, 400); }
  const email = (body.email ?? '').trim().toLowerCase();
  if (!EMAIL.test(email) || email.length > 254) return json({ error: 'invalid_email' }, 400);
  await ensureSchema(env.DB);
  const ip = request.headers.get('cf-connecting-ip');
  if (await tooManyRequests(env, 'magic', ip, 5, 15)) return json({ error: 'rate_limited' }, 429);
  const lang = body.lang === 'en' ? 'en' : 'es';
  const next = (body.next ?? '/app').replace(/[^a-zA-Z0-9/_-]/g, '').slice(0, 100) || '/app';
  const token = randomToken(32);
  const expires = new Date(Date.now() + 20 * 60_000).toISOString();
  await env.DB.prepare('INSERT INTO magic_tokens (hash, email, lang, expires_at) VALUES (?, ?, ?, ?)').bind(await sha256(token), email, lang, expires).run();
  const link = `${siteUrl(request, env)}/api/auth/magic/verify?t=${token}&next=${encodeURIComponent(next)}`;
  const sent = await sendMagicLink(env, email, link, lang);
  if (!sent) return json({ error: 'mail_failed' }, 502);
  return json({ ok: true });
};

export const onRequest = async (): Promise<Response> => new Response('Method not allowed', { status: 405, headers: { allow: 'POST' } });
