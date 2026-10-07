"""IANA timezone conversion and exact observation schedule handling."""
from __future__ import annotations

from datetime import date, datetime, time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from zoneinfo import TZPATH, ZoneInfo, ZoneInfoNotFoundError

import pandas as pd


def timezone_database_version() -> dict[str, str]:
    """Expose the IANA tzdb release used for reproducible schedule calculations."""
    try:
        return {"source": "python-tzdata", "version": version("tzdata")}
    except PackageNotFoundError:
        for root in TZPATH:
            metadata = Path(root) / "tzdata.zi"
            try:
                first_line = metadata.open(encoding="utf-8").readline().strip()
            except OSError:
                continue
            if first_line.startswith("# version "):
                return {"source": str(root), "version": first_line.removeprefix("# version ").strip()}
        return {"source": "system_tzdb", "version": "unknown"}


def validate_observation_window_config(config: dict[str, Any]) -> None:
    """Reject malformed or overlapping local-time windows before strategy runs."""
    observation = config.get("observation", {})
    windows = observation.get("windows")
    if windows is None:
        return
    normalized = []
    for item in windows:
        try:
            start = time.fromisoformat(item["start"])
            end = time.fromisoformat(item["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Observation windows require valid local start/end times") from exc
        if start >= end:
            raise ValueError("Observation window start must precede its end")
        normalized.append((start, end))
    normalized.sort(key=lambda bounds: bounds[0])
    for previous, current in zip(normalized, normalized[1:]):
        if current[0] < previous[1]:
            raise ValueError("Configured observation windows overlap")


def observation_windows_at(instant: str | datetime | pd.Timestamp, config: dict[str, Any]) -> list[int]:
    """Return half-open window indexes containing an aware instant in Madrid time."""
    validate_observation_window_config(config)
    timestamp = pd.Timestamp(instant)
    if timestamp.tzinfo is None:
        raise ValueError("Observation-window evaluation requires a timezone-aware timestamp")
    zone = ZoneInfo(config["timezones"]["reference"])
    local_time = timestamp.tz_convert(zone).time().replace(tzinfo=None)
    matches = []
    for index, window in enumerate(config.get("observation", {}).get("windows", [])):
        start, end = time.fromisoformat(window["start"]), time.fromisoformat(window["end"])
        if start <= local_time < end:
            matches.append(index)
    return matches


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
        new_york = ZoneInfo(config["timezones"].get("market_analysis", config["timezones"].get("market")))
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown IANA timezone in strategy config: {exc}") from exc
    target_date = date.fromisoformat(local_date) if isinstance(local_date, str) else local_date
    validate_observation_window_config(config)
    if "preparation_time" in config:
        prep_time = config["preparation_time"]
        observation_times = config["observation_times"]
    else:
        prep_time = config["preparation"]["time"]
        observation_times = config["observation"]["scheduled_times"]
    schedule = [("preparation", prep_time)] + [("observation", t) for t in observation_times]
    result = []
    for kind, clock in schedule:
        hour, minute = map(int, clock.split(":"))
        candidates = _local_candidates(datetime.combine(target_date, time(hour, minute)), madrid)
        if not candidates:
            is_v1 = "observation" in config
            result.append({"kind": kind, "status": "DST_NONEXISTENT_SKIPPED" if is_v1 else "nonexistent_dst_time", "madrid": None, "utc": None, "new_york": None,
                           "local_timestamp": datetime.combine(target_date, time(hour, minute)).isoformat()})
        elif len(candidates) > 1:
            policy = config.get("observation", {}).get("dst", {}).get("ambiguous_policy")
            if policy == "first_occurrence_earlier_utc":
                utc, local = min(candidates, key=lambda item: item[0])
                result.append({"kind": kind, "status": "DST_AMBIGUOUS_EARLY", "timezone_resolution": policy,
                               "local_timestamp": datetime.combine(target_date, time(hour, minute)).isoformat(),
                               "resolved_utc_timestamp": utc.isoformat(), "utc_offset": local.strftime("%z")[:3] + ":" + local.strftime("%z")[3:],
                               "new_york_timestamp": utc.tz_convert(new_york).isoformat(),
                               "madrid": local.isoformat(), "utc": utc.isoformat(), "new_york": utc.tz_convert(new_york).isoformat()})
            else:
                result.append({"kind": kind, "status": "ambiguous_dst_time", "madrid": None, "utc": None, "new_york": None,
                               "candidates": [{"madrid": local.isoformat(), "utc": utc.isoformat(), "new_york": utc.tz_convert(new_york).isoformat()} for utc, local in candidates]})
        else:
            utc, local = candidates[0]
            result.append({"kind": kind, "status": "scheduled", "madrid": local.isoformat(), "utc": utc.isoformat(), "new_york": utc.tz_convert(new_york).isoformat()})
    return result
