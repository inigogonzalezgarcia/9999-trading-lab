"""Causal Strategy V1 event generation and single-symbol execution simulator.

Every price decision consumes completed candles only. The module deliberately
keeps the event log even when spread or portfolio rules reject execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .data import aggregate_bars
from .execution import resolve_spread
from .timezones import observation_windows_at


def _stable_id(key: str) -> str:
    """Stable event identity for reproducible reruns of identical inputs."""
    return str(uuid5(NAMESPACE_URL, key))


@dataclass(frozen=True)
class Swing:
    kind: str
    index: int
    available_index: int
    price: float
    timestamp: pd.Timestamp
    available_at: pd.Timestamp


def confirmed_fractal_swings(bars: pd.DataFrame, left: int = 2, right: int = 2) -> list[Swing]:
    """Strict fractals; ties fail and each pivot appears only at right-bar close."""
    if left < 1 or right < 1:
        raise ValueError("Fractal left/right counts must be positive")
    found: list[Swing] = []
    highs, lows = bars.high.to_numpy(float), bars.low.to_numpy(float)
    for pivot in range(left, len(bars) - right):
        hi_window = highs[pivot-left:pivot+right+1]
        lo_window = lows[pivot-left:pivot+right+1]
        confirmed = pivot + right
        if highs[pivot] == np.max(hi_window) and np.count_nonzero(hi_window == highs[pivot]) == 1:
            found.append(Swing("HIGH", pivot, confirmed, highs[pivot], bars.timestamp.iloc[pivot], bars.timestamp.iloc[confirmed]))
        if lows[pivot] == np.min(lo_window) and np.count_nonzero(lo_window == lows[pivot]) == 1:
            found.append(Swing("LOW", pivot, confirmed, lows[pivot], bars.timestamp.iloc[pivot], bars.timestamp.iloc[confirmed]))
    return sorted(found, key=lambda swing: (swing.available_index, swing.index, swing.kind))


def _atr_before(bars: pd.DataFrame, index: int, period: int = 14) -> float | None:
    """Simple mean true range over the period ending before index (exclusive)."""
    end = index
    start = end - period
    if start < 0:
        return None
    prior_close = bars.close.iloc[start-1] if start else bars.open.iloc[start]
    ranges = []
    for i in range(start, end):
        ranges.append(max(bars.high.iloc[i]-bars.low.iloc[i], abs(bars.high.iloc[i]-prior_close), abs(bars.low.iloc[i]-prior_close)))
        prior_close = bars.close.iloc[i]
    return float(np.mean(ranges)) if ranges else None


def classify_h1_bias(swings: list[Swing], asof_index: int) -> tuple[str, float | None]:
    """Classify from the latest two confirmed highs and lows available at as-of."""
    known = [s for s in swings if s.available_index <= asof_index]
    highs = [s for s in known if s.kind == "HIGH"][-2:]
    lows = [s for s in known if s.kind == "LOW"][-2:]
    if len(highs) < 2 or len(lows) < 2:
        return "UNDEFINED", None
    high_up = highs[-1].price > highs[-2].price
    high_down = highs[-1].price < highs[-2].price
    low_up = lows[-1].price > lows[-2].price
    low_down = lows[-1].price < lows[-2].price
    if high_up and low_up and lows[-1].available_at <= highs[-1].available_at:
        return "BULLISH", lows[-1].price
    if high_down and low_down and highs[-1].available_at <= lows[-1].available_at:
        return "BEARISH", highs[-1].price
    return "RANGE", None


def _bias_at(m15_timestamp: pd.Timestamp, h1: pd.DataFrame, h1_swings: list[Swing]) -> tuple[str, float | None, int]:
    idx = int(h1.timestamp.searchsorted(m15_timestamp, side="right") - 1)
    if idx < 0:
        return "UNDEFINED", None, -1
    return (*classify_h1_bias(h1_swings, idx), idx)


def _countertrend_pullback(m15: pd.DataFrame, swings: list[Swing], index: int, bias: str, atr: float | None) -> bool:
    if index < 0:
        return False
    known = [s for s in swings if s.available_index <= index]
    recent = [s for s in known if index - s.available_index < 16]
    if bias == "BULLISH":
        lower = sum(1 for s in recent if any(p.kind == s.kind and p.available_index < s.available_index and p.price > s.price for p in known))
        displacement = max(0.0, max(m15.high.iloc[max(0,index-15):index+1]) - m15.close.iloc[index])
    elif bias == "BEARISH":
        lower = sum(1 for s in recent if any(p.kind == s.kind and p.available_index < s.available_index and p.price < s.price for p in known))
        displacement = max(0.0, m15.close.iloc[index] - min(m15.low.iloc[max(0,index-15):index+1]))
    else:
        return False
    return lower >= 2 or (atr is not None and atr > 0 and displacement >= 0.50 * atr)


def _nearest_opposite_zone_source(m15: pd.DataFrame, start: int, direction: str) -> int | None:
    for i in range(start - 1, -1, -1):
        bearish = m15.close.iloc[i] < m15.open.iloc[i]
        bullish = m15.close.iloc[i] > m15.open.iloc[i]
        if (direction == "LONG" and bearish) or (direction == "SHORT" and bullish):
            return i
    return None


def _window_id(timestamp: pd.Timestamp, config: dict[str, Any]) -> int | None:
    matches = observation_windows_at(timestamp, config)
    return matches[0] if matches else None


def _liquidity_level_history(m15: pd.DataFrame, h1_swings: list[Swing], m15_swings: list[Swing], tolerance_atr: float) -> list[dict[str, Any]]:
    """Build immutable level/cluster versions using ATR known at each creation time."""
    source_events = [("H1", swing) for swing in h1_swings] + [("M15", swing) for swing in m15_swings]
    source_events.sort(key=lambda item: (item[1].available_at, 0 if item[0] == "H1" else 1, item[1].kind))
    history: list[dict[str, Any]] = []
    live: list[dict[str, Any]] = []
    for timeframe, swing in source_events:
        m15_index = int(m15.timestamp.searchsorted(swing.available_at, side="right") - 1)
        atr_at_creation = _atr_before(m15, m15_index + 1, 14) if m15_index >= 0 else None
        possible = []
        for cluster in live:
            if cluster["kind"] != swing.kind:
                continue
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


def _candidate_from_sweep(
    m15: pd.DataFrame, m1: pd.DataFrame, h1: pd.DataFrame, h1_swings: list[Swing],
    sweep: dict[str, Any], m15_swings: list[Swing],
    config: dict[str, Any], symbol: str,
) -> dict[str, Any] | None:
    direction = sweep["direction"]
    start_after = sweep["confirmation_index"] + 1
    deadline = min(len(m15) - 1, sweep["confirmation_index"] + int(config["setup"]["lifetime_m15_bars_from_sweep_confirmation"]))
    period = int(config["displacement"]["atr_period"])
    for start in range(start_after, deadline + 1):
        current_bias, _, _ = _bias_at(pd.Timestamp(m15.timestamp.iloc[start]), h1, h1_swings)
        if current_bias != ("BULLISH" if direction == "LONG" else "BEARISH"):
            continue
        atr = _atr_before(m15, start, period)
        if atr is None or atr <= 0:
            continue
        bos_levels = [s for s in m15_swings if s.kind == ("HIGH" if direction == "LONG" else "LOW") and s.available_index < start]
        if not bos_levels:
            continue
        bos_level = max(bos_levels, key=lambda s: s.available_index)
        source_idx = _nearest_opposite_zone_source(m15, start, direction)
        if source_idx is None:
            continue
        source = m15.iloc[source_idx]
        if direction == "LONG":
            proximal, distal = float(source.close), float(source.low)
            zone_near = distal if sweep["extreme"] < distal else proximal if sweep["extreme"] > proximal else sweep["extreme"]
        else:
            proximal, distal = float(source.close), float(source.high)
            zone_near = proximal if sweep["extreme"] < proximal else distal if sweep["extreme"] > distal else sweep["extreme"]
        if abs(zone_near - sweep["extreme"]) > float(config["zones"]["max_distance_from_sweep_extreme_atr"]) * atr:
            continue
        for end in range(start, deadline + 1):
            if direction == "LONG":
                displacement_size = float(m15.high.iloc[start:end+1].max() - m15.open.iloc[start])
                qualifies = displacement_size >= float(config["displacement"]["minimum_atr"]) * atr
                bos = float(m15.close.iloc[end]) > bos_level.price
                leg_extreme = float(m15.high.iloc[start:end+1].max())
                leg_origin = float(m15.open.iloc[start])
            else:
                displacement_size = float(m15.open.iloc[start] - m15.low.iloc[start:end+1].min())
                qualifies = displacement_size >= float(config["displacement"]["minimum_atr"]) * atr
                bos = float(m15.close.iloc[end]) < bos_level.price
                leg_extreme = float(m15.low.iloc[start:end+1].min())
                leg_origin = float(m15.open.iloc[start])
            if not qualifies or not bos:
                continue

            leg_size = abs(leg_extreme - leg_origin)
            if leg_size < 0.50 * atr:
                continue
            retrace_min, retrace_max = map(float, config["two_leg"]["long"]["retracement_range"] if direction == "LONG" else config["two_leg"]["short"]["retracement_range"])
            if direction == "LONG":
                retrace_low, retrace_high = leg_extreme - retrace_max * leg_size, leg_extreme - retrace_min * leg_size
            else:
                retrace_low, retrace_high = leg_extreme + retrace_min * leg_size, leg_extreme + retrace_max * leg_size
            retrace_idx = None
            retrace_price = None
            leg2_idx = None
            bos_idx = None
            for r in range(end + 1, deadline + 1):
                current_bias, current_premise, _ = _bias_at(pd.Timestamp(m15.timestamp.iloc[r]), h1, h1_swings)
                if current_bias != ("BULLISH" if direction == "LONG" else "BEARISH") or current_premise is None:
                    break
                if direction == "LONG":
                    if m15.close.iloc[r] < sweep["extreme"] or m15.close.iloc[r] < current_premise:
                        break
                    if retrace_idx is None:
                        if m15.low.iloc[r] <= retrace_low:
                            break  # Retracement exceeded the maximum depth.
                        if m15.low.iloc[r] <= retrace_high and m15.high.iloc[r] >= retrace_low:
                            retrace_idx, retrace_price = r, float(min(retrace_high, m15.low.iloc[r]))
                    elif float(m15.high.iloc[r]) - float(retrace_price) >= 0.50 * atr:
                        leg2_idx = r
                    if leg2_idx is not None and float(m15.close.iloc[r]) > bos_level.price:
                        bos_idx = r
                        break
                else:
                    if m15.close.iloc[r] > sweep["extreme"] or m15.close.iloc[r] > current_premise:
                        break
                    if retrace_idx is None:
                        if m15.high.iloc[r] >= retrace_high:
                            break
                        if m15.high.iloc[r] >= retrace_low and m15.low.iloc[r] <= retrace_high:
                            retrace_idx, retrace_price = r, float(max(retrace_low, m15.high.iloc[r]))
                    elif float(retrace_price) - float(m15.low.iloc[r]) >= 0.50 * atr:
                        leg2_idx = r
                    if leg2_idx is not None and float(m15.close.iloc[r]) < bos_level.price:
                        bos_idx = r
                        break
            if retrace_idx is None or leg2_idx is None or bos_idx is None:
                continue

            # The source zone must still be fresh, valid, and within its configured life at BOS.
            if bos_idx - end > int(config["zones"]["expiry_m15_bars"]):
                continue
            mitigated = False
            invalidated = False
            for q in range(end + 1, bos_idx + 1):
                if direction == "LONG":
                    invalidated |= float(m15.close.iloc[q]) < distal
                    mitigated |= float(m15.low.iloc[q]) <= proximal and float(m15.high.iloc[q]) >= distal
                else:
                    invalidated |= float(m15.close.iloc[q]) > distal
                    mitigated |= float(m15.high.iloc[q]) >= proximal and float(m15.low.iloc[q]) <= distal
            if mitigated or invalidated:
                continue

            bos_time = pd.Timestamp(m15.timestamp.iloc[bos_idx])
            entry_rows = m1[m1.timestamp > bos_time]
            if entry_rows.empty or entry_rows.timestamp.iloc[0] - bos_time > pd.Timedelta(minutes=1):
                entry_time, entry_price, entry_spread = None, None, None
                rejection = "DATA_GAP"
            else:
                first = entry_rows.iloc[0]
                entry_time, entry_price = pd.Timestamp(first.timestamp) - pd.Timedelta(minutes=1), float(first.open)
                entry_spread = first.get("spread_pips", None)
                rejection = None
            window = _window_id(bos_time, config)
            entry_window = _window_id(entry_time, config) if entry_time is not None else None
            if window is None or entry_window is None:
                rejection = "NOT_TRADEABLE_OUTSIDE_OBSERVATION_WINDOW"
            stop_atr = _atr_before(m15, bos_idx, period) or atr
            stop = (sweep["extreme"] - 0.10 * stop_atr) if direction == "LONG" else (sweep["extreme"] + 0.10 * stop_atr)
            stop_distance = (entry_price - stop) if direction == "LONG" and entry_price is not None else (stop - entry_price) if entry_price is not None else None
            if stop_distance is not None and (stop_distance <= 0 or stop_distance > 3.0 * stop_atr):
                rejection = "STOP_DISTANCE_EXCEEDED"
            candidate_id = _stable_id(f"candidate|{symbol}|{direction}|{sweep['breach_time'].isoformat()}|{sweep['level']}")
            candidate = {
                "candidate_id": candidate_id, "symbol": symbol, "direction": direction,
                "state": "BOS_CONFIRMED", "candidate_status": rejection or "CANDIDATE_SETUP",
                "liquidity_level": sweep["level"], "sweep_timestamp": sweep["breach_time"].isoformat(),
                "constituent_levels": sweep.get("constituents", []), "cluster_atr_at_creation": sweep.get("cluster_atr"),
                "cluster_tolerance": sweep.get("cluster_tolerance"),
                "sweep_confirmation_timestamp": sweep["confirmation_time"].isoformat(), "sweep_extreme": sweep["extreme"],
                "sweep_depth": abs(sweep["extreme"] - sweep["level"]), "sweep_depth_atr": abs(sweep["extreme"]-sweep["level"])/atr,
                "zone": {"source_timestamp": pd.Timestamp(source.timestamp).isoformat(), "proximal": proximal, "distal": distal},
                "displacement": {"start": pd.Timestamp(m15.timestamp.iloc[start]).isoformat(), "end": pd.Timestamp(m15.timestamp.iloc[end]).isoformat(), "size": displacement_size, "atr": atr, "atr_multiple": displacement_size/atr},
                "leg1": {"start_index": start, "end_index": end, "origin": leg_origin, "extreme": leg_extreme},
                "retracement_timestamp": pd.Timestamp(m15.timestamp.iloc[retrace_idx]).isoformat(),
                "leg2_timestamp": pd.Timestamp(m15.timestamp.iloc[leg2_idx]).isoformat(),
                "bos_timestamp": bos_time.isoformat(), "bos_level": bos_level.price,
                "scheduled_observation_time": None if window is None else config["observation"]["scheduled_times"][window],
                "observation_window_index": window, "actual_signal_time": bos_time.isoformat(),
                "actual_execution_time": None if entry_time is None else entry_time.isoformat(),
                "entry_price": entry_price, "entry_spread_pips": entry_spread, "stop_price": stop,
                "stop_distance": stop_distance, "atr_at_setup": stop_atr, "atr_at_displacement_start": atr,
            }
            transitions = [
                ("WAITING_FOR_BIAS", sweep["breach_time"]),
                ("WAITING_FOR_PULLBACK", sweep["breach_time"]),
                ("WAITING_FOR_LIQUIDITY", sweep["breach_time"]),
                ("LIQUIDITY_SWEEP_DETECTED", sweep["confirmation_time"]),
                ("WAITING_FOR_ZONE", sweep["confirmation_time"]),
                ("ZONE_CONFIRMED", m15.timestamp.iloc[end]),
                ("DISPLACEMENT_DETECTED", m15.timestamp.iloc[end]),
                ("WAITING_FOR_RETRACEMENT", m15.timestamp.iloc[end]),
                ("LEG_2_DETECTED", m15.timestamp.iloc[leg2_idx]),
                ("WAITING_FOR_BOS", m15.timestamp.iloc[leg2_idx]),
                ("BOS_CONFIRMED", bos_time),
                ("READY_FOR_ENTRY", bos_time),
            ]
            candidate["state_events"] = [{"event_id": _stable_id(f"{candidate_id}|{state}|{pd.Timestamp(event_time).isoformat()}"), "candidate_id": candidate_id, "state": state,
                                            "timestamp": pd.Timestamp(event_time).isoformat(), "detection_timestamp": pd.Timestamp(event_time).isoformat()}
                                           for state, event_time in transitions]
            return candidate
    return None


def generate_v1_candidates(m1_bars: pd.DataFrame, symbol: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate sweep-to-BOS candidates from chronologically closed M1 bars."""
    if symbol not in config["instruments"]:
        raise ValueError(f"Unsupported V1 symbol: {symbol}")
    m1 = m1_bars.sort_values("timestamp").reset_index(drop=True).copy()
    if m1.empty or "timestamp" not in m1:
        return []
    m15 = aggregate_bars(m1, "M15")
    h1 = aggregate_bars(m1, "H1")
    if len(m15) < 20 or len(h1) < 6:
        return []
    m15_swings = confirmed_fractal_swings(m15, 2, 2)
    h1_swings = confirmed_fractal_swings(h1, 2, 2)
    levels = _liquidity_level_history(m15, h1_swings, m15_swings, float(config["liquidity"]["equal_level_tolerance_atr"]))
    sweeps: list[dict[str, Any]] = []
    swept_constituents: set[str] = set()
    previous_close = m15.timestamp.iloc[0] - pd.Timedelta(minutes=15)
    for j, bar in m15.iterrows():
        interval = m1[(m1.timestamp > previous_close) & (m1.timestamp <= bar.timestamp)]
        previous_close = pd.Timestamp(bar.timestamp)
        if interval.empty:
            continue
        bias, premise, h1_idx = _bias_at(pd.Timestamp(bar.timestamp), h1, h1_swings)
        if (bias == "BULLISH" and premise is not None and float(bar.close) < premise) or (bias == "BEARISH" and premise is not None and float(bar.close) > premise):
            continue
        atr = _atr_before(m15, j, 14)
        if bias not in {"BULLISH", "BEARISH"} or not _countertrend_pullback(m15, m15_swings, j, bias, atr):
            continue
        direction = "LONG" if bias == "BULLISH" else "SHORT"
        side = "LOW" if direction == "LONG" else "HIGH"
        breach_time_available = pd.Timestamp(interval.timestamp.iloc[0])
        active_levels = [level for level in levels if level["kind"] == side and level["effective_from"] <= breach_time_available
                         and (level["superseded_at"] is None or breach_time_available < level["superseded_at"])
                         and not any(f"{member['timeframe']}:{member['kind']}:{member['available_at']}:{member['price']}" in swept_constituents for member in level["constituents"])]
        active_levels.sort(key=lambda item: (0 if "H1" in item["timeframes"] else 1, item["oldest_confirmed"]))
        for level in active_levels:
            if direction == "LONG":
                breaches = interval[interval.low <= level["price"]]
                reclaimed = float(bar.close) > level["price"]
                extreme = float(breaches.low.min()) if not breaches.empty else None
            else:
                breaches = interval[interval.high >= level["price"]]
                reclaimed = float(bar.close) < level["price"]
                extreme = float(breaches.high.max()) if not breaches.empty else None
            if breaches.empty or not reclaimed:
                continue
            breach_time = pd.Timestamp(breaches.timestamp.iloc[0])
            # Confirmed levels can be swept only once in this chronological pass.
            constituent_ids = [f"{member['timeframe']}:{member['kind']}:{member['available_at']}:{member['price']}" for member in level["constituents"]]
            swept_constituents.update(constituent_ids)
            sweeps.append({"level_id": level["cluster_id"], "level": level["price"], "constituents": level["constituents"],
                           "cluster_atr": level["atr_at_creation"], "cluster_tolerance": level["tolerance"],
                           "extreme": extreme, "breach_time": breach_time,
                           "confirmation_time": pd.Timestamp(bar.timestamp), "confirmation_index": j,
                           "direction": direction})
            break

    candidates = []
    for sweep in sweeps:
        candidate = _candidate_from_sweep(m15, m1, h1, h1_swings, sweep, m15_swings, config, symbol)
        if candidate:
            candidates.append(candidate)
        else:
            expired_id = _stable_id(f"expired|{symbol}|{sweep['direction']}|{sweep['breach_time'].isoformat()}|{sweep['level']}")
            candidates.append({"candidate_id": expired_id, "symbol": symbol, "direction": sweep["direction"],
                               "state": "EXPIRED", "candidate_status": "SETUP_LIFETIME_EXPIRED",
                               "invalidation_reason": "SETUP_LIFETIME_EXPIRED", "liquidity_level": sweep["level"],
                               "constituent_levels": sweep.get("constituents", []), "cluster_atr_at_creation": sweep.get("cluster_atr"),
                               "cluster_tolerance": sweep.get("cluster_tolerance"),
                               "sweep_timestamp": sweep["breach_time"].isoformat(),
                               "sweep_confirmation_timestamp": sweep["confirmation_time"].isoformat(),
                               "sweep_extreme": sweep["extreme"], "state_events": [
                                   {"event_id": _stable_id(f"{expired_id}|LIQUIDITY_SWEEP_DETECTED"), "candidate_id": expired_id,
                                    "state": "LIQUIDITY_SWEEP_DETECTED", "timestamp": sweep["confirmation_time"].isoformat(),
                                    "detection_timestamp": sweep["confirmation_time"].isoformat()},
                                   {"event_id": _stable_id(f"{expired_id}|EXPIRED"), "candidate_id": expired_id,
                                    "state": "EXPIRED", "timestamp": sweep["confirmation_time"].isoformat(),
                                    "detection_timestamp": sweep["confirmation_time"].isoformat()},
                               ]})
    return sorted(candidates, key=lambda item: item.get("actual_signal_time", item["sweep_confirmation_timestamp"]))


def _simulate_candidate(candidate: dict[str, Any], m1: pd.DataFrame, execution_config: dict[str, Any], strategy_config: dict[str, Any], equity: float) -> dict[str, Any]:
    direction = candidate["direction"]
    pip = 0.0001
    slippage = float(execution_config.get("slippage", {}).get("baseline_pips", 0.1)) * pip
    start = pd.Timestamp(candidate["actual_execution_time"])
    entry_bar_index = int(m1.timestamp.searchsorted(start, side="right"))
    if entry_bar_index >= len(m1):
        return {"candidate_status": "DATA_GAP", "trade": None}
    entry_bar = m1.iloc[entry_bar_index]
    # A candidate records the expected open time of its first executable M1 bar.
    # Never bridge a missing candle or treat a later bar as the scheduled fill.
    entry_open = pd.Timestamp(entry_bar.timestamp) - pd.Timedelta(minutes=1)
    if entry_open != start:
        return {"candidate_status": "DATA_GAP", "spread_source": "NO_SPREAD_DATA", "trade": None}
    spread_data = resolve_spread(entry_bar.get("spread_pips"), execution_config)
    if spread_data["candidate_status"]:
        return {"candidate_status": spread_data["candidate_status"], "spread_source": spread_data["spread_source"], "trade": None}
    entry_spread_pips = float(spread_data["spread_pips"])
    spread = entry_spread_pips * pip
    mid_entry = float(entry_bar.open)
    entry = mid_entry + spread/2 + slippage if direction == "LONG" else mid_entry - spread/2 - slippage
    raw_stop = float(candidate["stop_price"])
    stop_distance = entry - raw_stop if direction == "LONG" else raw_stop - entry
    if stop_distance <= 0 or stop_distance > 3 * float(candidate["atr_at_setup"]):
        return {"candidate_status": "STOP_DISTANCE_EXCEEDED", "spread_source": spread_data["spread_source"], "trade": None}
    risk_fraction = float(strategy_config["risk"]["baseline_equity_risk_fraction"])
    risk_amount = equity * risk_fraction
    position_size = risk_amount / stop_distance
    lots = position_size / 100_000.0
    entry_commission_per_lot = float(entry_bar.get("commission_per_lot", execution_config.get("commission", {}).get("baseline_per_lot", 0.0)))
    target_r = float(strategy_config["target"]["baseline"].removesuffix("R"))
    target = entry + target_r * stop_distance if direction == "LONG" else entry - target_r * stop_distance
    madrid = ZoneInfo(strategy_config["timezones"]["reference"])
    session_end = time.fromisoformat(execution_config["session_end"])
    exit_info = None
    used_sources = {spread_data["spread_source"]}
    observations = []
    excursion = []
    for i in range(entry_bar_index, len(m1)):
        bar = m1.iloc[i]
        bar_open_time = pd.Timestamp(bar.timestamp) - pd.Timedelta(minutes=1)
        if i > entry_bar_index:
            previous_close_time = pd.Timestamp(m1.timestamp.iloc[i - 1])
            if pd.Timestamp(bar.timestamp) - previous_close_time > pd.Timedelta(minutes=1):
                # The path through the gap is unknowable. Preserve the candidate
                # as DATA_GAP instead of creating a stop, target, or expiry fill.
                return {"candidate_status": "DATA_GAP", "spread_source": "+".join(sorted(used_sources)), "trade": None}
        if bar_open_time > start and bar_open_time.tz_convert(madrid).time().replace(tzinfo=None) >= session_end:
            resolved = resolve_spread(bar.get("spread_pips"), execution_config)
            if resolved["candidate_status"]:
                return {"candidate_status": resolved["candidate_status"], "spread_source": resolved["spread_source"], "trade": None}
            used_sources.add(resolved["spread_source"])
            exit_price = float(bar.open)
            exit_price += (float(resolved["spread_pips"])*pip/2) if direction == "SHORT" else -(float(resolved["spread_pips"])*pip/2)
            exit_price += slippage if direction == "SHORT" else -slippage
            exit_info = (bar_open_time, exit_price, "SESSION_EXPIRY", float(bar.get("commission_per_lot", execution_config.get("commission", {}).get("baseline_per_lot", 0.0))))
            break
        resolved = resolve_spread(bar.get("spread_pips"), execution_config)
        if resolved["candidate_status"]:
            return {"candidate_status": resolved["candidate_status"], "spread_source": resolved["spread_source"], "trade": None}
        used_sources.add(resolved["spread_source"])
        half_cost = float(resolved["spread_pips"])*pip/2 + slippage
        if direction == "LONG":
            favorable = float(bar.high) - half_cost - entry
            adverse = float(bar.low) - half_cost - entry
            stop_hit = float(bar.low) - half_cost <= raw_stop
            target_hit = float(bar.high) - half_cost >= target
        else:
            favorable = entry - (float(bar.low) + half_cost)
            adverse = entry - (float(bar.high) + half_cost)
            stop_hit = float(bar.high) + half_cost >= raw_stop
            target_hit = float(bar.low) + half_cost <= target
        excursion.append((favorable / stop_distance, adverse / stop_distance))
        if stop_hit and target_hit:
            # V1 has M1 as its lowest supported execution resolution; assume adverse first.
            exit_info = (pd.Timestamp(bar.timestamp), raw_stop, "STOP_LOSS", float(bar.get("commission_per_lot", execution_config.get("commission", {}).get("baseline_per_lot", 0.0))))
            break
        if stop_hit:
            raw_exit = min(raw_stop, float(bar.open)-half_cost) if direction == "LONG" else max(raw_stop, float(bar.open)+half_cost)
            exit_info = (pd.Timestamp(bar.timestamp), raw_exit, "STOP_LOSS", float(bar.get("commission_per_lot", execution_config.get("commission", {}).get("baseline_per_lot", 0.0))))
            break
        if target_hit:
            exit_info = (pd.Timestamp(bar.timestamp), target, "TAKE_PROFIT", float(bar.get("commission_per_lot", execution_config.get("commission", {}).get("baseline_per_lot", 0.0))))
            break
    if exit_info is None:
        return {"candidate_status": "DATA_GAP", "spread_source": "+".join(sorted(used_sources)), "trade": None}
    exit_time, exit_price, exit_reason, exit_commission_per_lot = exit_info
    gross_pnl = (exit_price-entry)*position_size if direction == "LONG" else (entry-exit_price)*position_size
    commission = (entry_commission_per_lot + exit_commission_per_lot) * lots
    pnl = gross_pnl - commission
    r_multiple = pnl / risk_amount if risk_amount else 0.0
    source_list = sorted(used_sources)
    source_label = source_list[0] if len(source_list) == 1 else None
    trade = {
        "trade_id": _stable_id(f"trade|{candidate['candidate_id']}|{start.isoformat()}|{exit_time.isoformat()}"), "candidate_id": candidate["candidate_id"],
        "strategy_version": strategy_config["strategy_version"], "symbol": candidate["symbol"],
        "date": start.tz_convert(madrid).date().isoformat(), "timezone": strategy_config["timezones"]["reference"],
        "observation_window": str(candidate["observation_window_index"]), "direction": direction,
        "liquidity_price": candidate["liquidity_level"], "sweep_timestamp": candidate["sweep_timestamp"],
        "sweep_price": candidate["sweep_extreme"], "zone_high": max(candidate["zone"]["proximal"], candidate["zone"]["distal"]),
        "zone_low": min(candidate["zone"]["proximal"], candidate["zone"]["distal"]),
        "zone_timestamp": candidate["zone"]["source_timestamp"], "confirmation_type": "TWO_LEG_V1+BOS",
        "confirmation_timestamp": candidate["bos_timestamp"], "entry_timestamp": start.isoformat(),
        "entry_price": entry, "stop_price": raw_stop, "target_price": target, "exit_timestamp": exit_time.isoformat(),
        "exit_price": exit_price, "exit_reason": exit_reason, "risk_amount": risk_amount,
        "position_size": position_size, "spread_source": source_label, "spread_sources": source_list, "spread_pips": entry_spread_pips,
        "slippage_pips": float(execution_config.get("slippage", {}).get("baseline_pips", 0.1)),
        "commission": commission, "pnl": pnl, "r_multiple": r_multiple,
        "mfe": max((x[0] for x in excursion), default=0.0), "mae": min((x[1] for x in excursion), default=0.0),
        "scheduled_observation_time": candidate["scheduled_observation_time"],
        "actual_signal_time": candidate["actual_signal_time"], "actual_execution_time": start.isoformat(),
    }
    return {"candidate_status": "EXECUTED", "spread_source": source_label, "trade": trade}


def run_v1_portfolio(data_by_symbol: dict[str, pd.DataFrame], strategy_config: dict[str, Any], execution_config: dict[str, Any]) -> dict[str, Any]:
    """Simulate one or both symbols under shared daily and concurrent-position limits."""
    if strategy_config.get("status") != "FULLY_SPECIFIED":
        raise ValueError("Strategy V1 cannot run until its implementation and tests are validated")
    if not data_by_symbol or set(data_by_symbol) - set(strategy_config["instruments"]):
        raise ValueError("Portfolio input must contain EURUSD and/or GBPUSD M1 bars")
    bars_by_symbol = {symbol: data.sort_values("timestamp").reset_index(drop=True).copy() for symbol, data in data_by_symbol.items()}
    candidates = [candidate for symbol, bars in bars_by_symbol.items() for candidate in generate_v1_candidates(bars, symbol, strategy_config)]
    candidates.sort(key=lambda item: item.get("actual_execution_time", item["sweep_confirmation_timestamp"]))
    events, trades, state_events = [], [], []
    executed_windows: set[tuple[str, str, int]] = set()
    traded_symbol_dates: set[tuple[str, str]] = set()
    global_trade_dates: dict[str, int] = {}
    equity = 1.0
    last_exit: pd.Timestamp | None = None
    for candidate in candidates:
        state_events.extend(candidate.get("state_events", []))
        status = candidate["candidate_status"]
        if status not in {"CANDIDATE_SETUP", None}:
            events.append({**candidate, "candidate_status": status})
            continue
        spread = resolve_spread(candidate.get("entry_spread_pips"), execution_config)
        candidate["spread_source"] = spread["spread_source"]
        if spread["candidate_status"]:
            events.append({**candidate, "candidate_status": spread["candidate_status"]})
            continue
        date_key = pd.Timestamp(candidate["actual_execution_time"]).tz_convert(strategy_config["timezones"]["reference"]).date().isoformat()
        key = (candidate["symbol"], date_key, candidate["observation_window_index"])
        if key in executed_windows:
            events.append({**candidate, "candidate_status": "WINDOW_TRADE_LIMIT_REJECTED"})
            continue
        if (candidate["symbol"], date_key) in traded_symbol_dates or global_trade_dates.get(date_key, 0) >= int(strategy_config["risk"]["max_trades_global_per_trading_date"]):
            events.append({**candidate, "candidate_status": "RISK_LIMIT_REJECTED"})
            continue
        if last_exit is not None and pd.Timestamp(candidate["actual_execution_time"]) < last_exit:
            events.append({**candidate, "candidate_status": "CONCURRENT_POSITION_REJECTED"})
            continue
        result = _simulate_candidate(candidate, bars_by_symbol[candidate["symbol"]], execution_config, strategy_config, equity)
        if result["trade"] is None:
            events.append({**candidate, "candidate_status": result["candidate_status"], "spread_source": result.get("spread_source")})
            continue
        trade = result["trade"]
        trades.append(trade)
        state_events.append({"event_id": _stable_id(f"{candidate['candidate_id']}|EXECUTED|{trade['actual_execution_time']}"), "candidate_id": candidate["candidate_id"],
                             "state": "EXECUTED", "timestamp": trade["actual_execution_time"],
                             "detection_timestamp": trade["actual_execution_time"]})
        events.append({**candidate, "candidate_status": "EXECUTED", "spread_source": result["spread_source"]})
        executed_windows.add(key)
        traded_symbol_dates.add((candidate["symbol"], date_key))
        global_trade_dates[date_key] = global_trade_dates.get(date_key, 0) + 1
        last_exit = pd.Timestamp(trade["exit_timestamp"])
        equity *= max(0.0, 1.0 + float(strategy_config["risk"]["baseline_equity_risk_fraction"]) * trade["r_multiple"])
    state_events.sort(key=lambda item: (item["timestamp"], item["state"]))
    spread_sources = sorted({source for item in events for source in ([item.get("spread_source")] if item.get("spread_source") else [])})
    spread_sources.extend(source for trade in trades for source in trade.get("spread_sources", []) if source not in spread_sources)
    if not spread_sources:
        fallback = execution_config.get("spread", {}).get("fixed_fallback_pips")
        has_historical = any("spread_pips" in bars.columns and bars.spread_pips.notna().any() for bars in bars_by_symbol.values())
        spread_sources = ["HISTORICAL_SPREAD"] if has_historical else ["FIXED_CONFIGURED_SPREAD"] if fallback is not None else ["NO_SPREAD_DATA"]
    return {"strategy_version": strategy_config["strategy_version"], "strategy_status": strategy_config["status"],
            "symbols": sorted(bars_by_symbol), "candidate_count": len(events), "signal_count": len(trades), "trades": trades,
            "events": events, "state_events": state_events, "spread_sources": spread_sources,
            "ending_equity_normalized": equity}


def run_v1_backtest(m1_bars: pd.DataFrame, symbol: str, strategy_config: dict[str, Any], execution_config: dict[str, Any]) -> dict[str, Any]:
    """Single-symbol convenience wrapper; portfolio callers should pass both symbols together."""
    result = run_v1_portfolio({symbol: m1_bars}, strategy_config, execution_config)
    result["symbol"] = symbol
    return result
