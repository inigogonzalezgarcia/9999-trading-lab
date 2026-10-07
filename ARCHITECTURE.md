# Architecture

The MVP is a local-first Python service with CSV/Parquet import and a React dashboard. `backend/app` handles data validation, IANA timezone conversion, the observation schedule, and API concerns. YAML files define versioned strategy state.

Current flow: import → validate/report → normalize timestamps to UTC → display exact Madrid and New York schedule instants. `strategy_v0_1` is `PARTIALLY_SPECIFIED`; the API stops before signals, simulation, metrics, and trade export. This is intentional so TBD concepts do not become silent assumptions. Aggregation uses UTC-aligned, left-closed intervals and labels bars by close time. No synthetic candles are added.

No broker or live execution is present. There is no persistent database, benchmark, walk-forward analysis, sensitivity runner, or classification engine yet.
