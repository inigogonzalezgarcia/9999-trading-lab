/**
 * Shared helpers for the account functions (Cloudflare Pages Functions, no framework).
 *
 * Bindings (Pages project → Settings): D1 database binding "DB"; variables GOOGLE_CLIENT_ID, MAIL_FROM;
 * secrets GOOGLE_CLIENT_SECRET, BREVO_API_KEY, SESSION_SECRET. The schema is created on first use.
 *
 * Sessions: a signed cookie "fxlab_session" = base64url(payload).base64url(hmac), payload {uid, exp}.
 * Magic links: a random token sent by email; only its SHA-256 is stored, valid 20 minutes, single use.
 */
export interface D1Result<T = unknown> { results: T[]; success: boolean; meta?: unknown }
export interface D1PreparedStatement {
  bind(...values: unknown[]): D1PreparedStatement;
  first<T = unknown>(column?: string): Promise<T | null>;
  run(): Promise<D1Result>;
  all<T = unknown>(): Promise<D1Result<T>>;
}
export interface D1Database { prepare(query: string): D1PreparedStatement; batch(statements: D1PreparedStatement[]): Promise<D1Result[]> }

export interface Env {
  DB?: D1Database;
  SESSION_SECRET?: string;
  /** Alias accepted for the same value (name used in the dashboard). */
  SECRET_SESSION?: string;
  GOOGLE_CLIENT_ID?: string;
  GOOGLE_CLIENT_SECRET?: string;
  BREVO_API_KEY?: string;
  MAIL_FROM?: string;
  SITE_URL?: string;
}
export interface PagesContext { request: Request; env: Env; waitUntil?: (p: Promise<unknown>) => void }

export interface User { id: string; email: string; name: string | null; provider: string; plan: 'free' | 'pro'; pro_until: string | null; lang: string; created_at: string }

export const SESSION_COOKIE = 'fxlab_session';
export const SESSION_DAYS = 30;
export const EMAIL = /^[^\s@]{1,64}@[^\s@]{1,255}\.[^\s@]{2,}$/;

export const json = (body: unknown, status = 200, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store', ...headers } });

export const sessionSecret = (env: Env): string | undefined => env.SESSION_SECRET ?? env.SECRET_SESSION;

export const siteUrl = (request: Request, env: Env) => env.SITE_URL ?? new URL(request.url).origin;

/* ---------- schema ---------- */
let schemaReady: Promise<void> | null = null;
export function ensureSchema(db: D1Database): Promise<void> {
  if (!schemaReady) {
    schemaReady = db.batch([
      db.prepare(`CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT, provider TEXT NOT NULL, plan TEXT NOT NULL DEFAULT 'free',
        pro_until TEXT, lang TEXT NOT NULL DEFAULT 'es', created_at TEXT NOT NULL, last_login TEXT NOT NULL)`),
      db.prepare(`CREATE TABLE IF NOT EXISTS magic_tokens (hash TEXT PRIMARY KEY, email TEXT NOT NULL, lang TEXT NOT NULL, expires_at TEXT NOT NULL, used_at TEXT)`),
      db.prepare(`CREATE TABLE IF NOT EXISTS progress (user_id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL)`),
      db.prepare(`CREATE TABLE IF NOT EXISTS licenses (key_hash TEXT PRIMARY KEY, user_id TEXT, product TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, checked_at TEXT)`),
    ]).then(() => undefined).catch((e) => { schemaReady = null; throw e; });
  }
  return schemaReady;
}

/* ---------- crypto ---------- */
const enc = new TextEncoder();
export function b64url(bytes: ArrayBuffer | Uint8Array): string {
  const arr = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let s = '';
  for (const b of arr) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
export function b64urlDecode(text: string): string {
  const pad = text.length % 4 === 0 ? '' : '='.repeat(4 - (text.length % 4));
  return atob(text.replace(/-/g, '+').replace(/_/g, '/') + pad);
}
export async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', enc.encode(value));
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');
}
export function randomToken(bytes = 32): string {
  const buf = new Uint8Array(bytes);
  crypto.getRandomValues(buf);
  return b64url(buf);
}
async function hmac(secret: string, data: string): Promise<string> {
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return b64url(await crypto.subtle.sign('HMAC', key, enc.encode(data)));
}

/* ---------- sessions ---------- */
export async function sessionCookie(env: Env, uid: string): Promise<string> {
  const payload = b64url(enc.encode(JSON.stringify({ uid, exp: Date.now() + SESSION_DAYS * 86400_000 })));
  const sig = await hmac(sessionSecret(env)!, payload);
  return `${SESSION_COOKIE}=${payload}.${sig}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${SESSION_DAYS * 86400}`;
}
export const clearSessionCookie = () => `${SESSION_COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`;

function readCookie(request: Request, name: string): string | null {
  const raw = request.headers.get('cookie') ?? '';
  for (const part of raw.split(';')) {
    const [k, ...v] = part.trim().split('=');
    if (k === name) return v.join('=');
  }
  return null;
}

export async function sessionUserId(request: Request, env: Env): Promise<string | null> {
  const secret = sessionSecret(env);
  if (!secret) return null;
  const cookie = readCookie(request, SESSION_COOKIE);
  if (!cookie) return null;
  const [payload, sig] = cookie.split('.');
  if (!payload || !sig) return null;
  const expected = await hmac(secret, payload);
  if (expected.length !== sig.length || expected !== sig) return null;
  try {
    const data = JSON.parse(b64urlDecode(payload)) as { uid: string; exp: number };
    return data.exp > Date.now() ? data.uid : null;
  } catch {
    return null;
  }
}

/* ---------- users ---------- */
export async function getUser(env: Env, uid: string): Promise<User | null> {
  const row = await env.DB!.prepare('SELECT id, email, name, provider, plan, pro_until, lang, created_at FROM users WHERE id = ?').bind(uid).first<User>();
  if (!row) return null;
  // A subscription that lapsed goes back to free without touching the row.
  if (row.plan === 'pro' && row.pro_until && new Date(row.pro_until).getTime() < Date.now()) row.plan = 'free';
  return row;
}

export async function upsertUser(env: Env, email: string, provider: string, name: string | null, lang: string): Promise<User> {
  const db = env.DB!;
  const now = new Date().toISOString();
  const normalised = email.trim().toLowerCase();
  const existing = await db.prepare('SELECT id FROM users WHERE email = ?').bind(normalised).first<{ id: string }>();
  if (existing) {
    await db.prepare('UPDATE users SET last_login = ?, name = COALESCE(?, name) WHERE id = ?').bind(now, name, existing.id).run();
    return (await getUser(env, existing.id))!;
  }
  const id = randomToken(16);
  await db.prepare('INSERT INTO users (id, email, name, provider, plan, lang, created_at, last_login) VALUES (?, ?, ?, ?, ?, ?, ?, ?)')
    .bind(id, normalised, name, provider, 'free', lang === 'en' ? 'en' : 'es', now, now).run();
  return (await getUser(env, id))!;
}

/* ---------- email (Brevo transactional API) ---------- */
export async function sendMagicLink(env: Env, email: string, link: string, lang: string): Promise<boolean> {
  if (!env.BREVO_API_KEY || !env.MAIL_FROM) return false;
  const es = lang !== 'en';
  const subject = es ? 'Tu enlace para entrar en FX Research Lab' : 'Your sign-in link for FX Research Lab';
  const text = es
    ? `Hola,\n\nEntra en FX Research Lab con este enlace (caduca en 20 minutos y solo sirve una vez):\n\n${link}\n\nSi no has pedido este correo, ignóralo: nadie puede entrar sin él.\n\nFX Research Lab · material educativo, sin señales ni ejecución real.`
    : `Hello,\n\nSign in to FX Research Lab with this link (it expires in 20 minutes and works once):\n\n${link}\n\nIf you did not request this email, ignore it: nobody can sign in without it.\n\nFX Research Lab · educational material, no signals, no live execution.`;
  const html = `<p>${es ? 'Hola,' : 'Hello,'}</p><p>${es ? 'Entra en FX Research Lab con este botón (caduca en 20 minutos y solo sirve una vez):' : 'Sign in to FX Research Lab with this button (it expires in 20 minutes and works once):'}</p>
<p><a href="${link}" style="display:inline-block;padding:12px 20px;background:#c4672b;color:#fff;text-decoration:none;border-radius:8px;font-weight:600">${es ? 'Entrar' : 'Sign in'}</a></p>
<p style="color:#5c6670;font-size:13px">${es ? 'O copia este enlace:' : 'Or copy this link:'} <br><a href="${link}">${link}</a></p>
<p style="color:#5c6670;font-size:13px">${es ? 'Si no has pedido este correo, ignóralo: nadie puede entrar sin él.' : 'If you did not request this email, ignore it: nobody can sign in without it.'}</p>`;
  const response = await fetch('https://api.brevo.com/v3/smtp/email', {
    method: 'POST',
    headers: { 'api-key': env.BREVO_API_KEY, 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ sender: { email: env.MAIL_FROM, name: 'FX Research Lab' }, to: [{ email }], subject, textContent: text, htmlContent: html, tags: ['magic-link'] }),
  });
  return response.ok;
}

/* ---------- rate limiting (per IP, in D1, coarse) ---------- */
export async function tooManyRequests(env: Env, scope: string, ip: string | null, limit: number, windowMinutes: number): Promise<boolean> {
  if (!ip) return false;
  const db = env.DB!;
  const since = new Date(Date.now() - windowMinutes * 60_000).toISOString();
  const key = `${scope}:${(await sha256(ip)).slice(0, 16)}`;
  await db.prepare('CREATE TABLE IF NOT EXISTS hits (key TEXT NOT NULL, at TEXT NOT NULL)').run();
  const row = await db.prepare('SELECT COUNT(*) AS n FROM hits WHERE key = ? AND at > ?').bind(key, since).first<{ n: number }>();
  if ((row?.n ?? 0) >= limit) return true;
  await db.prepare('INSERT INTO hits (key, at) VALUES (?, ?)').bind(key, new Date().toISOString()).run();
  return false;
}
