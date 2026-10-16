"""Service pipeline, run store and job manager on synthetic fixtures (no HTTP layer required)."""
from __future__ import annotations

import time

import pytest

from backend.app import service
from backend.app.jobs import JobManager
from backend.app.store import RunStore
from tests.test_m1_completion_gates import _raw_m1_fixture


def _dataset(tmp_path):
    frame = _raw_m1_fixture()
    frame = frame.assign(timestamp=frame.timestamp - __import__("pandas").Timedelta(minutes=1))  # loader shifts opens to closes
    path = tmp_path / "SYNTHETIC_TEST_DATA.csv"
    frame.to_csv(path, index=False)
    return service.load_dataset(path)


def test_run_backtest_pipeline_attaches_metrics_chart_and_notice(tmp_path):
    dataset = _dataset(tmp_path)
    result = service.run_backtest(dataset, "EURUSD", {"daily_contexts": "none"})
    assert result["backtest_blocked"] is False
    assert result["notice"] == service.EDUCATIONAL_NOTICE
    assert result["metrics"]["total_trades"] == result["signal_count"] == len(result["trades"]) >= 1
    assert result["equity_curve"][-1]["cumulative_r"] == pytest.approx(result["metrics"]["total_r"])
    assert result["chart"]["timeframe"] == "M15" and len(result["chart"]["series"]["EURUSD"]) > 10
    assert result["report"]["daily_contexts"] == "none" and result["daily_contexts"] == []
    assert result["reproducibility"]["run_options"]["daily_contexts"] == "none"
    assert "EXECUTED" in result["report"]["rejections"] or result["report"]["rejections"]


def test_context_modes_and_fixed_spread_override(tmp_path):
    strategy, execution, _ = service.load_configs(fixed_spread_pips=1.2)
    assert execution["spread"]["fixed_fallback_pips"] == 1.2 and execution["spread"]["fixed_fallback_origin"] == "runtime_override"
    adjusted, include = service.apply_context_mode(strategy, "lookback:20")
    assert include is True and adjusted["preparation"]["context_lookback_days"] == 20 and "context_lookback_days" not in strategy["preparation"]
    assert service.apply_context_mode(strategy, "none")[1] is False
    with pytest.raises(ValueError):
        service.apply_context_mode(strategy, "weekly")
    dataset = _dataset(tmp_path)
    full = service.run_backtest(dataset, "EURUSD", {"daily_contexts": "full", "include_chart": False})
    assert full["daily_contexts"] and "chart" not in full
    assert full["daily_contexts"][0]["detail"] == "summary" and "h1_structure" not in full["daily_contexts"][0]
    detailed = service.run_backtest(dataset, "EURUSD", {"daily_contexts": "full", "include_chart": False, "context_detail": "full"})
    assert "h1_structure" in detailed["daily_contexts"][0]


def test_run_store_round_trip(tmp_path):
    store = RunStore(tmp_path / "runs.sqlite3")
    result = {"trades": [{"r_multiple": 1.0}], "reproducibility": {"strategy_version": "1.0", "config_hash": "abc", "software_revision": "rev"}, "dataset_version": "hash"}
    run_id = store.save("backtest", result, {"trades": 1}, "EURUSD", "file.csv", "first")
    listing = store.list()
    assert listing[0]["id"] == run_id and listing[0]["summary"] == {"trades": 1} and listing[0]["dataset_hash"] == "hash"
    assert store.get(run_id)["trades"][0]["r_multiple"] == 1.0
    assert store.relabel(run_id, "renamed") and store.meta(run_id)["label"] == "renamed"
    assert store.list(kind="research") == []
    assert store.delete(run_id) and store.get(run_id) is None and not store.delete(run_id)
    store.close()


def test_job_manager_tracks_progress_and_failures():
    manager = JobManager(workers=1)

    def work(progress):
        progress("half", 0.5)
        return {"ok": True}

    def broken(_progress):
        raise RuntimeError("boom")

    good = manager.submit("backtest", work, {"symbol": "EURUSD"})
    bad = manager.submit("research", broken)
    for _ in range(100):
        states = {manager.public(good["job_id"])["status"], manager.public(bad["job_id"])["status"]}
        if states <= {"done", "failed"}:
            break
        time.sleep(0.02)
    assert manager.public(good["job_id"])["result"] == {"ok": True}
    assert manager.public(bad["job_id"])["error"] == "boom"
    assert len(manager.list()) == 2 and manager.public("missing") is None
