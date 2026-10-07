from pathlib import Path
import pandas as pd
import pytest

from backend.app.core import (
    StrategyIncompleteError,
    aggregate,
    convert_time,
    generate_signals,
    load_config,
    scheduled_observations,
)

ROOT = Path(__file__).resolve().parents[1]


def test_dst_conversion_is_iana_aware():
    winter = convert_time("2024-01-15T07:00:00Z", "America/New_York")
    summer = convert_time("2024-07-15T07:00:00Z", "America/New_York")
    assert winter.endswith("-05:00") and summer.endswith("-04:00")


def test_aggregation_labels_close():
    ts = pd.date_range("2024-01-01", periods=10, freq="min", tz="UTC")
    bars = pd.DataFrame({"timestamp": ts, "open": range(10), "high": range(10), "low": range(10), "close": range(10), "volume": 1})
    out = aggregate(bars, "M5")
    assert out.timestamp.iloc[0] == pd.Timestamp("2024-01-01T00:05Z")
    assert out.close.iloc[0] == 4 and out.volume.iloc[0] == 5


def test_exact_schedule_converts_with_both_dst_calendars():
    config = load_config(ROOT / "config" / "strategy_v0_1.yaml")
    march = scheduled_observations("2024-03-25", config)
    assert len(march) == 4
    assert march[0]["kind"] == "preparation"
    assert march[0]["madrid"].startswith("2024-03-25T01:50:00+01:00")
    assert march[0]["new_york"].startswith("2024-03-24T20:50:00-04:00")


def test_schedule_does_not_guess_nonexistent_or_repeated_madrid_times():
    config = load_config(ROOT / "config" / "strategy_v0_1.yaml")
    spring = scheduled_observations("2024-03-31", config)
    fall = scheduled_observations("2024-10-27", config)
    assert spring[1]["status"] == "nonexistent_dst_time"
    assert fall[1]["status"] == "ambiguous_dst_time"
    assert len(fall[1]["candidates"]) == 2


def test_partial_strategy_cannot_generate_signals():
    config = load_config(ROOT / "config" / "strategy_v0_1.yaml")
    bars = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=3, tz="UTC"), "open": [1, 1, 1], "high": [1, 1, 1], "low": [1, 1, 1], "close": [1, 1, 1], "volume": [1, 1, 1]})
    with pytest.raises(StrategyIncompleteError):
        generate_signals(bars, config, "EURUSD")
