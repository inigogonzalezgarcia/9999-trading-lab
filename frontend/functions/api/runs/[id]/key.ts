import { ensureSchema, getUser, json, sessionSecret, sessionUserId, sha256, type PagesContext } from '../../../_lib';

const DEMO_MARKER = '2024';
const ID = /^[a-z0-9_.-]{3,80}$/;

/** GET /api/runs/:id/key → the per-run key that decrypts the Lab Pro part of a static run file.
 *  Given to everyone for the 2024 demo runs and to Pro sessions for the rest. Key = SHA-256(DATA_KEY + ":" + id). */
export const onRequestGet = async ({ request, env, params }: PagesContext & { params: { id: string } }): Promise<Response> => {
  const id = String(params.id ?? '');
  if (!ID.test(id)) return json({ error: 'bad_id' }, 400);
  const dataKey = (env as { DATA_KEY?: string }).DATA_KEY;
  if (!dataKey) return json({ error: 'not_configured' }, 503);
  let allowed = id.includes(DEMO_MARKER);
  if (!allowed && env.DB && sessionSecret(env)) {
    const uid = await sessionUserId(request, env);
    if (uid) {
      await ensureSchema(env.DB);
      const user = await getUser(env, uid);
      allowed = user?.plan === 'pro';
    }
  }
  if (!allowed) return json({ error: 'pro_required' }, 403, { 'cache-control': 'private, no-store' });
  return json({ id, key: await sha256(`${dataKey}:${id}`) }, 200, { 'cache-control': 'private, no-store' });
};
