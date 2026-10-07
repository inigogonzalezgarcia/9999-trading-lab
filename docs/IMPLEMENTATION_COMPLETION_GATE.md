# Strategy V1 implementation completion gate

Strategy V1 must remain `IMPLEMENTATION_PENDING` until every required software behavior below is implemented and verified. This gate adds no trading rules; it requires causal execution, persistence, reproducibility, and tests for the rules already defined in [STRATEGY_SPEC.md](STRATEGY_SPEC.md).

## Required implementation

- [x] Build a per-symbol daily context at 01:50 `Europe/Madrid` using only candles closed by that instant. Include confirmed H1/M15 structure, H1 bias, known liquidity, dataset hash, strategy/config hashes, and timezone database version.
- [ ] Include the complete inventory of valid active supply/demand zones in the daily context. The current inventory is derived only from completed setup candidates and can omit a zone whose two-leg/BOS sequence is still developing.
- [x] Persist liquidity-level transitions as causal events: `ACTIVE`, `TOUCHED`, `SWEPT`, and `INVALIDATED`; use M1 for breach and M15 close for confirmation.
- [x] Persist zone creation, confirmation, mitigation, invalidation, and expiry timestamps. A mitigated zone is not reused as fresh.
- [x] Preserve generated setup candidates, their event sequences, normalized rejection reasons, and rejection timestamps through the portfolio result and API.
- [ ] Verify the complete raw-data-to-signal path with a positive synthetic fixture. Current positive tests exercise the causal post-sweep candidate builder and execution path, while the portfolio/API tests inject a controlled candidate; they do not yet prove that raw M1 bars generate the entire H1-bias-to-sweep sequence.
- [x] Verify synthetic negative cases for bias invalidation, sweep-extreme invalidation, zone invalidation/mitigation/expiry, two-leg timeout, BOS timeout, entry-window rejection, missing spread, execution gaps, symbol/global risk limits, and concurrent-position rejection.
- [x] Verify stable IDs, context/config hashes, deterministic event ordering, and repeatable synthetic results.
- [x] Verify the API blocked path and API candidate/trade paths with synthetic uploads. Missing spread remains a research candidate and cannot become a trade.
- [x] Record dataset/config hashes, strategy version/config, execution model, spread labels, slippage/commission assumptions, timezone database version, date range, and software-source fingerprint in API reproducibility metadata.
- [x] Cover DST ambiguity/nonexistence, Madrid/New York conversions, half-open windows, candle-close availability, and fractal confirmation causality.

## Activation rule

Do not enable the strategy backtest or change `config/strategy_v1.yaml` to `FULLY_SPECIFIED` while any required item remains unchecked. The active API gate must continue returning no trades or performance metrics in that state.

After every item passes, record the activation in this document, `STRATEGY_SPEC.md`, `DECISION_LOG.md`, the versioned configuration, and the test suite. Synthetic results validate software behavior only; they are not market-performance evidence.
