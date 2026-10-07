# Data specification

CSV and Parquet require `timestamp, open, high, low, close, volume`. Timestamps must include a timezone or an explicit timezone setting on import. Internally timestamps are UTC. Duplicate rows are reported and rejected; out-of-order rows are reported and sorted; invalid OHLC relationships and non-positive prices are rejected. Missing intervals and large gaps are reported, never filled. Weekend FX closures are not counted as expected M1 candles. Dataset identity is a SHA-256 of source bytes.

Resampling is UTC-aligned, left-closed/right-open with OHLC first/max/min/last and volume sum; labels are bar close time. No synthetic data is added.
