# Architecture

Local-first Python service with a React dashboard. Research only: there is no broker connection and no live
execution anywhere in the code base.

```
backend/app/
  data.py          ingestion, validation, UTC candle-close normalisation, aggregation, causal access
  ingest.py        HistData / Dukascopy converters and the Dukascopy tick downloader → canonical CSV
  timezones.py     IANA conversion, observation windows, DST-aware schedule
  models.py        validated domain entities
  strategy/        the V1 engine, split by causal layer
    frames.py      numpy views over candle frames (timestamps, OHLC, true range, block min/max search)
    structure.py   fractal swings, ATR, H1 bias, pullback qualification
    liquidity.py   level history and ACTIVE/TOUCHED/SWEPT/INVALIDATED lifecycle
    zones.py       zone lifecycle from completed M15 candles
    candidates.py  sweep detection and the sweep → displacement → two legs → BOS state machine
    simulation.py  deterministic M1 execution with spread/slippage/commission/session expiry
    portfolio.py   daily 01:50 contexts, portfolio limits, run_v1_portfolio
  strategy_v1.py   public facade (stable import surface; routes candidate generation for tests)
  execution.py     spread resolution (historical → explicit fixed → blocked)
  metrics.py       per-trade statistics and daily-series annualised statistics, equity curve
  research.py      splits, walk-forward, Monte Carlo, sensitivity, cost-matched random benchmark
  service.py       orchestration shared by API, CLI and jobs; educational notice; reproducibility block
  store.py         SQLite run history (compressed full results + summaries)
  jobs.py          in-process background jobs with progress
  main.py          FastAPI boundary: uploads, sync/async runs, history, exports, static UI
  stress.py        labelled synthetic data for performance testing only
backend/cli.py     command-line entry point
config/            versioned YAML: data semantics, execution costs, strategy_v0_1 (preserved), strategy_v1
frontend/          Vite + React + lightweight-charts dashboard
tests/             pytest suite (causality gates, DST, execution, metrics, research, ingest, API, service)
```

**Flow.** import → validate/report → normalise timestamps to UTC close → schedule resolution → candidate
generation on the full M1 history (M15/H1 derived causally) → execution simulation under portfolio limits →
metrics → persistence → UI/CLI. The research protocol wraps the same engine over period slices.

**Causality.** A candle exists only after its close; pivots appear on their confirmation candle; windows are
half-open `[start, end)` in Madrid time; DST gaps/folds are reported, never guessed. Daily 01:50 contexts replay
only history available at that instant (`full`), or a capped lookback for long datasets; they are an audit
artefact and never feed execution.

**Performance.** Hot paths run on numpy arrays. One year of M1 (~380k rows) takes ~8 s for candidates and
~15 s for a full portfolio run without daily contexts (Apple Silicon / recent x86). The historical
`strategy_v1.py` monolith was replaced by the package above with bit-identical output on a labelled
synthetic stress dataset.

**Persistence and jobs.** SQLite (`FXLAB_DB`) stores every run's summary and zlib-compressed full result.
Background jobs live in process (progress polling) and are lost on restart; persisted runs are not.

**Deployment.** `Dockerfile` builds the UI and serves it from the FastAPI process. `deploy/render.yaml` and
`deploy/fly.toml` are starting points. Limits: `FXLAB_MAX_UPLOAD_MB`, `FXLAB_JOB_WORKERS`,
`FXLAB_CORS_ORIGINS`. There is no authentication; keep public deployments behind your platform's access
controls or run locally (the intended, educational use).

See `docs/STRATEGY_SPEC.md` for the rule register and `docs/DECISION_LOG.md` for decisions.
