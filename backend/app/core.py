"""Causal, configurable research backtest primitives."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yaml

REQUIRED = ["timestamp", "open", "high", "low", "close", "volume"]


@dataclass
class Dataset:
    bars: pd.DataFrame
    quality: dict[str, Any]
    version: str


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_data(path: str | Path, source_timezone: str | None = None, timeframe: str = "M1") -> Dataset:
    path = Path(path)
    digest = sha256(path.read_bytes()).hexdigest()
    frame = pd.read_parquet(path) if path.suffix.lower() in {".parquet", ".pq"} else pd.read_csv(path)
    absent = sorted(set(REQUIRED) - set(frame.columns))
    if absent:
        raise ValueError(f"Missing required columns: {', '.join(absent)}")
    raw = pd.to_datetime(frame.timestamp, errors="coerce")
    if raw.isna().any():
        raise ValueError("timestamp contains invalid values")
    if raw.dt.tz is None:
        if not source_timezone:
            raise ValueError("Naive timestamps require source_timezone (IANA name)")
        raw = raw.dt.tz_localize(ZoneInfo(source_timezone), ambiguous="raise", nonexistent="raise")
    frame["timestamp"] = raw.dt.tz_convert("UTC")
    frame = frame[REQUIRED].copy()
    duplicates = int(frame.timestamp.duplicated().sum())
    chronological = bool(frame.timestamp.is_monotonic_increasing)
    frame = frame.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    for col in REQUIRED[1:]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    bad = frame[frame[REQUIRED[1:]].isna().any(axis=1) | (frame.low > frame.high) | (frame.low > frame.open) | (frame.low > frame.close) | (frame.high < frame.open) | (frame.high < frame.close) | (frame["close"] <= 0)]
    if len(bad):
        raise ValueError(f"{len(bad)} rows contain invalid OHLCV values")
    freq = {"M1": "1min", "M5": "5min", "M15": "15min", "H1": "1h"}.get(timeframe)
    if not freq:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    delta = frame.timestamp.diff().dropna()
    gaps = int((delta > pd.Timedelta(freq) * 1.5).sum())
    report = {"rows": len(frame), "duplicate_timestamps": duplicates, "input_chronological": chronological, "gap_count": gaps, "invalid_rows": 0, "start_utc": frame.timestamp.min().isoformat(), "end_utc": frame.timestamp.max().isoformat(), "timezone_normalized": "UTC", "source_timezone": source_timezone or "embedded", "warnings": []}
    if duplicates: report["warnings"].append("Duplicate timestamps were removed (last row retained).")
    if gaps: report["warnings"].append("Data gaps detected; candles were not fabricated.")
    if not chronological: report["warnings"].append("Rows were sorted chronologically.")
    return Dataset(frame.reset_index(drop=True), report, digest)


def convert_time(timestamp: str | pd.Timestamp, timezone: str) -> str:
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is None: raise ValueError("timestamp must be timezone-aware")
    return ts.tz_convert(ZoneInfo(timezone)).isoformat()


def scheduled_observations(local_date: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return exact Madrid schedule instants with DST-aware UTC and New York values."""
    madrid = ZoneInfo(config["timezones"]["reference"])
    ny_name = config["timezones"]["market_analysis"]
    result = []
    for label, clock in [("preparation", config["preparation_time"])] + [("observation", t) for t in config["observation_times"]]:
        naive = pd.Timestamp(f"{local_date}T{clock}").to_pydatetime()
        candidates = []
        for fold in (0, 1):
            local = naive.replace(tzinfo=madrid, fold=fold)
            utc = pd.Timestamp(local).tz_convert("UTC")
            roundtrip = utc.tz_convert(madrid)
            if roundtrip.replace(tzinfo=None) == naive and all(utc != existing[0] for existing in candidates):
                candidates.append((utc, roundtrip))
        if not candidates:
            result.append({"kind": label, "status": "nonexistent_dst_time", "madrid": None, "utc": None, "new_york": None})
        elif len(candidates) > 1:
            result.append({"kind": label, "status": "ambiguous_dst_time", "madrid": None, "utc": None, "new_york": None,
                           "candidates": [{"madrid": local.isoformat(), "utc": utc.isoformat(), "new_york": utc.tz_convert(ZoneInfo(ny_name)).isoformat()} for utc, local in candidates]})
        else:
            utc, localized = candidates[0]
            result.append({"kind": label, "status": "scheduled", "madrid": localized.isoformat(), "utc": utc.isoformat(), "new_york": utc.tz_convert(ZoneInfo(ny_name)).isoformat()})
    return result


class StrategyIncompleteError(ValueError):
    pass


def require_deterministic_strategy(config: dict[str, Any]) -> None:
    if config.get("status") != "DETERMINISTIC":
        raise StrategyIncompleteError("Strategy status is PARTIALLY_SPECIFIED; TBD rules must be explicitly defined before signals or trades can be generated.")


def aggregate(bars: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    rule = {"M5": "5min", "M15": "15min", "H1": "1h"}[timeframe]
    x = bars.set_index("timestamp").resample(rule, closed="left", label="right", origin="epoch").agg({"open":"first", "high":"max", "low":"min", "close":"last", "volume":"sum"}).dropna().reset_index()
    return x


def generate_signals(bars: pd.DataFrame, config: dict[str, Any], symbol: str) -> list[dict[str, Any]]:
    """Generate signals only after every strategy rule has an approved definition."""
    require_deterministic_strategy(config)
    raise NotImplementedError("No signal algorithm is enabled while strategy_v0_1 is PARTIALLY_SPECIFIED.")


def backtest(bars: pd.DataFrame, signals: list[dict[str, Any]], config: dict[str, Any], symbol: str, dataset_version: str) -> list[dict[str, Any]]:
    require_deterministic_strategy(config)
    raise NotImplementedError("Execution rules are TBD; this strategy version cannot simulate trades.")


def metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    if not trades: return {"total_trades":0,"winning_trades":0,"losing_trades":0,"win_rate":0,"expectancy_r":0,"profit_factor":0,"max_drawdown_r":0,"sharpe":0,"sortino":0}
    r=np.array([t["r_multiple"] for t in trades],float); pnl=np.array([t["pnl"] for t in trades],float); eq=np.cumsum(r); peaks=np.maximum.accumulate(np.r_[0,eq]); dd=peaks[1:]-eq
    wins=r[r>0]; losses=r[r<0]; downside=r[r<0]
    return {"total_trades":len(r),"winning_trades":int((r>0).sum()),"losing_trades":int((r<0).sum()),"win_rate":float((r>0).mean()),"average_win_r":float(wins.mean()) if len(wins) else 0,"average_loss_r":float(losses.mean()) if len(losses) else 0,"expectancy_r":float(r.mean()),"average_r":float(r.mean()),"profit_factor":float(wins.sum()/abs(losses.sum())) if len(losses) else float("inf"),"gross_profit":float(pnl[pnl>0].sum()),"gross_loss":float(pnl[pnl<0].sum()),"net_pnl":float(pnl.sum()),"max_drawdown_r":float(dd.max()) if len(dd) else 0,"sharpe":float(r.mean()/r.std(ddof=1)*np.sqrt(252)) if len(r)>1 and r.std(ddof=1)>0 else 0,"sortino":float(r.mean()/downside.std(ddof=1)*np.sqrt(252)) if len(downside)>1 and downside.std(ddof=1)>0 else 0,"average_mfe_r":float(np.mean([t["mfe"] for t in trades])),"average_mae_r":float(np.mean([t["mae"] for t in trades]))}


def split_periods(frame: pd.DataFrame, train: float=.6, validation: float=.2) -> dict[str, tuple[str,str]]:
    ts=frame.timestamp.sort_values(); n=len(ts); a=max(1,int(n*train)); b=max(a+1,int(n*(train+validation)))
    return {"train":(ts.iloc[0].isoformat(),ts.iloc[a-1].isoformat()),"validation":(ts.iloc[a].isoformat(),ts.iloc[b-1].isoformat()),"out_of_sample":(ts.iloc[b].isoformat(),ts.iloc[-1].isoformat())}


def monte_carlo(returns: list[float], simulations: int=1000, seed: int=7) -> dict[str, Any]:
    if not returns: return {"simulations":simulations,"final_equity_percentiles":{},"drawdown_percentiles":{},"probability_losing":0.0}
    rng=np.random.default_rng(seed); data=np.asarray(returns,float); finals=[]; drawdowns=[]
    for _ in range(max(1000,simulations)):
        curve=np.cumsum(rng.choice(data,size=len(data),replace=True)); finals.append(float(curve[-1])); peaks=np.maximum.accumulate(np.r_[0,curve]); drawdowns.append(float((peaks[1:]-curve).max()))
    return {"simulations":max(1000,simulations),"final_equity_percentiles":{str(q):float(np.percentile(finals,q)) for q in [5,25,50,75,95]},"drawdown_percentiles":{str(q):float(np.percentile(drawdowns,q)) for q in [5,25,50,75,95]},"probability_losing":float(np.mean(np.asarray(finals)<0))}
