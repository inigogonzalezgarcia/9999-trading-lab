"""API-path checks using isolated synthetic fixtures only."""
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from backend.app import main, service, strategy_v1
from backend.app.core import load_config as read_config


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_LABEL = "SYNTHETIC_TEST_DATA"


def _enable_engine_config(monkeypatch):
    def configured_loader(path):
        result = read_config(path)
        if Path(path).name == "strategy_v1.yaml":
            result["status"] = "FULLY_SPECIFIED"
        return result

    monkeypatch.setattr(service, "load_config", configured_loader)


def _candidate(spread):
    bos_time = pd.Timestamp("2024-01-01T02:31:00Z")
    return {"candidate_id": "api-synthetic-candidate", "symbol": "EURUSD", "direction": "LONG",
            "state": "BOS_CONFIRMED", "candidate_status": "CANDIDATE_SETUP",
            "actual_execution_time": bos_time.isoformat(), "actual_signal_time": bos_time.isoformat(),
            "bos_timestamp": bos_time.isoformat(), "entry_spread_pips": spread, "stop_price": 1.0998,
            "atr_at_setup": 0.001, "liquidity_level": 1.0999, "sweep_timestamp": bos_time.isoformat(),
            "sweep_confirmation_timestamp": bos_time.isoformat(), "sweep_extreme": 1.09985,
            "zone": {"source_timestamp": bos_time.isoformat(), "proximal": 1.1000, "distal": 1.0998,
                     "zone_id": "api-synthetic-zone", "direction": "LONG"},
            "scheduled_observation_time": "03:30", "observation_window_index": 1,
            "state_events": [], "zone_events": []}


def _csv(spread: bool) -> bytes:
    spread_header = ",spread_pips" if spread else ""
    spread_values = ",0.8" if spread else ""
    lines = [f"timestamp,open,high,low,close,volume,dataset_classification{spread_header}"]
    rows = [("02:31", 1.1000, 1.1002, 1.09995, 1.1001),
            ("02:32", 1.1001, 1.1007, 1.1000, 1.1006),
            ("02:33", 1.1005, 1.1007, 1.1004, 1.1006)]
    for clock, opened, high, low, close in rows:
        lines.append(f"2024-01-01T{clock}:00Z,{opened},{high},{low},{close},1,{SYNTHETIC_LABEL}{spread_values}")
    return ("\n".join(lines) + "\n").encode()


def test_api_pending_configuration_still_blocks_backtest_and_returns_metadata(monkeypatch):
    def pending_loader(path):
        result = read_config(path)
        if Path(path).name == "strategy_v1.yaml":
            result["status"] = "IMPLEMENTATION_PENDING"
        return result

    monkeypatch.setattr(service, "load_config", pending_loader)
    client = TestClient(main.app)
    response = client.post("/api/backtest", data={"symbol": "EURUSD", "timeframe": "M1"},
                           files={"file": ("SYNTHETIC_TEST_DATA.csv", _csv(False), "text/csv")})
    assert response.status_code == 200
    result = response.json()
    assert result["strategy_status"] == "IMPLEMENTATION_PENDING"
    assert result["backtest_blocked"] is True
    assert result["trades"] == [] and result["metrics"] is None
    assert result["reproducibility"]["dataset_hash"] == result["dataset_version"]
    assert result["reproducibility"]["config_hash"]
    assert result["reproducibility"]["timezone_database_version"]["version"]
    assert result["reproducibility"]["software_revision"].startswith("source-sha256:")


def test_api_uses_fully_specified_configuration_for_research_backtest():
    client = TestClient(main.app)
    response = client.post("/api/backtest", data={"symbol": "EURUSD", "timeframe": "M1"},
                           files={"file": ("SYNTHETIC_TEST_DATA.csv", _csv(True), "text/csv")})
    assert response.status_code == 200
    result = response.json()
    assert result["strategy_status"] == "FULLY_SPECIFIED"
    assert result["backtest_blocked"] is False
    assert result["metrics"] is not None
    assert result["reproducibility"]["strategy_version"] == "1.0"
    assert result["notice"]["title"] == "Educational research tool"
    assert result["metrics"]["methodology"]["daily"].startswith("sum of R per weekday")
    assert "equity_curve" in result and "chart" in result


def test_api_persists_runs_and_exports_trades(monkeypatch):
    _enable_engine_config(monkeypatch)
    monkeypatch.setattr(strategy_v1, "generate_v1_candidates", lambda *_args: [_candidate(0.8)])
    client = TestClient(main.app)
    response = client.post("/api/backtest", data={"symbol": "EURUSD", "timeframe": "M1", "label": "api-test"},
                           files={"file": ("SYNTHETIC_TEST_DATA.csv", _csv(True), "text/csv")})
    run_id = response.json()["run_id"]
    listing = client.get("/api/runs").json()
    assert any(row["id"] == run_id and row["label"] == "api-test" and row["summary"]["trades"] == 1 for row in listing)
    stored = client.get(f"/api/runs/{run_id}").json()
    assert stored["result"]["trades"][0]["exit_reason"] == "TAKE_PROFIT"
    csv_export = client.get(f"/api/runs/{run_id}/trades.csv")
    assert csv_export.status_code == 200 and "TAKE_PROFIT" in csv_export.text and csv_export.text.startswith("# ")
    assert client.delete(f"/api/runs/{run_id}").json() == {"deleted": True}
    assert client.get(f"/api/runs/{run_id}").status_code == 404


def test_api_rejects_oversized_uploads(monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_MB", 0.00001)
    client = TestClient(main.app)
    response = client.post("/api/backtest", data={"symbol": "EURUSD"}, files={"file": ("big.csv", _csv(True) * 50, "text/csv")})
    assert response.status_code == 413


def test_api_background_job_reports_progress_and_persists(monkeypatch):
    _enable_engine_config(monkeypatch)
    monkeypatch.setattr(strategy_v1, "generate_v1_candidates", lambda *_args: [_candidate(0.8)])
    client = TestClient(main.app)
    submitted = client.post("/api/jobs/backtest", data={"symbol": "EURUSD", "options": "{\"daily_contexts\": \"none\"}"},
                            files={"file": ("SYNTHETIC_TEST_DATA.csv", _csv(True), "text/csv")}).json()
    assert submitted["status"] in {"queued", "running", "done"}
    import time
    for _ in range(200):
        job = client.get(f"/api/jobs/{submitted['job_id']}").json()
        if job["status"] in {"done", "failed"}:
            break
        time.sleep(0.05)
    assert job["status"] == "done", job
    assert job["result"]["summary"]["trades"] == 1
    assert client.get(f"/api/runs/{job['result']['run_id']}").status_code == 200
    assert client.post("/api/jobs/unknown", data={}, files={"file": ("x.csv", b"a", "text/csv")}).status_code == 404


def test_api_preserves_missing_spread_candidate_without_trade(monkeypatch):
    _enable_engine_config(monkeypatch)
    monkeypatch.setattr(strategy_v1, "generate_v1_candidates", lambda *_args: [_candidate(None)])
    client = TestClient(main.app)
    response = client.post("/api/backtest", data={"symbol": "EURUSD", "timeframe": "M1"},
                           files={"file": ("SYNTHETIC_TEST_DATA.csv", _csv(False), "text/csv")})
    assert response.status_code == 200
    result = response.json()
    assert result["backtest_blocked"] is False
    assert result["trades"] == []
    assert len(result["events"]) == 1
    assert result["events"][0]["candidate_status"] == "SPREAD_DATA_UNAVAILABLE"
    assert result["events"][0]["spread_source"] == "NO_SPREAD_DATA"
    assert result["events"][0]["rejection_reason"] == "SPREAD_DATA_UNAVAILABLE"


def test_api_path_returns_trade_for_synthetic_candidate_with_spread(monkeypatch):
    _enable_engine_config(monkeypatch)
    monkeypatch.setattr(strategy_v1, "generate_v1_candidates", lambda *_args: [_candidate(0.8)])
    client = TestClient(main.app)
    response = client.post("/api/backtest", data={"symbol": "EURUSD", "timeframe": "M1"},
                           files={"file": ("SYNTHETIC_TEST_DATA.csv", _csv(True), "text/csv")})
    assert response.status_code == 200
    result = response.json()
    assert result["backtest_blocked"] is False
    assert result["report"]["executable_trade_count"] == 1
    assert result["trades"][0]["spread_source"] == "HISTORICAL_SPREAD"
    assert result["trades"][0]["exit_reason"] == "TAKE_PROFIT"
    assert SYNTHETIC_LABEL in _csv(True).decode("utf-8")
