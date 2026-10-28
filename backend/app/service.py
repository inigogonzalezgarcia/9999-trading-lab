"""Shared orchestration used by the HTTP API, the CLI and background jobs.

Everything here is research-only. The educational notice is attached to every result so exports
and reports carry it verbatim.
"""
from __future__ import annotations

import copy
import logging
import os
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

from .core import load_config
from .data import Dataset, aggregate_bars, load_market_data
from .explain import explain_all
from .metrics import equity_curve, metrics
from .research import research_report
from .strategy_v1 import canonical_config_hash, run_v1_portfolio
from .timezones import scheduled_observations, timezone_database_version

log = logging.getLogger("fxlab")

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
SOFTWARE_VERSION = "0.5.0"

EDUCATIONAL_NOTICE = {
    "title": "Educational research tool",
    "lines": [
        "This software is an educational research and backtesting tool. It is not investment advice, "
        "not a trading signal service, and it has no broker connection or live execution.",
        "All results are simulated on historical data using the recorded strategy and execution "
        "assumptions. Simulated results are not evidence of a profitable edge and historical "
        "performance does not guarantee future results.",
        "The author is not a licensed or registered financial adviser. Trading leveraged foreign "
        "exchange involves a high risk of loss; nothing here should be used to place real trades.",
    ],
}


def software_revision() -> str:
    """Prefer the deployed commit; otherwise fingerprint the research engine sources."""
    commit = os.getenv("GIT_COMMIT")
    if commit:
        return commit
    digest = sha256()
    files = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "backend" / "app").rglob("*.py"))
    for relative in files:
        digest.update(relative.encode("utf-8"))
        digest.update((ROOT / relative).read_bytes())
    return "source-sha256:" + digest.hexdigest()


DEFAULT_STRATEGY = "strategy_v1.yaml"


def available_strategies() -> list[str]:
    """Strategy configuration files that can run (status FULLY_SPECIFIED), e.g. strategy_v1.yaml, strategy_v1_1.yaml."""
    names = []
    for path in sorted(CONFIG_DIR.glob("strategy_*.yaml")):
        try:
            if load_config(path).get("status") == "FULLY_SPECIFIED":
                names.append(path.name)
        except Exception:  # noqa: BLE001 - an unreadable experiment must not hide the others
            continue
    return names


def available_strategy_instruments(strategy_file: str) -> list[str]:
    return list(load_config(resolve_strategy_file(strategy_file)).get("instruments", []))


def resolve_strategy_file(name: str | None) -> Path:
    candidate = Path(name or DEFAULT_STRATEGY).name  # no directories: configs live in config/ only
    if not candidate.startswith("strategy_") or not candidate.endswith(".yaml"):
        raise ValueError("strategy must be a config/strategy_*.yaml file")
    path = CONFIG_DIR / candidate
    if not path.is_file():
        raise ValueError(f"Unknown strategy configuration: {candidate}")
    return path


def load_configs(fixed_spread_pips: float | None = None, strategy_file: str | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    strategy = load_config(resolve_strategy_file(strategy_file))
    execution = load_config(CONFIG_DIR / "execution.yaml")
    data_config = load_config(CONFIG_DIR / "data.yaml")
    if fixed_spread_pips is not None:
        execution = copy.deepcopy(execution)
        execution["spread"]["fixed_fallback_pips"] = float(fixed_spread_pips)
        execution["spread"]["fixed_fallback_origin"] = "runtime_override"
    return strategy, execution, data_config


def split_by_symbol(dataset: Dataset, symbol: str, strategy: dict[str, Any]) -> dict[str, pd.DataFrame]:
    if symbol != "PORTFOLIO" and symbol not in strategy["instruments"]:
        raise ValueError(f"Strategy {strategy['strategy_version']} permits {', '.join(strategy['instruments'])} or PORTFOLIO; add the instrument to its YAML to research it")
    if symbol == "PORTFOLIO":
        if "symbol" not in dataset.bars.columns:
            raise ValueError("Portfolio uploads require a symbol column containing EURUSD and/or GBPUSD")
        data = {name: group.drop(columns=["symbol"]).reset_index(drop=True) for name, group in dataset.bars.groupby("symbol") if name in strategy["instruments"]}
        if not data or len(data) != dataset.bars.symbol.nunique():
            raise ValueError("Portfolio data contains unsupported or missing symbols")
        return data
    return {symbol: dataset.bars}


def apply_context_mode(strategy: dict[str, Any], mode: str) -> tuple[dict[str, Any], bool]:
    """``full`` replays all history per day, ``lookback:N`` caps it to N days, ``none`` skips contexts."""
    if mode == "full":
        return strategy, True
    if mode == "none":
        return strategy, False
    if mode.startswith("lookback:"):
        days = int(mode.split(":", 1)[1])
        adjusted = copy.deepcopy(strategy)
        adjusted.setdefault("preparation", {})["context_lookback_days"] = days
        return adjusted, True
    raise ValueError("daily_contexts must be 'full', 'none' or 'lookback:<days>'")


def reproducibility(dataset: Dataset, strategy: dict[str, Any], execution: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    return {"dataset_hash": dataset.version,
            "dataset_date_range_utc": {"start": dataset.bars.timestamp.min().isoformat(), "end": dataset.bars.timestamp.max().isoformat()},
            "strategy_version": strategy["strategy_version"], "strategy_file": options.get("strategy", DEFAULT_STRATEGY),
            "config_hash": canonical_config_hash(strategy, execution),
            "strategy_config_hash": canonical_config_hash(strategy), "execution_config_hash": canonical_config_hash(execution),
            "strategy_config": strategy, "execution_config": execution, "execution_model": execution["entry_model"],
            "spread_source": execution["spread"]["report_source_labels"], "slippage_model": execution["slippage"],
            "commission_model": execution["commission"], "timezone_config": strategy["timezones"],
            "timezone_database_version": timezone_database_version(), "software_version": SOFTWARE_VERSION,
            "software_revision": software_revision(), "run_options": options}


def schedule_for(dataset: Dataset, strategy: dict[str, Any], max_days: int = 400) -> list[dict[str, Any]]:
    local_dates = dataset.bars.timestamp.dt.tz_convert(strategy["timezones"]["reference"]).dt.date
    days = pd.date_range(min(local_dates), max(local_dates), freq="D")
    schedule: list[dict[str, Any]] = []
    for day in days[:max_days]:
        schedule.extend(scheduled_observations(day.date().isoformat(), strategy))
    return schedule


def chart_series(data_by_symbol: dict[str, pd.DataFrame], timeframe: str = "M15", max_bars: int = 40000) -> dict[str, list[dict[str, Any]]]:
    """Aggregated candles for the UI (labelled by close time, UTC seconds)."""
    out = {}
    for symbol, bars in data_by_symbol.items():
        frame = aggregate_bars(bars, timeframe) if timeframe != "M1" else bars
        if len(frame) > max_bars:
            frame = frame.iloc[-max_bars:]
        seconds = (frame.timestamp.astype("int64") // 1_000_000_000).to_numpy()
        out[symbol] = [{"time": int(t), "open": float(o), "high": float(h), "low": float(lo), "close": float(c)}
                       for t, o, h, lo, c in zip(seconds, frame.open, frame.high, frame.low, frame.close)]
    return out


def run_backtest(dataset: Dataset, symbol: str, options: dict[str, Any] | None = None,
                 progress: Callable[[str, float], None] | None = None) -> dict[str, Any]:
    """Validate -> schedule -> V1 engine -> metrics -> chart material -> reproducibility."""
    options = {"daily_contexts": "lookback:30", "fixed_spread_pips": None, "chart_timeframe": "M15", "include_chart": True,
               "context_detail": "summary", "strategy": DEFAULT_STRATEGY, **(options or {})}
    strategy, execution, _ = load_configs(options["fixed_spread_pips"], options["strategy"])
    data_by_symbol = split_by_symbol(dataset, symbol, strategy)
    strategy, include_contexts = apply_context_mode(strategy, options["daily_contexts"])
    base = {"strategy_version": strategy["strategy_version"], "strategy_status": strategy["status"], "quality": dataset.quality,
            "dataset_version": dataset.version, "timezone_database": timezone_database_version(),
            "scheduled_observations": schedule_for(dataset, strategy), "reproducibility": reproducibility(dataset, strategy, execution, options),
            "notice": EDUCATIONAL_NOTICE}
    if strategy["status"] != "FULLY_SPECIFIED":
        return {**base, "backtest_blocked": True, "blocked_reason": "The V1 engine is not yet validated; no trades or performance results were generated.",
                "signal_count": None, "trades": [], "metrics": None, "report": None}
    result = run_v1_portfolio(data_by_symbol, strategy, execution, dataset_hash=dataset.version, include_daily_contexts=include_contexts, progress=progress)
    if symbol != "PORTFOLIO":
        result["symbol"] = symbol
    if options["context_detail"] != "full":
        # Full contexts carry every structure point and level per day (~90 MB for a year); keep a per-day digest.
        result["daily_contexts"] = [compact_context(context) for context in result["daily_contexts"]]
    period = base["reproducibility"]["dataset_date_range_utc"]
    result["metrics"] = metrics(result["trades"], period["start"], period["end"])
    result["equity_curve"] = equity_curve(result["trades"])
    if options.get("include_explainers", True):
        result["trade_explainers"] = explain_all(result["trades"], result["events"], data_by_symbol, strategy)
    if options["include_chart"]:
        result["chart"] = {"timeframe": options["chart_timeframe"], "series": chart_series(data_by_symbol, options["chart_timeframe"])}
    base["reproducibility"]["spread_source"] = result["spread_sources"]
    result.update(base)
    result.update({"backtest_blocked": False,
                   "report": {"spread_sources": result["spread_sources"], "candidate_count": result["candidate_count"],
                              "executable_trade_count": result["signal_count"], "timezone_database": base["timezone_database"],
                              "strategy_version": strategy["strategy_version"], "execution_version": execution["version"],
                              "execution_model": execution["entry_model"], "slippage_model": execution["slippage"],
                              "commission_model": execution["commission"], "daily_contexts": options["daily_contexts"],
                              "rejections": _rejection_histogram(result["events"]),
                              "timing": _timing_histograms(result["events"], strategy["timezones"]["reference"], strategy["observation"]["windows"])}})
    return result


def compact_context(context: dict[str, Any]) -> dict[str, Any]:
    keep = ("context_id", "symbol", "trading_date", "created_at", "available_data_through", "h1_bias", "h1_premise",
            "context_lookback_days", "config_hash", "dataset_hash")
    return {**{key: context.get(key) for key in keep},
            "h1_swings": len(context.get("h1_structure", [])), "m15_swings": len(context.get("m15_structure", [])),
            "liquidity_levels": len(context.get("liquidity_levels", [])), "active_zones": context.get("active_zones", []),
            "detail": "summary"}


def _rejection_histogram(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        key = event.get("rejection_reason") or event.get("candidate_status") or "UNKNOWN"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: -item[1]))


def _timing_histograms(events: list[dict[str, Any]], zone: str, windows: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """When the pattern actually completes, by local hour: tells whether the observation windows fit the market."""
    def by_hour(stamps: list[str]) -> dict[str, int]:
        counts = {f"{hour:02d}": 0 for hour in range(24)}
        for stamp in stamps:
            if stamp:
                counts[pd.Timestamp(stamp).tz_convert(zone).strftime("%H")] += 1
        return counts
    complete = [event for event in events if event.get("state") == "BOS_CONFIRMED"]
    return {"timezone": zone, "windows": windows,
            "sweep_confirmations_by_hour": by_hour([event.get("sweep_confirmation_timestamp") for event in events]),
            "complete_setups_by_hour": by_hour([event.get("actual_signal_time") for event in complete]),
            "complete_setups": len(complete),
            "complete_setups_outside_windows": sum(1 for event in complete if event.get("candidate_status") == "NOT_TRADEABLE_OUTSIDE_OBSERVATION_WINDOW")}


def run_research(dataset: Dataset, symbol: str, options: dict[str, Any] | None = None,
                 progress: Callable[[str, float], None] | None = None) -> dict[str, Any]:
    options = {"fixed_spread_pips": None, "strategy": DEFAULT_STRATEGY, **(options or {})}
    strategy, execution, _ = load_configs(options.pop("fixed_spread_pips"), options.get("strategy"))
    data_by_symbol = split_by_symbol(dataset, symbol, strategy)
    report = research_report(data_by_symbol, strategy, execution, dataset.version, options, progress)
    report.update({"symbol": symbol, "quality": dataset.quality, "dataset_version": dataset.version,
                   "reproducibility": reproducibility(dataset, strategy, execution, options), "notice": EDUCATIONAL_NOTICE})
    return report


def load_dataset(path: str | Path, timeframe: str = "M1", source_timezone: str | None = None) -> Dataset:
    _, _, data_config = load_configs()
    return load_market_data(path, timeframe=timeframe, source_timezone=source_timezone, timestamp_semantics=data_config["source_timestamp_semantics"])


def summarize(result: dict[str, Any], kind: str) -> dict[str, Any]:
    """Compact summary stored alongside the full result for run history listings."""
    if kind == "research":
        base = result.get("baseline", {})
        return {"trades": base.get("trades"), "expectancy_r": base.get("expectancy_r"), "total_r": base.get("total_r"),
                "max_drawdown_r": base.get("max_drawdown_r"), "benchmark_percentile": result.get("benchmark", {}).get("baseline_percentile_vs_random"),
                "walk_forward_consistency": result.get("walk_forward", {}).get("out_of_sample_concatenated", {}).get("consistency")}
    m = result.get("metrics") or {}
    return {"trades": m.get("total_trades"), "expectancy_r": m.get("expectancy_r"), "total_r": m.get("total_r"),
            "win_rate": m.get("win_rate"), "profit_factor": m.get("profit_factor"), "max_drawdown_r": m.get("max_drawdown_r"),
            "candidates": result.get("candidate_count"), "blocked": result.get("backtest_blocked")}
