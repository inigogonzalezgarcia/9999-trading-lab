"""Stable identifiers and configuration fingerprints for reproducible reruns."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any
from uuid import NAMESPACE_URL, uuid5


def _stable_id(key: str) -> str:
    """Stable event identity for reproducible reruns of identical inputs."""
    return str(uuid5(NAMESPACE_URL, key))


def canonical_config_hash(config: dict[str, Any], execution_config: dict[str, Any] | None = None) -> str:
    material = {"strategy": config, "execution": execution_config} if execution_config is not None else config
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _normalized_rejection(status: str | None) -> str | None:
    return {
        "CANDIDATE_SETUP": None, "EXECUTED": None,
        "NOT_TRADEABLE_OUTSIDE_OBSERVATION_WINDOW": "ENTRY_OUTSIDE_WINDOW",
        "STOP_DISTANCE_EXCEEDED": "INVALID_STOP_DISTANCE",
        "WINDOW_TRADE_LIMIT_REJECTED": "RISK_LIMIT_SYMBOL",
        "RISK_LIMIT_REJECTED": "RISK_LIMIT_GLOBAL",
        "CONCURRENT_POSITION_REJECTED": "CONCURRENT_POSITION_LIMIT",
        "SETUP_LIFETIME_EXPIRED": "SETUP_TIMEOUT",
        "SPREAD_DATA_UNAVAILABLE": "SPREAD_DATA_UNAVAILABLE",
        "DATA_GAP": "DATA_GAP",
    }.get(status, status)
