# Strategy specification

## Status and authority

This document and [`config/strategy_v0_1.yaml`](config/strategy_v0_1.yaml) are the single source of truth for the strategy engine. Version `strategy_v0_1` is **PARTIALLY_SPECIFIED**. It records the defined scope and unresolved rules without substituting invented definitions. The engine must not generate or backtest trades while required fields remain TBD. A report from data validation alone is not evidence about strategy performance.

## Defined scope

- Instruments: EUR/USD and GBP/USD, tested independently before any combined result.
- Reference timezone: `Europe/Madrid`; market analysis timezone: `America/New_York`. Use IANA timezone data; never fixed offsets.
- Daily preparation point: exactly 01:50 Madrid. It is preparation only and cannot open a trade.
- Discrete observation points: exactly 02:30, 03:30, and 04:00 Madrid. No tolerance is allowed in this version. Any tolerance or continuous monitoring requires a later explicit configuration/version.
- Preparation uses H1 external and M15 internal context: structure, directional bias, liquidity, and supply/demand areas.
- A long conceptually requires downside liquidity → sweep → demand interaction → bullish confirmation. A short conceptually requires upside liquidity → sweep → supply interaction → bearish confirmation.
- Permitted confirmation families are BOS and two-leg; their rules are unresolved below.

For every applicable local date, scheduled observation instants are localized using `Europe/Madrid` and converted to UTC and `America/New_York`. Never calculate the New York time from a hard-coded offset. Store both local timestamps with every future signal and trade.

## Explicitly unresolved (TBD)

The following fields are `null`/TBD in the configuration. Do not infer defaults:

- Swing high/low definition; minimum bars; fractal/lookback; equal highs/lows; wick versus close; minimum displacement.
- H1 external structure algorithm; M15 internal structure algorithm; structure classifications; exact H1/M15 bias relationship.
- Liquidity ranking/relevance beyond the supported swing-high and swing-low types. Previous-day/session/equal highs and lows are excluded from baseline pending approval.
- Sweep confirmation, penetration threshold, and reclaim rule.
- Supply/demand origin candles, boundaries, wick/body treatment, displacement, freshness, age, mitigation, invalidation, concurrent zones, and maximum distance/sequence relationship to liquidity.
- BOS break source, wick/close rule, threshold, timeframe, pre-sweep structural-point requirement, and timeout.
- Two-leg first leg, retracement, second leg, structural relationship, entry, and timeout.
- Entry trigger/fill model selected for the strategy; stop model; target model; risk per trade; maximum trades/day; setup expiry; invalidation rules; news filter.
- Observation tolerance remains zero in the baseline; any nonzero tolerance is TBD.

Configurable execution cost fields exist for spread, slippage, and commission. Their values are test assumptions, not market facts; comparisons should include optimistic, base, and conservative scenarios before any robustness claim.

## Required event and trade provenance

Signals must store `signal_timestamp`, `latest_candle_timestamp_used`, and `data_available_at_decision`, all timezone-aware, plus Madrid and New York representations. Trade records must provide: `trade_id`, strategy version, symbol, date, timezone, observation window, direction, H1/M15 bias, liquidity type/price, sweep timestamp/price, zone type/high/low/timestamp, confirmation type/timestamp, entry timestamp/price, stop, target, risk amount, position size, spread, slippage, commission, exit timestamp/price/reason, PnL, R multiple, MFE, and MAE. Unknown fields remain null; they must not be fabricated.

## Causality and evaluation

Only completed candles are available. A pivot requiring later bars cannot be exposed before those bars close. Removing candles after a decision timestamp must not change signals generated at or before that timestamp. Do not create signals in this partially specified version.

Once a fully specified version exists, evaluation must include global and breakdown results (symbol, observation point, direction, confirmation, year, month), a cost-matched randomized-entry benchmark, configured in-sample/validation/out-of-sample splits, rolling walk-forward results, at least 1,000 trade-order Monte Carlo simulations, parameter sensitivity, and explicit limitations. Any classification must use `INSUFFICIENT_EVIDENCE`, `PROMISING`, `ROBUST`, `OVERFIT_RISK`, or `FAILED`; none guarantees future profitability.

Historical performance does not guarantee future results. The research goal is to test reproducible evidence, not to make a strategy look profitable.
