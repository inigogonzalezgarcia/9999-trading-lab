# FX Research Lab

Local-first research and backtesting for EUR/USD and GBP/USD. This project has **no broker connection or live execution**. The V1 rules are deterministic, but the signal and execution engine remains implementation-pending, so uploads are validated without generating trades or performance claims.

## Requirements and install

Python 3.11+ and Node.js 20+ are recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install
```

## Run

From repository root, start the API and UI in separate terminals:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

```bash
cd frontend && npm run dev
```

Open http://localhost:5173. Upload a CSV or Parquet file to inspect data quality and the exact Madrid/New York observation schedule. Naive timestamps require an IANA source timezone, such as `UTC` or `Europe/Madrid`; offset-bearing timestamps are converted directly to UTC. The API docs are at http://localhost:8000/docs.

## Dataset format

Required validation columns: `timestamp,open,high,low,close,volume`. V1 execution also requires a valid provider-supplied `spread_pips` value; trades are blocked when that field is absent. Example CSV:

```csv
timestamp,open,high,low,close,volume,spread_pips
2024-01-02T07:00:00Z,1.1030,1.1034,1.1028,1.1032,120,0.8
2024-01-02T07:01:00Z,1.1032,1.1036,1.1031,1.1035,95,0.8
```

No missing candles are generated. Data validation reports duplicates, order, and gaps. Dataset version is a SHA-256 source-file hash.

## Strategy and reproducibility

The V1 baseline is specified in [docs/STRATEGY_SPEC.md](docs/STRATEGY_SPEC.md), with machine-readable rules in [config/strategy_v1.yaml](config/strategy_v1.yaml) and fills/costs in [config/execution.yaml](config/execution.yaml). The earlier partial hypothesis is preserved as [config/strategy_v0_1.yaml](config/strategy_v0_1.yaml). Decisions are tracked in [docs/DECISION_LOG.md](docs/DECISION_LOG.md), data semantics in [DATA_SPEC.md](DATA_SPEC.md), and research safeguards in [RESEARCH_METHOD.md](RESEARCH_METHOD.md). V1 remains implementation-pending until the causal engine and tests are complete. All timestamps use UTC internally and IANA zones for display and DST handling.

## Tests

```bash
python -m pytest
```

## Current implementation status

- Data import, quality checks, UTC normalization, and DST-aware exact schedule display are implemented.
- Strategy V1 is recorded in YAML, including explicit observation windows, DST resolution, spread requirements, state and execution rules. Signal generation and backtesting remain blocked until the causal V1 engine and tests are implemented.
- Statistical benchmark, out-of-sample runs, walk-forward, Monte Carlo, sensitivity, trade chart, and classification are not implemented.

## Recommended next steps

1. Implement the causal V1 state machine for H1/M15 structure, liquidity, zones, confirmation, and observation windows.
2. Implement spread-aware M1 fills, risk limits, exits, and persisted candidate/rejection events.
3. Test signal provenance and prove future-candle removal does not alter prior signals.
4. Implement cost scenarios, OOS/walk-forward, matched baseline, Monte Carlo, and sensitivity.
5. Add annotated candle review, persistence, and classification criteria.

See [ARCHITECTURE.md](ARCHITECTURE.md), [CONTRIBUTING.md](CONTRIBUTING.md), and [LICENSE](LICENSE).
