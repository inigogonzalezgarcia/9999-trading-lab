"""Clearly labelled SYNTHETIC M1 data for performance and robustness testing.

The output is a seeded random walk with session-shaped volatility, volume and spread. It is NOT
market data and must never be used as research evidence; every row carries a
``dataset_classification`` column equal to ``SYNTHETIC_STRESS_DATA`` so the engine, reports and
readers can tell it apart from provider history.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LABEL = "SYNTHETIC_STRESS_DATA"


def make_stress_bars(start: str, months: int, seed: int = 7, start_price: float = 1.10, pip: float = 0.0001) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    opens = pd.date_range(start, periods=1, tz="UTC")[0]
    minutes = pd.date_range(opens, opens + pd.DateOffset(months=months), freq="min", inclusive="left", tz="UTC")
    # Keep FX hours only: drop Saturday and Sunday before 22:00 UTC.
    weekday = minutes.dayofweek
    hour = minutes.hour
    keep = ~((weekday == 5) | ((weekday == 6) & (hour < 22)) | ((weekday == 4) & (hour >= 22)))
    minutes = minutes[keep]
    n = len(minutes)
    # Volatility follows the session clock: quiet Asia, busier London/New York overlap.
    session_vol = np.where((hour[keep] >= 7) & (hour[keep] < 17), 1.6, np.where((hour[keep] >= 0) & (hour[keep] < 7), 0.7, 1.0))
    step = rng.standard_normal(n) * 0.9 * pip * session_vol
    # Occasional larger impulses so structure, sweeps, and displacements can occur.
    impulses = rng.random(n) < 0.004
    step = step + impulses * rng.standard_normal(n) * 8 * pip
    close = start_price + np.cumsum(step)
    open_ = np.r_[start_price, close[:-1]]
    wick = np.abs(rng.standard_normal(n)) * 0.8 * pip * session_vol
    high = np.maximum(open_, close) + wick
    low = np.minimum(open_, close) - np.abs(rng.standard_normal(n)) * 0.8 * pip * session_vol
    volume = np.maximum(1, (rng.gamma(2.0, 40.0, n) * session_vol)).round().astype(int)
    spread = np.round(np.clip(rng.normal(0.9, 0.25, n) / session_vol, 0.2, 4.0), 2)
    frame = pd.DataFrame({
        "timestamp": minutes.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "open": np.round(open_, 5), "high": np.round(high, 5), "low": np.round(low, 5), "close": np.round(close, 5),
        "volume": volume, "spread_pips": spread, "dataset_classification": LABEL,
    })
    return frame


