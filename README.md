# FX Research Lab

Local-first, **educational** research and backtesting platform for a deterministic intraday FX hypothesis
(EUR/USD and GBP/USD, Madrid-session observation windows). Strategy V1 is fully specified in software and runs
causal historical backtests with recorded costs; a research protocol (independent periods, rolling
out-of-sample, Monte Carlo, parameter sensitivity, cost-matched random benchmark) tells you whether a result
deserves any trust.

> **Educational research tool.** No broker connection, no live execution, no signals. Simulated historical
> results are not evidence of a profitable edge and historical performance does not guarantee future results.
> The author is not a financial adviser. See [DISCLAIMER.md](DISCLAIMER.md).

## What you get

| Layer | What it does |
|---|---|
| Data | CSV/Parquet import with quality report (duplicates, gaps, weekends, spread), UTC normalisation, DST-aware schedule. Converters for **HistData** and **Dukascopy** (CSV exports and raw tick feed). |
| Engine | Causal V1 state machine (H1 bias → M15 pullback → liquidity sweep → zone → displacement → two legs → BOS → M1 entry) with spread, slippage, commission, session expiry and portfolio risk limits. ~15 s per year of M1 data. |
| Research | Chronological splits, walk-forward folds, Monte Carlo bootstrap, one-at-a-time sensitivity, random entries with identical costs. |
| Persistence | SQLite run history with compressed full results; CSV/JSON export. |
| UI | React dashboard: KPI tiles, equity curve, M15 candles with entry/exit markers, sortable trades, **per-trade explainer** (M1 candles with sweep, zone, legs, BOS, entry, stop, exit), R by hour/weekday/month, rejection breakdown, research report, run history, bilingual notice/method page. |
| Reports | Server-generated PDF (cover with notice and reproducibility hashes, data, results, breakdowns, sensitivity, limitations): `GET /api/runs/{id}/report.pdf` or `python -m backend.cli report`. |
| Instruments | `config/instruments.yaml` (pip size, Dukascopy scale, contract size) for 11 majors/crosses incl. JPY pairs; each strategy lists which it may trade. |
| CLI | `python -m backend.cli …` for data download/conversion, validation, backtests, research and history without the UI. |

## Quick start

Python 3.11+ and Node.js 20+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
(cd frontend && npm install)

uvicorn backend.app.main:app --reload --port 8000     # API + docs at http://localhost:8000/docs
cd frontend && npm run dev                              # UI at http://localhost:5173
```

Or `docker compose up` (dev) / `docker compose --profile prod up lab` (single container serving API + UI).

## Getting real data

The engine needs **M1 bars with UTC bar-open timestamps** and, ideally, a `spread_pips` column.

```bash
# Dukascopy tick feed → M1 bid bars with per-minute median spread (needs network)
python -m backend.cli fetch dukascopy --symbol EURUSD --start 2024-01-01 --end 2024-07-01 --out data/raw/EURUSD_2024H1.csv

# HistData.com "Generic ASCII" M1 download (EST without DST; no spread → use a fixed fallback)
python -m backend.cli convert histdata data/raw/DAT_ASCII_EURUSD_M1_2024.csv data/raw/EURUSD_2024.csv --symbol EURUSD

# Dukascopy CSV exports (bid + ask) → spread derived from ask-bid at bar open
python -m backend.cli convert dukascopy bid.csv data/raw/EURUSD.csv --ask ask.csv --symbol EURUSD

# Monthly .bi5 bundles saved by a browser (when the shell has no network; see DATA_SPEC.md)
python -m backend.cli convert bundle fxlab_EURUSD_2024-01.bundle data/raw/EURUSD_2024.csv --more fxlab_EURUSD_2024-0{2..9}.bundle --symbol EURUSD

python -m backend.cli validate data/raw/EURUSD_2024.csv
```

Without historical spreads, set `spread.fixed_fallback_pips` in `config/execution.yaml` or pass
`--fixed-spread-pips 0.9`; otherwise candidates are kept as `SPREAD_DATA_UNAVAILABLE` and never traded. The
spread source is recorded in every result.

## Running research

```bash
python -m backend.cli backtest data/raw/EURUSD_2024.csv --symbol EURUSD --out results/EURUSD_2024.json
python -m backend.cli research data/raw/EURUSD_2024.csv --symbol EURUSD --out results/EURUSD_2024_research.json
python -m backend.cli backtest data/raw/EURUSD_2024.csv --symbol EURUSD --strategy strategy_v1_1.yaml   # logged experiment
python -m backend.cli merge EURUSD=data/raw/EURUSD_2024.csv GBPUSD=data/raw/GBPUSD_2024.csv --out data/raw/PORTFOLIO_2024.csv
python -m backend.cli backtest data/raw/PORTFOLIO_2024.csv --symbol PORTFOLIO
python -m backend.cli runs list
```

Strategy versions live in `config/strategy_*.yaml`. `strategy_v1.yaml` is the frozen baseline; `strategy_v1_1.yaml`
is the experiment derived from the first real run. New versions are new files, never edits.

Both commands persist to the SQLite history (`FXLAB_DB`, default `data/fxlab.sqlite3`) unless `--no-save`.
The UI runs the same pipeline: small files synchronously, larger ones as background jobs with progress.

Dataset format, timestamps and the loader's rules are in [DATA_SPEC.md](DATA_SPEC.md). The strategy rules are
in [docs/STRATEGY_SPEC.md](docs/STRATEGY_SPEC.md) with machine-readable defaults in `config/strategy_v1.yaml`
and costs in `config/execution.yaml`. Research safeguards: [RESEARCH_METHOD.md](RESEARCH_METHOD.md) and
[BACKTESTING.md](BACKTESTING.md). Architecture: [ARCHITECTURE.md](ARCHITECTURE.md).

### Daily 01:50 contexts

The per-day preparation snapshot replays history at 01:50 Madrid for audit. `full` is exact but quadratic in
the number of trading days; `lookback:30` (default) caps the replayed history; `none` skips it. Trades never
depend on this setting — execution always uses the complete causal candidate pass.

## Tests and quality gates

```bash
python -m pytest            # ~60 tests: causality gates, DST, execution, metrics, research, ingest, API
ruff check backend tests scripts
cd frontend && npm run build
```

CI (GitHub Actions) runs the Python matrix, ruff, the frontend build, a one-month synthetic engine smoke run
with a time limit, and the Docker image build.

## Status

- Implemented: data import and quality checks, UTC/DST handling, V1 engine with causal gates, metrics
  (per-trade, daily-series and by hour/weekday/month), research protocol, SQLite history, background jobs,
  CLI, dashboard with trade explainers and method page, PDF reports, multi-instrument specs, Docker.
- First real-data runs done on Dukascopy EUR/USD 2024 ticks (see `docs/FIRST_REAL_RUN.md`). The baseline
  triggers very rarely in its 02:15–04:15 Madrid windows; the pattern completes mostly at the London and New
  York opens. Publish nothing as evidence before the research protocol has been run on independent periods.
- Not implemented: multi-user authentication, alerts, broker connectivity (deliberately never).

## Customisation and contact

Questions or customisation requests: [contact form](https://inigogonzalezgarcia.github.io/about.html#contacto)
or LinkedIn (linked from [inigogonzalezgarcia.github.io](https://inigogonzalezgarcia.github.io/)).

MIT License — see [LICENSE](LICENSE) and [DISCLAIMER.md](DISCLAIMER.md).
