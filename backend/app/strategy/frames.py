"""Numpy views over closed-candle DataFrames.

The engine only ever reads completed candles whose ``timestamp`` is the UTC close time.
Pandas row access is far too slow for minute data (hundreds of thousands of rows per year), so
hot paths work on these arrays and convert back to ``pd.Timestamp`` only when emitting events.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import numpy as np
import pandas as pd

NS_PER_MINUTE = 60_000_000_000


def utc_ns(values: pd.Series | pd.DatetimeIndex) -> np.ndarray:
    """Timezone-aware timestamps as int64 nanoseconds since the epoch (UTC)."""
    index = pd.DatetimeIndex(values)
    if index.tz is None:
        raise ValueError("engine timestamps must be timezone-aware")
    return index.tz_convert("UTC").tz_localize(None).to_numpy().astype("datetime64[ns]").astype("int64")


def ts(ns: int) -> pd.Timestamp:
    return pd.Timestamp(int(ns), unit="ns", tz="UTC")


def ns_of(value: pd.Timestamp | str | int | np.integer) -> int:
    """Nanoseconds since epoch for one timezone-aware instant (ints pass through)."""
    if isinstance(value, (int, np.integer)):
        return int(value)
    return int(utc_ns(pd.DatetimeIndex([pd.Timestamp(value)]))[0])


@dataclass
class Bars:
    """Immutable array view over a chronologically sorted candle frame."""

    frame: pd.DataFrame

    def __post_init__(self) -> None:
        frame = self.frame
        self.ts = utc_ns(frame["timestamp"])

        def column(name: str) -> np.ndarray | None:
            # Test fixtures may supply partial frames; missing price columns become NaN arrays.
            return frame[name].to_numpy(dtype=float) if name in frame.columns else None

        self.open = column("open") if "open" in frame.columns else np.full(len(self.ts), np.nan)
        self.high = column("high") if "high" in frame.columns else np.full(len(self.ts), np.nan)
        self.low = column("low") if "low" in frame.columns else np.full(len(self.ts), np.nan)
        self.close = column("close") if "close" in frame.columns else np.full(len(self.ts), np.nan)
        self.spread = column("spread_pips")
        self.commission = column("commission_per_lot")

    def __len__(self) -> int:
        return len(self.ts)

    @cached_property
    def true_range(self) -> np.ndarray:
        """True range with the first bar's prior close taken as its own open (engine convention)."""
        if len(self.ts) == 0:
            return np.zeros(0)
        prior_close = np.r_[self.open[0], self.close[:-1]]
        return np.maximum.reduce([self.high - self.low, np.abs(self.high - prior_close), np.abs(self.low - prior_close)])

    def atr_before(self, index: int, period: int = 14) -> float | None:
        """Mean true range over ``period`` bars ending before ``index`` (exclusive)."""
        start = index - period
        if start < 0:
            return None
        window = self.true_range[start:index]
        return float(np.mean(window)) if len(window) else None

    def stamp(self, index: int) -> pd.Timestamp:
        return ts(self.ts[index])

    def index_at_or_before(self, instant: pd.Timestamp | int) -> int:
        """Index of the last bar closed at or before ``instant`` (``-1`` when none)."""
        value = ns_of(instant)
        return int(np.searchsorted(self.ts, value, side="right") - 1)

    def first_index_after(self, instant: pd.Timestamp | int) -> int:
        value = ns_of(instant)
        return int(np.searchsorted(self.ts, value, side="right"))

    def first_index_at_or_after(self, instant: pd.Timestamp | int) -> int:
        value = ns_of(instant)
        return int(np.searchsorted(self.ts, value, side="left"))

    def spread_at(self, index: int):
        return None if self.spread is None else self.spread[index]

    def commission_at(self, index: int, default: float) -> float:
        if self.commission is None:
            return float(default)
        value = self.commission[index]
        return float(default) if np.isnan(value) else float(value)


class BlockMinMax:
    """Find the first index in a range where ``low <= price`` or ``high >= price`` quickly.

    Levels that are never touched would otherwise force a full scan of every later M1 bar for
    every level. Block minima/maxima skip untouched blocks in O(n / block + block).
    """

    def __init__(self, low: np.ndarray, high: np.ndarray, block: int = 512):
        self.low, self.high, self.block = low, high, block
        n = len(low)
        padded = -(-n // block) * block if n else 0
        low_pad = np.full(padded, np.inf)
        high_pad = np.full(padded, -np.inf)
        low_pad[:n], high_pad[:n] = low, high
        self.block_low = low_pad.reshape(-1, block).min(axis=1) if padded else np.zeros(0)
        self.block_high = high_pad.reshape(-1, block).max(axis=1) if padded else np.zeros(0)

    def first_low_at_or_below(self, price: float, start: int, stop: int) -> int | None:
        return self._first(self.low, self.block_low, price, start, stop, below=True)

    def first_high_at_or_above(self, price: float, start: int, stop: int) -> int | None:
        return self._first(self.high, self.block_high, price, start, stop, below=False)

    def _first(self, values, blocks, price, start, stop, below):
        stop = min(stop, len(values))
        if start >= stop:
            return None
        i = start
        while i < stop:
            b = i // self.block
            block_end = min((b + 1) * self.block, stop)
            hit_block = blocks[b] <= price if below else blocks[b] >= price
            if hit_block:
                segment = values[i:block_end]
                mask = segment <= price if below else segment >= price
                if mask.any():
                    return i + int(np.argmax(mask))
            i = block_end
        return None
