"""Research safeguards around the V1 baseline: splits, rolling out-of-sample, Monte Carlo,
parameter sensitivity, and a cost-matched random benchmark.

None of these optimise parameters. V1 is a fixed baseline, so the honest questions are:
is its edge stable across independent periods, is it distinguishable from random entries that pay
the same costs, how fragile is it to cost and parameter assumptions, and how wide is the range of
outcomes a trader could have lived through. Every function returns plain dictionaries suitable for
JSON persistence and all randomness is seeded.
"""
from __future__ import annotations

import copy
from collections.abc import Callable
from datetime import time
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .metrics import metrics
from .strategy.frames import NS_PER_MINUTE, Bars
from .strategy.ids import _stable_id
from .strategy.simulation import _simulate_candidate
from .strategy_v1 import run_v1_portfolio

Progress = Callable[[str, float], None]
DEFAULT_WARMUP_DAYS = 15


# --------------------------------------------------------------------------- helpers

def _period_bounds(data_by_symbol: dict[str, pd.DataFrame]) -> tuple[pd.Timestamp, pd.Timestamp]:
    starts = [frame.timestamp.min() for frame in data_by_symbol.values() if len(frame)]
    ends = [frame.timestamp.max() for frame in data_by_symbol.values() if len(frame)]
    return min(starts), max(ends)


def _slice(data_by_symbol: dict[str, pd.DataFrame], start: pd.Timestamp | None, end: pd.Timestamp | None, warmup_days: int) -> dict[str, pd.DataFrame]:
    out = {}
    for symbol, frame in data_by_symbol.items():
        mask = pd.Series(True, index=frame.index)
        if start is not None:
            mask &= frame.timestamp >= start - pd.Timedelta(days=warmup_days)
        if end is not None:
            mask &= frame.timestamp < end
        out[symbol] = frame.loc[mask].reset_index(drop=True)
    return {symbol: frame for symbol, frame in out.items() if len(frame)}


def run_period(data_by_symbol: dict[str, pd.DataFrame], strategy_config: dict[str, Any], execution_config: dict[str, Any],
               start: pd.Timestamp | None = None, end: pd.Timestamp | None = None, warmup_days: int = DEFAULT_WARMUP_DAYS,
               dataset_hash: str | None = None) -> dict[str, Any]:
    """Run the baseline on ``[start, end)`` with warm-up history, keeping only trades entered inside the period.

    The engine needs prior candles to build structure, so ``warmup_days`` of history before
    ``start`` are supplied but any trade entered before ``start`` is discarded. Daily contexts are
    skipped for speed; they are an audit artefact of the full run, not an input to execution.
    """
    sliced = _slice(data_by_symbol, start, end, warmup_days)
    if not sliced:
        return {"trades": [], "events": [], "candidate_count": 0, "metrics": metrics([], start.isoformat() if start else None, end.isoformat() if end else None)}
    result = run_v1_portfolio(sliced, strategy_config, execution_config, dataset_hash, include_daily_contexts=False)
    if start is not None:
        result["trades"] = [trade for trade in result["trades"] if pd.Timestamp(trade["entry_timestamp"]) >= start]
        result["events"] = [event for event in result["events"] if pd.Timestamp(event.get("sweep_confirmation_timestamp")) >= start]
    period_start, period_end = _period_bounds(sliced)
    result["period"] = {"start": (start or period_start).isoformat(), "end": (end or period_end).isoformat(), "warmup_days": warmup_days}
    result["metrics"] = metrics(result["trades"], result["period"]["start"], result["period"]["end"])
    result["candidate_count"] = len(result["events"])
    for heavy in ("daily_contexts", "liquidity_events", "zone_events", "state_events"):
        result.pop(heavy, None)
    return result


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    m = result["metrics"]
    return {"period": result.get("period"), "trades": m["total_trades"], "candidates": result.get("candidate_count"),
            "expectancy_r": m["expectancy_r"], "total_r": m["total_r"], "win_rate": m["win_rate"],
            "profit_factor": m["profit_factor"], "max_drawdown_r": m["max_drawdown_r"],
            "annualized_sharpe": m["daily"]["annualized_sharpe"], "trading_days": m["daily"]["trading_days"]}


# --------------------------------------------------------------------------- splits

def chronological_splits(data_by_symbol: dict[str, pd.DataFrame], train: float = 0.6, validation: float = 0.2) -> dict[str, dict[str, str]]:
    """Independent, chronological in-sample / validation / out-of-sample periods by calendar time."""
    if not 0 < train < 1 or not 0 <= validation < 1 or train + validation >= 1:
        raise ValueError("train and validation fractions must leave room for an out-of-sample period")
    start, end = _period_bounds(data_by_symbol)
    span = end - start
    a = start + span * train
    b = start + span * (train + validation)
    return {"train": {"start": start.isoformat(), "end": a.isoformat()},
            "validation": {"start": a.isoformat(), "end": b.isoformat()},
            "out_of_sample": {"start": b.isoformat(), "end": (end + pd.Timedelta(minutes=1)).isoformat()}}


def split_evaluation(data_by_symbol, strategy_config, execution_config, train=0.6, validation=0.2,
                     warmup_days=DEFAULT_WARMUP_DAYS, dataset_hash=None, progress: Progress | None = None) -> dict[str, Any]:
    splits = chronological_splits(data_by_symbol, train, validation)
    out = {"splits": splits, "results": {}}
    for i, (name, bounds) in enumerate(splits.items()):
        if progress:
            progress(f"split:{name}", i / len(splits))
        result = run_period(data_by_symbol, strategy_config, execution_config, pd.Timestamp(bounds["start"]), pd.Timestamp(bounds["end"]), warmup_days, dataset_hash)
        out["results"][name] = _summary(result)
    out["note"] = "Out-of-sample metrics are the only ones that may be quoted as evidence; the baseline has no fitted parameters, so train/validation serve as independent replications."
    return out


# --------------------------------------------------------------------------- walk-forward

def walk_forward(data_by_symbol, strategy_config, execution_config, train_days: int = 120, test_days: int = 30, step_days: int | None = None,
                 anchored: bool = False, warmup_days: int = DEFAULT_WARMUP_DAYS, dataset_hash=None, progress: Progress | None = None) -> dict[str, Any]:
    """Rolling in-sample / out-of-sample folds over calendar time.

    Because V1 has fixed rules, the in-sample window is a reference replication, not a fit. The
    out-of-sample folds concatenated chronologically form a continuous unseen-period track record.
    """
    start, end = _period_bounds(data_by_symbol)
    step = pd.Timedelta(days=step_days or test_days)
    folds = []
    fold_start = start
    index = 0
    total_span = (end - start) / step if step else 1
    while True:
        train_start = start if anchored else fold_start
        train_end = fold_start + pd.Timedelta(days=train_days)
        test_end = train_end + pd.Timedelta(days=test_days)
        if train_end >= end:
            break
        if progress:
            progress(f"walk_forward:fold{index + 1}", min(0.99, index / max(1, total_span)))
        in_sample = run_period(data_by_symbol, strategy_config, execution_config, train_start, train_end, warmup_days, dataset_hash)
        out_sample = run_period(data_by_symbol, strategy_config, execution_config, train_end, min(test_end, end + pd.Timedelta(minutes=1)), warmup_days, dataset_hash)
        folds.append({"fold": index + 1, "in_sample": _summary(in_sample), "out_of_sample": _summary(out_sample),
                      "out_of_sample_trades": [{"trade_id": t["trade_id"], "symbol": t["symbol"], "entry_timestamp": t["entry_timestamp"], "r_multiple": t["r_multiple"]} for t in out_sample["trades"]]})
        index += 1
        fold_start = fold_start + step
        if test_end >= end:
            break
    oos_r = [t["r_multiple"] for fold in folds for t in fold["out_of_sample_trades"]]
    positive = [fold for fold in folds if fold["out_of_sample"]["trades"] and fold["out_of_sample"]["expectancy_r"] > 0]
    with_trades = [fold for fold in folds if fold["out_of_sample"]["trades"]]
    return {"parameters": {"train_days": train_days, "test_days": test_days, "step_days": step_days or test_days, "anchored": anchored, "warmup_days": warmup_days},
            "folds": folds, "fold_count": len(folds),
            "out_of_sample_concatenated": {"trades": len(oos_r), "total_r": float(np.sum(oos_r)) if oos_r else 0.0,
                                           "expectancy_r": float(np.mean(oos_r)) if oos_r else 0.0,
                                           "folds_with_trades": len(with_trades), "folds_positive": len(positive),
                                           "consistency": float(len(positive) / len(with_trades)) if with_trades else None}}


# --------------------------------------------------------------------------- Monte Carlo

def monte_carlo(returns: list[float], simulations: int = 1000, seed: int = 7, block: int = 1) -> dict[str, Any]:
    """Bootstrap trade-sequence resampling (optionally in blocks) for drawdown and outcome ranges."""
    simulations = int(max(1, simulations))
    if not returns:
        return {"simulations": simulations, "trades_per_path": 0, "final_r_percentiles": {}, "max_drawdown_r_percentiles": {}, "probability_losing": None, "seed": seed}
    rng = np.random.default_rng(seed)
    data = np.asarray(returns, dtype=float)
    n = len(data)
    finals = np.empty(simulations)
    drawdowns = np.empty(simulations)
    for k in range(simulations):
        if block > 1:
            starts = rng.integers(0, n, size=-(-n // block))
            idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
            sample = data[idx]
        else:
            sample = rng.choice(data, size=n, replace=True)
        curve = np.cumsum(sample)
        finals[k] = curve[-1]
        drawdowns[k] = (np.maximum.accumulate(np.r_[0.0, curve])[1:] - curve).max()
    percentiles = [5, 25, 50, 75, 95]
    return {"simulations": simulations, "trades_per_path": n, "seed": seed, "block": block,
            "final_r_percentiles": {str(q): float(np.percentile(finals, q)) for q in percentiles},
            "max_drawdown_r_percentiles": {str(q): float(np.percentile(drawdowns, q)) for q in percentiles},
            "probability_losing": float(np.mean(finals < 0)),
            "observed": {"final_r": float(data.sum()), "max_drawdown_r": float((np.maximum.accumulate(np.r_[0.0, np.cumsum(data)])[1:] - np.cumsum(data)).max())}}


# --------------------------------------------------------------------------- sensitivity

def _set_path(config: dict[str, Any], path: str, value: Any) -> None:
    node = config
    keys = path.split(".")
    for key in keys[:-1]:
        node = node[key]
    node[keys[-1]] = value


def default_sensitivity_grid(strategy_config: dict[str, Any], execution_config: dict[str, Any]) -> list[dict[str, Any]]:
    """One-at-a-time variations declared as experiments in the versioned configuration."""
    grid = [
        {"scope": "strategy", "path": "target.baseline", "values": list(strategy_config.get("target", {}).get("experiments", []))[:4]},
        {"scope": "execution", "path": "slippage.baseline_pips", "values": list(execution_config.get("slippage", {}).get("sensitivity_pips", []))},
        {"scope": "strategy", "path": "risk.baseline_equity_risk_fraction", "values": list(strategy_config.get("risk", {}).get("experiments_equity_risk_fraction", []))},
        {"scope": "strategy", "path": "zones.expiry_m15_bars", "values": [4, 8, 12]},
        {"scope": "strategy", "path": "setup.lifetime_m15_bars_from_sweep_confirmation", "values": [6, 8, 12]},
        {"scope": "strategy", "path": "displacement.minimum_atr", "values": [0.75, 1.0, 1.25]},
        {"scope": "strategy", "path": "stop.reference", "values": ["sweep_extreme", "zone_distal", "leg1_origin"]},
        {"scope": "strategy", "path": "stop.max_distance_atr", "values": [3.0, 4.0, 5.0]},
        {"scope": "strategy", "path": "liquidity.level_max_age_m15_bars", "values": [None, 960, 1920, 3840]},
        # Session experiments: the same rules observed at other session opens. Several keys must move
        # together (windows, scheduled times, session expiry), hence the multi-change form.
        {"scope": "multi", "path": "session", "values": [
            {"label": "london_open_09:00-10:30", "changes": [
                {"scope": "strategy", "path": "observation.windows", "value": [{"start": "09:00", "end": "09:45"}, {"start": "09:45", "end": "10:30"}]},
                {"scope": "strategy", "path": "observation.scheduled_times", "value": ["09:30", "10:00"]},
                {"scope": "strategy", "path": "execution.session_end", "value": "13:00"}]},
            {"label": "new_york_open_15:00-16:30", "changes": [
                {"scope": "strategy", "path": "observation.windows", "value": [{"start": "15:00", "end": "15:45"}, {"start": "15:45", "end": "16:30"}]},
                {"scope": "strategy", "path": "observation.scheduled_times", "value": ["15:30", "16:00"]},
                {"scope": "strategy", "path": "execution.session_end", "value": "19:00"}]},
        ]},
    ]
    return [item for item in grid if item["values"]]


def parameter_sensitivity(data_by_symbol, strategy_config, execution_config, grid: list[dict[str, Any]] | None = None,
                          dataset_hash=None, progress: Progress | None = None) -> dict[str, Any]:
    """Re-run the baseline changing one parameter at a time; report how metrics move."""
    grid = grid if grid is not None else default_sensitivity_grid(strategy_config, execution_config)
    baseline = run_period(data_by_symbol, strategy_config, execution_config, dataset_hash=dataset_hash)
    rows = []
    total = sum(len(item["values"]) for item in grid) or 1
    done = 0
    for item in grid:
        for value in item["values"]:
            if progress:
                progress(f"sensitivity:{item['path']}={value}", done / total)
            done += 1
            strategy = copy.deepcopy(strategy_config)
            execution = copy.deepcopy(execution_config)
            label = value
            try:
                if item["scope"] == "multi":
                    label = value["label"]
                    for change in value["changes"]:
                        _set_path(strategy if change["scope"] == "strategy" else execution, change["path"], change["value"])
                else:
                    target = strategy if item["scope"] == "strategy" else execution
                    _set_path(target, item["path"], value if not (item["path"] == "target.baseline" and isinstance(value, (int, float))) else f"{value}R")
                result = run_period(data_by_symbol, strategy, execution, dataset_hash=dataset_hash)
                summary = _summary(result)
                summary.update({"scope": item["scope"], "parameter": item["path"], "value": label, "error": None})
            except Exception as exc:  # noqa: BLE001 - a bad variant must not abort the whole study
                summary = {"scope": item["scope"], "parameter": item["path"], "value": label, "error": str(exc)}
            rows.append(summary)
    return {"baseline": _summary(baseline), "variants": rows,
            "note": "One-at-a-time variations (and labelled multi-key session experiments); large swings between neighbouring values indicate parameter fragility. Experiments are not the baseline and must not be reported as such."}


# --------------------------------------------------------------------------- cost-matched random benchmark

def _window_minute_mask(bars: Bars, strategy_config: dict[str, Any]) -> np.ndarray:
    """Boolean mask of M1 bars whose *open* lies inside any configured observation window (Madrid)."""
    zone = ZoneInfo(strategy_config["timezones"]["reference"])
    opens = pd.DatetimeIndex(pd.to_datetime(bars.ts - NS_PER_MINUTE, unit="ns", utc=True)).tz_convert(zone)
    minute_of_day = opens.hour.to_numpy() * 60 + opens.minute.to_numpy()
    mask = np.zeros(len(bars), dtype=bool)
    for window in strategy_config["observation"]["windows"]:
        start, end = time.fromisoformat(window["start"]), time.fromisoformat(window["end"])
        s, e = start.hour * 60 + start.minute, end.hour * 60 + end.minute
        mask |= (minute_of_day >= s) & (minute_of_day < e)
    return mask


def cost_matched_random_benchmark(data_by_symbol, strategy_config, execution_config, trades: list[dict[str, Any]],
                                  simulations: int = 200, seed: int = 11, progress: Progress | None = None) -> dict[str, Any]:
    """Random entries inside the observation windows paying the same spread, slippage and commission.

    Each simulation draws one random trade per real trade on the same symbol: a random M1 bar
    whose open lies inside an observation window, a random direction, the real trade's stop
    distance, the baseline target in R and the same session expiry. Comparing the baseline's
    expectancy with this distribution answers "could random timing with identical costs have done
    this?"; the reported percentile is an empirical, one-sided estimate, not a formal test.
    """
    if not trades:
        return {"simulations": simulations, "seed": seed, "note": "No baseline trades to benchmark."}
    rng = np.random.default_rng(seed)
    views = {symbol: Bars(frame.sort_values("timestamp").reset_index(drop=True)) for symbol, frame in data_by_symbol.items()}
    eligible = {symbol: np.flatnonzero(_window_minute_mask(view, strategy_config)) for symbol, view in views.items()}
    eligible = {symbol: idx for symbol, idx in eligible.items() if len(idx)}
    if not eligible:
        return {"simulations": simulations, "seed": seed, "note": "No M1 bars inside observation windows."}
    expectancies = np.empty(simulations)
    totals = np.empty(simulations)
    for k in range(simulations):
        if progress and k % 20 == 0:
            progress("benchmark", k / simulations)
        rs = []
        for real in trades:
            symbol = real["symbol"] if real["symbol"] in eligible else next(iter(eligible))
            view = views[symbol]
            for _attempt in range(10):
                i = int(rng.choice(eligible[symbol]))
                direction = "LONG" if rng.random() < 0.5 else "SHORT"
                stop_distance = abs(float(real["entry_price"]) - float(real["stop_price"]))
                entry_open = view.stamp(i) - pd.Timedelta(minutes=1)
                mid = float(view.open[i])
                stop = mid - stop_distance if direction == "LONG" else mid + stop_distance
                candidate = {"candidate_id": _stable_id(f"random|{k}|{real['trade_id']}|{i}"), "symbol": symbol, "direction": direction,
                             "actual_execution_time": entry_open.isoformat(), "actual_signal_time": entry_open.isoformat(),
                             "bos_timestamp": entry_open.isoformat(), "stop_price": stop, "atr_at_setup": max(stop_distance, 1e-9),
                             "liquidity_level": mid, "sweep_timestamp": entry_open.isoformat(), "sweep_extreme": stop,
                             "zone": {"proximal": mid, "distal": stop, "source_timestamp": entry_open.isoformat()},
                             "scheduled_observation_time": None, "observation_window_index": None}
                outcome = _simulate_candidate(candidate, view, execution_config, strategy_config, 1.0)
                if outcome["trade"] is not None:
                    rs.append(float(outcome["trade"]["r_multiple"]))
                    break
        expectancies[k] = float(np.mean(rs)) if rs else 0.0
        totals[k] = float(np.sum(rs)) if rs else 0.0
    actual = float(np.mean([t["r_multiple"] for t in trades]))
    percentile = float(np.mean(expectancies < actual))
    percentiles = [5, 25, 50, 75, 95]
    return {"simulations": simulations, "seed": seed, "trades_per_simulation": len(trades),
            "baseline_expectancy_r": actual, "baseline_total_r": float(np.sum([t["r_multiple"] for t in trades])),
            "random_expectancy_percentiles": {str(q): float(np.percentile(expectancies, q)) for q in percentiles},
            "random_total_r_percentiles": {str(q): float(np.percentile(totals, q)) for q in percentiles},
            "baseline_percentile_vs_random": percentile,
            "empirical_p_value_one_sided": float(1.0 - percentile),
            "note": "Random entries inside the observation windows with identical stop distance, target, costs and session expiry."}


# --------------------------------------------------------------------------- orchestration

def research_report(data_by_symbol: dict[str, pd.DataFrame], strategy_config: dict[str, Any], execution_config: dict[str, Any],
                    dataset_hash: str | None = None, options: dict[str, Any] | None = None, progress: Progress | None = None) -> dict[str, Any]:
    """Run the full research protocol described in RESEARCH_METHOD.md and return one JSON-ready report."""
    options = {"splits": True, "walk_forward": True, "monte_carlo": True, "sensitivity": True, "benchmark": True,
               "train": 0.6, "validation": 0.2, "train_days": 120, "test_days": 30, "anchored": False,
               "mc_simulations": 1000, "benchmark_simulations": 200, "warmup_days": DEFAULT_WARMUP_DAYS, "seed": 7, **(options or {})}
    report_progress = progress or (lambda _s, _f: None)
    report_progress("baseline", 0.0)
    baseline = run_period(data_by_symbol, strategy_config, execution_config, warmup_days=0, dataset_hash=dataset_hash)
    report: dict[str, Any] = {"options": options, "baseline": _summary(baseline),
                              "limitations": ["Simulated fills on historical M1 data; no live execution was involved.",
                                              "Costs follow config/execution.yaml; provider spreads are used when present.",
                                              "A positive result in one period is not evidence of a robust edge.",
                                              "Historical performance does not guarantee future results."]}
    if options["splits"]:
        report_progress("splits", 0.1)
        report["splits"] = split_evaluation(data_by_symbol, strategy_config, execution_config, options["train"], options["validation"], options["warmup_days"], dataset_hash, progress)
    if options["walk_forward"]:
        report_progress("walk_forward", 0.3)
        report["walk_forward"] = walk_forward(data_by_symbol, strategy_config, execution_config, options["train_days"], options["test_days"], None, options["anchored"], options["warmup_days"], dataset_hash, progress)
    if options["monte_carlo"]:
        report_progress("monte_carlo", 0.6)
        report["monte_carlo"] = monte_carlo([t["r_multiple"] for t in baseline["trades"]], options["mc_simulations"], options["seed"])
    if options["sensitivity"]:
        report_progress("sensitivity", 0.65)
        report["sensitivity"] = parameter_sensitivity(data_by_symbol, strategy_config, execution_config, None, dataset_hash, progress)
    if options["benchmark"]:
        report_progress("benchmark", 0.9)
        report["benchmark"] = cost_matched_random_benchmark(data_by_symbol, strategy_config, execution_config, baseline["trades"], options["benchmark_simulations"], options["seed"], progress)
    report_progress("done", 1.0)
    return report
