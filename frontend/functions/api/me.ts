import { ensureSchema, getUser, json, sessionSecret, sessionUserId, type PagesContext } from '../_lib';

/** GET /api/me → {user, progress} for the session, or {user: null}. PUT /api/me {progress} → saves the simulator progress. */
export const onRequestGet = async ({ request, env }: PagesContext): Promise<Response> => {
  if (!env.DB || !sessionSecret(env)) return json({ user: null, configured: false, missing: [!env.DB && 'DB', !sessionSecret(env) && 'SESSION_SECRET'].filter(Boolean) });
  const uid = await sessionUserId(request, env);
  if (!uid) return json({ user: null, configured: true });
  await ensureSchema(env.DB);
  const user = await getUser(env, uid);
  if (!user) return json({ user: null, configured: true });
  const row = await env.DB.prepare('SELECT data, updated_at FROM progress WHERE user_id = ?').bind(uid).first<{ data: string; updated_at: string }>();
  let progress: unknown = {};
  try { progress = row ? JSON.parse(row.data) : {}; } catch { progress = {}; }
  return json({ user: { email: user.email, name: user.name, provider: user.provider, plan: user.plan, pro_until: user.pro_until, created_at: user.created_at }, progress, progress_updated_at: row?.updated_at ?? null, configured: true });
};

export const onRequestPut = async ({ request, env }: PagesContext): Promise<Response> => {
  if (!env.DB || !sessionSecret(env)) return json({ error: 'not_configured' }, 503);
  const uid = await sessionUserId(request, env);
  if (!uid) return json({ error: 'unauthenticated' }, 401);
  let body: { progress?: unknown };
  try { body = (await request.json()) as typeof body; } catch { return json({ error: 'bad_json' }, 400); }
  const data = JSON.stringify(body.progress ?? {});
  if (data.length > 200_000) return json({ error: 'too_large' }, 413);
  await ensureSchema(env.DB);
  const now = new Date().toISOString();
  await env.DB.prepare('INSERT INTO progress (user_id, data, updated_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at').bind(uid, data, now).run();
  return json({ ok: true, updated_at: now });
};
