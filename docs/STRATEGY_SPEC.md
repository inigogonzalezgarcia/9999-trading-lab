# Strategy specification

## Status

**PARTIALLY_SPECIFIED.** This document defines research hypotheses from the project brief, not universal market facts or a proprietary ICAP strategy. The engine must refuse to generate setups or trades until all enabled rules and execution choices have explicit values. The current implementation is limited to the data and timezone phases.

Each rule is labelled **DEFINED**, **CONFIGURABLE**, **RESEARCH HYPOTHESIS**, **FUTURE EXPERIMENT**, or **TBD**. The YAML files under `config/` are machine-readable and must be recorded in every future research run.

## Scope and schedule

- **DEFINED:** baseline instruments are EUR/USD and GBP/USD. Evaluate them independently before any combined result.
- **DEFINED:** H1 is external context, M15 is internal context, M1 is intended for execution modeling, and M5 is optional.
- **DEFINED:** IANA zones are `Europe/Madrid` and `America/New_York`; store UTC internally and show both zones where relevant.
- **DEFINED:** preparation at 01:50 Madrid is reference-only; observation points are 02:30, 03:30, and 04:00 Madrid.
- **CONFIGURABLE:** observation schedule is in `config/strategy_v0_1.yaml`.
- **TBD:** ambiguous or nonexistent local times on DST transition dates require an explicit policy. Until selected, report candidates/status; do not choose an offset silently.
- **TBD:** whether observation points have tolerance or permit continuous monitoring. The current schedule uses exact instants only.

## Structure and bias

- **RESEARCH HYPOTHESIS:** initial swing candidates use strict fractals with 2 bars to the left and 2 to the right. Equal highs/lows do not qualify as strict pivots; they are handled separately. A point is usable only after all right-side candles close.
- **CONFIGURABLE:** left/right bar counts and wick-based high/low fields are configured. A future version may compare close-based structural points as a sensitivity experiment.
- **RESEARCH HYPOTHESIS:** H1 bullish structure requires a confirmed higher high and higher low sequence; bearish requires a lower low and lower high sequence. Otherwise report RANGE or UNDEFINED, never force a direction.
- **RESEARCH HYPOTHESIS:** M15 uses the same swing method and can disagree with H1. A long context uses bullish H1 with M15 pullback; a short context uses bearish H1 with M15 pullback.
- **TBD:** exact pullback/correction state algorithm and minimum sequence evidence. Until defined, no directional bias/setup is produced.

## Liquidity and sweep

- **RESEARCH HYPOTHESIS:** initial levels come from confirmed H1/M15 swing highs and lows. Daily/weekly/session levels, round numbers, news levels, and manual levels are excluded.
- **FUTURE EXPERIMENT:** equal highs/lows within a configurable tolerance, initially proposed as `0.10 × ATR(14, M15)`. This feature remains disabled pending exact clustering, ATR timing, and level-price rules.
- **RESEARCH HYPOTHESIS:** sell-side sweep means price trades at or below a previously known liquidity low and the same completed candle closes back above it. Buy-side is the inverse. A level must predate the sweep.
- **CONFIGURABLE:** record level, source timeframe/swing IDs, confirmation and creation times, sweep extreme, close, and penetration distance.
- **TBD:** relevance ranking, level lifecycle/interactions, and how overlapping levels are selected.

## Zones, displacement, BOS, two-leg

- **RESEARCH HYPOTHESIS:** M15 demand is the last bearish candle or cluster before significant bullish displacement; supply is the last bullish candle or cluster before bearish displacement.
- **RESEARCH HYPOTHESIS:** displacement requires a directional move of at least `1.0 × ATR(14, M15)` and a meaningful structural break. ATR uses only closed candles.
- **CONFIGURABLE:** ATR period and displacement multiple are stored in strategy YAML.
- **RESEARCH HYPOTHESIS:** a zone becomes MITIGATED when price first trades into it after creation; mitigated zones are not reused as fresh primary zones.
- **TBD:** candle-cluster selection, zone proximal/distal boundary, the interval used to measure displacement, ATR anchor, and all invalidation/overlap rules. Zone detection remains disabled until specified.
- **RESEARCH HYPOTHESIS:** bullish BOS is a completed M15 close above the last confirmed M15 swing high that existed before displacement; bearish is the inverse. Wicks alone are not BOS.
- **TWO_LEG_V1 RESEARCH HYPOTHESIS:** sweep → first directional displacement → retracement → second directional leg → BOS → entry. It is a named experimental interpretation, not an established or proprietary rule.
- **TBD:** objective bounds for retracement, leg separation, second-leg identification, and timeouts. TWO_LEG_V1 remains disabled until these are supplied.

## Setup, execution, and risk

- **DEFINED:** conceptual long chain is bullish H1 → M15 pullback → known sell-side liquidity → sweep → demand interaction → bullish displacement/BOS → configured entry. Short is inverse.
- **TBD:** exact pullback, zone interaction/sequence, setup expiry, maximum distance, invalidation, news filter, and candidate-vs-executed setup rules.
- **RESEARCH HYPOTHESIS:** proposed entry is after the M15 BOS close at the next executable M1 price, not at the BOS candle close. This remains inactive until fill/spread/slippage semantics are finalized.
- **RESEARCH HYPOTHESIS:** proposed stop is beyond the sweep extreme with a `0.10 × ATR(M15)` buffer.
- **FUTURE EXPERIMENT:** test TP models independently: 1.5R, 2R, next external liquidity, and a configured R multiple. Never retrospectively select a winner and present it as predetermined.
- **TBD:** risk sizing, maximum one trade per symbol per trading date, order/fill rules, spread, slippage, commission, gap handling, and same-candle ambiguity. See `config/execution.yaml`; the execution model is not active.
- **DEFINED:** no broker order submission, live account integration, or real-money execution in this project.

## Causality and result claims

- **DEFINED:** a candle is available only at its close timestamp. A swing is unavailable before confirmation. Every future event must record source and detection timestamps.
- **DEFINED:** deleting candles after time T must not alter any event emitted at or before T.
- **DEFINED:** no profitability or robustness claim from positive historical P&L alone. Results must distinguish profitability, statistical evidence, robustness, OOS behavior, and cost sensitivity.
- **FUTURE EXPERIMENT:** variants A (sweep+zone+BOS), B (sweep+two-leg), C (sweep+two-leg+BOS), matched benchmarks, walk-forward, Monte Carlo, sensitivity, regime breakdown, and research classification.

## Versioning

Any change to a rule increments the strategy version and is recorded in `docs/DECISION_LOG.md`. Do not overwrite old run configurations. `strategy_v0_1.yaml` is deliberately partial and must not be represented as a faithful, fully specified implementation.
