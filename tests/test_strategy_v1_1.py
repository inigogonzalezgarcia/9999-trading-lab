"""V1.1 experiment: new engine parameters default to V1 behaviour and the V1.1 configuration activates them."""
from __future__ import annotations

import copy

import pandas as pd
import pytest

from backend.app import service
from backend.app.core import load_config
from backend.app.strategy.candidates import _LevelTable, level_max_age_ns, stop_rules_from
from backend.app.strategy_v1 import run_v1_portfolio
from tests.test_m1_completion_gates import _raw_m1_fixture

ROOT = service.ROOT


def test_stop_rules_default_to_v1_and_reject_unknown_reference():
    assert stop_rules_from({}) == {"reference": "sweep_extreme", "buffer_atr": 0.10, "max_distance_atr": 3.0}
    v1 = load_config(ROOT / "config" / "strategy_v1.yaml")
    assert stop_rules_from(v1)["reference"] == "sweep_extreme" and stop_rules_from(v1)["max_distance_atr"] == 3.0
    v11 = load_config(ROOT / "config" / "strategy_v1_1.yaml")
    assert stop_rules_from(v11)["reference"] == "zone_distal"
    with pytest.raises(ValueError):
        stop_rules_from({"stop": {"reference": "moon"}})


def test_level_max_age_defaults_to_never_and_filters_old_levels():
    assert level_max_age_ns({}) is None
    assert level_max_age_ns({"liquidity": {"level_max_age_m15_bars": 4}}) == 4 * 15 * 60 * 10**9
    base = pd.Timestamp("2024-01-01T00:00:00Z")
    levels = [{"kind": "LOW", "price": 1.1000, "effective_from": base, "superseded_at": None, "oldest_confirmed": base, "timeframes": ["H1"], "constituents": [], "cluster_id": "old"},
              {"kind": "LOW", "price": 1.1000, "effective_from": base + pd.Timedelta(hours=5), "superseded_at": None, "oldest_confirmed": base + pd.Timedelta(hours=5), "timeframes": ["M15"], "constituents": [], "cluster_id": "new"}]
    table = _LevelTable(levels)
    now = int((base + pd.Timedelta(hours=6)).value)
    assert table.levels[table.first_eligible(now, 1.0999, 1.1001)]["cluster_id"] == "old"  # V1: H1 priority, no expiry
    assert table.levels[table.first_eligible(now, 1.0999, 1.1001, max_age_ns=2 * 3600 * 10**9)]["cluster_id"] == "new"  # old level expired
    assert table.first_eligible(now, 1.0999, 1.1001, max_age_ns=10**9) is None


def test_v1_1_configuration_loads_and_differs_only_in_logged_decisions():
    v1 = load_config(ROOT / "config" / "strategy_v1.yaml")
    v11 = load_config(ROOT / "config" / "strategy_v1_1.yaml")
    assert v11["strategy_version"] == "1.1" and v11["status"] == "FULLY_SPECIFIED" and v11["derived_from"] == "strategy_v1.yaml"
    assert v11["observation"]["windows"] == [{"start": "09:00", "end": "09:45"}, {"start": "09:45", "end": "10:30"}]
    assert v11["execution"]["session_end"] == "13:00" and v11["liquidity"]["level_max_age_m15_bars"] == 1920
    unchanged = ("structure", "pullback", "sweep", "zones", "displacement", "two_leg", "bos", "setup", "entry", "target", "risk", "eligibility")
    for key in unchanged:
        assert v1[key] == v11[key], key


def test_strategy_selection_in_service(tmp_path):
    assert "strategy_v1.yaml" in service.available_strategies() and "strategy_v1_1.yaml" in service.available_strategies()
    strategy, execution, _ = service.load_configs(strategy_file="strategy_v1_1.yaml")
    assert strategy["strategy_version"] == "1.1"
    with pytest.raises(ValueError):
        service.resolve_strategy_file("../etc/passwd.yaml")
    with pytest.raises(ValueError):
        service.resolve_strategy_file("strategy_missing.yaml")
    frame = _raw_m1_fixture()
    frame = frame.assign(timestamp=frame.timestamp - pd.Timedelta(minutes=1))
    path = tmp_path / "SYNTHETIC_TEST_DATA.csv"
    frame.to_csv(path, index=False)
    dataset = service.load_dataset(path)
    result = service.run_backtest(dataset, "EURUSD", {"daily_contexts": "none", "include_chart": False, "strategy": "strategy_v1_1.yaml"})
    assert result["strategy_version"] == "1.1" and result["reproducibility"]["strategy_file"] == "strategy_v1_1.yaml"
    assert result["report"]["timing"]["windows"][0]["start"] == "09:00"


def test_zone_distal_stop_changes_candidate_stop_but_not_detection():
    """Same fixture, two stop references: identical candidate ids, different stop prices."""
    bars = _raw_m1_fixture()
    v1 = load_config(ROOT / "config" / "strategy_v1.yaml")
    execution = load_config(ROOT / "config" / "execution.yaml")
    variant = copy.deepcopy(v1)
    variant["stop"]["reference"] = "zone_distal"
    base = run_v1_portfolio({"EURUSD": bars}, v1, execution, "FIXTURE", include_daily_contexts=False)
    other = run_v1_portfolio({"EURUSD": bars}, variant, execution, "FIXTURE", include_daily_contexts=False)
    complete_base = [e for e in base["events"] if e.get("state") == "BOS_CONFIRMED"]
    complete_other = [e for e in other["events"] if e.get("state") == "BOS_CONFIRMED"]
    assert [e["candidate_id"] for e in complete_base] == [e["candidate_id"] for e in complete_other]
    assert complete_base and complete_base[0]["stop_reference"] == "sweep_extreme" and complete_other[0]["stop_reference"] == "zone_distal"
    assert complete_other[0]["stop_price"] == pytest.approx(complete_other[0]["zone"]["distal"] - 0.10 * complete_other[0]["atr_at_setup"])


def test_instrument_pip_size_drives_execution_costs(tmp_path):
    """A JPY pair prices one pip at 0.01: the same spread in pips costs 100x more in price terms."""
    from backend.app.instruments import dukascopy_point, known_instruments, pip_size, spec
    from backend.app.strategy.simulation import _simulate_candidate

    assert pip_size("USDJPY") == 0.01 and dukascopy_point("USDJPY") == 1000 and pip_size("EURUSD") == 0.0001
    assert "USDJPY" in known_instruments() and spec("UNKNOWN")["pip"] == 0.0001
    execution = load_config(ROOT / "config" / "execution.yaml")
    strategy = load_config(ROOT / "config" / "strategy_v1.yaml")
    timestamps = pd.date_range("2024-01-01T02:31:00Z", periods=3, freq="min")
    bars = pd.DataFrame({"timestamp": timestamps, "open": [150.000, 150.010, 150.050], "high": [150.020, 150.070, 150.400],
                         "low": [149.995, 150.000, 150.040], "close": [150.010, 150.060, 150.350], "volume": 1, "spread_pips": 1.0})
    candidate = {"candidate_id": "jpy", "symbol": "USDJPY", "direction": "LONG", "actual_execution_time": "2024-01-01T02:30:00+00:00",
                 "actual_signal_time": "2024-01-01T02:30:00+00:00", "bos_timestamp": "2024-01-01T02:30:00+00:00", "stop_price": 149.90,
                 "atr_at_setup": 0.10, "liquidity_level": 149.95, "sweep_timestamp": "2024-01-01T02:30:00+00:00", "sweep_extreme": 149.94,
                 "zone": {"proximal": 150.0, "distal": 149.9, "source_timestamp": "2024-01-01T02:30:00+00:00"},
                 "scheduled_observation_time": "03:30", "observation_window_index": 1}
    outcome = _simulate_candidate(candidate, bars, execution, strategy, 1.0)
    trade = outcome["trade"]
    assert trade is not None
    # entry = open + spread/2 + slippage = 150.000 + 0.005 + 0.001
    assert trade["entry_price"] == pytest.approx(150.006) and trade["exit_reason"] == "TAKE_PROFIT"
