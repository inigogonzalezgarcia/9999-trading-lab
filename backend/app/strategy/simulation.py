"""Deterministic M1 execution of one candidate with spread, slippage, and commission costs."""
from __future__ import annotations

from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from ..execution import resolve_spread
from .frames import NS_PER_MINUTE, Bars, ns_of
from .ids import _stable_id
from .structure import _as_bars

PIP = 0.0001


def _simulate_candidate(candidate: dict[str, Any], m1: pd.DataFrame | Bars, execution_config: dict[str, Any], strategy_config: dict[str, Any], equity: float) -> dict[str, Any]:
    m1v = _as_bars(m1)
    direction = candidate["direction"]
    slippage_pips = float(execution_config.get("slippage", {}).get("baseline_pips", 0.1))
    slippage = slippage_pips * PIP
    commission_default = float(execution_config.get("commission", {}).get("baseline_per_lot", 0.0))
    start = pd.Timestamp(candidate["actual_execution_time"])
    start_ns = ns_of(start)
    entry_bar_index = m1v.first_index_after(start_ns)
    if entry_bar_index >= len(m1v):
        return {"candidate_status": "EXECUTION_DATA_UNAVAILABLE", "trade": None}
    # A candidate records the expected open time of its first executable M1 bar.
    # Never bridge a missing candle or treat a later bar as the scheduled fill.
    if int(m1v.ts[entry_bar_index]) - NS_PER_MINUTE != start_ns:
        return {"candidate_status": "DATA_GAP", "spread_source": "NO_SPREAD_DATA", "trade": None}
    spread_data = resolve_spread(m1v.spread_at(entry_bar_index), execution_config)
    if spread_data["candidate_status"]:
        return {"candidate_status": spread_data["candidate_status"], "spread_source": spread_data["spread_source"], "trade": None}
    entry_spread_pips = float(spread_data["spread_pips"])
    spread = entry_spread_pips * PIP
    mid_entry = float(m1v.open[entry_bar_index])
    entry = mid_entry + spread / 2 + slippage if direction == "LONG" else mid_entry - spread / 2 - slippage
    raw_stop = float(candidate["stop_price"])
    stop_distance = entry - raw_stop if direction == "LONG" else raw_stop - entry
    max_distance_atr = float((strategy_config.get("stop", {}) or {}).get("max_distance_atr", 3.0))
    if stop_distance <= 0 or stop_distance > max_distance_atr * float(candidate["atr_at_setup"]):
        return {"candidate_status": "STOP_DISTANCE_EXCEEDED", "spread_source": spread_data["spread_source"], "trade": None}
    risk_fraction = float(strategy_config["risk"]["baseline_equity_risk_fraction"])
    risk_amount = equity * risk_fraction
    position_size = risk_amount / stop_distance
    lots = position_size / 100_000.0
    entry_commission_per_lot = m1v.commission_at(entry_bar_index, commission_default)
    target_r = float(strategy_config["target"]["baseline"].removesuffix("R"))
    target = entry + target_r * stop_distance if direction == "LONG" else entry - target_r * stop_distance
    madrid = ZoneInfo(strategy_config["timezones"]["reference"])
    # The strategy version may carry its own session expiry (V1.1 session experiments); else the execution model's.
    session_end = time.fromisoformat((strategy_config.get("execution", {}) or {}).get("session_end") or execution_config["session_end"])
    exit_info = None
    used_sources = {spread_data["spread_source"]}
    excursion: list[tuple[float, float]] = []
    for i in range(entry_bar_index, len(m1v)):
        bar_ns = int(m1v.ts[i])
        bar_open_ns = bar_ns - NS_PER_MINUTE
        if i > entry_bar_index and bar_ns - int(m1v.ts[i - 1]) > NS_PER_MINUTE:
            # The path through the gap is unknowable. Preserve the candidate
            # as DATA_GAP instead of creating a stop, target, or expiry fill.
            return {"candidate_status": "DATA_GAP", "spread_source": "+".join(sorted(used_sources)), "trade": None}
        bar_open_local = datetime.fromtimestamp(bar_open_ns / 1e9, tz=madrid).time()
        if bar_open_ns > start_ns and bar_open_local >= session_end:
            resolved = resolve_spread(m1v.spread_at(i), execution_config)
            if resolved["candidate_status"]:
                return {"candidate_status": resolved["candidate_status"], "spread_source": resolved["spread_source"], "trade": None}
            used_sources.add(resolved["spread_source"])
            exit_price = float(m1v.open[i])
            exit_price += (float(resolved["spread_pips"]) * PIP / 2) if direction == "SHORT" else -(float(resolved["spread_pips"]) * PIP / 2)
            exit_price += slippage if direction == "SHORT" else -slippage
            exit_info = (pd.Timestamp(bar_open_ns, unit="ns", tz="UTC"), exit_price, "SESSION_EXPIRY", m1v.commission_at(i, commission_default))
            break
        resolved = resolve_spread(m1v.spread_at(i), execution_config)
        if resolved["candidate_status"]:
            return {"candidate_status": resolved["candidate_status"], "spread_source": resolved["spread_source"], "trade": None}
        used_sources.add(resolved["spread_source"])
        half_cost = float(resolved["spread_pips"]) * PIP / 2 + slippage
        high, low, open_ = float(m1v.high[i]), float(m1v.low[i]), float(m1v.open[i])
        if direction == "LONG":
            favorable = high - half_cost - entry
            adverse = low - half_cost - entry
            stop_hit = low - half_cost <= raw_stop
            target_hit = high - half_cost >= target
        else:
            favorable = entry - (low + half_cost)
            adverse = entry - (high + half_cost)
            stop_hit = high + half_cost >= raw_stop
            target_hit = low + half_cost <= target
        excursion.append((favorable / stop_distance, adverse / stop_distance))
        bar_time = m1v.stamp(i)
        if stop_hit and target_hit:
            # V1 has M1 as its lowest supported execution resolution; assume adverse first.
            exit_info = (bar_time, raw_stop, "STOP_LOSS", m1v.commission_at(i, commission_default))
            break
        if stop_hit:
            raw_exit = min(raw_stop, open_ - half_cost) if direction == "LONG" else max(raw_stop, open_ + half_cost)
            exit_info = (bar_time, raw_exit, "STOP_LOSS", m1v.commission_at(i, commission_default))
            break
        if target_hit:
            exit_info = (bar_time, target, "TAKE_PROFIT", m1v.commission_at(i, commission_default))
            break
    if exit_info is None:
        return {"candidate_status": "DATA_GAP", "spread_source": "+".join(sorted(used_sources)), "trade": None}
    exit_time, exit_price, exit_reason, exit_commission_per_lot = exit_info
    gross_pnl = (exit_price - entry) * position_size if direction == "LONG" else (entry - exit_price) * position_size
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
        "slippage_pips": slippage_pips,
        "commission": commission, "pnl": pnl, "r_multiple": r_multiple,
        "mfe": max((x[0] for x in excursion), default=0.0), "mae": min((x[1] for x in excursion), default=0.0),
        "scheduled_observation_time": candidate["scheduled_observation_time"],
        "actual_signal_time": candidate["actual_signal_time"], "actual_execution_time": start.isoformat(),
    }
    return {"candidate_status": "EXECUTED", "spread_source": source_label, "trade": trade}
