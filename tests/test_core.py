from pathlib import Path
import math
import copy
import pandas as pd
import pytest

from backend.app.core import (
    StrategyIncompleteError,
    convert_time,
    generate_signals,
    load_config,
    scheduled_observations,
)
from backend.app.data import DataQualityError, aggregate_bars, bars_available_at, load_market_data
from backend.app.execution import resolve_spread
from backend.app.timezones import observation_windows_at, timezone_database_version, validate_observation_window_config
from backend.app.strategy_v1 import Swing, _candidate_from_sweep, _simulate_candidate, build_daily_contexts, build_liquidity_lifecycle_events, build_zone_lifecycle, confirmed_fractal_swings, generate_v1_candidates, run_v1_backtest
import backend.app.strategy_v1 as strategy_v1_module

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


def test_v1_is_fully_specified_after_all_implementation_gates_pass():
    config = load_config(ROOT / "config" / "strategy_v1.yaml")
    assert config["status"] == "FULLY_SPECIFIED"


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


def test_daily_context_is_causal_and_reproducible():
    config = load_config(ROOT / "config" / "strategy_v1.yaml")
    timestamps = pd.date_range("2024-01-01T00:01:00Z", periods=240, freq="min")
    close = pd.Series([1.10 + 0.0001 * math.sin(i / 5) for i in range(len(timestamps))])
    opened = close.shift(1, fill_value=close.iloc[0])
    bars = pd.DataFrame({"timestamp": timestamps, "open": opened,
                         "high": pd.concat([opened, close], axis=1).max(axis=1) + 0.00001,
                         "low": pd.concat([opened, close], axis=1).min(axis=1) - 0.00001,
                         "close": close, "volume": 1})
    first = build_daily_contexts({"EURUSD": bars}, config, "fixture-hash")
    second = build_daily_contexts({"EURUSD": bars}, config, "fixture-hash")
    cutoff = pd.Timestamp(first[0]["created_at"])
    truncated = build_daily_contexts({"EURUSD": bars[bars.timestamp <= cutoff]}, config, "fixture-hash")
    assert first == second
    assert first == truncated
    assert first[0]["created_at"] == "2024-01-01T00:50:00+00:00"
    assert first[0]["available_data_through"] <= first[0]["created_at"]
    assert first[0]["dataset_hash"] == "fixture-hash"
    assert first[0]["config_hash"] and first[0]["timezone_database_version"]["version"]


def test_liquidity_lifecycle_records_m1_touch_before_m15_sweep_confirmation():
    effective = pd.Timestamp("2024-01-01T00:15:00Z")
    m1_times = pd.date_range("2024-01-01T00:16:00Z", periods=14, freq="min")
    lows = [1.099] + [1.100] * 13
    m1 = pd.DataFrame({"timestamp": m1_times, "low": lows, "high": 1.102})
    m15 = pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-01T00:30Z"]), "close": [1.101]})
    level = {"cluster_id": "level-fixture", "price": 1.100, "kind": "LOW", "timeframes": ["H1"],
             "effective_from": effective, "superseded_at": None, "constituents": []}
    events = build_liquidity_lifecycle_events(m1, m15, [level], "EURUSD")
    assert [event["new_state"] for event in events] == ["ACTIVE", "TOUCHED", "SWEPT"]
    assert events[1]["source_timeframe"] == "M1"
    assert events[2]["source_timeframe"] == "M15"
    assert pd.Timestamp(events[1]["detection_timestamp"]) < pd.Timestamp(events[2]["detection_timestamp"])


def test_synthetic_positive_signal_reaches_trade_and_exit_deterministically():
    synthetic_data_label = "SYNTHETIC_TEST_DATA"
    config = load_config(ROOT / "config" / "strategy_v1.yaml")
    execution = load_config(ROOT / "config" / "execution.yaml")
    start = pd.Timestamp("2023-12-31T20:45:00Z")
    timestamps = pd.date_range(start, periods=30, freq="15min")
    m15 = pd.DataFrame({"timestamp": timestamps, "open": 1.1000, "high": 1.1001,
                        "low": 1.0999, "close": 1.1000, "volume": 1})
    m15.loc[20, ["open", "high", "low", "close"]] = [1.1000, 1.10005, 1.0998, 1.09995]
    m15.loc[21, ["open", "high", "low", "close"]] = [1.1000, 1.10055, 1.09995, 1.1004]
    m15.loc[22, ["open", "high", "low", "close"]] = [1.1004, 1.10045, 1.10020, 1.1003]
    m15.loc[23, ["open", "high", "low", "close"]] = [1.1003, 1.10060, 1.10025, 1.1005]
    h1_times = pd.date_range("2023-12-31T20:00:00Z", periods=7, freq="h")
    h1 = pd.DataFrame({"timestamp": h1_times, "open": 1.1000, "high": 1.1010,
                       "low": 1.0990, "close": 1.1000, "volume": 1})
    h1_swings = [Swing("LOW", 1, 1, 1.0990, h1_times[1], h1_times[1]),
                 Swing("HIGH", 2, 2, 1.1000, h1_times[2], h1_times[2]),
                 Swing("LOW", 3, 3, 1.0995, h1_times[3], h1_times[3]),
                 Swing("HIGH", 4, 4, 1.1005, h1_times[4], h1_times[4])]
    m15_swings = [Swing("HIGH", 17, 19, 1.1002, timestamps[17], timestamps[19])]
    sweep = {"direction": "LONG", "confirmation_index": 20, "level": 1.0999,
             "level_id": "synthetic-sell-side-level", "breach_time": timestamps[20]-pd.Timedelta(minutes=1),
             "confirmation_time": timestamps[20], "extreme": 1.09985, "constituents": []}
    bos_time = timestamps[23]
    m1_times = pd.date_range(bos_time + pd.Timedelta(minutes=1), periods=3, freq="min")
    m1 = pd.DataFrame({"timestamp": m1_times, "open": [1.1000, 1.1001, 1.1005],
                       "high": [1.1002, 1.1007, 1.1007], "low": [1.09995, 1.1000, 1.1004],
                       "close": [1.1001, 1.1006, 1.1006], "volume": 1, "spread_pips": 0.8})
    candidate = _candidate_from_sweep(m15, m1, h1, h1_swings, sweep, m15_swings, config, "EURUSD")
    assert candidate is not None
    assert candidate["candidate_status"] == "CANDIDATE_SETUP"
    assert candidate["observation_window_index"] == 1
    assert pd.Timestamp(candidate["actual_execution_time"]) >= pd.Timestamp(candidate["bos_timestamp"])
    event_times = [pd.Timestamp(event["detection_timestamp"]) for event in candidate["state_events"]]
    assert event_times == sorted(event_times)
    assert all(timestamp.tzinfo is not None for timestamp in event_times)
    assert [event["state"] for event in candidate["state_events"]][-3:] == ["WAITING_FOR_BOS", "BOS_CONFIRMED", "READY_FOR_ENTRY"]
    first = _simulate_candidate(candidate, m1, execution, config, equity=1.0)
    second = _simulate_candidate(candidate, m1, execution, config, equity=1.0)
    assert first == second
    assert first["candidate_status"] == "EXECUTED"
    assert first["trade"]["exit_reason"] == "TAKE_PROFIT"
    assert synthetic_data_label == "SYNTHETIC_TEST_DATA"

    assert _candidate_from_sweep(m15, m1, h1, [], sweep, m15_swings, config, "EURUSD")["candidate_status"] == "BIAS_INVALIDATED"
    sweep_broken = m15.copy()
    sweep_broken.loc[21, "close"] = sweep["extreme"] - 0.00001
    assert _candidate_from_sweep(sweep_broken, m1, h1, h1_swings, sweep, m15_swings, config, "EURUSD")["candidate_status"] == "SWEEP_EXTREME_INVALIDATED"

    no_retrace = m15.copy()
    no_retrace.loc[22, ["open", "high", "low", "close"]] = [1.1001, 1.1001, 1.1000, 1.1001]
    no_retrace.loc[23, ["open", "high", "low", "close"]] = [1.1001, 1.1001, 1.1000, 1.1001]
    assert _candidate_from_sweep(no_retrace, m1, h1, h1_swings, sweep, m15_swings, config, "EURUSD")["candidate_status"] == "TWO_LEG_TIMEOUT"
    developing = _candidate_from_sweep(no_retrace.iloc[:24], m1, h1, h1_swings, sweep, m15_swings, config, "EURUSD")
    assert developing["candidate_status"] == "TWO_LEG_TIMEOUT"
    assert developing["zone"]["current_state"] == "CONFIRMED"
    assert pd.Timestamp(developing["zone"]["confirmation_timestamp"]) <= no_retrace.timestamp.iloc[23]

    no_bos = m15.copy()
    no_bos.loc[23, "close"] = 1.1001
    assert _candidate_from_sweep(no_bos, m1, h1, h1_swings, sweep, m15_swings, config, "EURUSD")["candidate_status"] == "BOS_TIMEOUT"

    zone_invalidated = m15.copy()
    zone_invalidated.loc[23, ["open", "high", "low", "close"]] = [1.1003, 1.1006, 1.0997, 1.09975]
    zone_invalidated.loc[24, ["open", "high", "low", "close"]] = [1.09975, 1.1005, 1.1002, 1.1003]
    lower_sweep = {**sweep, "extreme": 1.0997}
    assert _candidate_from_sweep(zone_invalidated, m1, h1, h1_swings, lower_sweep, m15_swings, config, "EURUSD")["candidate_status"] == "ZONE_INVALIDATED"

    changed_windows = copy.deepcopy(config)
    changed_windows["observation"]["windows"] = [{"start": "04:15", "end": "04:45"}]
    outside = _candidate_from_sweep(m15, m1, h1, h1_swings, sweep, m15_swings, changed_windows, "EURUSD")
    assert outside["candidate_status"] == "NOT_TRADEABLE_OUTSIDE_OBSERVATION_WINDOW"


def test_synthetic_candidate_to_portfolio_result_is_repeatable(monkeypatch):
    config = load_config(ROOT / "config" / "strategy_v1.yaml")
    config["status"] = "FULLY_SPECIFIED"
    execution = load_config(ROOT / "config" / "execution.yaml")
    timestamps = pd.date_range("2024-01-01T02:31:00Z", periods=3, freq="min")
    bars = pd.DataFrame({"timestamp": timestamps, "open": [1.1000, 1.1001, 1.1005],
                         "high": [1.1002, 1.1007, 1.1007], "low": [1.09995, 1.1000, 1.1004],
                         "close": [1.1001, 1.1006, 1.1006], "volume": 1, "spread_pips": 0.8})
    bos_time = pd.Timestamp("2024-01-01T02:30:00Z")
    candidate = {"candidate_id": "synthetic-e2e-candidate", "symbol": "EURUSD", "direction": "LONG",
                 "state": "BOS_CONFIRMED", "candidate_status": "CANDIDATE_SETUP",
                 "actual_execution_time": bos_time.isoformat(), "actual_signal_time": bos_time.isoformat(),
                 "bos_timestamp": bos_time.isoformat(), "entry_spread_pips": 0.8, "stop_price": 1.0998,
                 "atr_at_setup": 0.001, "liquidity_level": 1.0999, "sweep_timestamp": bos_time.isoformat(),
                 "sweep_confirmation_timestamp": bos_time.isoformat(), "sweep_extreme": 1.09985,
                 "zone": {"source_timestamp": bos_time.isoformat(), "proximal": 1.1000, "distal": 1.0998,
                          "zone_id": "synthetic-zone", "direction": "LONG"},
                 "scheduled_observation_time": "03:30", "observation_window_index": 1,
                 "state_events": [], "zone_events": []}
    monkeypatch.setattr(strategy_v1_module, "generate_v1_candidates", lambda *_args: [candidate])
    first = strategy_v1_module.run_v1_portfolio({"EURUSD": bars}, config, execution, "SYNTHETIC_TEST_DATA")
    second = strategy_v1_module.run_v1_portfolio({"EURUSD": bars}, config, execution, "SYNTHETIC_TEST_DATA")
    assert first == second
    assert first["dataset_hash"] == "SYNTHETIC_TEST_DATA"
    assert len(first["trades"]) == 1
    assert first["events"][0]["candidate_status"] == "EXECUTED"


@pytest.mark.parametrize(("terminal_bar", "expected_state"), [
    ((1.1010, 1.1020, 1.0800), "INVALIDATED"),
    ((1.0950, 1.1050, 1.1000), "MITIGATED"),
    ((1.1010, 1.1020, 1.1010), "EXPIRED"),
])
def test_synthetic_zone_lifecycle_terminal_states(terminal_bar, expected_state):
    times = pd.date_range("2024-01-01T00:15:00Z", periods=4, freq="15min")
    bars = pd.DataFrame({"timestamp": times, "open": [1.1] * 4, "high": [1.102] * 4,
                         "low": [1.098, 1.098, 1.101, 1.101], "close": [1.1] * 4})
    bars.loc[2, ["low", "high", "close"]] = terminal_bar
    zone, events = build_zone_lifecycle(bars, "EURUSD", "LONG", 0, 1, 1.1000, 1.0900, "sweep-fixture", 2)
    assert zone["current_state"] == expected_state
    assert events[-1]["new_state"] == expected_state
    assert pd.Timestamp(events[-1]["detection_timestamp"]) >= pd.Timestamp(events[-2]["detection_timestamp"])


def test_portfolio_records_symbol_risk_and_concurrency_rejections(monkeypatch):
    strategy = load_config(ROOT / "config" / "strategy_v1.yaml")
    strategy["status"] = "FULLY_SPECIFIED"
    execution = load_config(ROOT / "config" / "execution.yaml")
    timestamps = pd.date_range("2024-01-01T02:32:00Z", periods=5, freq="min")
    bars = pd.DataFrame({"timestamp": timestamps, "open": [1.1000] * 5, "high": [1.1002, 1.1007, 1.1007, 1.1007, 1.1007],
                         "low": [1.09995, 1.1000, 1.1000, 1.1000, 1.1000], "close": [1.1001, 1.1006, 1.1006, 1.1006, 1.1006],
                         "volume": 1, "spread_pips": 0.8})

    def candidate(symbol, minute):
        signal = pd.Timestamp("2024-01-01T02:00:00Z") + pd.Timedelta(minutes=minute)
        return {"candidate_id": f"candidate-{symbol}-{minute}", "symbol": symbol, "direction": "LONG",
                "state": "BOS_CONFIRMED", "candidate_status": "CANDIDATE_SETUP",
                "actual_execution_time": signal.isoformat(), "actual_signal_time": signal.isoformat(),
                "bos_timestamp": signal.isoformat(), "entry_spread_pips": 0.8, "stop_price": 1.0998,
                "atr_at_setup": 0.001, "liquidity_level": 1.0999, "sweep_timestamp": signal.isoformat(),
                "sweep_confirmation_timestamp": signal.isoformat(), "sweep_extreme": 1.09985,
                "zone": {"source_timestamp": signal.isoformat(), "proximal": 1.1000, "distal": 1.0998},
                "scheduled_observation_time": "04:00" if minute >= 60 else "03:30", "observation_window_index": 2 if minute >= 60 else 1,
                "state_events": [], "zone_events": []}

    generated = {"EURUSD": [candidate("EURUSD", 31), candidate("EURUSD", 60)],
                 "GBPUSD": [candidate("GBPUSD", 32)]}
    monkeypatch.setattr(strategy_v1_module, "generate_v1_candidates", lambda _bars, symbol, _config: generated[symbol])
    result = strategy_v1_module.run_v1_portfolio({"EURUSD": bars, "GBPUSD": bars}, strategy, execution, "SYNTHETIC_TEST_DATA")
    statuses = {(event["symbol"], event["candidate_status"]) for event in result["events"]}
    assert ("EURUSD", "EXECUTED") in statuses
    assert ("EURUSD", "RISK_LIMIT_REJECTED") in statuses
    assert ("GBPUSD", "CONCURRENT_POSITION_REJECTED") in statuses

    strategy["risk"]["max_trades_global_per_trading_date"] = 1
    generated["GBPUSD"] = [candidate("GBPUSD", 60)]
    global_limited = strategy_v1_module.run_v1_portfolio({"EURUSD": bars, "GBPUSD": bars}, strategy, execution, "SYNTHETIC_TEST_DATA")
    assert any(event["symbol"] == "GBPUSD" and event["candidate_status"] == "RISK_LIMIT_REJECTED" for event in global_limited["events"])


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
