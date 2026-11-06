import { applyLicense, ensureSchema, getUser, json, sessionSecret, sessionUserId, tooManyRequests, verifyLicense, type PagesContext } from '../_lib';

/** POST /api/license {key} → verifies a Lab Pro licence with Gumroad and activates the plan on the signed-in account. */
export const onRequestPost = async ({ request, env }: PagesContext): Promise<Response> => {
  if (!env.DB || !sessionSecret(env)) return json({ error: 'not_configured' }, 503);
  const uid = await sessionUserId(request, env);
  if (!uid) return json({ error: 'unauthenticated' }, 401);
  let body: { key?: string };
  try { body = (await request.json()) as typeof body; } catch { return json({ error: 'bad_json' }, 400); }
  const key = (body.key ?? '').trim().toUpperCase();
  if (!/^[A-Z0-9]{8}(-[A-Z0-9]{8}){3}$/.test(key)) return json({ error: 'invalid_format' }, 400);
  await ensureSchema(env.DB);
  if (await tooManyRequests(env, 'license', request.headers.get('cf-connecting-ip'), 10, 15)) return json({ error: 'rate_limited' }, 429);
  const verdict = await verifyLicense(key);
  if (!verdict.ok) return json({ ok: false, reason: verdict.reason ?? 'not_found' }, 200);
  await applyLicense(env, uid, key, verdict);
  const user = await getUser(env, uid);
  return json({ ok: true, product: verdict.product, lifetime: verdict.lifetime, plan: user?.plan, pro_until: user?.pro_until });
};

export const onRequest = async (): Promise<Response> => new Response('Method not allowed', { status: 405, headers: { allow: 'POST' } });
