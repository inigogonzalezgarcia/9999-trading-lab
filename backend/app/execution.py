"""Deterministic execution-input resolution for research backtests."""
from __future__ import annotations

from math import isfinite
from typing import Any


def resolve_spread(historical_spread_pips: Any, execution_config: dict[str, Any]) -> dict[str, Any]:
    """Prefer valid provider spread, then explicit fixed config, else block the candidate."""
    try:
        historical = float(historical_spread_pips)
    except (TypeError, ValueError):
        historical = float("nan")
    if isfinite(historical) and historical >= 0:
        return {"spread_pips": historical, "spread_source": "HISTORICAL_SPREAD", "candidate_status": None}

    spread_cfg = execution_config.get("spread", {})
    fixed_value = spread_cfg.get("fixed_fallback_pips")
    try:
        fixed = float(fixed_value)
    except (TypeError, ValueError):
        fixed = float("nan")
    if isfinite(fixed) and fixed >= 0:
        return {"spread_pips": fixed, "spread_source": "FIXED_CONFIGURED_SPREAD", "candidate_status": None}

    return {"spread_pips": None, "spread_source": "NO_SPREAD_DATA", "candidate_status": "SPREAD_DATA_UNAVAILABLE"}
