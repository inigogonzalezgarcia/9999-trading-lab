# Changelog

## 0.3.0 — 2026-10-16

- Strategy V1.1 experiment (`config/strategy_v1_1.yaml`): London-open windows, zone-distal stop, liquidity
  level expiry. Engine parameters default to V1 behaviour (bit-identical); `--strategy` / form field /
  UI selector choose the configuration.
- Sensitivity grid covers stop reference, stop max distance and level expiry.
- PORTFOLIO mode: symbol-aware loader checks, `merge` CLI command, GBPUSD 2024 run.
- `docs/FIRST_REAL_RUN.md` extended with the V1.1 comparison and its fragility table.

## 0.2.1 — 2026-10-16

- First real-data run: Dukascopy EUR/USD 2024 ticks (20.7M) → 372 774 M1 bars; report in `docs/FIRST_REAL_RUN.md`.
- `ingest.read_bi5_bundle` / `convert bundle`: decode monthly `.bi5` bundles saved by a browser.
- Report `timing`: hour-of-day histograms of sweep confirmations and complete setups (UI section).
- Sensitivity study accepts labelled multi-key variants; default grid adds London/New York session experiments.

## 0.2.0 — 2026-10-15

- Engine split into `backend/app/strategy/` with numpy hot paths; bit-identical output, ~40× faster.
- Fixed crash sorting candidates without execution time; fixed per-trade Sharpe annualisation.
- New `metrics.py` (per-trade vs daily-series statistics, equity curve) and `research.py` (splits,
  walk-forward, Monte Carlo, sensitivity, cost-matched random benchmark).
- Data acquisition: HistData and Dukascopy converters, Dukascopy tick downloader, labelled stress generator.
- SQLite run history, background jobs with progress, upload limits, CORS/env configuration, CSV/JSON exports.
- CLI (`python -m backend.cli`): fetch, convert, validate, backtest, research, runs, stress.
- React dashboard: KPI tiles, equity curve, candles with trade markers, sortable trades, rejection breakdown,
  research report, history, print-to-PDF; pinned dependencies.
- Educational notice embedded in API, results, UI and exports; `DISCLAIMER.md`; documentation synchronised;
  CI with Python matrix, ruff, frontend build and Docker build; pinned Python requirements.

## 0.1.0 — 2026-10-07

- Initial scaffold: data import and quality checks, UTC/DST handling, Strategy V1 specification and causal
  engine with completion gates, minimal API and UI.
