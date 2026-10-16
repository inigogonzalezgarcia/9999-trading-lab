"""HTTP boundary: uploads, synchronous and background research runs, run history, static UI.

Research-only. No broker connection or live execution exists anywhere in this service.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import service
from .data import DataQualityError
from .jobs import JobManager
from .store import RunStore, dumps

logging.basicConfig(level=os.getenv("FXLAB_LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("fxlab.api")

ROOT = service.ROOT
MAX_UPLOAD_MB = float(os.getenv("FXLAB_MAX_UPLOAD_MB", "250"))
CORS_ORIGINS = [origin.strip() for origin in os.getenv("FXLAB_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
STATIC_DIR = Path(os.getenv("FXLAB_STATIC_DIR", ROOT / "frontend" / "dist"))

app = FastAPI(title="FX Research Lab", version=service.SOFTWARE_VERSION,
              description="Educational historical research and backtesting only; no broker execution.")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
jobs = JobManager(workers=int(os.getenv("FXLAB_JOB_WORKERS", "2")))
_store: RunStore | None = None


def store() -> RunStore:
    global _store
    if _store is None:
        _store = RunStore()
    return _store


class _JSON(JSONResponse):
    """JSON that tolerates NaN/inf and numpy scalars from pandas."""

    def render(self, content: Any) -> bytes:
        return dumps(content).encode("utf-8")


# Backwards-compatible alias: older tests patched ``main.load_config``.
load_config = service.load_config


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "mode": "research_only", "version": service.SOFTWARE_VERSION, "max_upload_mb": MAX_UPLOAD_MB}


@app.get("/api/config")
def config() -> Any:
    strategy, execution, data_config = service.load_configs()
    return _JSON({"strategy": strategy, "execution": execution, "data": data_config, "notice": service.EDUCATIONAL_NOTICE,
                  "strategies": service.available_strategies(), "default_strategy": service.DEFAULT_STRATEGY,
                  "limits": {"max_upload_mb": MAX_UPLOAD_MB}, "software_revision": service.software_revision()})


@app.get("/api/notice")
def notice() -> dict[str, Any]:
    return service.EDUCATIONAL_NOTICE


async def _save_upload(file: UploadFile) -> Path:
    suffix = Path(file.filename or "data.csv").suffix.lower()
    if suffix not in {".csv", ".parquet", ".pq"}:
        raise HTTPException(400, "Upload CSV or Parquet")
    limit = int(MAX_UPLOAD_MB * 1024 * 1024)
    written = 0
    with NamedTemporaryFile(suffix=suffix, delete=False) as uploaded:
        path = Path(uploaded.name)
        while chunk := await file.read(1024 * 1024):
            written += len(chunk)
            if written > limit:
                uploaded.close()
                path.unlink(missing_ok=True)
                raise HTTPException(413, f"Upload exceeds {MAX_UPLOAD_MB:g} MB; run large datasets through the CLI or raise FXLAB_MAX_UPLOAD_MB")
            uploaded.write(chunk)
    return path


def _parse_options(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        options = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(422, f"options must be JSON: {exc}") from exc
    if not isinstance(options, dict):
        raise HTTPException(422, "options must be a JSON object")
    return options


def _load(path: Path, timeframe: str, source_timezone: str | None):
    try:
        return service.load_dataset(path, timeframe=timeframe, source_timezone=source_timezone)
    except DataQualityError as exc:
        raise HTTPException(422, {"detail": str(exc), "quality": exc.report}) from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/backtest")
async def run_backtest(file: UploadFile = File(...), symbol: str = Form("EURUSD"), timeframe: str = Form("M1"),
                       source_timezone: str | None = Form(None), daily_contexts: str = Form("lookback:30"),
                       fixed_spread_pips: float | None = Form(None), save: bool = Form(True), label: str | None = Form(None),
                       strategy: str = Form(service.DEFAULT_STRATEGY)) -> Any:
    """Synchronous research backtest; use ``/api/jobs/backtest`` for multi-year files."""
    path = await _save_upload(file)
    try:
        if timeframe != "M1":
            raise HTTPException(422, "Strategy V1 requires M1 data for causal fills and execution costs")
        dataset = _load(path, timeframe, source_timezone)
        result = service.run_backtest(dataset, symbol, {"daily_contexts": daily_contexts, "fixed_spread_pips": fixed_spread_pips, "strategy": strategy})
        if save and not result.get("backtest_blocked"):
            result["run_id"] = store().save("backtest", result, service.summarize(result, "backtest"), symbol, file.filename, label)
        return _JSON(result)
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        path.unlink(missing_ok=True)


def _job(kind: str, path: Path, filename: str | None, symbol: str, timeframe: str, source_timezone: str | None, options: dict[str, Any], label: str | None) -> dict[str, Any]:
    def work(progress):
        try:
            progress("loading", 0.01)
            dataset = service.load_dataset(path, timeframe=timeframe, source_timezone=source_timezone)
            if kind == "backtest":
                result = service.run_backtest(dataset, symbol, options, progress)
            else:
                result = service.run_research(dataset, symbol, options, progress)
            run_id = store().save(kind, result, service.summarize(result, kind), symbol, filename, label)
            return {"run_id": run_id, "summary": service.summarize(result, kind), "notice": service.EDUCATIONAL_NOTICE}
        finally:
            path.unlink(missing_ok=True)

    return jobs.submit(kind, work, {"symbol": symbol, "dataset_name": filename, "label": label})


@app.post("/api/jobs/{kind}")
async def submit_job(kind: str, file: UploadFile = File(...), symbol: str = Form("EURUSD"), timeframe: str = Form("M1"),
                     source_timezone: str | None = Form(None), options: str | None = Form(None), label: str | None = Form(None)) -> Any:
    """Queue a ``backtest`` or ``research`` run; poll ``/api/jobs/{job_id}`` for progress."""
    if kind not in {"backtest", "research"}:
        raise HTTPException(404, "Unknown job kind")
    if timeframe != "M1":
        raise HTTPException(422, "Strategy V1 requires M1 data")
    path = await _save_upload(file)
    return _JSON(_job(kind, path, file.filename, symbol, timeframe, source_timezone, _parse_options(options), label))


@app.get("/api/jobs")
def list_jobs() -> Any:
    return _JSON(jobs.list())


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> Any:
    job = jobs.public(job_id)
    if job is None:
        raise HTTPException(404, "Unknown job")
    return _JSON(job)


@app.get("/api/runs")
def list_runs(limit: int = 100, kind: str | None = None) -> Any:
    return _JSON(store().list(limit=limit, kind=kind))


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> Any:
    result = store().get(run_id)
    if result is None:
        raise HTTPException(404, "Unknown run")
    meta = store().meta(run_id) or {}
    return _JSON({"meta": meta, "result": result})


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: str) -> dict[str, bool]:
    if not store().delete(run_id):
        raise HTTPException(404, "Unknown run")
    return {"deleted": True}


@app.patch("/api/runs/{run_id}")
def relabel_run(run_id: str, label: str = Form(...)) -> dict[str, bool]:
    if not store().relabel(run_id, label):
        raise HTTPException(404, "Unknown run")
    return {"updated": True}


@app.get("/api/runs/{run_id}/trades.csv")
def run_trades_csv(run_id: str) -> Response:
    result = store().get(run_id)
    if result is None:
        raise HTTPException(404, "Unknown run")
    trades = result.get("trades", [])
    columns = ["trade_id", "symbol", "date", "direction", "observation_window", "entry_timestamp", "entry_price", "stop_price", "target_price",
               "exit_timestamp", "exit_price", "exit_reason", "spread_pips", "spread_source", "slippage_pips", "commission", "r_multiple", "pnl", "mfe", "mae"]
    buffer = io.StringIO()
    # Plain comment line (not through csv.writer, which would quote the commas in the sentence).
    buffer.write("# " + service.EDUCATIONAL_NOTICE["lines"][0] + "\n")
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for trade in trades:
        writer.writerow([trade.get(column) for column in columns])
    return Response(buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="trades-{run_id[:8]}.csv"'})


@app.get("/api/runs/{run_id}/result.json")
def run_result_json(run_id: str) -> Response:
    result = store().get(run_id)
    if result is None:
        raise HTTPException(404, "Unknown run")
    return Response(dumps(result), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="run-{run_id[:8]}.json"'})


if STATIC_DIR.is_dir():  # production image: serve the built UI from the same origin
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="ui")
