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
