# Backtesting status

`strategy_v0_1` remains the preserved partial hypothesis and can never emit signals. V1's deterministic
baseline rules are defined in `docs/STRATEGY_SPEC.md` and `config/strategy_v1.yaml`. The causal engine passed
its completion gates on 2026-10-07 and historical M1 research backtests are enabled through the API, the UI and
`python -m backend.cli backtest`.

**Costs.** V1 prefers provider `spread_pips`, then an explicitly configured fixed fallback
(`config/execution.yaml` or `--fixed-spread-pips`); without either the candidate is retained as
`SPREAD_DATA_UNAVAILABLE` and excluded from executable trades. Slippage and commission follow
`config/execution.yaml`; every result records the spread sources actually used.

**Metrics.** Per-trade statistics (expectancy, win rate, profit factor, payoff, max drawdown in R, per-trade
Sharpe) are never annualised. Annualised Sharpe/Sortino come from the daily sum of R over every weekday of the
dataset range (zero on days without trades), with 252 trading days per year. Earlier versions annualised the
per-trade Sharpe with √252; those numbers were meaningless and are gone.

**Research protocol** (`python -m backend.cli research`, `/api/jobs/research`): independent chronological
in-sample / validation / out-of-sample periods; rolling walk-forward folds (V1 has no fitted parameters, so the
in-sample window is a replication, not a fit); Monte Carlo bootstrap of the trade sequence; one-at-a-time
parameter sensitivity over the experiments declared in the configuration, plus labelled multi-key *session experiments*
(the same rules observed at the London and New York opens, with a matching session expiry); and a cost-matched random benchmark
(random entries inside the observation windows with identical stop distance, target, costs and session
expiry). Period runs receive warm-up history before the period; because V1 liquidity levels have no expiry,
trades in a sliced period can differ from the same dates inside a full run — report which mode you used.

**Evidence bar.** Only out-of-sample and walk-forward results may be quoted, always with the random
benchmark percentile, the Monte Carlo drawdown range and the sensitivity table. A positive full-sample result
alone is not evidence of an edge. Historical performance does not guarantee future performance. This is an
educational tool, not investment advice.
