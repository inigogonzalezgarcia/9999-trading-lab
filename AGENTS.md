# Repository guidance

## Product boundaries
- This is a research and backtesting platform. Never add broker connections, live order execution, or claims that a profitable historical result proves an edge.
- Keep strategy assumptions in versioned YAML configuration and record them in every result.
- Prevent look-ahead: confirmed pivots become available only on their confirmation candle; a candle is available only after its close.
- Normalize timestamps to UTC; use IANA zones `Europe/Madrid` and `America/New_York` for display and windows.

## Engineering
- Keep data validation, strategy logic, execution, metrics, and HTTP/UI layers separate.
- Prefer deterministic behavior and synthetic tests. Do not fabricate market data.
- Document limitations and assumptions alongside changes.
