"""Causal, configurable research backtest primitives."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from .data import Dataset, aggregate_bars, load_market_data
from .timezones import convert_timestamp, scheduled_observations, validate_observation_window_config

REQUIRED = ["timestamp", "open", "high", "low", "close", "volume"]


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    validate_observation_window_config(config)
    return config


def convert_time(timestamp: str | pd.Timestamp, timezone: str) -> str:
    return convert_timestamp(timestamp, timezone)


def load_data(path: str | Path, source_timezone: str | None = None, timeframe: str = "M1") -> Dataset:
    """Compatibility wrapper; source timestamps follow config/data.yaml semantics."""
    return load_market_data(path, timeframe=timeframe, source_timezone=source_timezone)


class StrategyIncompleteError(ValueError):
    pass


def require_deterministic_strategy(config: dict[str, Any]) -> None:
    if config.get("status") not in {"DETERMINISTIC", "FULLY_SPECIFIED"}:
        raise StrategyIncompleteError("Strategy implementation is not validated; signals and trades remain disabled.")


def aggregate(bars: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    return aggregate_bars(bars, timeframe)


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
    return {"total_trades":len(r),"winning_trades":int((r>0).sum()),"losing_trades":int((r<0).sum()),"win_rate":float((r>0).mean()),"average_win_r":float(wins.mean()) if len(wins) else 0,"average_loss_r":float(losses.mean()) if len(losses) else 0,"expectancy_r":float(r.mean()),"average_r":float(r.mean()),"profit_factor":float(wins.sum()/abs(losses.sum())) if len(losses) else None,"gross_profit":float(pnl[pnl>0].sum()),"gross_loss":float(pnl[pnl<0].sum()),"net_pnl":float(pnl.sum()),"max_drawdown_r":float(dd.max()) if len(dd) else 0,"sharpe":float(r.mean()/r.std(ddof=1)*np.sqrt(252)) if len(r)>1 and r.std(ddof=1)>0 else 0,"sortino":float(r.mean()/downside.std(ddof=1)*np.sqrt(252)) if len(downside)>1 and downside.std(ddof=1)>0 else 0,"average_mfe_r":float(np.mean([t["mfe"] for t in trades])),"average_mae_r":float(np.mean([t["mae"] for t in trades]))}


def split_periods(frame: pd.DataFrame, train: float=.6, validation: float=.2) -> dict[str, tuple[str,str]]:
    ts=frame.timestamp.sort_values(); n=len(ts); a=max(1,int(n*train)); b=max(a+1,int(n*(train+validation)))
    return {"train":(ts.iloc[0].isoformat(),ts.iloc[a-1].isoformat()),"validation":(ts.iloc[a].isoformat(),ts.iloc[b-1].isoformat()),"out_of_sample":(ts.iloc[b].isoformat(),ts.iloc[-1].isoformat())}


def monte_carlo(returns: list[float], simulations: int=1000, seed: int=7) -> dict[str, Any]:
    if not returns: return {"simulations":simulations,"final_equity_percentiles":{},"drawdown_percentiles":{},"probability_losing":0.0}
    rng=np.random.default_rng(seed); data=np.asarray(returns,float); finals=[]; drawdowns=[]
    for _ in range(max(1000,simulations)):
        curve=np.cumsum(rng.choice(data,size=len(data),replace=True)); finals.append(float(curve[-1])); peaks=np.maximum.accumulate(np.r_[0,curve]); drawdowns.append(float((peaks[1:]-curve).max()))
    return {"simulations":max(1000,simulations),"final_equity_percentiles":{str(q):float(np.percentile(finals,q)) for q in [5,25,50,75,95]},"drawdown_percentiles":{str(q):float(np.percentile(drawdowns,q)) for q in [5,25,50,75,95]},"probability_losing":float(np.mean(np.asarray(finals)<0))}
