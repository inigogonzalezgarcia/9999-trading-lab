"""Historical market data ingestion, normalization, and quality reporting."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
TIMEFRAME_DURATION = {"M1": pd.Timedelta(minutes=1), "M5": pd.Timedelta(minutes=5), "M15": pd.Timedelta(minutes=15), "H1": pd.Timedelta(hours=1)}


@dataclass
class Dataset:
    bars: pd.DataFrame
    quality: dict[str, Any]
    version: str


class DataQualityError(ValueError):
    def __init__(self, message: str, report: dict[str, Any]):
        super().__init__(message)
        self.report = report


def _normalize_timestamps(values: pd.Series, source_timezone: str | None) -> pd.DatetimeIndex:
    parsed = [pd.Timestamp(value) for value in values]
    if any(pd.isna(value) for value in parsed):
        raise ValueError("timestamp contains invalid values")
    aware = [value.tzinfo is not None for value in parsed]
    if any(aware) and not all(aware):
        raise ValueError("timestamp column mixes timezone-aware and naive values")
    if all(aware):
        return pd.DatetimeIndex([value.tz_convert("UTC") for value in parsed])
    if not source_timezone:
        raise ValueError("Naive timestamps require an explicit IANA source_timezone")
    try:
        zone = ZoneInfo(source_timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown IANA source_timezone: {source_timezone}") from exc
    naive = pd.DatetimeIndex(parsed)
    try:
        return naive.tz_localize(zone, ambiguous="raise", nonexistent="raise").tz_convert("UTC")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Naive timestamps are ambiguous or nonexistent in {source_timezone}: {exc}") from exc


def load_market_data(
    path: str | Path,
    timeframe: str = "M1",
    source_timezone: str | None = None,
    timestamp_semantics: str = "bar_open",
) -> Dataset:
    path = Path(path)
    if timeframe not in TIMEFRAME_DURATION:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    if timestamp_semantics not in {"bar_open", "bar_close"}:
        raise ValueError("timestamp_semantics must be 'bar_open' or 'bar_close'")
    raw_bytes = path.read_bytes()
    digest = sha256(raw_bytes).hexdigest()
    frame = pd.read_parquet(path) if path.suffix.lower() in {".parquet", ".pq"} else pd.read_csv(path)
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("Dataset contains no candles")

    frame = frame.copy()
    source_timestamps = _normalize_timestamps(frame["timestamp"], source_timezone)
    multi_symbol = "symbol" in frame.columns
    chronological = bool(source_timestamps.is_monotonic_increasing) if not multi_symbol else bool(
        all(group.is_monotonic_increasing for _, group in pd.Series(source_timestamps).groupby(frame["symbol"].to_numpy())))
    if timestamp_semantics == "bar_open":
        source_timestamps = source_timestamps + TIMEFRAME_DURATION[timeframe]
    frame["timestamp"] = source_timestamps
    # Portfolio files carry several symbols: a timestamp may legitimately repeat once per symbol.
    duplicates = int(frame.duplicated(subset=["symbol", "timestamp"] if multi_symbol else ["timestamp"], keep=False).sum())
    for column in REQUIRED_COLUMNS[1:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "spread_pips" in frame.columns:
        frame["spread_pips"] = pd.to_numeric(frame["spread_pips"], errors="coerce")
    numeric = frame[REQUIRED_COLUMNS[1:]].to_numpy(dtype=float)
    finite = np.isfinite(numeric).all(axis=1)
    prices_positive = (frame[["open", "high", "low", "close"]] > 0).all(axis=1)
    ohlc_valid = (frame.low <= frame[["open", "close"]].min(axis=1)) & (frame.high >= frame[["open", "close"]].max(axis=1)) & (frame.low <= frame.high)
    volume_valid = frame.volume >= 0
    spread_valid = frame.spread_pips.notna() & np.isfinite(frame.spread_pips) & (frame.spread_pips >= 0) if "spread_pips" in frame.columns else pd.Series(True, index=frame.index)
    invalid_rows = int((~finite | ~prices_positive.to_numpy() | ~ohlc_valid.to_numpy() | ~volume_valid.to_numpy() | ~spread_valid.to_numpy()).sum())

    ordered = frame.sort_values(["symbol", "timestamp"] if multi_symbol else ["timestamp"]).reset_index(drop=True)
    expected = TIMEFRAME_DURATION[timeframe]
    if multi_symbol:
        deltas = ordered.groupby("symbol", sort=False).timestamp.diff().dropna()
    else:
        deltas = ordered.timestamp.diff().dropna()
    gaps = int((deltas > expected * 1.5).sum())
    weekend_rows = int((ordered.timestamp.dt.dayofweek >= 5).sum())
    report = {
        "rows": int(len(frame)), "duplicate_timestamps": duplicates, "input_chronological": chronological,
        "gap_count": gaps, "invalid_rows": invalid_rows, "weekend_rows": weekend_rows,
        "start_utc": ordered.timestamp.min().isoformat(), "end_utc": ordered.timestamp.max().isoformat(),
        "timezone_normalized": "UTC", "source_timezone": source_timezone or "embedded_offsets",
        "source_timestamp_semantics": timestamp_semantics, "internal_timestamp_semantics": "bar_close",
        "spread_available": "spread_pips" in ordered.columns,
        "symbols": sorted(ordered["symbol"].astype(str).unique()) if multi_symbol else None,
        "dataset_version": digest, "warnings": [], "errors": [],
    }
    if duplicates:
        report["errors"].append("Duplicate normalized timestamps are not allowed.")
    if invalid_rows:
        report["errors"].append(f"{invalid_rows} rows contain non-finite, non-positive, or invalid OHLCV values.")
    if not chronological:
        report["warnings"].append("Input rows were out of order and have been sorted.")
    if gaps:
        report["warnings"].append("Data gaps detected; no candles were fabricated.")
    if weekend_rows:
        report["warnings"].append("Weekend-dated bars detected; verify source sessions and market closures.")
    if report["errors"]:
        raise DataQualityError("Dataset failed quality checks: " + " ".join(report["errors"]), report)
    return Dataset(ordered, report, digest)


def aggregate_bars(bars: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
    """Aggregate close-timestamped UTC candles; each output is available at its label/close."""
    if target_timeframe not in TIMEFRAME_DURATION or target_timeframe == "M1":
        raise ValueError(f"Unsupported aggregation target: {target_timeframe}")
    rule = {"M5": "5min", "M15": "15min", "H1": "1h"}[target_timeframe]
    return (
        bars.set_index("timestamp")
        .resample(rule, closed="right", label="right", origin="epoch")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna(subset=["open", "high", "low", "close"])
        .reset_index()
    )


def bars_available_at(bars: pd.DataFrame, decision_time: str | pd.Timestamp) -> pd.DataFrame:
    """Return only fully closed candles available at or before a decision instant."""
    instant = pd.Timestamp(decision_time)
    if instant.tzinfo is None:
        raise ValueError("decision_time must be timezone-aware")
    utc = instant.tz_convert("UTC")
    return bars.loc[bars.timestamp <= utc].copy()
