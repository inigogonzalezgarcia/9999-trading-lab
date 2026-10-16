# First real-data run — EUR/USD 2024, Dukascopy ticks

> Educational research record. Simulated results on historical data; not investment advice and not
> evidence of an edge (or of its absence beyond this sample). See DISCLAIMER.md.

## Data

| Item | Value |
|---|---|
| Source | Dukascopy tick feed (`.bi5`), 2024-01-01 22:00 → 2024-12-31 21:59 UTC, 20 687 149 ticks |
| Aggregation | Bid M1 bars labelled by open; `spread_pips` = per-minute median of ask−bid |
| Rows | 372 774 M1 bars; 1 617 minutes without ticks (reported as gaps, never filled); 8 005 weekend-dated rows (Sunday evening session) |
| Dataset SHA-256 | `65a7a807004594d4a14e4408ce4abc71db1bc8f2d6c73e72a19f5ca25acde62d` |
| Spread source used | `HISTORICAL_SPREAD` for every executed trade (0.2–0.3 pips at entry) |
| Engine | strategy_v1 `1.0`, `FULLY_SPECIFIED`; execution_v1; software 0.2.0 |

Run time on the full year: ~4 s without daily contexts, ~80 s with `lookback:30` contexts and chart data.

## Baseline result (`config/strategy_v1.yaml`, unchanged)

| Metric | Value |
|---|---|
| Candidates tracked | 3 138 |
| Complete setups (BOS confirmed) | 300 |
| Executed trades | **5** |
| Winners / losers | 1 / 4 (one SESSION_EXPIRY exit at +0.84R, one at −0.45R, three stops at −1R) |
| Total / expectancy | **−2.61R / −0.52R per trade** |
| Max drawdown | 3.45R |
| Annualised Sharpe (daily series, 262 weekdays) | −1.30 |

Five trades in a year is far too few to say anything statistically about the edge. What the run does
establish is *where the candidates die*:

| Rejection | Count | Meaning |
|---|---|---|
| SWEEP_EXTREME_INVALIDATED | 1 474 | M15 closed back through the sweep extreme before displacement |
| BIAS_INVALIDATED | 920 | H1 bias flipped during the setup |
| SETUP_TIMEOUT / TWO_LEG_TIMEOUT / BOS_TIMEOUT | 427 | Lifetime of 8 M15 bars exhausted |
| ENTRY_OUTSIDE_WINDOW | 153 | Complete setup, BOS outside 02:15–04:15 Madrid |
| INVALID_STOP_DISTANCE | 136 | Complete setup inside a window, but stop > 3 ATR from entry (135 of 136) |
| Zone mitigated/invalidated, risk limits, data gaps | 25 | |
| EXECUTED | 5 | |

## Two structural observations (hypothesis, not harness)

1. **The pattern completes when the market is open elsewhere.** Of 300 complete setups, 49 finished inside
   the 02–04 Madrid hours and 251 outside: the peaks are 09–11 (London open, 108 setups) and 14–16 (New
   York open, 78). The observation windows and the pattern are largely disjoint.
2. **The stop rule rejects almost everything that survives the window.** The stop sits at the sweep
   extreme ± 0.10 ATR; by the time two legs and a BOS have printed, entry is typically more than 3 ATR
   away, so 135 setups were rejected for stop distance. The two rules together leave 5 trades.

## Research protocol (`results/EURUSD_2024_research.json`)

| Section | Result |
|---|---|
| Chronological splits (60/20/20) | train 4 trades (−0.86R each on average), validation 1 trade (+0.84R), out-of-sample **0 trades** |
| Walk-forward (120/30 days, 9 folds) | 3 OOS trades in 3 folds, −0.66R total; 1 of 3 folds positive |
| Monte Carlo (1 000 bootstrap paths of the 5 trades) | probability of a losing path 94 %; final R p5/p50/p95 = −5.0 / −2.61 / +0.52 |
| Cost-matched random benchmark (200 sims) | baseline expectancy at **percentile 8.5 %** of random entries with identical costs (random median −0.10R/trade) |
| Sensitivity | target 1.5R–3.0R, risk fraction, zone expiry: no change (the 5 trades never reach a target); slippage 0→0.5 pips: −2.16R → −2.82R; displacement 1.25 ATR: 4 trades, −1.66R |
| Session experiments (labelled, not baseline) | London open 09:00–10:30 Madrid: **17 trades, +0.29R** (≈ breakeven); New York open 15:00–16:30: 11 trades, −5.79R |

Every line above is dominated by sample size; the London experiment is the only configuration that produces
a count worth studying further, and it is still breakeven before any additional cost.

## V1.1 experiment (`config/strategy_v1_1.yaml`) on the same data

The three logged decisions were implemented as engine parameters whose defaults reproduce V1 exactly
(verified bit-identical) and activated in a separate configuration: London-open windows 09:00–10:30 Madrid
with session expiry 13:00, stop anchored at the zone distal edge, liquidity levels expiring after 1 920 M15
bars. V1 stays frozen.

| | V1 baseline | V1.1 experiment |
|---|---|---|
| Candidates / complete setups | 3 138 / 300 | 2 037 / 204 |
| Trades | 5 | **12** (5 winners: 3 targets, 2 expiries in profit) |
| Total / expectancy | −2.61R / −0.52R | **+2.35R / +0.20R** |
| Max drawdown | 3.45R | 3.01R |
| Random cost-matched benchmark | percentile 8.5 % | **percentile 75.5 %** (needs > 95 % to mean anything) |
| Walk-forward OOS (9 folds) | 3 trades, −0.66R | 6 trades, +3.0R, 2 of 4 folds positive |
| Splits train / validation / OOS | 4 / 1 / 0 trades | 8 (+1.07R) / 3 (+1.31R) / **1 (−0.03R)** |
| Monte Carlo p(losing path) | 94 % | 28 %; drawdown p95 5.3R |

Sensitivity on V1.1 (one change at a time, `results/EURUSD_2024_v1_1_research.json`):

| Change | Trades | Total R |
|---|---|---|
| stop max distance 3 → 4 ATR | 17 | **−1.55R** |
| stop max distance 3 → 5 ATR | 19 | −1.82R |
| stop reference → leg-1 origin | 18 | −3.74R |
| stop reference → sweep extreme (V1 rule) | 13 | +0.35R |
| level expiry 1 920 → 960 bars | 10 | +0.04R |
| level expiry removed | 15 | +3.29R |
| New York open instead of London | 8 | −6.66R |
| slippage 0 → 0.5 pips | 12 → 11 | +2.46R → +2.06R |

**Reading.** The headline +2.35R is not evidence. Twelve trades cannot separate skill from noise (the random
benchmark says exactly that), the out-of-sample slice holds one trade, and neighbouring parameter values flip
the sign. Still, 110 of 204 complete setups are rejected for stop distance even with the zone-distal stop
(median 3.7 ATR), so the next honest question for a V1.2 is structural — where the stop belongs relative to
the entry — not a parameter sweep. Multi-year data (2022–2025) is required before any further claim.

## Portfolio run (EUR/USD + GBP/USD 2024, 745 242 M1 bars, shared risk limits)

| | V1 baseline | V1.1 experiment |
|---|---|---|
| Candidates | 6 529 | 4 259 |
| Trades | 8 | 20 |
| Total / expectancy | −4.07R / −0.51R | **−1.18R / −0.06R** |
| Win rate | 25 % | 35 % |
| Max drawdown | 4.35R | 4.01R |

Adding GBP/USD removes the positive sign V1.1 showed on EUR/USD alone (the GBP/USD leg contributes roughly
−3.5R). Two symbols, one year, 20 trades: the honest summary of the hypothesis so far is *no edge detected*,
with a documented list of structural reasons and a tool that makes the next iteration a few seconds of
compute. GBP/USD data: 21 982 402 Dukascopy ticks → 372 468 M1 bars (`data/raw/GBPUSD_2024.csv`).

## What this means for the project

- The software did its job: it ran a year of real ticks in seconds, kept every candidate with its reason,
  and produced a result that is honest rather than flattering.
- The hypothesis as written is **not tradeable as a research subject**: it produces too few events to be
  evaluated. Before any claim, V1.1 must decide (as strategy decisions, recorded in the decision log):
  whether windows should follow the pattern (London/New York) rather than the Madrid night; whether the
  stop may use the zone distal edge or the leg-1 origin instead of the sweep extreme; and whether
  liquidity levels should expire.
- Research-protocol output for this dataset lives in `results/EURUSD_2024_research.json` (splits,
  walk-forward, Monte Carlo, sensitivity incl. session experiments, cost-matched random benchmark). With five
  trades, every one of those sections is dominated by sample size; read them as a demonstration of the
  method, not as evidence.

Historical performance does not guarantee future results.
