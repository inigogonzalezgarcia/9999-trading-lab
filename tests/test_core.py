from pathlib import Path
import math
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
from backend.app.data import DataQualityError, aggregate_bars, bars_available_at, load_market_data
from backend.app.execution import resolve_spread
from backend.app.timezones import observation_windows_at, timezone_database_version, validate_observation_window_config
from backend.app.strategy_v1 import _simulate_candidate, confirmed_fractal_swings, generate_v1_candidates, run_v1_backtest

ROOT = Path(__file__).resolve().parents[1]


def test_dst_conversion_is_iana_aware():
    winter = convert_time("2024-01-15T07:00:00Z", "America/New_York")
    summer = convert_time("2024-07-15T07:00:00Z", "America/New_York")
    assert winter.endswith("-05:00") and summer.endswith("-04:00")


def test_aggregation_labels_close():
    ts = pd.date_range("2024-01-01T00:01:00Z", periods=10, freq="min")
    bars = pd.DataFrame({"timestamp": ts, "open": range(10), "high": range(10), "low": range(10), "close": range(10), "volume": 1})
    out = aggregate_bars(bars, "M5")
    assert out.timestamp.iloc[0] == pd.Timestamp("2024-01-01T00:05Z")
    assert out.close.iloc[0] == 4 and out.volume.iloc[0] == 5


def test_source_open_timestamps_become_utc_close_timestamps(tmp_path):
    path = tmp_path / "bars.csv"
    path.write_text("timestamp,open,high,low,close,volume\n2024-01-01T00:00:00Z,1,1.1,0.9,1.05,2\n")
    dataset = load_market_data(path, timeframe="M1")
    assert dataset.bars.timestamp.iloc[0] == pd.Timestamp("2024-01-01T00:01:00Z")
    assert dataset.quality["source_timestamp_semantics"] == "bar_open"


def test_duplicate_normalized_timestamps_are_rejected(tmp_path):
    path = tmp_path / "duplicate.csv"
    row = "2024-01-01T00:00:00Z,1,1.1,0.9,1.05,2"
    path.write_text(f"timestamp,open,high,low,close,volume\n{row}\n{row}\n")
    with pytest.raises(DataQualityError):
        load_market_data(path)


def test_future_candles_are_not_available_at_prior_decision_time():
    bars = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=3, freq="min", tz="UTC"), "close": [1, 2, 3]})
    visible = bars_available_at(bars, "2024-01-01T00:01:00Z")
    assert visible.close.tolist() == [1, 2]


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


def test_v1_dst_policy_skips_spring_gap_and_selects_first_fall_occurrence():
    config = load_config(ROOT / "config" / "strategy_v1.yaml")
    spring = scheduled_observations("2024-03-31", config)
    fall = scheduled_observations("2024-10-27", config)
    assert spring[1]["status"] == "DST_NONEXISTENT_SKIPPED"
    assert fall[1]["status"] == "DST_AMBIGUOUS_EARLY"
    assert fall[1]["timezone_resolution"] == "first_occurrence_earlier_utc"
    assert fall[1]["local_timestamp"] == "2024-10-27T02:30:00"
    assert fall[1]["utc_offset"] == "+02:00"
    assert fall[1]["utc"].endswith("+00:00")


def test_observation_windows_are_half_open_and_require_aware_instants():
    config = load_config(ROOT / "config" / "strategy_v1.yaml")
    assert observation_windows_at("2024-10-27T00:15:00Z", config) == [0]
    assert observation_windows_at("2024-10-27T00:45:00Z", config) == []
    with pytest.raises(ValueError, match="timezone-aware"):
        observation_windows_at("2024-10-27T02:15:00", config)


def test_overlapping_configured_windows_raise():
    config = load_config(ROOT / "config" / "strategy_v1.yaml")
    config["observation"]["windows"].append({"start": "02:30", "end": "03:00"})
    with pytest.raises(ValueError, match="overlap"):
        validate_observation_window_config(config)


def test_timezone_database_release_is_recorded_for_reproducibility():
    info = timezone_database_version()
    assert info["source"] and info["version"]


def test_spread_resolution_prefers_provider_then_explicit_fixed_value():
    config = load_config(ROOT / "config" / "execution.yaml")
    assert resolve_spread(0.7, config)["spread_source"] == "HISTORICAL_SPREAD"
    config["spread"]["fixed_fallback_pips"] = 0.9
    assert resolve_spread(None, config)["spread_source"] == "FIXED_CONFIGURED_SPREAD"
    config["spread"]["fixed_fallback_pips"] = None
    unavailable = resolve_spread(None, config)
    assert unavailable["spread_source"] == "NO_SPREAD_DATA"
    assert unavailable["candidate_status"] == "SPREAD_DATA_UNAVAILABLE"


def test_spread_column_is_validated_and_reported(tmp_path):
    path = tmp_path / "with_spread.csv"
    path.write_text("timestamp,open,high,low,close,volume,spread_pips\n2024-01-01T00:00:00Z,1,1.1,0.9,1.05,2,0.8\n")
    dataset = load_market_data(path, timeframe="M1")
    assert dataset.quality["spread_available"] is True
    assert dataset.bars.spread_pips.iloc[0] == 0.8


def test_v1_is_not_reported_fully_specified_before_engine_implementation():
    config = load_config(ROOT / "config" / "strategy_v1.yaml")
    assert config["status"] == "IMPLEMENTATION_PENDING"


def test_fractal_is_available_only_after_two_right_bars_close():
    timestamps = pd.date_range("2024-01-01T00:01:00Z", periods=5, freq="min")
    bars = pd.DataFrame({"timestamp": timestamps, "high": [1, 2, 5, 3, 2], "low": [0, 1, 2, 1, 0]})
    swings = confirmed_fractal_swings(bars, left=2, right=2)
    swing = next(item for item in swings if item.kind == "HIGH")
    assert swing.index == 2
    assert swing.available_index == 4
    assert swing.available_at == timestamps[4]


def test_future_candle_removal_removes_unconfirmed_fractal():
    timestamps = pd.date_range("2024-01-01T00:01:00Z", periods=5, freq="min")
    bars = pd.DataFrame({"timestamp": timestamps, "high": [1, 2, 5, 3, 2], "low": [0, 1, 2, 1, 0]})
    assert not any(item.kind == "HIGH" for item in confirmed_fractal_swings(bars.iloc[:4], left=2, right=2))


def test_v1_engine_runs_deterministically_on_research_fixture():
    config = load_config(ROOT / "config" / "strategy_v1.yaml")
    execution = load_config(ROOT / "config" / "execution.yaml")
    n = 2400
    timestamps = pd.date_range("2024-01-01T00:01:00Z", periods=n, freq="min")
    close = 1.10 + 0.0002 * pd.Series([math.sin(x / 30) for x in range(n)])
    open_price = close.shift(1, fill_value=close.iloc[0])
    bars = pd.DataFrame({"timestamp": timestamps, "open": open_price, "high": pd.concat([open_price, close], axis=1).max(axis=1)+0.00002,
                         "low": pd.concat([open_price, close], axis=1).min(axis=1)-0.00002, "close": close, "volume": 1, "spread_pips": 0.8})
    first = generate_v1_candidates(bars, "EURUSD", config)
    second = generate_v1_candidates(bars, "EURUSD", config)
    assert first == second
    executable_config = {**config, "status": "FULLY_SPECIFIED"}
    result = run_v1_backtest(bars, "EURUSD", executable_config, execution)
    assert result["spread_sources"] == ["HISTORICAL_SPREAD"]
    assert result["trades"] == []


def test_m1_execution_uses_spread_and_records_target_exit():
    strategy = load_config(ROOT / "config" / "strategy_v1.yaml")
    execution = load_config(ROOT / "config" / "execution.yaml")
    candidate = {"candidate_id": "candidate-test", "symbol": "EURUSD", "direction": "LONG",
                 "actual_execution_time": "2024-01-01T00:00:00+00:00", "entry_spread_pips": 0.8,
                 "stop_price": 1.099, "atr_at_setup": 0.01, "liquidity_level": 1.1,
                 "sweep_timestamp": "2024-01-01T00:00:00+00:00", "sweep_confirmation_timestamp": "2024-01-01T00:00:00+00:00",
                 "sweep_extreme": 1.0995, "zone": {"source_timestamp": "2024-01-01T00:00:00+00:00", "proximal": 1.100, "distal": 1.099},
                 "bos_timestamp": "2024-01-01T00:00:00+00:00", "scheduled_observation_time": "02:30",
                 "observation_window_index": 0, "actual_signal_time": "2024-01-01T00:00:00+00:00"}
    bars = pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-01T00:01Z", "2024-01-01T00:02Z"]),
                         "open": [1.100, 1.1005], "high": [1.101, 1.1023], "low": [1.100, 1.1005],
                         "close": [1.1005, 1.1020], "volume": [1, 1], "spread_pips": [0.8, 0.8]})
    result = _simulate_candidate(candidate, bars, execution, strategy, equity=1.0)
    assert result["candidate_status"] == "EXECUTED"
    assert result["trade"]["exit_reason"] == "TAKE_PROFIT"
    assert result["trade"]["spread_source"] == "HISTORICAL_SPREAD"
    assert result["trade"]["r_multiple"] == pytest.approx(2.0)


def test_stop_wins_when_stop_and_target_touch_same_m1_candle():
    strategy = load_config(ROOT / "config" / "strategy_v1.yaml")
    execution = load_config(ROOT / "config" / "execution.yaml")
    candidate = {"candidate_id": "candidate-tie", "symbol": "EURUSD", "direction": "LONG",
                 "actual_execution_time": "2024-01-01T00:00:00+00:00", "entry_spread_pips": 0.8,
                 "stop_price": 1.099, "atr_at_setup": 0.01, "liquidity_level": 1.1,
                 "sweep_timestamp": "2024-01-01T00:00:00+00:00", "sweep_confirmation_timestamp": "2024-01-01T00:00:00+00:00",
                 "sweep_extreme": 1.0995, "zone": {"source_timestamp": "2024-01-01T00:00:00+00:00", "proximal": 1.100, "distal": 1.099},
                 "bos_timestamp": "2024-01-01T00:00:00+00:00", "scheduled_observation_time": "02:30",
                 "observation_window_index": 0, "actual_signal_time": "2024-01-01T00:00:00+00:00"}
    bars = pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-01T00:01Z", "2024-01-01T00:02Z"]),
                         "open": [1.100, 1.1005], "high": [1.101, 1.103], "low": [1.100, 1.098],
                         "close": [1.1005, 1.1000], "volume": [1, 1], "spread_pips": [0.8, 0.8]})
    result = _simulate_candidate(candidate, bars, execution, strategy, equity=1.0)
    assert result["trade"]["exit_reason"] == "STOP_LOSS"


def test_execution_stops_at_missing_m1_bar_instead_of_inventing_exit():
    strategy = load_config(ROOT / "config" / "strategy_v1.yaml")
    execution = load_config(ROOT / "config" / "execution.yaml")
    candidate = {"candidate_id": "candidate-gap", "symbol": "EURUSD", "direction": "LONG",
                 "actual_execution_time": "2024-01-01T00:00:00+00:00", "entry_spread_pips": 0.8,
                 "stop_price": 1.099, "atr_at_setup": 0.01, "liquidity_level": 1.1,
                 "sweep_timestamp": "2024-01-01T00:00:00+00:00", "sweep_extreme": 1.0995,
                 "zone": {"source_timestamp": "2024-01-01T00:00:00+00:00", "proximal": 1.100, "distal": 1.099},
                 "bos_timestamp": "2024-01-01T00:00:00+00:00", "scheduled_observation_time": "02:30",
                 "observation_window_index": 0, "actual_signal_time": "2024-01-01T00:00:00+00:00"}
    bars = pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-01T00:01Z", "2024-01-01T00:03Z"]),
                         "open": [1.100, 1.1005], "high": [1.101, 1.1023], "low": [1.100, 1.1005],
                         "close": [1.1005, 1.1020], "volume": [1, 1], "spread_pips": [0.8, 0.8]})
    result = _simulate_candidate(candidate, bars, execution, strategy, equity=1.0)
    assert result["candidate_status"] == "DATA_GAP"
    assert result["trade"] is None


def test_missing_spread_retains_candidate_without_executable_trade():
    strategy = load_config(ROOT / "config" / "strategy_v1.yaml")
    execution = load_config(ROOT / "config" / "execution.yaml")
    candidate = {"candidate_id": "candidate-spread", "symbol": "EURUSD", "direction": "LONG",
                 "actual_execution_time": "2024-01-01T00:00:00+00:00", "entry_spread_pips": None,
                 "stop_price": 1.099, "atr_at_setup": 0.01, "liquidity_level": 1.1,
                 "sweep_timestamp": "2024-01-01T00:00:00+00:00", "sweep_extreme": 1.0995,
                 "zone": {"source_timestamp": "2024-01-01T00:00:00+00:00", "proximal": 1.100, "distal": 1.099},
                 "bos_timestamp": "2024-01-01T00:00:00+00:00", "scheduled_observation_time": "02:30",
                 "observation_window_index": 0, "actual_signal_time": "2024-01-01T00:00:00+00:00"}
    bars = pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-01T00:01Z", "2024-01-01T00:02Z"]),
                         "open": [1.100, 1.1005], "high": [1.101, 1.1023], "low": [1.100, 1.1005],
                         "close": [1.1005, 1.1020], "volume": [1, 1]})
    result = _simulate_candidate(candidate, bars, execution, strategy, equity=1.0)
    assert result["candidate_status"] == "SPREAD_DATA_UNAVAILABLE"
    assert result["spread_source"] == "NO_SPREAD_DATA"
    assert result["trade"] is None


def test_partial_strategy_cannot_generate_signals():
    config = load_config(ROOT / "config" / "strategy_v0_1.yaml")
    bars = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=3, tz="UTC"), "open": [1, 1, 1], "high": [1, 1, 1], "low": [1, 1, 1], "close": [1, 1, 1], "volume": [1, 1, 1]})
    with pytest.raises(StrategyIncompleteError):
        generate_signals(bars, config, "EURUSD")
