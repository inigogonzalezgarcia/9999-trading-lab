# Public site (Cloudflare Pages)

The public site is the same React frontend built in **static mode**: it reads precomputed results from
`frontend/public/data/` instead of calling the API. There is no backend in public; the FastAPI tool stays
local (or Docker) for the author.

## Regenerate the published results

```bash
python -m backend.cli export-web                 # all runs in config/web_runs.yaml → frontend/public/data/
python -m backend.cli export-web --only eurusd-2024-v1_1   # one run; the index keeps the rest
```

Each run becomes `data/runs/<id>.json` (trimmed: trades, metrics, equity, M15 chart, rejections, timing,
explainers, quality, reproducibility; no event streams) plus `data/runs/<id>.pdf`, and `data/runs.json` is the
index the site reads. Commit the generated files; they are the content of the site.

## Build locally

```bash
cd frontend && npm ci
npm run build:static          # → frontend/dist (VITE_STATIC_MODE=1)
npm run dev:static            # local preview of the static site
```

## Cloudflare Pages settings

| Setting | Value |
|---|---|
| Production branch | `main` |
| Root directory | `frontend` |
| Build command | `npm ci && npm run build:static` |
| Build output directory | `dist` |
| Environment variable | `VITE_TURNSTILE_SITE_KEY` = Turnstile site key (optional; the form works without it but unprotected) |
| Environment variable (encrypted) | `TURNSTILE_SECRET` = Turnstile secret key (used by the Function) |
| KV namespace binding | `SUBSCRIBERS` → a KV namespace created for the mailing list |
| Node version | 20 or 22 |

## Accounts (Lab Pro area)

`frontend/functions/api/auth/*` and `frontend/functions/api/me.ts` implement sign-in with Google (OAuth 2.0, scopes
email + profile) and by single-use email link (Brevo transactional API), a 30-day signed session cookie, and the
account copy of the simulator progress. The schema is created on first use in a D1 database. Bindings (Pages project
→ Settings):

| Binding / variable | Value |
|---|---|
| D1 database binding `DB` | the `fxlab-accounts` database |
| `SESSION_SECRET` (secret) | long random string (`openssl rand -hex 32`); rotating it signs everyone out |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (secret) | OAuth client "Web application" with redirect URI `https://fx-trading-lab.pages.dev/api/auth/google/callback` |
| `BREVO_API_KEY` (secret), `MAIL_FROM` | Brevo API key and a sender address verified in Brevo |
| `DATA_KEY` (secret) | derives the per-run keys that unlock the encrypted Lab Pro part of the static run files; the same value goes in `secrets/data_key.txt` on the machine that runs `export-web` / `protect-web` |

Without `DB` + `SESSION_SECRET` the `/api/me` endpoint answers `configured: false` and the app area opens without a
session (local previews). Plans: `users.plan` is `free` or `pro` (`pro_until` for subscriptions); the Gumroad
membership hook will set it.

## Lab Pro content in static files

`backend/app/webprotect.py` splits every exported run (except the 2024 demo runs) into the public JSON and an
encrypted part (`runs/<id>.enc`: trade explainers; for research reports the splits, walk-forward folds, Monte Carlo,
benchmark detail and sensitivity) plus `runs/<id>.pdf.enc`. AES-256-GCM, per-run key = SHA-256(DATA_KEY + ":" + id).
`GET /api/runs/:id/key` returns that key to Pro sessions (and to everyone for 2024); `src/api.ts` decrypts in the
browser with WebCrypto and merges. `python -m backend.cli protect-web` processes already exported runs; `export-web`
does it after each run when the key is available.

`frontend/public/_headers` sets the CSP and security headers; `_redirects` serves the SPA. The Pages Function
`frontend/functions/api/subscribe.ts` handles the mailing-list opt-in (Turnstile verification + KV).

## Before launch

- Fill the `OWNER` block in `frontend/src/content/legal.ts` (tax id, address, contact email).
- Create the Turnstile widget (Cloudflare dashboard → Turnstile) and the KV namespace; bind them as above.
- Decide the repository visibility (the site links to it as the source).
