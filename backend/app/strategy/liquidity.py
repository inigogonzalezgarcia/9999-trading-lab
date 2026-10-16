"""Liquidity levels: immutable cluster history and ACTIVE/TOUCHED/SWEPT/INVALIDATED lifecycle events."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .frames import Bars, BlockMinMax, ns_of
from .ids import _stable_id
from .structure import Swing, _as_bars


def _liquidity_level_history(m15: pd.DataFrame | Bars, h1_swings: list[Swing], m15_swings: list[Swing], tolerance_atr: float) -> list[dict[str, Any]]:
    """Build immutable level/cluster versions using ATR known at each creation time."""
    view = _as_bars(m15)
    source_events = [("H1", swing) for swing in h1_swings] + [("M15", swing) for swing in m15_swings]
    source_events.sort(key=lambda item: (item[1].available_at, 0 if item[0] == "H1" else 1, item[1].kind))
    history: list[dict[str, Any]] = []
    live_by_kind: dict[str, list[dict[str, Any]]] = {"HIGH": [], "LOW": []}
    m15_ts = view.ts
    for timeframe, swing in source_events:
        m15_index = int(np.searchsorted(m15_ts, ns_of(swing.available_at), side="right") - 1)
        atr_at_creation = view.atr_before(m15_index + 1, 14) if m15_index >= 0 else None
        live = live_by_kind.setdefault(swing.kind, [])
        possible = []
        for cluster in live:
            # Equal highs/lows within one timeframe remain an experimental, disabled feature.
            if timeframe in cluster["timeframes"]:
                continue
            atr = cluster["atr_at_creation"] or atr_at_creation
            if atr is not None and atr > 0 and abs(float(swing.price) - cluster["price"]) <= tolerance_atr * atr:
                possible.append(cluster)
        if possible:
            chosen = min(possible, key=lambda cluster: (0 if "H1" in cluster["timeframes"] else 1, cluster["oldest_confirmed"]))
            chosen["superseded_at"] = swing.available_at
            live.remove(chosen)
            members = chosen["constituents"] + [{"timeframe": timeframe, "kind": swing.kind, "price": swing.price,
                                                  "available_at": swing.available_at.isoformat()}]
            frozen_atr = chosen["atr_at_creation"] or atr_at_creation
            new = {"kind": swing.kind, "constituents": members, "price": float(np.mean([item["price"] for item in members])),
                   "timeframes": sorted(set(chosen["timeframes"] + [timeframe])), "oldest_confirmed": min(chosen["oldest_confirmed"], swing.available_at),
                   "effective_from": swing.available_at, "superseded_at": None, "atr_at_creation": frozen_atr,
                   "tolerance": tolerance_atr * frozen_atr if frozen_atr is not None else None}
            new["cluster_id"] = _stable_id("liquidity|" + "|".join(sorted(f"{item['timeframe']}:{item['kind']}:{item['available_at']}:{item['price']}" for item in members)))
        else:
            member = {"timeframe": timeframe, "kind": swing.kind, "price": swing.price, "available_at": swing.available_at.isoformat()}
            new = {"kind": swing.kind, "constituents": [member], "price": float(swing.price), "timeframes": [timeframe],
                   "oldest_confirmed": swing.available_at, "effective_from": swing.available_at, "superseded_at": None,
                   "atr_at_creation": None, "tolerance": None}
            new["cluster_id"] = _stable_id(f"liquidity|{timeframe}|{swing.kind}|{swing.available_at.isoformat()}|{swing.price}")
        history.append(new)
        live.append(new)
    return history


def build_liquidity_lifecycle_events(
    m1: pd.DataFrame | Bars, m15: pd.DataFrame | Bars, levels: list[dict[str, Any]], symbol: str,
) -> list[dict[str, Any]]:
    """Emit level state transitions at the first candle close that proves them."""
    m1v, m15v = _as_bars(m1), _as_bars(m15)
    finder = BlockMinMax(m1v.low, m1v.high)
    events: list[dict[str, Any]] = []
    for level in levels:
        level_id = level["cluster_id"]
        price = float(level["price"])
        kind = level["kind"]
        timeframe_label = "+".join(level["timeframes"])
        events.append({"event_id": _stable_id(f"{level_id}|ACTIVE|{level['effective_from'].isoformat()}"),
                       "level_id": level_id, "symbol": symbol, "timeframe": timeframe_label,
                       "level_price": price, "level_type": kind, "previous_state": None, "new_state": "ACTIVE",
                       "detection_timestamp": level["effective_from"].isoformat(),
                       "source_candle_timestamp": level["effective_from"].isoformat(), "source_timeframe": timeframe_label,
                       "metadata": {"constituents": level["constituents"]}})
        lo = m1v.first_index_after(level["effective_from"])
        hi = len(m1v) if level["superseded_at"] is None else m1v.first_index_at_or_after(level["superseded_at"])
        touch_index = finder.first_low_at_or_below(price, lo, hi) if kind == "LOW" else finder.first_high_at_or_above(price, lo, hi)
        if touch_index is None:
            continue
        touch_time = m1v.stamp(touch_index)
        events.append({"event_id": _stable_id(f"{level_id}|TOUCHED|{touch_time.isoformat()}"),
                       "level_id": level_id, "symbol": symbol, "timeframe": timeframe_label,
                       "level_price": price, "level_type": kind, "previous_state": "ACTIVE", "new_state": "TOUCHED",
                       "detection_timestamp": touch_time.isoformat(), "source_candle_timestamp": touch_time.isoformat(),
                       "source_timeframe": "M1", "metadata": {"wick_low": float(m1v.low[touch_index]), "wick_high": float(m1v.high[touch_index])}})
        m15_index = m15v.first_index_at_or_after(m1v.ts[touch_index])
        if m15_index >= len(m15v):
            continue
        close = float(m15v.close[m15_index])
        swept = close > price if kind == "LOW" else close < price
        invalidated = close < price if kind == "LOW" else close > price
        if swept or invalidated:
            new_state = "SWEPT" if swept else "INVALIDATED"
            confirm_time = m15v.stamp(m15_index)
            events.append({"event_id": _stable_id(f"{level_id}|{new_state}|{confirm_time.isoformat()}"),
                           "level_id": level_id, "symbol": symbol, "timeframe": timeframe_label,
                           "level_price": price, "level_type": kind, "previous_state": "TOUCHED", "new_state": new_state,
                           "detection_timestamp": confirm_time.isoformat(), "source_candle_timestamp": confirm_time.isoformat(),
                           "source_timeframe": "M15", "metadata": {"m15_close": close, "m1_breach_timestamp": touch_time.isoformat()}})
    events.sort(key=lambda event: (event["detection_timestamp"], event["level_id"], event["new_state"]))
    return events
