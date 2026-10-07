# FX Research Lab

Local-first data validation for an EUR/USD and GBP/USD strategy specification. This version has **no broker connection or live execution**. Its strategy is marked `PARTIALLY_SPECIFIED`, so uploads are validated but no signals, trades, or performance claims are generated.

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

Required columns: `timestamp,open,high,low,close,volume`. Example CSV:

```csv
timestamp,open,high,low,close,volume
2024-01-02T07:00:00Z,1.1030,1.1034,1.1028,1.1032,120
2024-01-02T07:01:00Z,1.1032,1.1036,1.1031,1.1035,95
```

No missing candles are generated. Data validation reports duplicates, order, and gaps. Dataset version is a SHA-256 source-file hash.

## Strategy and reproducibility

The machine-readable strategy state is [config/strategy_v0_1.yaml](config/strategy_v0_1.yaml). The complete rule and ambiguity register is in [docs/STRATEGY_SPEC.md](docs/STRATEGY_SPEC.md); decisions are tracked in [docs/DECISION_LOG.md](docs/DECISION_LOG.md), data semantics in [DATA_SPEC.md](DATA_SPEC.md), and research safeguards in [RESEARCH_METHOD.md](RESEARCH_METHOD.md). Rules marked TBD stay disabled. Madrid and New York timestamps use IANA zones and account for DST transitions.

## Tests

```bash
python -m pytest
```

## Current implementation status

- Data import, quality checks, UTC normalization, and DST-aware exact schedule display are implemented.
- Signal generation and backtesting are intentionally blocked until the TBD strategy definitions are resolved. The current version is not a working backtester.
- Statistical benchmark, out-of-sample runs, walk-forward, Monte Carlo, sensitivity, trade chart, and classification are not implemented.

## Recommended next steps

1. Resolve TBD strategy definitions with the strategy owner and create a fully specified version.
2. Implement causal H1/M15 structure, liquidity, zone, confirmation, and exact observation gating from that version.
3. Test signal provenance and prove future-candle removal does not alter prior signals.
4. Implement the execution engine, cost scenarios, OOS/walk-forward, matched baseline, Monte Carlo, and sensitivity.
5. Add annotated candle review, persistence, and classification criteria.

See [ARCHITECTURE.md](ARCHITECTURE.md), [CONTRIBUTING.md](CONTRIBUTING.md), and [LICENSE](LICENSE).
