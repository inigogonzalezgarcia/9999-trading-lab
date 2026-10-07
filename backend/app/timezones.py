"""IANA timezone conversion and exact observation schedule handling."""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd


def convert_timestamp(value: str | datetime | pd.Timestamp, timezone: str) -> str:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    try:
        return ts.tz_convert(ZoneInfo(timezone)).isoformat()
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown IANA timezone: {timezone}") from exc


def _local_candidates(local_naive: datetime, timezone: ZoneInfo) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    candidates: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for fold in (0, 1):
        local = local_naive.replace(tzinfo=timezone, fold=fold)
        utc = pd.Timestamp(local).tz_convert("UTC")
        roundtrip = utc.tz_convert(timezone)
        if roundtrip.replace(tzinfo=None) == local_naive and all(utc != seen[0] for seen in candidates):
            candidates.append((utc, roundtrip))
    return candidates


def scheduled_observations(local_date: str | date, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert exact local schedule points, reporting DST gaps/folds without guessing."""
    try:
        madrid = ZoneInfo(config["timezones"]["reference"])
        new_york = ZoneInfo(config["timezones"]["market_analysis"])
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown IANA timezone in strategy config: {exc}") from exc
    target_date = date.fromisoformat(local_date) if isinstance(local_date, str) else local_date
    schedule = [("preparation", config["preparation_time"])] + [("observation", t) for t in config["observation_times"]]
    result = []
    for kind, clock in schedule:
        hour, minute = map(int, clock.split(":"))
        candidates = _local_candidates(datetime.combine(target_date, time(hour, minute)), madrid)
        if not candidates:
            result.append({"kind": kind, "status": "nonexistent_dst_time", "madrid": None, "utc": None, "new_york": None})
        elif len(candidates) > 1:
            result.append({"kind": kind, "status": "ambiguous_dst_time", "madrid": None, "utc": None, "new_york": None,
                           "candidates": [{"madrid": local.isoformat(), "utc": utc.isoformat(), "new_york": utc.tz_convert(new_york).isoformat()} for utc, local in candidates]})
        else:
            utc, local = candidates[0]
            result.append({"kind": kind, "status": "scheduled", "madrid": local.isoformat(), "utc": utc.isoformat(), "new_york": utc.tz_convert(new_york).isoformat()})
    return result
