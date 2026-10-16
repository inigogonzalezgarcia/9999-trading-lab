"""Sweep detection and the sweep -> displacement -> two legs -> BOS candidate state machine.

Every decision consumes completed candles only. Rejected and expired candidates are kept with
their event sequences so research can audit why a setup never became a trade.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..data import aggregate_bars
from ..timezones import observation_windows_at
from .frames import NS_PER_MINUTE, Bars, ns_of
from .ids import _stable_id
from .liquidity import _liquidity_level_history
from .structure import (Swing, SwingIndex, _as_bars, _bias_at, _countertrend_pullback,
                        _nearest_opposite_zone_source, confirmed_fractal_swings)
from .zones import build_zone_lifecycle


def stop_rules_from(config: dict[str, Any]) -> dict[str, Any]:
    """Stop placement rules; defaults reproduce V1 exactly (sweep extreme, 0.10 ATR buffer, max 3 ATR)."""
    stop = config.get("stop", {}) or {}
    reference = stop.get("reference", "sweep_extreme")
    if reference not in {"sweep_extreme", "zone_distal", "leg1_origin"}:
        raise ValueError(f"Unsupported stop.reference: {reference}")
    return {"reference": reference, "buffer_atr": float(stop.get("buffer_atr", 0.10)), "max_distance_atr": float(stop.get("max_distance_atr", 3.0))}


def level_max_age_ns(config: dict[str, Any]) -> int | None:
    """Optional liquidity-level expiry in M15 bars since confirmation (V1: never expires)."""
    value = (config.get("liquidity", {}) or {}).get("level_max_age_m15_bars")
    return None if value in (None, "", "null") else int(value) * 15 * NS_PER_MINUTE


def _window_id(timestamp: pd.Timestamp, config: dict[str, Any]) -> int | None:
    matches = observation_windows_at(timestamp, config)
    return matches[0] if matches else None


def _rejected_sweep_candidate(symbol: str, sweep: dict[str, Any], reason: str,
                              timestamp: pd.Timestamp,
                              zone_record: dict[str, Any] | None = None,
                              zone_events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    candidate_id = _stable_id(f"candidate|{symbol}|{sweep['direction']}|{sweep['breach_time'].isoformat()}|{sweep['level']}")
    state = "EXPIRED" if reason in {"TWO_LEG_TIMEOUT", "BOS_TIMEOUT", "SETUP_TIMEOUT", "ZONE_EXPIRED"} else "INVALIDATED"
    state_events = []
    for sequence_index, (name, event_time) in enumerate((("LIQUIDITY_SWEEP_DETECTED", sweep["confirmation_time"]), (state, timestamp))):
        state_events.append({"event_id": _stable_id(f"{candidate_id}|{name}|{pd.Timestamp(event_time).isoformat()}"),
                             "candidate_id": candidate_id, "state": name, "sequence_index": sequence_index,
                             "timestamp": pd.Timestamp(event_time).isoformat(), "detection_timestamp": pd.Timestamp(event_time).isoformat(),
                             "reason": reason if name == state else None})
    result = {"candidate_id": candidate_id, "symbol": symbol, "direction": sweep["direction"],
              "state": state, "candidate_status": reason, "rejection_reason": reason,
              "rejection_timestamp": pd.Timestamp(timestamp).isoformat(),
              "liquidity_level": sweep["level"], "sweep_timestamp": sweep["breach_time"].isoformat(),
              "sweep_confirmation_timestamp": sweep["confirmation_time"].isoformat(),
              "sweep_extreme": sweep["extreme"], "state_events": state_events}
    if zone_record is not None:
        result["zone"] = zone_record
        result["zone_events"] = zone_events or []
    return result


def _candidate_from_sweep(
    m15: pd.DataFrame | Bars, m1: pd.DataFrame | Bars, h1: pd.DataFrame | Bars, h1_swings: list[Swing] | SwingIndex,
    sweep: dict[str, Any], m15_swings: list[Swing] | SwingIndex,
    config: dict[str, Any], symbol: str,
) -> dict[str, Any] | None:
    m15v, m1v, h1v = _as_bars(m15), _as_bars(m1), _as_bars(h1)
    h1_index = h1_swings if isinstance(h1_swings, SwingIndex) else SwingIndex(h1_swings)
    m15_index = m15_swings if isinstance(m15_swings, SwingIndex) else SwingIndex(m15_swings)
    direction = sweep["direction"]
    want_bias = "BULLISH" if direction == "LONG" else "BEARISH"
    start_after = sweep["confirmation_index"] + 1
    deadline = min(len(m15v) - 1, sweep["confirmation_index"] + int(config["setup"]["lifetime_m15_bars_from_sweep_confirmation"]))
    period = int(config["displacement"]["atr_period"])
    expiry_bars = int(config["zones"]["expiry_m15_bars"])
    extreme = float(sweep["extreme"])
    saw_displacement = saw_retrace = saw_leg2 = False
    latest_zone: dict[str, Any] | None = None
    latest_zone_events: list[dict[str, Any]] = []
    for start in range(start_after, deadline + 1):
        current_bias, _, _ = _bias_at(m15v.ts[start], h1v, h1_index)
        if current_bias != want_bias:
            return _rejected_sweep_candidate(symbol, sweep, "BIAS_INVALIDATED", m15v.stamp(start), latest_zone, latest_zone_events)
        if (direction == "LONG" and float(m15v.close[start]) < extreme) or (direction == "SHORT" and float(m15v.close[start]) > extreme):
            return _rejected_sweep_candidate(symbol, sweep, "SWEEP_EXTREME_INVALIDATED", m15v.stamp(start), latest_zone, latest_zone_events)
        atr = m15v.atr_before(start, period)
        if atr is None or atr <= 0:
            continue
        bos_level = m15_index.latest_of_kind_before("HIGH" if direction == "LONG" else "LOW", start)
        if bos_level is None:
            continue
        source_idx = _nearest_opposite_zone_source(m15v, start, direction)
        if source_idx is None:
            continue
        if direction == "LONG":
            proximal, distal = float(m15v.close[source_idx]), float(m15v.low[source_idx])
            zone_near = distal if extreme < distal else proximal if extreme > proximal else extreme
        else:
            proximal, distal = float(m15v.close[source_idx]), float(m15v.high[source_idx])
            zone_near = proximal if extreme < proximal else distal if extreme > distal else extreme
        if abs(zone_near - extreme) > float(config["zones"]["max_distance_from_sweep_extreme_atr"]) * atr:
            continue
        leg_origin = float(m15v.open[start])
        for end in range(start, deadline + 1):
            if direction == "LONG":
                leg_extreme = float(m15v.high[start:end + 1].max())
                displacement_size = leg_extreme - leg_origin
                bos = float(m15v.close[end]) > bos_level.price
            else:
                leg_extreme = float(m15v.low[start:end + 1].min())
                displacement_size = leg_origin - leg_extreme
                bos = float(m15v.close[end]) < bos_level.price
            qualifies = displacement_size >= float(config["displacement"]["minimum_atr"]) * atr
            if not qualifies or not bos:
                continue
            saw_displacement = True
            zone_id_key = str(sweep.get("level_id", ""))
            latest_zone, latest_zone_events = build_zone_lifecycle(m15v, symbol, direction, source_idx, end, proximal, distal, zone_id_key, expiry_bars)

            leg_size = abs(leg_extreme - leg_origin)
            if leg_size < 0.50 * atr:
                continue
            retrace_min, retrace_max = map(float, config["two_leg"]["long"]["retracement_range"] if direction == "LONG" else config["two_leg"]["short"]["retracement_range"])
            if direction == "LONG":
                retrace_low, retrace_high = leg_extreme - retrace_max * leg_size, leg_extreme - retrace_min * leg_size
            else:
                retrace_low, retrace_high = leg_extreme + retrace_min * leg_size, leg_extreme + retrace_max * leg_size
            retrace_idx = retrace_price = leg2_idx = bos_idx = None
            for r in range(end + 1, deadline + 1):
                current_bias, current_premise, _ = _bias_at(m15v.ts[r], h1v, h1_index)
                if current_bias != want_bias or current_premise is None:
                    break
                close_r, low_r, high_r = m15v.close[r], m15v.low[r], m15v.high[r]
                if direction == "LONG":
                    if close_r < extreme or close_r < current_premise:
                        break
                    if retrace_idx is None:
                        if low_r <= retrace_low:
                            break  # Retracement exceeded the maximum depth.
                        if low_r <= retrace_high and high_r >= retrace_low:
                            retrace_idx, retrace_price = r, float(min(retrace_high, low_r))
                            saw_retrace = True
                    elif float(high_r) - float(retrace_price) >= 0.50 * atr:
                        leg2_idx = r
                        saw_leg2 = True
                    if leg2_idx is not None and float(close_r) > bos_level.price:
                        bos_idx = r
                        break
                else:
                    if close_r > extreme or close_r > current_premise:
                        break
                    if retrace_idx is None:
                        if high_r >= retrace_high:
                            break
                        if high_r >= retrace_low and low_r <= retrace_high:
                            retrace_idx, retrace_price = r, float(max(retrace_low, high_r))
                            saw_retrace = True
                    elif float(retrace_price) - float(low_r) >= 0.50 * atr:
                        leg2_idx = r
                        saw_leg2 = True
                    if leg2_idx is not None and float(close_r) < bos_level.price:
                        bos_idx = r
                        break
            if retrace_idx is None or leg2_idx is None or bos_idx is None:
                continue

            # The source zone must still be fresh, valid, and within its configured life at BOS.
            if bos_idx - end > expiry_bars:
                expiry_index = min(len(m15v) - 1, end + expiry_bars)
                return _rejected_sweep_candidate(symbol, sweep, "ZONE_EXPIRED", m15v.stamp(expiry_index), latest_zone, latest_zone_events)
            mitigated = invalidated = False
            zone_terminal_time = None
            for q in range(end + 1, bos_idx + 1):
                if direction == "LONG":
                    invalidated = float(m15v.close[q]) < distal
                    mitigated = float(m15v.low[q]) <= proximal and float(m15v.high[q]) >= distal
                else:
                    invalidated = float(m15v.close[q]) > distal
                    mitigated = float(m15v.high[q]) >= proximal and float(m15v.low[q]) <= distal
                if invalidated or mitigated:
                    zone_terminal_time = m15v.stamp(q)
                    break
            if mitigated or invalidated:
                reason = "ZONE_INVALIDATED" if invalidated else "ZONE_MITIGATED"
                return _rejected_sweep_candidate(symbol, sweep, reason, zone_terminal_time, latest_zone, latest_zone_events)

            bos_ns = int(m15v.ts[bos_idx])
            bos_time = m15v.stamp(bos_idx)
            entry_index = m1v.first_index_after(bos_ns)
            if entry_index >= len(m1v):
                entry_time, entry_price, entry_spread = None, None, None
                rejection = "EXECUTION_DATA_UNAVAILABLE"
            elif m1v.ts[entry_index] - bos_ns > NS_PER_MINUTE:
                entry_time, entry_price, entry_spread = None, None, None
                rejection = "DATA_GAP"
            else:
                entry_time, entry_price = m1v.stamp(entry_index) - pd.Timedelta(minutes=1), float(m1v.open[entry_index])
                entry_spread = m1v.spread_at(entry_index)
                rejection = None
            window = _window_id(bos_time, config)
            entry_window = _window_id(entry_time, config) if entry_time is not None else None
            if window is None or entry_window is None:
                rejection = "NOT_TRADEABLE_OUTSIDE_OBSERVATION_WINDOW"
            stop_atr = m15v.atr_before(bos_idx, period) or atr
            stop_rules = stop_rules_from(config)
            anchor = {"sweep_extreme": extreme, "zone_distal": distal, "leg1_origin": leg_origin}[stop_rules["reference"]]
            stop = (anchor - stop_rules["buffer_atr"] * stop_atr) if direction == "LONG" else (anchor + stop_rules["buffer_atr"] * stop_atr)
            stop_distance = (entry_price - stop) if direction == "LONG" and entry_price is not None else (stop - entry_price) if entry_price is not None else None
            if stop_distance is not None and (stop_distance <= 0 or stop_distance > stop_rules["max_distance_atr"] * stop_atr):
                rejection = "STOP_DISTANCE_EXCEEDED"
            candidate_id = _stable_id(f"candidate|{symbol}|{direction}|{sweep['breach_time'].isoformat()}|{sweep['level']}")
            zone_record, zone_events = build_zone_lifecycle(m15v, symbol, direction, source_idx, end, proximal, distal,
                                                            str(sweep.get("level_id", candidate_id)), expiry_bars)
            candidate = {
                "candidate_id": candidate_id, "symbol": symbol, "direction": direction,
                "state": "BOS_CONFIRMED", "candidate_status": rejection or "CANDIDATE_SETUP",
                "liquidity_level": sweep["level"], "sweep_timestamp": sweep["breach_time"].isoformat(),
                "constituent_levels": sweep.get("constituents", []), "cluster_atr_at_creation": sweep.get("cluster_atr"),
                "cluster_tolerance": sweep.get("cluster_tolerance"),
                "sweep_confirmation_timestamp": sweep["confirmation_time"].isoformat(), "sweep_extreme": sweep["extreme"],
                "sweep_depth": abs(sweep["extreme"] - sweep["level"]), "sweep_depth_atr": abs(sweep["extreme"] - sweep["level"]) / atr,
                "zone": {**zone_record, "source_timestamp": m15v.stamp(source_idx).isoformat()},
                "zone_events": zone_events,
                "displacement": {"start": m15v.stamp(start).isoformat(), "end": m15v.stamp(end).isoformat(), "size": displacement_size, "atr": atr, "atr_multiple": displacement_size / atr},
                "leg1": {"start_index": start, "end_index": end, "origin": leg_origin, "extreme": leg_extreme},
                "retracement_timestamp": m15v.stamp(retrace_idx).isoformat(),
                "leg2_timestamp": m15v.stamp(leg2_idx).isoformat(),
                "bos_timestamp": bos_time.isoformat(), "bos_level": bos_level.price,
                "scheduled_observation_time": None if window is None else config["observation"]["scheduled_times"][window],
                "observation_window_index": window, "actual_signal_time": bos_time.isoformat(),
                "actual_execution_time": None if entry_time is None else entry_time.isoformat(),
                "entry_price": entry_price, "entry_spread_pips": entry_spread, "stop_price": stop,
                "stop_distance": stop_distance, "atr_at_setup": stop_atr, "atr_at_displacement_start": atr,
                "stop_reference": stop_rules["reference"], "stop_max_distance_atr": stop_rules["max_distance_atr"],
            }
            bias_h1_index = _bias_at(m15v.ts[start], h1v, h1_index)[2]
            swings_list = h1_index.swings
            latest_highs = sorted([s for s in swings_list if s.kind == "HIGH" and s.available_index <= bias_h1_index], key=lambda s: s.available_index)[-2:]
            latest_lows = sorted([s for s in swings_list if s.kind == "LOW" and s.available_index <= bias_h1_index], key=lambda s: s.available_index)[-2:]
            transitions = [
                ("WAITING_FOR_BIAS", h1v.stamp(0)),
                ("WAITING_FOR_PULLBACK", max(s.available_at for s in latest_highs + latest_lows)),
                ("WAITING_FOR_LIQUIDITY", sweep.get("pullback_confirmation_time", sweep["confirmation_time"])),
                ("LIQUIDITY_SWEEP_DETECTED", sweep["confirmation_time"]),
                ("WAITING_FOR_ZONE", sweep["confirmation_time"]),
                ("ZONE_CONFIRMED", m15v.stamp(end)),
                ("DISPLACEMENT_DETECTED", m15v.stamp(end)),
                ("WAITING_FOR_RETRACEMENT", m15v.stamp(end)),
                ("LEG_2_DETECTED", m15v.stamp(leg2_idx)),
                ("WAITING_FOR_BOS", m15v.stamp(leg2_idx)),
                ("BOS_CONFIRMED", bos_time),
                ("READY_FOR_ENTRY", bos_time),
            ]
            candidate["state_events"] = [{"event_id": _stable_id(f"{candidate_id}|{state}|{pd.Timestamp(event_time).isoformat()}"), "candidate_id": candidate_id, "state": state, "sequence_index": sequence_index,
                                          "timestamp": pd.Timestamp(event_time).isoformat(), "detection_timestamp": pd.Timestamp(event_time).isoformat()}
                                         for sequence_index, (state, event_time) in enumerate(transitions)]
            return candidate
    reason = "BOS_TIMEOUT" if saw_leg2 else "TWO_LEG_TIMEOUT" if saw_displacement or saw_retrace else "SETUP_TIMEOUT"
    return _rejected_sweep_candidate(symbol, sweep, reason, m15v.stamp(deadline), latest_zone, latest_zone_events)


def _constituent_key(member: dict[str, Any]) -> str:
    return f"{member['timeframe']}:{member['kind']}:{member['available_at']}:{member['price']}"


class _LevelTable:
    """Vectorised view of the level history for one side (LOW or HIGH)."""

    def __init__(self, levels: list[dict[str, Any]]):
        self.levels = levels
        n = len(levels)
        self.effective = np.array([ns_of(level["effective_from"]) for level in levels], dtype="int64") if n else np.zeros(0, "int64")
        self.superseded = np.array([np.iinfo("int64").max if level["superseded_at"] is None else ns_of(level["superseded_at"]) for level in levels], dtype="int64") if n else np.zeros(0, "int64")
        self.price = np.array([float(level["price"]) for level in levels]) if n else np.zeros(0)
        # Selection order: H1-containing clusters first, then oldest confirmed.
        order = sorted(range(n), key=lambda i: (0 if "H1" in levels[i]["timeframes"] else 1, levels[i]["oldest_confirmed"]))
        self.rank = np.empty(n, dtype="int64")
        self.rank[order] = np.arange(n)
        self.swept = np.zeros(n, dtype=bool)
        self.by_constituent: dict[str, list[int]] = {}
        for i, level in enumerate(levels):
            for member in level["constituents"]:
                self.by_constituent.setdefault(_constituent_key(member), []).append(i)

    def first_eligible(self, breach_available_ns: int, lower_bound: float, upper_bound: float, max_age_ns: int | None = None) -> int | None:
        """Highest-priority active level whose price lies in [lower_bound, upper_bound)."""
        if not len(self.levels):
            return None
        mask = ((self.effective <= breach_available_ns) & (breach_available_ns < self.superseded) & ~self.swept
                & (self.price >= lower_bound) & (self.price < upper_bound))
        if max_age_ns is not None:
            mask &= (breach_available_ns - self.effective) <= max_age_ns
        if not mask.any():
            return None
        ranks = np.where(mask, self.rank, np.iinfo("int64").max)
        return int(np.argmin(ranks))

    def mark_swept(self, index: int) -> None:
        # Confirmed levels can be swept only once in this chronological pass; every cluster
        # version sharing a constituent is excluded as well.
        for member in self.levels[index]["constituents"]:
            for other in self.by_constituent.get(_constituent_key(member), []):
                self.swept[other] = True


def detect_sweeps(m1v: Bars, m15v: Bars, h1v: Bars, h1_swings: list[Swing], m15_swings: list[Swing],
                  levels: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Chronological pass over M15 closes detecting the first eligible level swept per bar.

    A LOW level is breached inside an M15 interval when the interval's lowest M1 low is at or
    below the level and the M15 close reclaims it (close above the level); HIGH levels mirror
    this. The sweep extreme is therefore the interval's extreme low/high.
    """
    h1_index, m15_index = SwingIndex(h1_swings), SwingIndex(m15_swings)
    tables = {kind: _LevelTable([level for level in levels if level["kind"] == kind]) for kind in ("LOW", "HIGH")}
    max_age = level_max_age_ns(config)
    sweeps: list[dict[str, Any]] = []
    previous_close = int(m15v.ts[0]) - 15 * NS_PER_MINUTE
    for j in range(len(m15v)):
        bar_ns = int(m15v.ts[j])
        lo, hi = m1v.first_index_after(previous_close), m1v.first_index_after(bar_ns)
        previous_close = bar_ns
        if hi <= lo:
            continue
        bar_close = float(m15v.close[j])
        bias, premise, _ = _bias_at(bar_ns, h1v, h1_index)
        if (bias == "BULLISH" and premise is not None and bar_close < premise) or (bias == "BEARISH" and premise is not None and bar_close > premise):
            continue
        atr = m15v.atr_before(j, 14)
        if bias not in {"BULLISH", "BEARISH"} or not _countertrend_pullback(m15v, m15_index, j, bias, atr):
            continue
        direction = "LONG" if bias == "BULLISH" else "SHORT"
        breach_available_ns = int(m1v.ts[lo])
        if direction == "LONG":
            lows = m1v.low[lo:hi]
            extreme = float(lows.min())
            table = tables["LOW"]
            chosen = table.first_eligible(breach_available_ns, extreme, bar_close, max_age)
        else:
            highs = m1v.high[lo:hi]
            extreme = float(highs.max())
            table = tables["HIGH"]
            # price > close and price <= extreme  <=>  price in (close, extreme]
            chosen = table.first_eligible(breach_available_ns, np.nextafter(bar_close, np.inf), np.nextafter(extreme, np.inf), max_age)
        if chosen is None:
            continue
        level = table.levels[chosen]
        price = level["price"]
        mask = lows <= price if direction == "LONG" else highs >= price
        breach_time = m1v.stamp(lo + int(mask.argmax()))
        table.mark_swept(chosen)
        sweeps.append({"level_id": level["cluster_id"], "level": level["price"], "constituents": level["constituents"],
                       "cluster_atr": level["atr_at_creation"], "cluster_tolerance": level["tolerance"],
                       "extreme": extreme, "breach_time": breach_time,
                       "confirmation_time": m15v.stamp(j), "confirmation_index": j,
                       "pullback_confirmation_time": m15v.stamp(j),
                       "direction": direction})
    return sweeps


def _expired_candidate(symbol: str, sweep: dict[str, Any]) -> dict[str, Any]:
    expired_id = _stable_id(f"expired|{symbol}|{sweep['direction']}|{sweep['breach_time'].isoformat()}|{sweep['level']}")
    confirmation = sweep["confirmation_time"].isoformat()
    return {"candidate_id": expired_id, "symbol": symbol, "direction": sweep["direction"],
            "state": "EXPIRED", "candidate_status": "SETUP_LIFETIME_EXPIRED",
            "invalidation_reason": "SETUP_LIFETIME_EXPIRED", "liquidity_level": sweep["level"],
            "constituent_levels": sweep.get("constituents", []), "cluster_atr_at_creation": sweep.get("cluster_atr"),
            "cluster_tolerance": sweep.get("cluster_tolerance"),
            "sweep_timestamp": sweep["breach_time"].isoformat(),
            "sweep_confirmation_timestamp": confirmation,
            "sweep_extreme": sweep["extreme"], "state_events": [
                {"event_id": _stable_id(f"{expired_id}|LIQUIDITY_SWEEP_DETECTED"), "candidate_id": expired_id,
                 "state": "LIQUIDITY_SWEEP_DETECTED", "timestamp": confirmation, "detection_timestamp": confirmation},
                {"event_id": _stable_id(f"{expired_id}|EXPIRED"), "candidate_id": expired_id,
                 "state": "EXPIRED", "timestamp": confirmation, "detection_timestamp": confirmation},
            ]}


def generate_v1_candidates(m1_bars: pd.DataFrame, symbol: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate sweep-to-BOS candidates from chronologically closed M1 bars."""
    if symbol not in config["instruments"]:
        raise ValueError(f"Unsupported V1 symbol: {symbol}")
    if m1_bars.empty or "timestamp" not in m1_bars:
        return []
    m1 = m1_bars.sort_values("timestamp").reset_index(drop=True)
    m15 = aggregate_bars(m1, "M15")
    h1 = aggregate_bars(m1, "H1")
    if len(m15) < 20 or len(h1) < 6:
        return []
    m1v, m15v, h1v = Bars(m1), Bars(m15), Bars(h1)
    m15_swings = confirmed_fractal_swings(m15v, 2, 2)
    h1_swings = confirmed_fractal_swings(h1v, 2, 2)
    levels = _liquidity_level_history(m15v, h1_swings, m15_swings, float(config["liquidity"]["equal_level_tolerance_atr"]))
    sweeps = detect_sweeps(m1v, m15v, h1v, h1_swings, m15_swings, levels, config)
    h1_index, m15_index = SwingIndex(h1_swings), SwingIndex(m15_swings)
    candidates = []
    for sweep in sweeps:
        candidate = _candidate_from_sweep(m15v, m1v, h1v, h1_index, sweep, m15_index, config, symbol)
        candidates.append(candidate if candidate else _expired_candidate(symbol, sweep))
    return sorted(candidates, key=lambda item: item.get("actual_signal_time", item["sweep_confirmation_timestamp"]))
