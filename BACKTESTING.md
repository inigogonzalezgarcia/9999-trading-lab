# Backtesting status

`strategy_v0_1` does not permit trade simulation. The strategy specification has unresolved definitions and the API returns data-quality results and the DST-aware observation schedule without creating signals or trades. The strategy must remain labelled `PARTIALLY_SPECIFIED` until those rules have explicit definitions in a new version.

Before a later version enables simulation, its execution model must state entry timing, spread, slippage, commission, stop/target behavior, sizing, gap fills, and same-candle ambiguity. Evaluation must include independent in-sample, validation, and out-of-sample periods; a transaction-cost matched random baseline; walk-forward testing; Monte Carlo; parameter sensitivity; and stated classification criteria. Historical performance does not guarantee future performance.
