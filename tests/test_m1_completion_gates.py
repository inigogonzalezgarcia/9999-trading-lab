"""Raw-M1 acceptance gates for the causal V1 engine.

The helper returns only M1 bars. Strategy code under test receives no supplied
swings, liquidity levels, zones, sweeps, candidates, or higher-timeframe bars.
"""
from __future__ import annotations

import pandas as pd

from backend.app.core import load_config
from backend.app.strategy_v1 import (
    _simulate_candidate,
    build_daily_contexts,
    generate_v1_candidates,
)


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
EXPECTED_STATES = [
    "WAITING_FOR_BIAS", "WAITING_FOR_PULLBACK", "WAITING_FOR_LIQUIDITY",
    "LIQUIDITY_SWEEP_DETECTED", "WAITING_FOR_ZONE", "ZONE_CONFIRMED",
    "DISPLACEMENT_DETECTED", "WAITING_FOR_RETRACEMENT", "LEG_2_DETECTED",
    "WAITING_FOR_BOS", "BOS_CONFIRMED", "READY_FOR_ENTRY",
]


def _raw_m1_fixture(start: str = "2023-12-31T07:00:00Z",
                    terminal: str | None = None) -> pd.DataFrame:
    """Return deterministic M1 candles encoding a causal setup and its lifecycle."""
    start_at = pd.Timestamp(start)
    hourly_base = [1.104 + hour * 0.00005 for hour in range(25)]
    hourly_structure = {
        1: (1.100, 1.103), 3: (1.099, 1.105),
        5: (1.101, 1.104), 7: (1.100, 1.106),
        9: (1.102, 1.105), 11: (1.101, 1.107),
        13: (1.103, 1.106), 17: (1.102, 1.108),
        19: (1.103, 1.109), 21: (1.105, 1.108),
        23: (1.104, 1.110),
    }
    # H1 bullish structure is already confirmed before the intended setup.
    hourly_structure.pop(15, None)

    rows = []
    for index in range(100):
        price = hourly_base[index // 4]
        rows.append([price, price + 0.00015, price - 0.00015, price])

    for hour, (low, high) in hourly_structure.items():
        index = hour * 4 + 1
        rows[index][1] = high
        rows[index][2] = low
        rows[index][3] = hourly_base[hour] + 0.00001

    # Reproducible pre-event range establishes the frozen M15 ATR from bars.
    for index in range(50, 62):
        price = 1.1045 + (index % 3) * 0.00003
        rows[index] = [price, price + 0.00135, price - 0.00135, price]

    pattern = {
        62: (1.1050, 1.1052, 1.1048, 1.1050),
        63: (1.1050, 1.1052, 1.1048, 1.1050),
        64: (1.1050, 1.1059, 1.1049, 1.1052),
        65: (1.1050, 1.1052, 1.1042, 1.1043),
        66: (1.1043, 1.1046, 1.1038, 1.1040),
        67: (1.1040, 1.1042, 1.1033, 1.1035),
        68: (1.1035, 1.1037, 1.1020, 1.1024),  # M1 sweep below 1.1020
        69: (1.1024, 1.1025, 1.1023, 1.1024),  # last bearish source candle
        70: (1.1024, 1.1062, 1.10235, 1.1061),  # displacement and structure break
        71: (1.1061, 1.1062, 1.1044, 1.1048),  # retracement
        72: (1.1048, 1.1065, 1.1047, 1.1050),  # second leg, below BOS close
    }
    if terminal == "MITIGATED":
        pattern[71] = (1.1048, 1.1050, 1.1023, 1.1046)
    elif terminal == "INVALIDATED":
        pattern[71] = (1.1024, 1.1025, 1.1017, 1.1018)
    for index, ohlc in pattern.items():
        rows[index] = list(ohlc)

    for index in range(73, 100):
        price = 1.1062 + 0.0001 * (index - 76)
        rows[index] = [price, price + 0.00005, price - 0.00005, price + 0.00002]

    m15_closes = pd.date_range(start_at + pd.Timedelta(minutes=15), periods=100, freq="15min")
    m1_rows = []
    for index, (opened, high, low, closed) in enumerate(rows):
        m15_close = m15_closes[index]
        closes = [opened + (closed - opened) * minute / 14 for minute in range(15)]
        for minute, close in enumerate(closes):
            prior = opened if minute == 0 else closes[minute - 1]
            minute_high, minute_low = max(prior, close), min(prior, close)
            if minute == 5:
                minute_high = max(minute_high, high)
            if minute == 6:
                minute_low = min(minute_low, low)
            # This single M1 observation is the only breach below the 1.1020 level.
            if index == 68 and minute == 6:
                minute_low = 1.1019
            if terminal == "INVALIDATED" and index == 71:
                minute_low = min(minute_low, 1.1017)
            m1_rows.append([
                m15_close - pd.Timedelta(minutes=14 - minute),
                prior, minute_high, minute_low, close, 1, 0.8,
            ])
    return pd.DataFrame(m1_rows, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "spread_pips",
    ])


def test_daily_context_zone_inventory_is_causal_and_lifecycle_aware():
    config = load_config(ROOT / "config" / "strategy_v1.yaml")
    raw_m1 = _raw_m1_fixture()
    contexts = build_daily_contexts({"EURUSD": raw_m1}, config, "M1-GATE-FIXTURE")
    context = next(item for item in contexts if item["trading_date"] == "2024-01-01")
    cutoff = pd.Timestamp(context["created_at"])

    assert context["created_at"] == "2024-01-01T00:50:00+00:00"
    assert len(context["active_zones"]) == 1
    zone = context["active_zones"][0]
    assert zone["current_state"] == "CONFIRMED"
    assert pd.Timestamp(zone["confirmation_timestamp"]) <= cutoff

    truncated = build_daily_contexts(
        {"EURUSD": raw_m1.loc[raw_m1.timestamp <= cutoff]}, config, "M1-GATE-FIXTURE",
    )
    truncated_context = next(item for item in truncated if item["trading_date"] == "2024-01-01")
    assert context == truncated_context

    for lifecycle, start in (("MITIGATED", "2023-12-31T06:45:00Z"),
                             ("INVALIDATED", "2023-12-31T06:45:00Z"),
                             ("EXPIRED", "2023-12-31T04:00:00Z")):
        lifecycle_m1 = _raw_m1_fixture(start=start, terminal=lifecycle)
        lifecycle_contexts = build_daily_contexts(
            {"EURUSD": lifecycle_m1}, config, f"M1-{lifecycle}-FIXTURE",
        )
        lifecycle_context = next(item for item in lifecycle_contexts if item["trading_date"] == "2024-01-01")
        assert lifecycle_context["active_zones"] == []


def test_complete_signal_is_discovered_and_executed_from_m1_only():
    config = load_config(ROOT / "config" / "strategy_v1.yaml")
    execution = load_config(ROOT / "config" / "execution.yaml")
    raw_m1 = _raw_m1_fixture()

    candidates = generate_v1_candidates(raw_m1, "EURUSD", config)
    complete = [item for item in candidates if item["candidate_status"] == "CANDIDATE_SETUP"]
    assert len(complete) == 1
    candidate = complete[0]
    assert [event["state"] for event in candidate["state_events"]] == EXPECTED_STATES
    assert candidate["liquidity_level"] == 1.102
    assert candidate["zone"]["confirmation_timestamp"] == "2024-01-01T00:45:00+00:00"
    assert candidate["bos_timestamp"] == "2024-01-01T01:30:00+00:00"
    assert candidate["actual_execution_time"] == "2024-01-01T01:30:00+00:00"

    outcome = _simulate_candidate(candidate, raw_m1, execution, config, equity=1.0)
    assert outcome["candidate_status"] == "EXECUTED"
    trade = outcome["trade"]
    assert trade["entry_timestamp"] == candidate["actual_execution_time"]
    assert trade["stop_price"] == candidate["stop_price"]
    assert trade["target_price"] > trade["entry_price"]

    # Remove only the M1 candle that contains the liquidity breach. The full
    # sweep-to-entry signal must disappear from the detector output.
    causal_candle_index = 68 * 15 + 6
    without_breach = raw_m1.drop(index=causal_candle_index).reset_index(drop=True)
    changed = generate_v1_candidates(without_breach, "EURUSD", config)
    assert not any(item["candidate_status"] == "CANDIDATE_SETUP" for item in changed)
    assert not any(item.get("liquidity_level") == 1.102 for item in changed)
