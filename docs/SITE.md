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

`frontend/public/_headers` sets the CSP and security headers; `_redirects` serves the SPA. The Pages Function
`frontend/functions/api/subscribe.ts` handles the mailing-list opt-in (Turnstile verification + KV).

## Before launch

- Fill the `OWNER` block in `frontend/src/content/legal.ts` (tax id, address, contact email).
- Create the Turnstile widget (Cloudflare dashboard → Turnstile) and the KV namespace; bind them as above.
- Decide the repository visibility (the site links to it as the source).
