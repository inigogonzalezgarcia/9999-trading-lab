# Architecture

The MVP is a local-first Python service with CSV/Parquet import and a React dashboard. `backend/app/data.py` handles ingestion, validation, UTC candle-close normalization, aggregation, and causal data access; `backend/app/timezones.py` handles IANA timezone conversion and the observation schedule; `backend/app/models.py` defines validated domain entities; `backend/app/main.py` is the HTTP boundary. YAML files define versioned data, execution, and strategy assumptions.

Current flow: import → validate/report → normalize timestamps to UTC → display exact Madrid and New York schedule instants. `strategy_v0_1` is `PARTIALLY_SPECIFIED`; the API stops before signals, simulation, metrics, and trade export. This is intentional so TBD concepts do not become silent assumptions. Aggregation uses UTC-aligned, left-closed intervals and labels bars by close time. No synthetic candles are added.

No broker or live execution is present. There is no persistent database, benchmark, walk-forward analysis, sensitivity runner, or classification engine yet. See `docs/STRATEGY_SPEC.md` for the rule register and `docs/DECISION_LOG.md` for decisions and unresolved items.
