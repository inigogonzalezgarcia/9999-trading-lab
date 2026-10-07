# Strategy V1 implementation completion gate

Strategy V1 reached `FULLY_SPECIFIED` on 2026-10-07 after every required software behavior below passed. This gate adds no trading rules; it verifies causal execution, persistence, reproducibility, and tests for the rules already defined in [STRATEGY_SPEC.md](STRATEGY_SPEC.md).

## Required implementation

- [x] Build a per-symbol daily context at 01:50 `Europe/Madrid` using only candles closed by that instant. Include confirmed H1/M15 structure, H1 bias, known liquidity, dataset hash, strategy/config hashes, and timezone database version.
- [x] Include the complete inventory of valid active supply/demand zones in the daily context. A raw-M1 fixture proves an active confirmed zone is retained while its setup is still developing, future candles do not change the 01:50 snapshot, and mitigated, invalidated, and expired zones are excluded.
- [x] Persist liquidity-level transitions as causal events: `ACTIVE`, `TOUCHED`, `SWEPT`, and `INVALIDATED`; use M1 for breach and M15 close for confirmation.
- [x] Persist zone creation, confirmation, mitigation, invalidation, and expiry timestamps. A mitigated zone is not reused as fresh.
- [x] Preserve generated setup candidates, their event sequences, normalized rejection reasons, and rejection timestamps through the portfolio result and API.
- [x] Verify the complete raw-data-to-signal path with a positive synthetic fixture. The fixture contains only M1 bars; the engine derives H1/M15 structure and generates all required setup transitions, a valid M1 entry, and an executed research trade. Removing the sole M1 sweep-breach candle removes the complete candidate.
- [x] Verify synthetic negative cases for bias invalidation, sweep-extreme invalidation, zone invalidation/mitigation/expiry, two-leg timeout, BOS timeout, entry-window rejection, missing spread, execution gaps, symbol/global risk limits, and concurrent-position rejection.
- [x] Verify stable IDs, context/config hashes, deterministic event ordering, and repeatable synthetic results.
- [x] Verify the API pending-state blocked path and API candidate/trade paths with synthetic uploads. Missing spread remains a research candidate and cannot become a trade; the configured `FULLY_SPECIFIED` path now enables historical research backtests.
- [x] Record dataset/config hashes, strategy version/config, execution model, spread labels, slippage/commission assumptions, timezone database version, date range, and software-source fingerprint in API reproducibility metadata.
- [x] Cover DST ambiguity/nonexistence, Madrid/New York conversions, half-open windows, candle-close availability, and fractal confirmation causality.

## Activation record

- **Activated:** 2026-10-07. All checklist items are verified; `config/strategy_v1.yaml` is `FULLY_SPECIFIED`, and the API may run historical research backtests.
- **Scope:** This activates software behavior only. Synthetic results validate causal implementation; they are not market-performance evidence. The platform remains research-only with no broker connection or live execution.
