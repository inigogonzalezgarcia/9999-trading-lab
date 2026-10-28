/**
 * Cloudflare Pages Function: POST /api/subscribe
 *
 * Stores a mailing-list opt-in in a KV namespace bound as SUBSCRIBERS and verifies a Turnstile token
 * when TURNSTILE_SECRET is configured. No third party receives the address. Bindings (Pages project
 * → Settings → Functions): KV namespace binding "SUBSCRIBERS"; environment variable "TURNSTILE_SECRET"
 * (encrypted). Without the KV binding the function answers 503 so the form shows an error instead of
 * silently dropping addresses.
 */
interface Env {
  SUBSCRIBERS?: KVNamespace;
  TURNSTILE_SECRET?: string;
}

interface KVNamespace {
  get(key: string): Promise<string | null>;
  put(key: string, value: string, options?: { metadata?: unknown }): Promise<void>;
}

interface PagesContext {
  request: Request;
  env: Env;
}

const EMAIL = /^[^\s@]{1,64}@[^\s@]{1,255}\.[^\s@]{2,}$/;
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });

async function verifyTurnstile(secret: string, token: string, ip: string | null): Promise<boolean> {
  const form = new FormData();
  form.append('secret', secret);
  form.append('response', token);
  if (ip) form.append('remoteip', ip);
  const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', { method: 'POST', body: form });
  const outcome = (await response.json()) as { success?: boolean };
  return Boolean(outcome.success);
}

async function hash(value: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value.toLowerCase()));
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

export const onRequestPost = async ({ request, env }: PagesContext): Promise<Response> => {
  if (!env.SUBSCRIBERS) return json({ error: 'not_configured' }, 503);
  let body: { email?: string; lang?: string; consent?: boolean; token?: string; source?: string };
  try {
    body = (await request.json()) as typeof body;
  } catch {
    return json({ error: 'bad_json' }, 400);
  }
  const email = (body.email ?? '').trim();
  if (!EMAIL.test(email) || email.length > 254) return json({ error: 'invalid_email' }, 400);
  if (body.consent !== true) return json({ error: 'consent_required' }, 400);
  const ip = request.headers.get('cf-connecting-ip');
  if (env.TURNSTILE_SECRET) {
    if (!body.token || !(await verifyTurnstile(env.TURNSTILE_SECRET, body.token, ip))) return json({ error: 'turnstile_failed' }, 403);
  }
  const key = `email:${await hash(email)}`;
  const existing = await env.SUBSCRIBERS.get(key);
  if (!existing) {
    const record = {
      email, lang: body.lang === 'es' ? 'es' : 'en', consent: true, consent_at: new Date().toISOString(),
      source: typeof body.source === 'string' ? body.source.slice(0, 200) : null,
      // Kept only as evidence of consent (GDPR art. 7); never used for anything else.
      ip_hash: ip ? (await hash(ip)).slice(0, 16) : null,
    };
    await env.SUBSCRIBERS.put(key, JSON.stringify(record));
  }
  return json({ ok: true });
};

// Any other method (Pages routes POST to onRequestPost first).
export const onRequest = async (): Promise<Response> => new Response('Method not allowed', { status: 405, headers: { allow: 'POST' } });
