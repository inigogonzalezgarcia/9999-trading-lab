"""Configuration loading and the guard that keeps partially specified strategies from running."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .data import Dataset, aggregate_bars, load_market_data
from .metrics import metrics  # noqa: F401  (re-exported for backwards compatibility)
from .timezones import convert_timestamp, scheduled_observations, validate_observation_window_config  # noqa: F401

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
    """Guard for legacy/partial strategy versions (``strategy_v0_1``): they can never emit signals.

    Fully specified versions run through :mod:`backend.app.strategy_v1`.
    """
    require_deterministic_strategy(config)
    raise NotImplementedError("Use backend.app.strategy_v1.run_v1_portfolio for the fully specified V1 engine.")


def backtest(bars: pd.DataFrame, signals: list[dict[str, Any]], config: dict[str, Any], symbol: str, dataset_version: str) -> list[dict[str, Any]]:
    require_deterministic_strategy(config)
    raise NotImplementedError("Use backend.app.strategy_v1.run_v1_portfolio for the fully specified V1 engine.")
