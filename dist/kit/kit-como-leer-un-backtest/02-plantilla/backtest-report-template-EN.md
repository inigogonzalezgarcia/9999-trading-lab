# Backtest report — <hypothesis> <version>

> Educational material. Simulated results on historical data. Not investment advice. Past performance does not guarantee future results.

| Field | Value |
|---|---|
| Report date | YYYY-MM-DD |
| Author | |
| Strategy version | V_._ (`file.yaml`, hash `…`) |
| Changes from the previous version | … (link to the decision log) |
| Software | version · revision |

## 1. Hypothesis
What the rule claims, in one sentence. Which market, which hours, which direction. What you should see if it is true and what you should see if it is false.

## 2. Data
| Field | Value |
|---|---|
| Provider and type | (e.g. ticks aggregated to M1) |
| Symbol(s) | |
| Range (UTC) | |
| Rules timezone | (e.g. Europe/Madrid, tzdata …) |
| Dataset SHA-256 | |
| Rows · gaps · duplicates · invalid | |
| Spread column available | yes / no |

## 3. Execution and costs
| Field | Value |
|---|---|
| Fill model | (decision at close, execution at the next price) |
| Spread | source and value |
| Slippage | pips, also on the stop? |
| Commission | |
| Risk per trade | fraction of equity |
| Session expiry | yes / no, time |

## 4. Result
| Metric | Value |
|---|---|
| Trades (N) | |
| Expectancy (R) | |
| Win rate | |
| Average win / average loss (R) | |
| Profit factor | |
| Max drawdown (R) | |
| Total R | |
| **Total R without the best trade** | |

Exit reasons: stop … · target … · session expiry …

Equity curve (in R, X axis = trades): *insert figure*.

## 5. Protocol
### 5.1 Monte Carlo
| Percentile | Final R | Max drawdown |
|---|---|---|
| P5 | | |
| P25 | | |
| P50 | | |
| P75 | | |
| P95 | | |

Probability of ending negative: … %. Simulations: … · seed: …

### 5.2 Random benchmark
Rule expectancy … R · random expectancy P50 … R · P95 … R · rule percentile … % · empirical p-value …

### 5.3 Sensitivity
| Parameter | Value | N | Total R | Expectancy |
|---|---|---|---|---|
| | | | | |

Parameters that flip the sign: …

### 5.4 Splits and walk-forward
| Segment | Days | N | Total R | Expectancy |
|---|---|---|---|---|
| train | | | | |
| validation | | | | |
| out of sample | | | | |

Walk-forward: windows … · with trades … · positive … · out-of-sample total … R

## 6. Limitations
- Simulated fills on historical data; no live execution.
- …

## 7. Decision
One of: **discard** / **keep researching** (with which new data) / **new version** (with which exact change, and why).

Decision-log entry: `YYYY-MM-DD — …`

## 8. Checklist
Paste the kit checklist here (03-checklist) with every question answered.
