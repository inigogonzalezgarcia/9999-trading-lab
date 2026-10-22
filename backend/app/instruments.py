"""Instrument specifications (pip size, Dukascopy price scale, contract size) from config/instruments.yaml."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
INSTRUMENTS_FILE = ROOT / "config" / "instruments.yaml"


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    with open(INSTRUMENTS_FILE, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def known_instruments() -> list[str]:
    return sorted(_load()["instruments"])


def spec(symbol: str) -> dict[str, Any]:
    """Specification for ``symbol``; unknown symbols fall back to the configured default (4-decimal FX)."""
    data = _load()
    return {**data["default"], **data["instruments"].get(symbol.upper(), {})}


def pip_size(symbol: str) -> float:
    return float(spec(symbol)["pip"])


def dukascopy_point(symbol: str) -> int:
    return int(spec(symbol)["dukascopy_point"])


def contract_size(symbol: str) -> float:
    return float(spec(symbol)["contract_size"])
