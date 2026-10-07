# Strategy V1 specification

## Status and research scope

V1 is a deterministic baseline research hypothesis, not proprietary ICAP methodology and not a claim of profitability. Its rules are defined in `config/strategy_v1.yaml`; the code must remain `IMPLEMENTATION_PENDING` until the full causal state machine and execution model pass their automated tests. Only then may the runtime report `FULLY_SPECIFIED`. No parameter may be optimized against the complete historical sample before the baseline is established. Every run records the exact strategy and execution configurations, data hash, date range, timezone choices, and software revision.

The platform is historical research only. It has no broker connection or live execution.

## Clock, daily context, and observation windows

- Store event and candle times in UTC. Render local times using `Europe/Madrid` and `America/New_York` IANA zones.
- At 01:50 Madrid, build context independently for EURUSD and GBPUSD from only candles closed by that instant: H1/M15 structure, known eligible liquidity, active zones, trading date, and active strategy version. Preparation cannot trade.
- Scheduled observations are 02:30, 03:30, and 04:00 Madrid. Their respective windows are 02:15–02:45, 03:15–03:45, and 03:45–04:15. Both endpoints are included, as selected for V1; 03:45 belongs to both adjacent windows. An event ID can be executed only once even if it is associated with both windows.
- Monitor M1 continuously inside each window. These are observation windows, not guaranteed fills. Select the first fully valid candidate chronologically in each window; once a symbol has an execution in a window, reject further executions for that symbol/window.
- Record scheduled observation, actual signal, and actual execution timestamps. Entry must occur inside an active window. A setup whose BOS occurs outside a window remains a candidate marked `NOT_TRADEABLE`.
- A nonexistent local observation is `SKIPPED_DST_NONEXISTENT`, with no fabricated instant. For an ambiguous fall-back time, use its first occurrence (earlier UTC instant), and record the policy, UTC instant, and New York instant. Reports enumerate skipped and resolved observations.

## Structure, bias, and pullback

- H1 and M15 pivots use strict wick fractals with two bars on each side. Ties are not pivots. A pivot is available only when the second right-hand candle closes.
- H1 bullish bias requires the latest relevant confirmed sequence to establish a higher low followed by a higher high; bearish is lower high followed by lower low. A confirmed opposite structural break invalidates that sequence. Otherwise classify `RANGE` or `UNDEFINED`, neither tradeable.
- Longs require bullish H1 and a corrective bearish M15 pullback. Shorts require bearish H1 and a corrective bullish M15 pullback. A pullback qualifies by at least two confirmed countertrend structural swings or a countertrend displacement of at least 0.50 ATR(14, M15). One countertrend candle alone is insufficient.
- A confirmed M15 close through the H1 premise (below the active H1 higher-low premise for longs, above the active H1 lower-high premise for shorts) invalidates the bias and cancels dependent setups. Structure and bias are recomputed causally from the history available at each close.

## Liquidity and sweeps

- Baseline liquidity consists of confirmed H1 and M15 swing highs/lows. Priority is H1 then M15. Equal H1 and M15 levels rank after those but remain disabled experimental features in baseline V1.
- Two levels cluster when their distance is at most 0.10 × ATR(14, M15) measured at cluster creation. Cluster price is the arithmetic mean. Freeze the ATR and constituent levels; never regroup using future volatility. For overlapping levels, prefer H1; within a timeframe prefer the older confirmed level. A swept level cannot be the primary target of another setup.
- Level states are `ACTIVE`, `TOUCHED`, `SWEPT`, or `INVALIDATED`. A touch alone is not a sweep. A level at or through its price becomes touched; only the close-back rule confirms swept status.
- Sell-side sweep: an M1 trade at or below active low liquidity, followed by the containing completed M15 candle closing above the level. Buy-side is the inverse. Breach time is the first M1 breach; confirmation time is the M15 close. A level must have been confirmed before breach.
- No minimum sweep depth. Record absolute distance of the sweep extreme beyond the level and distance divided by the frozen M15 ATR(14); do not filter on depth in V1.

## Zones and displacement

- Demand source is the last bearish M15 candle immediately before qualifying bullish displacement; supply is the last bullish candle immediately before qualifying bearish displacement. If several consecutive opposite candles precede the move, use the final one.
- Demand boundaries are proximal=source close and distal=source low. Supply boundaries are proximal=source close and distal=source high.
- Displacement is a directional M15 move of at least 1.00 × ATR(14), after the relevant sweep, that breaks relevant M15 structure or satisfies the BOS definition. At the start, freeze ATR from the latest M15 candles already closed before the first displacement candle. Record start/end, size, ATR multiple, direction, and structure broken; do not update that event's ATR while it forms.
- The nearest zone edge must be no farther than 1.00 × frozen M15 ATR from the sweep extreme. Otherwise reject the setup.
- Zone expiry is eight M15 candles after creation. The first subsequent price entry into the zone (wick overlap, inclusive) marks it mitigated; a mitigated zone is not reused as fresh. Demand is invalidated by an M15 close below distal; supply by a close above distal.
- When zones overlap, prefer the newest valid zone for the current displacement. Current H1 bias selects direction when opposite zones overlap. Never merge zones.

## TWO_LEG_V1 and BOS

- Long leg 1 is a bullish post-sell-sweep move of at least 0.50 × frozen ATR(14, M15); short leg 1 is the inverse after a buy sweep. Measure each leg from its first directional candle open to its extreme wick, using only completed candles.
- After leg 1 completes, price must retrace 38.2%–78.6%, inclusive, of the distance from its origin to its extreme. Then leg 2 must move at least 0.50 × the same frozen ATR in the original direction. Long leg 2 must exceed leg 1's extreme or achieve bullish BOS; short is inverse.
- Long sequence invalidates if an M15 close falls below sweep extreme before leg 2 completes; short if it closes above. The complete two-leg sequence must finish within eight M15 candles of sweep confirmation or emit `TWO_LEG_TIMEOUT`.
- Bullish BOS is an M15 close strictly above the last confirmed M15 swing high that existed before displacement. Bearish BOS is a close strictly below the last such swing low. Wick-only breaks do not qualify. BOS must occur within eight M15 candles of sweep confirmation; if two-leg is enabled, it must also complete before that timeout.

## Setup state machine and eligibility

Persist each transition and reason in the event log: `WAITING_FOR_BIAS`, `WAITING_FOR_PULLBACK`, `WAITING_FOR_LIQUIDITY`, `LIQUIDITY_SWEEP_DETECTED`, `WAITING_FOR_ZONE`, `ZONE_CONFIRMED`, `DISPLACEMENT_DETECTED`, `WAITING_FOR_RETRACEMENT`, `LEG_2_DETECTED`, `WAITING_FOR_BOS`, `BOS_CONFIRMED`, `READY_FOR_ENTRY`, `EXECUTED`, `INVALIDATED`, `EXPIRED`.

Long order is bullish H1 → M15 pullback → active sell-side liquidity → sell-side sweep → valid demand zone → bullish displacement → retracement → second bullish leg → bullish BOS → entry. Short is the complete inverse. Total life is at most eight M15 candles from sweep confirmation, independent of the observation window. Cancel on bias invalidation, wrong-way sweep-extreme breach, zone invalidation/expiry, BOS/two-leg timeout, lifetime expiry, stop-distance failure, missing required data, or observation/session expiry. Record a machine-readable invalidation reason and retain rejected candidates for research.

A setup is `TRADEABLE` only when bias, pullback, liquidity, sweep, zone, displacement, two-leg, BOS, in-window entry, stop distance, per-symbol/global risk limits, concurrency, required data, and executable price are all valid. Otherwise retain it as a candidate with its rejection reason (including `RISK_LIMIT_REJECTED`, `CONCURRENT_POSITION_REJECTED`, or `DATA_GAP`). Never revise an event with future candles.

## Entry, risk, fills, and exits

- Enter at the first executable M1 price after BOS confirmation. Never substitute BOS close. If no next executable price exists because of a gap, record `DATA_GAP`, do not invent a fill, and do not create a trade.
- Long stop is sweep low minus 0.10 × frozen setup ATR; short stop is sweep high plus the buffer. Reject nonpositive stop distance or distance greater than 3.00 ATR.
- Baseline target is 2.0R, where 1R is entry-to-stop distance. Independent experiments may test 1.5R, 2.5R, 3.0R, and next external liquidity; they never replace the predeclared baseline after seeing results.
- Primary reporting is in R. Portfolio baseline risk is 0.50% equity per trade; separate, unoptimized sensitivity runs may use 0.25% and 1.00%.
- Limits: at most one executed trade per symbol per Madrid trading date, two total across both symbols per date, and one open position across the strategy. Keep candidates after rejecting a limit breach.
- Require provider-supplied `spread_pips` for a trade. If absent, block execution; do not invent a universal spread or silently assume zero. Apply provider commission when specified; baseline commission is zero only where provider quotes are documented all-in. Never double-count costs. Baseline slippage is 0.1 pip; sensitivity values are 0.0, 0.2, and 0.5 pip.
- If stop and target both touch within one M1 candle, use lower-timeframe data when available; otherwise assume stop first. Exit priority is stop, target, then session expiry; stop wins exact timestamp ties.
- At 05:00 Madrid, close any remaining position at the first executable price after session end and mark `SESSION_EXPIRY`.
- No news filter in V1. Any later news-filter implementation is a separately identified experiment.

## Research integrity and configurable parameters

V1 defaults and parameter metadata (type, default, permitted range, description, rationale) live in `config/strategy_v1.yaml`; execution defaults live in `config/execution.yaml`. Any variation is a separately versioned experiment. Required spread data is an execution precondition, not a fabricated baseline value.

Do not tune on the complete history before recording the baseline. Report cost sensitivity, chronological train/validation/out-of-sample results, walk-forward, Monte Carlo, parameter sensitivity, and regime breakdown separately. A result that only works in one period is `OVERFITTING_RISK`; positive historical P&L alone does not establish an edge. No historical-performance guarantee is made.
