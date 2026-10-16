"""Causal market structure: confirmed fractal swings, ATR, H1 bias, and pullback qualification."""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .frames import Bars


@dataclass(frozen=True)
class Swing:
    kind: str
    index: int
    available_index: int
    price: float
    timestamp: pd.Timestamp
    available_at: pd.Timestamp


def _as_bars(bars: pd.DataFrame | Bars) -> Bars:
    return bars if isinstance(bars, Bars) else Bars(bars)


def confirmed_fractal_swings(bars: pd.DataFrame | Bars, left: int = 2, right: int = 2) -> list[Swing]:
    """Strict fractals; ties fail and each pivot appears only at right-bar close."""
    if left < 1 or right < 1:
        raise ValueError("Fractal left/right counts must be positive")
    view = _as_bars(bars)
    highs, lows = view.high, view.low
    found: list[Swing] = []
    n = len(view)
    for pivot in range(left, n - right):
        hi_window = highs[pivot - left:pivot + right + 1]
        lo_window = lows[pivot - left:pivot + right + 1]
        confirmed = pivot + right
        if highs[pivot] == np.max(hi_window) and np.count_nonzero(hi_window == highs[pivot]) == 1:
            found.append(Swing("HIGH", pivot, confirmed, float(highs[pivot]), view.stamp(pivot), view.stamp(confirmed)))
        if lows[pivot] == np.min(lo_window) and np.count_nonzero(lo_window == lows[pivot]) == 1:
            found.append(Swing("LOW", pivot, confirmed, float(lows[pivot]), view.stamp(pivot), view.stamp(confirmed)))
    return sorted(found, key=lambda swing: (swing.available_index, swing.index, swing.kind))


def _atr_before(bars: pd.DataFrame | Bars, index: int, period: int = 14) -> float | None:
    """Simple mean true range over the period ending before index (exclusive)."""
    return _as_bars(bars).atr_before(index, period)


class SwingIndex:
    """Sorted-swing helpers so per-bar queries do not rescan the whole swing list."""

    def __init__(self, swings: list[Swing]):
        self.swings = swings
        self.available = [swing.available_index for swing in swings]
        # Highest price of an earlier same-kind swing, exclusive of the swing itself.
        self.prior_max: list[float] = []
        self.prior_min: list[float] = []
        running_max: dict[str, float] = {}
        running_min: dict[str, float] = {}
        for swing in swings:
            self.prior_max.append(running_max.get(swing.kind, -np.inf))
            self.prior_min.append(running_min.get(swing.kind, np.inf))
            running_max[swing.kind] = max(running_max.get(swing.kind, -np.inf), swing.price)
            running_min[swing.kind] = min(running_min.get(swing.kind, np.inf), swing.price)

    def known_count(self, asof_index: int) -> int:
        return bisect_right(self.available, asof_index)

    def latest_of_kind_before(self, kind: str, index: int) -> Swing | None:
        """Most recently confirmed swing of ``kind`` with ``available_index < index``."""
        for k in range(bisect_left(self.available, index) - 1, -1, -1):
            if self.swings[k].kind == kind:
                return self.swings[k]
        return None


def classify_h1_bias(swings: list[Swing] | SwingIndex, asof_index: int) -> tuple[str, float | None]:
    """Classify from the latest two confirmed highs and lows available at as-of."""
    if isinstance(swings, SwingIndex):
        ordered, count = swings.swings, swings.known_count(asof_index)
    else:
        ordered = [s for s in swings if s.available_index <= asof_index]
        count = len(ordered)
    highs: list[Swing] = []
    lows: list[Swing] = []
    for k in range(count - 1, -1, -1):
        swing = ordered[k]
        if swing.kind == "HIGH" and len(highs) < 2:
            highs.append(swing)
        elif swing.kind == "LOW" and len(lows) < 2:
            lows.append(swing)
        if len(highs) == 2 and len(lows) == 2:
            break
    if len(highs) < 2 or len(lows) < 2:
        return "UNDEFINED", None
    highs.reverse()
    lows.reverse()
    high_up = highs[-1].price > highs[-2].price
    high_down = highs[-1].price < highs[-2].price
    low_up = lows[-1].price > lows[-2].price
    low_down = lows[-1].price < lows[-2].price
    if high_up and low_up and lows[-1].available_at <= highs[-1].available_at:
        return "BULLISH", lows[-1].price
    if high_down and low_down and highs[-1].available_at <= lows[-1].available_at:
        return "BEARISH", highs[-1].price
    return "RANGE", None


def _bias_at(m15_timestamp: pd.Timestamp | int, h1: pd.DataFrame | Bars, h1_swings: list[Swing] | SwingIndex) -> tuple[str, float | None, int]:
    idx = _as_bars(h1).index_at_or_before(m15_timestamp)
    if idx < 0:
        return "UNDEFINED", None, -1
    return (*classify_h1_bias(h1_swings, idx), idx)


def _countertrend_pullback(m15: pd.DataFrame | Bars, swings: list[Swing] | SwingIndex, index: int, bias: str, atr: float | None) -> bool:
    if index < 0:
        return False
    view = _as_bars(m15)
    sindex = swings if isinstance(swings, SwingIndex) else SwingIndex(swings)
    count = sindex.known_count(index)
    recent_positions = [k for k in range(count) if index - sindex.available[k] < 16]
    if bias == "BULLISH":
        lower = sum(1 for k in recent_positions if sindex.prior_max[k] > sindex.swings[k].price)
        displacement = max(0.0, float(np.max(view.high[max(0, index - 15):index + 1])) - float(view.close[index]))
    elif bias == "BEARISH":
        lower = sum(1 for k in recent_positions if sindex.prior_min[k] < sindex.swings[k].price)
        displacement = max(0.0, float(view.close[index]) - float(np.min(view.low[max(0, index - 15):index + 1])))
    else:
        return False
    return lower >= 2 or (atr is not None and atr > 0 and displacement >= 0.50 * atr)


def _nearest_opposite_zone_source(m15: pd.DataFrame | Bars, start: int, direction: str) -> int | None:
    view = _as_bars(m15)
    for i in range(start - 1, -1, -1):
        bearish = view.close[i] < view.open[i]
        bullish = view.close[i] > view.open[i]
        if (direction == "LONG" and bearish) or (direction == "SHORT" and bullish):
            return i
    return None
