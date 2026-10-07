# FX Research Lab

Local-first research and backtesting for EUR/USD and GBP/USD. This project has **no broker connection or live execution**. Strategy V1 is fully specified in software and can run historical research backtests; historical results are not evidence of a profitable edge.

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

Required validation columns: `timestamp,open,high,low,close,volume`. For V1 execution, historical `spread_pips` is preferred; a fixed fallback may be set explicitly in `config/execution.yaml`. Without either source, the candidate is logged and excluded from executable trades. Example CSV:

```csv
timestamp,open,high,low,close,volume,spread_pips
2024-01-02T07:00:00Z,1.1030,1.1034,1.1028,1.1032,120,0.8
2024-01-02T07:01:00Z,1.1032,1.1036,1.1031,1.1035,95,0.8
```

No missing candles are generated. Data validation reports duplicates, order, and gaps. Dataset version is a SHA-256 source-file hash.

## Strategy and reproducibility

The V1 baseline is specified in [docs/STRATEGY_SPEC.md](docs/STRATEGY_SPEC.md), with machine-readable rules in [config/strategy_v1.yaml](config/strategy_v1.yaml) and fills/costs in [config/execution.yaml](config/execution.yaml). The earlier partial hypothesis is preserved as [config/strategy_v0_1.yaml](config/strategy_v0_1.yaml). Decisions are tracked in [docs/DECISION_LOG.md](docs/DECISION_LOG.md), data semantics in [DATA_SPEC.md](DATA_SPEC.md), and research safeguards in [RESEARCH_METHOD.md](RESEARCH_METHOD.md). The causal implementation gates have passed; all timestamps use UTC internally and IANA zones for display and DST handling.

## Tests

```bash
python -m pytest
```

## Current implementation status

- Data import, quality checks, UTC normalization, and DST-aware exact schedule display are implemented.
- Strategy V1 is recorded in YAML, including explicit observation windows, DST resolution, spread requirements, state and execution rules. The causal signal and execution engine is verified and historical backtesting is enabled.
- Statistical benchmark, out-of-sample runs, walk-forward, Monte Carlo, sensitivity, trade chart, and classification are not implemented.

## Recommended next steps

1. Run the baseline on validated historical data and review candidate/trade provenance.
2. Build independent in-sample, validation, and out-of-sample periods with a cost-matched baseline.
3. Add walk-forward evaluation, Monte Carlo, and parameter sensitivity.
4. Add annotated candle review, persistence, and classification criteria.

See [ARCHITECTURE.md](ARCHITECTURE.md), [CONTRIBUTING.md](CONTRIBUTING.md), and [LICENSE](LICENSE).
