import { clearSessionCookie, json, type PagesContext } from '../../_lib';

/** POST /api/auth/logout → clears the session cookie. */
export const onRequestPost = async (_ctx: PagesContext): Promise<Response> => json({ ok: true }, 200, { 'set-cookie': clearSessionCookie() });
export const onRequest = async (): Promise<Response> => new Response('Method not allowed', { status: 405, headers: { allow: 'POST' } });
