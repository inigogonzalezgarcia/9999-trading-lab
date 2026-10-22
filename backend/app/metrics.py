"""Performance statistics for research backtests, measured in R multiples.

Two families are reported and must not be confused:

* **Per-trade** statistics (expectancy, win rate, profit factor, per-trade Sharpe) describe the
  distribution of individual trade outcomes. They are *not* annualised, because trades are not
  evenly spaced in time.
* **Daily-series** statistics (annualised Sharpe/Sortino, CAGR-like growth) are computed from
  the daily sum of R over every weekday in the evaluated period, including days with no trade
  (0 R). Only these may be annualised, with 252 trading days per year.

Historical results are simulated and do not establish a profitable edge.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def _empty() -> dict[str, Any]:
    return {"total_trades": 0, "winning_trades": 0, "losing_trades": 0, "breakeven_trades": 0, "win_rate": 0.0,
            "expectancy_r": 0.0, "average_r": 0.0, "median_r": 0.0, "average_win_r": 0.0, "average_loss_r": 0.0,
            "profit_factor": None, "payoff_ratio": None, "gross_profit": 0.0, "gross_loss": 0.0, "net_pnl": 0.0,
            "total_r": 0.0, "max_drawdown_r": 0.0, "max_consecutive_losses": 0, "sharpe_per_trade": 0.0,
            "average_mfe_r": 0.0, "average_mae_r": 0.0, "exit_reasons": {}, "by_symbol": {}, "by_window": {},
            "by_hour": {}, "by_weekday": {}, "by_month": {}, "by_exit_reason": {}, "by_direction": {},
            "daily": {"trading_days": 0, "days_with_trades": 0, "mean_daily_r": 0.0, "std_daily_r": 0.0,
                      "annualized_sharpe": None, "annualized_sortino": None, "annualized_r": None},
            # Kept for backwards compatibility with earlier result payloads; same values as "daily".
            "sharpe": None, "sortino": None,
            "methodology": {"per_trade": "unannualised R-multiple statistics",
                            "daily": "sum of R per weekday incl. zero days; annualised with sqrt(252)",
                            "note": "Simulated historical results; not evidence of a profitable edge."}}


def daily_r_series(trades: list[dict[str, Any]], period_start: str | None = None, period_end: str | None = None) -> pd.Series:
    """Sum of R by trading date over every weekday of the period (zero on days without trades)."""
    if not trades and not (period_start and period_end):
        return pd.Series(dtype=float)
    dates = pd.to_datetime([trade["date"] for trade in trades]) if trades else pd.DatetimeIndex([])
    values = pd.Series([float(trade["r_multiple"]) for trade in trades], index=dates, dtype=float)
    start = pd.Timestamp(period_start).normalize().tz_localize(None) if period_start else dates.min()
    end = pd.Timestamp(period_end).normalize().tz_localize(None) if period_end else dates.max()
    if pd.isna(start) or pd.isna(end):
        return pd.Series(dtype=float)
    calendar = pd.bdate_range(start, end)
    daily = values.groupby(level=0).sum().reindex(calendar, fill_value=0.0)
    # Trades dated on a weekend (possible with Sunday-opening providers) are kept by appending them.
    extra = values[~values.index.isin(calendar)]
    if len(extra):
        daily = pd.concat([daily, extra.groupby(level=0).sum()]).sort_index()
    return daily


def _max_consecutive_losses(r: np.ndarray) -> int:
    best = run = 0
    for value in r:
        run = run + 1 if value < 0 else 0
        best = max(best, run)
    return best


def metrics(trades: list[dict[str, Any]], period_start: str | None = None, period_end: str | None = None) -> dict[str, Any]:
    """Compute per-trade and daily-series statistics for a list of simulated trades."""
    result = _empty()
    if not trades:
        if period_start and period_end:
            result["daily"]["trading_days"] = int(len(pd.bdate_range(pd.Timestamp(period_start).normalize().tz_localize(None), pd.Timestamp(period_end).normalize().tz_localize(None))))
        return result
    ordered = sorted(trades, key=lambda trade: trade["entry_timestamp"])
    r = np.array([float(trade["r_multiple"]) for trade in ordered])
    pnl = np.array([float(trade.get("pnl", 0.0)) for trade in ordered])
    wins, losses = r[r > 0], r[r < 0]
    equity = np.cumsum(r)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])
    drawdown = peaks[1:] - equity
    result.update({
        "total_trades": int(len(r)), "winning_trades": int((r > 0).sum()), "losing_trades": int((r < 0).sum()),
        "breakeven_trades": int((r == 0).sum()), "win_rate": float((r > 0).mean()),
        "expectancy_r": float(r.mean()), "average_r": float(r.mean()), "median_r": float(np.median(r)),
        "average_win_r": float(wins.mean()) if len(wins) else 0.0, "average_loss_r": float(losses.mean()) if len(losses) else 0.0,
        "profit_factor": float(wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else None,
        "payoff_ratio": float(wins.mean() / abs(losses.mean())) if len(wins) and len(losses) else None,
        "gross_profit": float(pnl[pnl > 0].sum()), "gross_loss": float(pnl[pnl < 0].sum()), "net_pnl": float(pnl.sum()),
        "total_r": float(r.sum()), "max_drawdown_r": float(drawdown.max()) if len(drawdown) else 0.0,
        "max_consecutive_losses": _max_consecutive_losses(r),
        "sharpe_per_trade": float(r.mean() / r.std(ddof=1)) if len(r) > 1 and r.std(ddof=1) > 0 else 0.0,
        "average_mfe_r": float(np.mean([trade.get("mfe", 0.0) for trade in ordered])),
        "average_mae_r": float(np.mean([trade.get("mae", 0.0) for trade in ordered])),
        "exit_reasons": {reason: int(sum(1 for trade in ordered if trade.get("exit_reason") == reason)) for reason in sorted({trade.get("exit_reason") for trade in ordered})},
        "by_symbol": _grouped(ordered, "symbol"), "by_window": _grouped(ordered, "observation_window"),
        "by_hour": _grouped_by_time(ordered, "hour"), "by_weekday": _grouped_by_time(ordered, "weekday"),
        "by_month": _grouped_by_time(ordered, "month"), "by_exit_reason": _grouped(ordered, "exit_reason"),
        "by_direction": _grouped(ordered, "direction"),
    })
    daily = daily_r_series(ordered, period_start, period_end)
    if len(daily):
        mean, std = float(daily.mean()), float(daily.std(ddof=1)) if len(daily) > 1 else 0.0
        downside = np.sqrt(np.mean(np.minimum(daily.to_numpy(), 0.0) ** 2))
        result["daily"] = {
            "trading_days": int(len(daily)), "days_with_trades": int((daily != 0).sum()),
            "mean_daily_r": mean, "std_daily_r": std,
            "annualized_sharpe": float(mean / std * np.sqrt(TRADING_DAYS_PER_YEAR)) if std > 0 else None,
            "annualized_sortino": float(mean / downside * np.sqrt(TRADING_DAYS_PER_YEAR)) if downside > 0 else None,
            "annualized_r": float(mean * TRADING_DAYS_PER_YEAR),
        }
        result["sharpe"] = result["daily"]["annualized_sharpe"]
        result["sortino"] = result["daily"]["annualized_sortino"]
    return result


def _grouped(trades: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[float]] = {}
    for trade in trades:
        groups.setdefault(str(trade.get(key)), []).append(float(trade["r_multiple"]))
    return {name: {"trades": len(values), "total_r": float(np.sum(values)), "expectancy_r": float(np.mean(values)),
                   "win_rate": float(np.mean(np.asarray(values) > 0))} for name, values in sorted(groups.items())}


WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _grouped_by_time(trades: list[dict[str, Any]], unit: str) -> dict[str, dict[str, Any]]:
    """R by local entry hour, weekday or calendar month (strategy reference timezone recorded on each trade)."""
    groups: dict[str, list[float]] = {}
    for trade in trades:
        zone = trade.get("timezone") or "UTC"
        stamp = pd.Timestamp(trade["entry_timestamp"]).tz_convert(zone)
        key = f"{stamp.hour:02d}" if unit == "hour" else WEEKDAYS[stamp.dayofweek] if unit == "weekday" else stamp.strftime("%Y-%m")
        groups.setdefault(key, []).append(float(trade["r_multiple"]))
    if unit == "weekday":
        ordered_keys = [day for day in WEEKDAYS if day in groups]
    else:
        ordered_keys = sorted(groups)
    return {key: {"trades": len(groups[key]), "total_r": float(np.sum(groups[key])), "expectancy_r": float(np.mean(groups[key])),
                  "win_rate": float(np.mean(np.asarray(groups[key]) > 0))} for key in ordered_keys}


def equity_curve(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cumulative R after each trade, ordered by exit time, for charting."""
    ordered = sorted(trades, key=lambda trade: trade["exit_timestamp"])
    total = 0.0
    peak = 0.0
    points = []
    for trade in ordered:
        total += float(trade["r_multiple"])
        peak = max(peak, total)
        points.append({"timestamp": trade["exit_timestamp"], "trade_id": trade["trade_id"], "symbol": trade["symbol"],
                       "r_multiple": float(trade["r_multiple"]), "cumulative_r": total, "drawdown_r": peak - total})
    return points
