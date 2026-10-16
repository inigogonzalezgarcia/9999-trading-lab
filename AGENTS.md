# Repository guidance

## Product boundaries
- This is an educational research and backtesting platform. Never add broker connections, live order execution, signals/alerts, or claims that a profitable historical result proves an edge. Keep the educational notice (`service.EDUCATIONAL_NOTICE`, `DISCLAIMER.md`) in API responses, UI and exports.
- Keep strategy assumptions in versioned YAML configuration and record them in every result.
- Prevent look-ahead: confirmed pivots become available only on their confirmation candle; a candle is available only after its close.
- Normalize timestamps to UTC; use IANA zones `Europe/Madrid` and `America/New_York` for display and windows.

## Engineering
- Keep data validation, strategy logic (`backend/app/strategy/`), execution, metrics, research, persistence and HTTP/UI layers separate. `strategy_v1.py` is a facade; do not put logic there.
- Hot paths run on numpy arrays (`strategy/frames.py`); never reintroduce per-row pandas access in loops over M1 data.
- Prefer deterministic behavior and synthetic tests. Do not fabricate market data.
- Document limitations and assumptions alongside changes.
