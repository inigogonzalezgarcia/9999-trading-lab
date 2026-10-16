"""Public facade for the Strategy V1 engine.

The implementation lives in :mod:`backend.app.strategy`; this module keeps the historical import
surface stable (``from backend.app.strategy_v1 import run_v1_portfolio``) and routes candidate
generation through the module attribute so tests can monkeypatch ``generate_v1_candidates`` here.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from .strategy import portfolio as _portfolio
from .strategy.candidates import (_candidate_from_sweep, _expired_candidate, _rejected_sweep_candidate, _window_id,
                                  detect_sweeps, generate_v1_candidates)
from .strategy.frames import Bars
from .strategy.ids import _normalized_rejection, _stable_id, canonical_config_hash
from .strategy.liquidity import _liquidity_level_history, build_liquidity_lifecycle_events
from .strategy.simulation import _simulate_candidate
from .strategy.structure import (Swing, SwingIndex, _atr_before, _bias_at, _countertrend_pullback,
                                 _nearest_opposite_zone_source, classify_h1_bias, confirmed_fractal_swings)
from .strategy.zones import build_zone_lifecycle

__all__ = [
    "Bars", "Swing", "SwingIndex", "build_daily_contexts", "build_liquidity_lifecycle_events", "build_zone_lifecycle",
    "canonical_config_hash", "classify_h1_bias", "confirmed_fractal_swings", "detect_sweeps", "generate_v1_candidates",
    "run_v1_backtest", "run_v1_portfolio",
    "_atr_before", "_bias_at", "_candidate_from_sweep", "_countertrend_pullback", "_expired_candidate",
    "_liquidity_level_history", "_nearest_opposite_zone_source", "_normalized_rejection", "_rejected_sweep_candidate",
    "_simulate_candidate", "_stable_id", "_window_id",
]


def _generator(bars: pd.DataFrame, symbol: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    # Resolved at call time so a monkeypatched module attribute takes effect.
    return generate_v1_candidates(bars, symbol, config)


def build_daily_contexts(data_by_symbol: dict[str, pd.DataFrame], strategy_config: dict[str, Any],
                         dataset_hash: str | None = None, execution_config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return _portfolio.build_daily_contexts(data_by_symbol, strategy_config, dataset_hash, execution_config, _generator)


def run_v1_portfolio(data_by_symbol: dict[str, pd.DataFrame], strategy_config: dict[str, Any], execution_config: dict[str, Any],
                     dataset_hash: str | None = None, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("candidate_generator", _generator)
    return _portfolio.run_v1_portfolio(data_by_symbol, strategy_config, execution_config, dataset_hash, **kwargs)


def run_v1_backtest(m1_bars: pd.DataFrame, symbol: str, strategy_config: dict[str, Any], execution_config: dict[str, Any],
                    dataset_hash: str | None = None, **kwargs: Any) -> dict[str, Any]:
    result = run_v1_portfolio({symbol: m1_bars}, strategy_config, execution_config, dataset_hash, **kwargs)
    result["symbol"] = symbol
    return result
