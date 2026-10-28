# Decision log

## 2026-10-07 — Keep strategy status partial

- **Decision:** Strategy and execution remain disabled while any required rule is TBD.
- **Reason:** The discretionary method still leaves pullback, zone boundaries, two-leg thresholds, and fill details unresolved. Inventing these would produce evidence about a different strategy.
- **Status:** Adopted.

## 2026-10-07 — Store internal timestamps at candle close

- **Decision:** Internal candle `timestamp` and `available_at` represent the close/availability time. Source timestamps are converted according to `config/data.yaml`.
- **Reason:** A strategy event must not consume a candle before it is complete. Source files commonly label bar opens; their close availability is one interval later.
- **Status:** Adopted; source-label convention remains configurable and is recorded per import.

## 2026-10-07 — Reject duplicate normalized timestamps

- **Decision:** Reject duplicate candle timestamps after timezone normalization; do not keep an arbitrary row.
- **Reason:** Silently choosing one duplicate can alter price history and reproducibility.
- **Status:** Adopted.

## 2026-10-07 — Research hypotheses are not facts

- **Decision:** Record proposed 2/2 fractals, pullback context, ATR displacement, sweep reclaim, and two-leg protocol with explicit labels.
- **Reason:** These are measurable hypotheses from the prompt and require independent testing; several details remain TBD.
- **Status:** Adopted; dependent signals remain disabled.

## 2026-10-07 — Record Strategy V1 deterministic baseline

- **Decision:** Add `strategy_v1.yaml` as a new version, retaining `strategy_v0_1.yaml` unchanged. Translate the supplied rules into a fully ordered causal sequence, explicit timeouts, state transitions, invalidation reasons, and baseline execution/risk assumptions.
- **Decision:** Keep the runtime status `IMPLEMENTATION_PENDING` until the complete signal/execution engine is implemented and its automated tests pass. Do not label the implementation fully specified prematurely.
- **Decision:** Observation windows use half-open `[start, end)` intervals, per the latest edge-case rules. Window configuration rejects overlaps; event times at the end boundary are excluded.
- **Decision:** Resolve repeated Madrid local observation times to the first occurrence (earlier UTC instant), per user selection. Nonexistent times are recorded as `DST_NONEXISTENT_SKIPPED`.
- **Decision:** Prefer historical provider `spread_pips`; otherwise use only an explicitly configured fixed spread. If neither exists, retain the candidate as `SPREAD_DATA_UNAVAILABLE`, report `NO_SPREAD_DATA`, and block execution. Never invent a spread.
- **Decision:** Emit `DST_AMBIGUOUS_EARLY` with local, UTC, offset, and New York values for repeated local times; emit `DST_NONEXISTENT_SKIPPED` for nonexistent ones. Record the IANA timezone database version for reproducibility.
- **Decision:** Enable TWO_LEG_V1 as the baseline confirmation requirement; equal-high/low levels remain experimental and disabled.
- **Decision:** Do not change prior strategy runs/configuration when introducing V1.
- **Status:** Baseline rules and machine-readable configuration recorded; implementation and causal backtest validation remain pending.

## 2026-10-07 — Apply final edge-case rules

- **Decision:** Use half-open `[start, end)` windows and reject overlapping intervals at configuration load. Evaluate membership using timezone-aware instants converted to Madrid.
- **Decision:** Prefer historical spread, then explicitly configured fixed spread, else preserve the candidate with `SPREAD_DATA_UNAVAILABLE` and report `NO_SPREAD_DATA` without execution.
- **Decision:** Emit `DST_AMBIGUOUS_EARLY` and `DST_NONEXISTENT_SKIPPED`, recording local time, resolved UTC time, offset, and New York time. Include the IANA timezone database release in API output.
- **Status:** Edge-case rules and helper tests added; full V1 state machine remains implementation-pending.

## 2026-10-07 — Enforce the implementation completion gate

- **Decision:** Keep `config/strategy_v1.yaml` at `IMPLEMENTATION_PENDING` until the checklist in `docs/IMPLEMENTATION_COMPLETION_GATE.md` is fully satisfied.
- **Implementation:** Add 01:50 causal daily contexts, level and zone lifecycle events, candidate rejection metadata, deterministic configuration hashes, source fingerprints, synthetic positive/negative cases, and API-path tests.
- **Reason:** Current synthetic positive coverage starts from a confirmed sweep and the API tests inject controlled candidates. The raw M1-to-complete-signal path and the full active-zone inventory are not yet demonstrated.
- **Status:** 35 automated tests pass. Backtest remains blocked pending the two remaining gate items; no historical performance output is enabled.

## 2026-10-07 — Activate Strategy V1 after raw-M1 gates pass

- **Decision:** Mark Strategy V1 `FULLY_SPECIFIED` and enable the historical research backtest API after every completion-gate item passed.
- **Verification:** A raw-M1-only fixture builds the 01:50 `DailyContext`, retains its active confirmed zone while the setup is incomplete, excludes mitigated/invalidated/expired zones, and produces the same context from data truncated at the cutoff. The same fixture independently derives the complete H1-bias-to-BOS sequence and an executable M1 trade; removing the sole M1 sweep-breach candle removes the candidate.
- **Test result:** 38 tests pass, including both raw-M1 gates. Synthetic results validate implementation only and do not establish market performance.
- **Scope:** Historical research/backtesting only. No broker connection or live order execution is enabled.
- **Status:** Adopted; out-of-sample evaluation, walk-forward analysis, and research benchmarks remain future work.

## 2026-10-15 — Educational positioning, performance, research protocol

- **Decision:** Position the platform explicitly as an educational research tool. The notice lives in
  `service.EDUCATIONAL_NOTICE`, is returned by `/api/notice`, embedded in every result payload, shown in the
  UI banner and written into CSV exports; `DISCLAIMER.md` carries the bilingual legal text. No signals,
  alerts or live execution will ever be added.
- **Decision:** Split `strategy_v1.py` (869 lines) into `backend/app/strategy/` by causal layer and rewrite
  hot paths on numpy arrays. Verified bit-identical output against the previous engine on a labelled synthetic
  one-month dataset (candidates and full portfolio result). One year of M1 now runs in seconds instead of
  hours.
- **Bug fixed:** candidates without an executable entry (`DATA_GAP`, no next M1) carry `None` as execution
  time; the portfolio sort compared `None` with strings and crashed on long datasets. Sorting now falls back
  to signal/confirmation time. Found by the synthetic stress run; previously masked by short fixtures.
- **Bug fixed:** Sharpe/Sortino annualised per-trade R with √252. Replaced by `metrics.py`: per-trade
  statistics unannualised; annualised figures from the daily R series.
- **Decision:** Daily 01:50 contexts accept `preparation.context_lookback_days` (`full` | `lookback:N` |
  `none` at run level). Contexts are audit artefacts and never feed execution; the default `lookback:30`
  keeps year-long runs under a few minutes. `full` remains available and exact.
- **Decision:** Add `research.py` (splits, walk-forward, Monte Carlo, sensitivity, cost-matched random
  benchmark) wired to CLI and `/api/jobs/research`. Period slices use warm-up history; results can differ from
  the same dates inside a full run because V1 liquidity levels have no expiry — recorded as a known property
  of the hypothesis, not a defect of the harness.
- **Open question (strategy, not software):** liquidity levels never expire, so swings from months earlier
  remain eligible sweep targets. Whether V1 should cap level age is a strategy-version decision for V1.1.
- **Decision:** Persist runs in SQLite (`store.py`), run long jobs in process with progress (`jobs.py`), cap
  uploads (`FXLAB_MAX_UPLOAD_MB`), read CORS from the environment, serve the built UI from the API in the
  Docker image. No authentication: intended use is local/educational; public deployments must sit behind the
  platform's access controls.
- **Decision:** Data acquisition via `ingest.py` (HistData generic ASCII in EST without DST; Dukascopy CSV
  exports; Dukascopy `.bi5` tick feed aggregated to bid M1 with per-minute median spread). Synthetic candles
  are never created.
- **Status:** 60 tests pass (engine gates, DST, execution, metrics, research, ingest, API, service). Real
  provider data has not been run yet; the first real run and its research report are the next step and must
  precede any public claim.

## 2026-10-16 — First real-data run and what it changes

- **Record:** Dukascopy EUR/USD 2024 ticks aggregated to M1 with historical spreads (dataset
  `65a7a807…cde62d`). Baseline: 3 138 candidates, 300 complete setups, 5 trades, −2.61R. Details in
  `docs/FIRST_REAL_RUN.md`.
- **Decision:** Treat the result as a property of the hypothesis, not of the harness. The software stays
  unchanged in its rules; V1.1 questions are logged as open strategy decisions: window placement (the pattern
  completes mostly at the London and New York opens), stop reference (135 of 136 window-valid setups rejected
  for stop > 3 ATR when anchored at the sweep extreme), and liquidity level expiry.
- **Decision:** Add hour-of-day timing histograms to every backtest report and labelled session experiments
  to the sensitivity study, so the tool itself shows whether a window fits the market. Experiments are never
  reported as the baseline.
- **Decision:** Support browser-saved `.bi5` bundles (`convert bundle`) for machines without shell network;
  Dukascopy throttles with HTTP 503 above ~2 concurrent requests, so the downloader paces itself.
- **Status:** 51 offline tests pass; API tests still require fastapi locally. Educational positioning
  unchanged.

## 2026-10-16 — V1.1 experiment implemented; V1 frozen

- **Decision:** Implement the three open decisions as engine parameters with V1-preserving defaults
  (`stop.reference` sweep_extreme | zone_distal | leg1_origin, `stop.buffer_atr`, `stop.max_distance_atr`,
  `liquidity.level_max_age_m15_bars`, strategy-level `execution.session_end`), verified bit-identical on the
  stress dataset, and activate them only in `config/strategy_v1_1.yaml` (London 09:00–10:30 windows, zone
  distal stop, 1 920-bar level expiry). The CLI/API/UI select the strategy file; `strategy_v1.yaml` remains
  the default and is never edited.
- **Result (EURUSD 2024):** 12 trades, +2.35R, random-benchmark percentile 75.5 %, OOS slice 1 trade,
  sign flips under neighbouring parameters. Recorded as *not evidence*; see `docs/FIRST_REAL_RUN.md`.
- **Decision:** Sensitivity grid now includes stop reference, stop max distance and level expiry so every
  future version reports its own fragility.
- **Decision:** PORTFOLIO mode made usable: the loader treats `symbol` columns per symbol (duplicates, order,
  gaps), and `python -m backend.cli merge` stacks single-symbol CSVs. GBPUSD 2024 downloaded for the first
  two-symbol run.
- **Open for V1.2 (strategy):** stop placement relative to entry is the binding constraint (110/204 complete
  setups rejected at 3 ATR); and multi-year data before any claim.

## 2026-10-22 — Explainability and product surface (v0.4.0)

- **Decision:** Every trade must be explainable on its own chart. The explainer is derived only from the
  events the engine already emits (no rule is recomputed in the UI or the PDF), so what the learner sees is
  exactly what the engine did. Explainers are stored with the run; older runs show a "re-run" hint instead.
- **Decision:** The method and the legal notice live inside the app (ES/EN), not only in the repository, so a
  web visitor meets the educational framing before any number.
- **Decision:** PDF reports are server-side and carry the notice, dataset hash, config hash and software
  revision on the cover; a report without its reproducibility block is not a report.
- **Decision:** Time breakdowns use the strategy reference timezone recorded on each trade. Buckets with few
  trades are shown with their count and must not be read as evidence.
- **Decision:** Instrument specifications move to `config/instruments.yaml`; a strategy may only trade the
  instruments it lists. Pip size is per symbol in the simulator (JPY pairs 0.01).
- **Status:** V1 output bit-identical to 0.3.0; offline suite extended (explainers, PDF, instruments, metrics
  breakdowns).

## 2026-10-28 — Public site as an educational simulator (v0.5.0)

- **Decision:** The product is "learn to test a trading idea with method", never the strategy. The public site
  shows the lab's real results (including negative ones), explains every trade and teaches the protocol; it
  does not run anything live and never will.
- **Decision:** No backend in public. Cloudflare Pages serves precomputed, trimmed results (`export-web`);
  the FastAPI tool stays local/Docker for the author. Reasons: no auth surface, no CPU bill, no uploads from
  strangers, and the results shown are exactly the ones in the repository.
- **Decision:** Lessons are built on real runs via widgets that read the same JSON the lab uses, so a lesson
  can never quote a number the lab does not show.
- **Decision:** Mailing list stored in Cloudflare KV by a Pages Function with Turnstile; consent evidence
  (timestamp, source page, hashed IP) kept per GDPR art. 7; no third-party email tool until there is a list.
- **Decision:** Legal pages (notice, privacy, cookies, terms) ship with the site, ES/EN, with the owner block
  to be completed before launch; paid products, when they exist, go through a merchant of record.
- **Status:** 63 offline tests; `tsc` clean; static build verified on the author's machine / Pages.
