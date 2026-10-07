from __future__ import annotations
from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .core import load_config
from .data import DataQualityError, load_market_data
from .timezones import scheduled_observations, timezone_database_version

ROOT=Path(__file__).resolve().parents[2]
CONFIG=ROOT/"config"/"strategy_v1.yaml"
DATA_CONFIG=ROOT/"config"/"data.yaml"
app=FastAPI(title="FX Research Lab",version="0.1.0",description="Historical research and backtesting only; no broker execution.")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173"],allow_methods=["*"],allow_headers=["*"])

@app.get("/api/health")
def health(): return {"status":"ok","mode":"research_only"}

@app.get("/api/config")
def config(): return load_config(CONFIG)

@app.post("/api/backtest")
async def run_backtest(file: UploadFile=File(...),symbol: str=Form("EURUSD"),timeframe: str=Form("M1"),source_timezone: str|None=Form(None)):
    suffix=Path(file.filename or "data.csv").suffix.lower()
    if suffix not in {".csv",".parquet",".pq"}: raise HTTPException(400,"Upload CSV or Parquet")
    with NamedTemporaryFile(suffix=suffix, delete=False) as uploaded:
        path=Path(uploaded.name)
        uploaded.write(await file.read())
    try:
        ds=load_market_data(path,source_timezone=source_timezone,timeframe=timeframe,timestamp_semantics=load_config(DATA_CONFIG)["source_timestamp_semantics"]); cfg=load_config(CONFIG)
        if symbol not in cfg["instruments"]:
            raise HTTPException(422,"Baseline permits only EURUSD and GBPUSD")
        first_local_date=ds.bars.timestamp.min().tz_convert(cfg["timezones"]["reference"]).date().isoformat()
        return {"strategy_version":cfg["strategy_version"],"strategy_status":cfg["status"],"backtest_blocked":True,"blocked_reason":"The V1 rules are recorded, but the complete signal and execution engine is still implementation-pending.","quality":ds.quality,"dataset_version":ds.version,"timezone_database":timezone_database_version(),"scheduled_observations":scheduled_observations(first_local_date,cfg),"signal_count":None,"trades":[],"metrics":None,"report":None}
    except DataQualityError as e:
        raise HTTPException(422, {"detail": str(e), "quality": e.report}) from e
    except (ValueError,KeyError) as e: raise HTTPException(422,str(e)) from e
    finally: path.unlink(missing_ok=True)
