"""Metrics and research-protocol checks on synthetic trade lists and stubbed engine runs."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from backend.app import research
from backend.app.metrics import daily_r_series, equity_curve, metrics

SYNTHETIC = "SYNTHETIC_TEST_DATA"


def _trade(day: str, r: float, symbol: str = "EURUSD", window: str = "1") -> dict:
    entry = pd.Timestamp(f"{day}T02:31:00Z")
    return {"trade_id": f"{symbol}-{day}-{r}", "symbol": symbol, "date": day, "observation_window": window,
            "entry_timestamp": entry.isoformat(), "exit_timestamp": (entry + pd.Timedelta(minutes=30)).isoformat(),
            "entry_price": 1.1, "stop_price": 1.099, "r_multiple": r, "pnl": r * 5.0, "mfe": max(r, 0.2), "mae": min(r, -0.1),
            "exit_reason": "TAKE_PROFIT" if r > 0 else "STOP_LOSS"}


def test_metrics_do_not_annualise_per_trade_statistics():
    trades = [_trade("2024-01-02", 2.0), _trade("2024-01-03", -1.0), _trade("2024-01-04", -1.0), _trade("2024-01-08", 2.0)]
    result = metrics(trades, "2024-01-01T00:00:00Z", "2024-01-12T23:59:00Z")
    assert result["total_trades"] == 4 and result["winning_trades"] == 2 and result["losing_trades"] == 2
    assert result["expectancy_r"] == pytest.approx(0.5)
    assert result["profit_factor"] == pytest.approx(2.0)
    assert result["max_drawdown_r"] == pytest.approx(2.0)
    assert result["max_consecutive_losses"] == 2
    r = np.array([2.0, -1.0, -1.0, 2.0])
    assert result["sharpe_per_trade"] == pytest.approx(r.mean() / r.std(ddof=1))
    # Daily series spans every weekday of the period, including zero days.
    daily = daily_r_series(trades, "2024-01-01T00:00:00Z", "2024-01-12T23:59:00Z")
    assert len(daily) == 10 and result["daily"]["trading_days"] == 10 and result["daily"]["days_with_trades"] == 4
    expected = daily.mean() / daily.std(ddof=1) * math.sqrt(252)
    assert result["daily"]["annualized_sharpe"] == pytest.approx(expected)
    assert result["sharpe"] == result["daily"]["annualized_sharpe"]
    assert result["by_symbol"]["EURUSD"]["trades"] == 4
    assert result["exit_reasons"] == {"STOP_LOSS": 2, "TAKE_PROFIT": 2}
    assert result["by_month"] == {"2024-01": {"trades": 4, "total_r": 2.0, "expectancy_r": 0.5, "win_rate": 0.5}}
    assert list(result["by_weekday"]) == ["Mon", "Tue", "Wed", "Thu"] and result["by_weekday"]["Mon"]["trades"] == 1
    assert list(result["by_hour"]) == ["02"]  # 02:31 UTC entries; fixture trades carry no timezone -> UTC


def test_metrics_handle_empty_trade_lists():
    result = metrics([], "2024-01-01T00:00:00Z", "2024-01-05T00:00:00Z")
    assert result["total_trades"] == 0 and result["profit_factor"] is None
    assert result["daily"]["trading_days"] == 5 and result["daily"]["annualized_sharpe"] is None
    assert equity_curve([]) == []


def test_equity_curve_tracks_cumulative_r_and_drawdown():
    curve = equity_curve([_trade("2024-01-02", 2.0), _trade("2024-01-03", -1.0), _trade("2024-01-04", -1.5)])
    assert [point["cumulative_r"] for point in curve] == pytest.approx([2.0, 1.0, -0.5])
    assert [point["drawdown_r"] for point in curve] == pytest.approx([0.0, 1.0, 2.5])


def test_chronological_splits_are_ordered_and_disjoint():
    bars = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", "2024-12-31", freq="D", tz="UTC")})
    splits = research.chronological_splits({"EURUSD": bars}, 0.6, 0.2)
    train, validation, oos = (pd.Timestamp(splits[k]["start"]) for k in ("train", "validation", "out_of_sample"))
    assert train < validation < oos
    assert splits["train"]["end"] == splits["validation"]["start"]
    assert splits["validation"]["end"] == splits["out_of_sample"]["start"]
    with pytest.raises(ValueError):
        research.chronological_splits({"EURUSD": bars}, 0.9, 0.2)


def test_monte_carlo_is_seeded_and_reports_observed_path():
    returns = [2.0, -1.0, -1.0, 2.0, -1.0, 2.0]
    first = research.monte_carlo(returns, simulations=200, seed=3)
    second = research.monte_carlo(returns, simulations=200, seed=3)
    assert first == second
    assert first["observed"]["final_r"] == pytest.approx(3.0)
    assert first["trades_per_path"] == 6 and 0.0 <= first["probability_losing"] <= 1.0
    assert research.monte_carlo([], 10)["trades_per_path"] == 0


def _stub_engine(monkeypatch):
    """Replace the engine with a stub that emits one trade per Monday present in the supplied bars."""

    def fake_run(data_by_symbol, strategy_config, execution_config, dataset_hash=None, **_kwargs):
        trades, events = [], []
        for symbol, frame in data_by_symbol.items():
            for stamp in frame.timestamp:
                if stamp.dayofweek == 0:
                    day = stamp.date().isoformat()
                    r = 2.0 if stamp.day % 2 else -1.0
                    trades.append(_trade(day, r, symbol))
                    events.append({"sweep_confirmation_timestamp": stamp.isoformat(), "candidate_status": "EXECUTED"})
        return {"trades": trades, "events": events, "daily_contexts": [], "liquidity_events": [], "zone_events": [], "state_events": []}

    monkeypatch.setattr(research, "run_v1_portfolio", fake_run)


def test_run_period_discards_warmup_trades(monkeypatch):
    _stub_engine(monkeypatch)
    bars = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", "2024-03-31", freq="D", tz="UTC")})
    start, end = pd.Timestamp("2024-02-01T00:00:00Z"), pd.Timestamp("2024-03-01T00:00:00Z")
    result = research.run_period({"EURUSD": bars}, {}, {}, start, end, warmup_days=10, dataset_hash=SYNTHETIC)
    entries = [pd.Timestamp(trade["entry_timestamp"]) for trade in result["trades"]]
    assert entries and all(start <= entry < end for entry in entries)
    assert result["period"]["warmup_days"] == 10
    assert result["metrics"]["total_trades"] == len(entries)


def test_walk_forward_builds_chronological_folds(monkeypatch):
    _stub_engine(monkeypatch)
    bars = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", "2024-06-30", freq="D", tz="UTC")})
    report = research.walk_forward({"EURUSD": bars}, {}, {}, train_days=60, test_days=30, warmup_days=5, dataset_hash=SYNTHETIC)
    assert report["fold_count"] >= 3
    previous_end = None
    for fold in report["folds"]:
        in_sample, oos = fold["in_sample"]["period"], fold["out_of_sample"]["period"]
        assert in_sample["end"] == oos["start"]
        if previous_end:
            assert pd.Timestamp(oos["start"]) >= pd.Timestamp(previous_end)
        previous_end = oos["start"]
    concatenated = report["out_of_sample_concatenated"]
    assert concatenated["trades"] == sum(len(fold["out_of_sample_trades"]) for fold in report["folds"])
    assert 0.0 <= concatenated["consistency"] <= 1.0


def test_sensitivity_varies_one_parameter_at_a_time(monkeypatch):
    _stub_engine(monkeypatch)
    bars = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", "2024-02-29", freq="D", tz="UTC")})
    strategy = {"target": {"baseline": "2.0R", "experiments": ["1.5R", "2.0R"]}, "risk": {"baseline_equity_risk_fraction": 0.005}}
    execution = {"slippage": {"baseline_pips": 0.1, "sensitivity_pips": [0.0, 0.5]}}
    grid = [{"scope": "strategy", "path": "target.baseline", "values": ["1.5R", "2.0R"]},
            {"scope": "execution", "path": "slippage.baseline_pips", "values": [0.0, 0.5]},
            {"scope": "multi", "path": "session", "values": [{"label": "london", "changes": [
                {"scope": "strategy", "path": "target.baseline", "value": "3.0R"}, {"scope": "execution", "path": "slippage.baseline_pips", "value": 0.2}]}]},
            {"scope": "strategy", "path": "missing.path", "values": [1]}]
    report = research.parameter_sensitivity({"EURUSD": bars}, strategy, execution, grid, SYNTHETIC)
    assert len(report["variants"]) == 6
    assert report["variants"][4]["value"] == "london" and report["variants"][4]["error"] is None
    assert report["variants"][0]["parameter"] == "target.baseline" and report["variants"][0]["error"] is None
    assert report["variants"][-1]["error"]  # unknown path is reported, not raised
    assert strategy["target"]["baseline"] == "2.0R"  # baseline configuration untouched
