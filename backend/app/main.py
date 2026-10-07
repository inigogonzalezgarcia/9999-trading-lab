from __future__ import annotations
from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .core import load_config, metrics
from .data import DataQualityError, load_market_data
from .timezones import scheduled_observations, timezone_database_version
from .strategy_v1 import run_v1_backtest, run_v1_portfolio

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
        if symbol != "PORTFOLIO" and symbol not in cfg["instruments"]:
            raise HTTPException(422,"Baseline permits EURUSD, GBPUSD, or PORTFOLIO")
        if symbol == "PORTFOLIO":
            if "symbol" not in ds.bars.columns:
                raise HTTPException(422,"Portfolio uploads require a symbol column containing EURUSD and/or GBPUSD")
            data_by_symbol={name: group.drop(columns=["symbol"]).reset_index(drop=True) for name, group in ds.bars.groupby("symbol") if name in cfg["instruments"]}
            if not data_by_symbol or len(data_by_symbol) != ds.bars.symbol.nunique():
                raise HTTPException(422,"Portfolio data contains unsupported or missing symbols")
        else:
            data_by_symbol={symbol: ds.bars}
        execution=load_config(ROOT/"config"/"execution.yaml")
        first_local_date=ds.bars.timestamp.min().tz_convert(cfg["timezones"]["reference"]).date().isoformat()
        schedule=scheduled_observations(first_local_date,cfg)
        timezone_version=timezone_database_version()
        if timeframe != "M1":
            raise HTTPException(422,"Strategy V1 requires M1 data for causal fills and execution costs")
        if cfg["status"] != "FULLY_SPECIFIED":
            return {"strategy_version":cfg["strategy_version"],"strategy_status":cfg["status"],"backtest_blocked":True,"blocked_reason":"The V1 engine is not yet validated; no trades or performance results were generated.","quality":ds.quality,"dataset_version":ds.version,"timezone_database":timezone_version,"scheduled_observations":schedule,"signal_count":None,"trades":[],"metrics":None,"report":None}
        result=run_v1_portfolio(data_by_symbol,cfg,execution)
        if symbol != "PORTFOLIO":
            result["symbol"]=symbol
        result.update({"backtest_blocked":False,"quality":ds.quality,"dataset_version":ds.version,"timezone_database":timezone_version,"scheduled_observations":schedule,"metrics":metrics(result["trades"]),"report":{"spread_sources":result["spread_sources"],"candidate_count":result["candidate_count"],"executable_trade_count":result["signal_count"],"timezone_database":timezone_version,"strategy_version":cfg["strategy_version"],"execution_version":execution["version"]}})
        return result
    except DataQualityError as e:
        raise HTTPException(422, {"detail": str(e), "quality": e.report}) from e
    except (ValueError,KeyError) as e: raise HTTPException(422,str(e)) from e
    finally: path.unlink(missing_ok=True)
