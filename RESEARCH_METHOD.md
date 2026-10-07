# Research method

The project is a historical research platform, not a trading recommendation or live execution system. Strategy rules are versioned and labelled as defined, configurable, research hypothesis, future experiment, or TBD. TBD behavior remains disabled.

Every research run must retain immutable strategy/data/execution configuration, data hash and date range, symbol/timeframe, timezone rules, random seed, software version, and source revision. Out-of-sample periods are chronological and are never used to choose parameters. Walk-forward testing, cost-matched controls, sensitivity, and Monte Carlo must be reported separately; a positive historical outcome alone is not evidence of a robust edge.

If results are unexpectedly strong, investigate look-ahead, data gaps, execution costs, concentration by symbol/time/regime, sample size, and parameter dependence. Report limitations and the phrase: historical performance does not guarantee future results.
