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


def test_trade_explainers_cover_every_trade_with_candles_levels_and_steps(tmp_path):
    dataset = _dataset(tmp_path)
    result = service.run_backtest(dataset, "EURUSD", {"daily_contexts": "none", "include_chart": False})
    assert result["trades"], "fixture must produce a trade"
    for trade in result["trades"]:
        explainer = result["trade_explainers"][trade["trade_id"]]
        assert explainer["candles"] and explainer["window"]["bars"] == len(explainer["candles"])
        ids = {level["id"] for level in explainer["levels"]}
        assert {"liquidity", "sweep_extreme", "zone_proximal", "zone_distal", "entry", "stop", "target"} <= ids
        steps = [step["id"] for step in explainer["steps"]]
        assert steps[0] == "sweep" and steps[-1] == "exit" and "bos" in steps and "entry" in steps
        assert all(step["time"] for step in explainer["steps"])
        first, last = explainer["candles"][0]["time"], explainer["candles"][-1]["time"]
        assert first <= explainer["steps"][0]["time"] and last >= explainer["steps"][-1]["time"]
        assert explainer["rules"]["stop_distance_atr"] is not None and explainer["notice"]


def test_pdf_report_renders_for_backtest_and_research(tmp_path):
    pytest.importorskip("reportlab")
    from backend.app.report import build_pdf

    dataset = _dataset(tmp_path)
    result = service.run_backtest(dataset, "EURUSD", {"daily_contexts": "none", "include_chart": False})
    payload = build_pdf(result, "backtest", {"label": "fixture"})
    assert payload.startswith(b"%PDF") and len(payload) > 3000
    research = {"baseline": {"trades": 1, "expectancy_r": 0.5, "total_r": 0.5, "win_rate": 1.0, "profit_factor": None, "max_drawdown_r": 0.0, "annualized_sharpe": None, "trading_days": 5},
                "limitations": ["synthetic"], "reproducibility": result["reproducibility"], "quality": result["quality"],
                "monte_carlo": {"simulations": 10, "trades_per_path": 1, "probability_losing": 0.0, "final_r_percentiles": {"5": 0.5, "50": 0.5, "95": 0.5}, "max_drawdown_r_percentiles": {"50": 0.0, "95": 0.0}},
                "sensitivity": {"baseline": {"trades": 1, "expectancy_r": 0.5, "total_r": 0.5, "max_drawdown_r": 0.0}, "variants": [{"scope": "strategy", "parameter": "x", "value": 1, "trades": 1, "expectancy_r": 0.5, "total_r": 0.5, "max_drawdown_r": 0.0, "error": None}], "note": "n"}}
    assert build_pdf(research, "research").startswith(b"%PDF")


def test_export_web_writes_trimmed_runs_and_index(tmp_path):
    """The static site export keeps what the UI renders, drops the audit streams and carries the notice."""
    import json

    from backend.app import webexport

    frame = _raw_m1_fixture()
    frame = frame.assign(timestamp=frame.timestamp - __import__("pandas").Timedelta(minutes=1))
    (tmp_path / "data").mkdir()
    frame.to_csv(tmp_path / "data" / "SYNTHETIC.csv", index=False)
    spec = {"runs": [
        {"id": "synthetic-v1", "kind": "backtest", "dataset": "data/SYNTHETIC.csv", "symbol": "EURUSD", "label": {"es": "Sintético", "en": "Synthetic"}, "order": 1},
        {"id": "synthetic-v1-research", "kind": "research", "dataset": "data/SYNTHETIC.csv", "symbol": "EURUSD", "mc_simulations": 50,
         "benchmark_simulations": 5, "walk_forward": False, "sensitivity": False, "order": 2},
    ]}
    index = webexport.export_site(spec, tmp_path / "site", data_root=tmp_path, pdf=False)
    assert [run["id"] for run in index["runs"]] == ["synthetic-v1", "synthetic-v1-research"]
    assert index["notice"] == service.EDUCATIONAL_NOTICE
    payload = json.loads((tmp_path / "site" / "runs" / "synthetic-v1.json").read_text())
    assert payload["run_id"] == "synthetic-v1" and payload["notice"] == service.EDUCATIONAL_NOTICE
    assert "events" not in payload and "liquidity_events" not in payload and "daily_contexts" not in payload
    assert payload["trades"] and payload["trade_explainers"] and payload["chart"]["series"]["EURUSD"]
    assert payload["web_export"]["trimmed"] is True
    research = json.loads((tmp_path / "site" / "runs" / "synthetic-v1-research.json").read_text())
    assert research["baseline"] and research["monte_carlo"] and "options" not in research
    # Re-exporting a single run keeps the other entry in the index.
    index = webexport.export_site(spec, tmp_path / "site", data_root=tmp_path, pdf=False, only=["synthetic-v1"])
    assert len(index["runs"]) == 2
