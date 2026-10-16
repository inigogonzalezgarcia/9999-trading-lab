"""Daily preparation contexts, portfolio limits, and the public research backtest entry points."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from ..data import aggregate_bars
from ..execution import resolve_spread
from ..timezones import timezone_database_version
from .candidates import generate_v1_candidates
from .frames import Bars
from .ids import _normalized_rejection, _stable_id, canonical_config_hash
from .liquidity import _liquidity_level_history, build_liquidity_lifecycle_events
from .simulation import _simulate_candidate
from .structure import classify_h1_bias, confirmed_fractal_swings

CandidateGenerator = Callable[[pd.DataFrame, str, dict[str, Any]], list[dict[str, Any]]]


def _context_lookback_days(strategy_config: dict[str, Any]) -> int | None:
    """Optional cap on how much history each 01:50 snapshot replays (``None`` = full history)."""
    value = strategy_config.get("preparation", {}).get("context_lookback_days")
    return None if value in (None, "", "null") else int(value)


def build_daily_contexts(
    data_by_symbol: dict[str, pd.DataFrame], strategy_config: dict[str, Any],
    dataset_hash: str | None = None, execution_config: dict[str, Any] | None = None,
    candidate_generator: CandidateGenerator | None = None,
) -> list[dict[str, Any]]:
    """Create a 01:50 Madrid snapshot using only candles closed by that instant.

    With ``preparation.context_lookback_days`` unset the snapshot replays the full history
    available at 01:50 (exact but quadratic in the number of trading days). A lookback limits the
    replayed history for long real datasets; trades are unaffected because execution always uses
    the complete candidate pass in :func:`run_v1_portfolio`.
    """
    generator = candidate_generator or generate_v1_candidates
    madrid = ZoneInfo(strategy_config["timezones"]["reference"])
    tzdb = timezone_database_version()
    config_hash = canonical_config_hash(strategy_config, execution_config)
    lookback = _context_lookback_days(strategy_config)
    prep_time = time.fromisoformat(strategy_config["preparation"]["time"])
    contexts: list[dict[str, Any]] = []
    for symbol, raw in sorted(data_by_symbol.items()):
        bars = raw.sort_values("timestamp").reset_index(drop=True)
        if bars.empty:
            continue
        local_dates = bars.timestamp.dt.tz_convert(madrid).dt.date
        for trading_date in sorted(set(local_dates)):
            prep_local = pd.Timestamp(datetime.combine(trading_date, prep_time)).tz_localize(madrid)
            prep_utc = prep_local.tz_convert("UTC")
            visible = bars.loc[bars.timestamp <= prep_utc]
            if lookback is not None:
                visible = visible.loc[visible.timestamp > prep_utc - pd.Timedelta(days=lookback)]
            visible = visible.copy().reset_index(drop=True)
            m15, h1 = aggregate_bars(visible, "M15"), aggregate_bars(visible, "H1")
            m15v, h1v = Bars(m15), Bars(h1)
            m15_swings = confirmed_fractal_swings(m15v, 2, 2) if len(m15) >= 5 else []
            h1_swings = confirmed_fractal_swings(h1v, 2, 2) if len(h1) >= 5 else []
            bias, premise = classify_h1_bias(h1_swings, len(h1) - 1) if len(h1) else ("UNDEFINED", None)
            levels = _liquidity_level_history(m15v, h1_swings, m15_swings, float(strategy_config["liquidity"]["equal_level_tolerance_atr"]))
            known_levels = [
                {"level_id": level["cluster_id"], "symbol": symbol, "timeframes": level["timeframes"], "kind": level["kind"],
                 "price": level["price"], "state": "ACTIVE", "created_at": level["effective_from"].isoformat(),
                 "source_constituents": level["constituents"]}
                for level in levels if level["effective_from"] <= prep_utc
            ]
            active_zones: list[dict[str, Any]] = []
            if len(m15) >= 20 and len(h1) >= 6:
                prior_setups = generator(visible, symbol, strategy_config)
                active_zones = [candidate["zone"] for candidate in prior_setups
                                if candidate.get("zone", {}).get("current_state") == "CONFIRMED"
                                and pd.Timestamp(candidate["zone"]["displacement_timestamp"]) <= prep_utc]
                active_zones = sorted({zone["zone_id"]: zone for zone in active_zones}.values(), key=lambda zone: zone["zone_id"])
            payload_key = f"{dataset_hash or 'unknown'}|{strategy_config['strategy_version']}|{config_hash}|{tzdb['version']}|{symbol}|{trading_date.isoformat()}"
            contexts.append({"context_id": _stable_id("daily-context|" + payload_key), "symbol": symbol,
                             "trading_date": trading_date.isoformat(), "created_at": prep_utc.isoformat(),
                             "strategy_version": strategy_config["strategy_version"], "dataset_hash": dataset_hash,
                             "config_hash": config_hash, "timezone_database_version": tzdb,
                             "available_data_through": None if visible.empty else visible.timestamp.max().isoformat(),
                             "context_lookback_days": lookback,
                             "h1_structure": [{"kind": swing.kind, "price": swing.price, "formed_at": swing.timestamp.isoformat(), "confirmed_at": swing.available_at.isoformat()} for swing in h1_swings],
                             "m15_structure": [{"kind": swing.kind, "price": swing.price, "formed_at": swing.timestamp.isoformat(), "confirmed_at": swing.available_at.isoformat()} for swing in m15_swings],
                             "h1_bias": bias, "h1_premise": premise, "liquidity_levels": known_levels,
                             "active_zones": active_zones,
                             "initial_state": "PREPARED"})
    return contexts


def run_v1_portfolio(data_by_symbol: dict[str, pd.DataFrame], strategy_config: dict[str, Any], execution_config: dict[str, Any],
                     dataset_hash: str | None = None, candidate_generator: CandidateGenerator | None = None,
                     include_daily_contexts: bool = True, progress: Callable[[str, float], None] | None = None) -> dict[str, Any]:
    """Simulate one or both symbols under shared daily and concurrent-position limits."""
    if strategy_config.get("status") != "FULLY_SPECIFIED":
        raise ValueError("Strategy V1 cannot run until its implementation and tests are validated")
    if not data_by_symbol or set(data_by_symbol) - set(strategy_config["instruments"]):
        raise ValueError("Portfolio input must contain EURUSD and/or GBPUSD M1 bars")
    generator = candidate_generator or generate_v1_candidates
    report = progress or (lambda _stage, _fraction: None)
    bars_by_symbol = {symbol: data.sort_values("timestamp").reset_index(drop=True).copy() for symbol, data in data_by_symbol.items()}
    report("daily_contexts", 0.05)
    daily_contexts = build_daily_contexts(bars_by_symbol, strategy_config, dataset_hash, execution_config, generator) if include_daily_contexts else []
    report("liquidity", 0.35)
    liquidity_events: list[dict[str, Any]] = []
    for symbol, bars in bars_by_symbol.items():
        m15, h1 = aggregate_bars(bars, "M15"), aggregate_bars(bars, "H1")
        if len(m15) >= 5 and len(h1) >= 5:
            m15v, h1v = Bars(m15), Bars(h1)
            h1_swings = confirmed_fractal_swings(h1v, 2, 2)
            m15_swings = confirmed_fractal_swings(m15v, 2, 2)
            levels = _liquidity_level_history(m15v, h1_swings, m15_swings, float(strategy_config["liquidity"]["equal_level_tolerance_atr"]))
            liquidity_events.extend(build_liquidity_lifecycle_events(Bars(bars), m15v, levels, symbol))
    report("candidates", 0.5)
    candidates = [candidate for symbol, bars in bars_by_symbol.items() for candidate in generator(bars, symbol, strategy_config)]
    # Candidates without an executable entry (DATA_GAP, no next M1) carry a None execution time;
    # order them by signal time so they never break the chronological pass.
    candidates.sort(key=lambda item: item.get("actual_execution_time") or item.get("actual_signal_time") or item["sweep_confirmation_timestamp"])
    report("simulation", 0.8)
    views = {symbol: Bars(bars) for symbol, bars in bars_by_symbol.items()}
    events, trades, state_events, zone_events = [], [], [], []
    executed_windows: set[tuple[str, str, int]] = set()
    traded_symbol_dates: set[tuple[str, str]] = set()
    global_trade_dates: dict[str, int] = {}
    equity = 1.0
    last_exit: pd.Timestamp | None = None
    reference_zone = strategy_config["timezones"]["reference"]
    risk_fraction = float(strategy_config["risk"]["baseline_equity_risk_fraction"])
    max_global = int(strategy_config["risk"]["max_trades_global_per_trading_date"])
    for candidate in candidates:
        state_events.extend(candidate.get("state_events", []))
        zone_events.extend(candidate.get("zone_events", []))
        status = candidate["candidate_status"]
        if status not in {"CANDIDATE_SETUP", None}:
            events.append({**candidate, "candidate_status": status})
            continue
        spread = resolve_spread(candidate.get("entry_spread_pips"), execution_config)
        candidate["spread_source"] = spread["spread_source"]
        if spread["candidate_status"]:
            events.append({**candidate, "candidate_status": spread["candidate_status"]})
            continue
        date_key = pd.Timestamp(candidate["actual_execution_time"]).tz_convert(reference_zone).date().isoformat()
        key = (candidate["symbol"], date_key, candidate["observation_window_index"])
        if key in executed_windows:
            events.append({**candidate, "candidate_status": "WINDOW_TRADE_LIMIT_REJECTED"})
            continue
        if (candidate["symbol"], date_key) in traded_symbol_dates or global_trade_dates.get(date_key, 0) >= max_global:
            events.append({**candidate, "candidate_status": "RISK_LIMIT_REJECTED"})
            continue
        if last_exit is not None and pd.Timestamp(candidate["actual_execution_time"]) < last_exit:
            events.append({**candidate, "candidate_status": "CONCURRENT_POSITION_REJECTED"})
            continue
        result = _simulate_candidate(candidate, views[candidate["symbol"]], execution_config, strategy_config, equity)
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
        equity *= max(0.0, 1.0 + risk_fraction * trade["r_multiple"])
    spread_sources = sorted({source for item in events for source in ([item.get("spread_source")] if item.get("spread_source") else [])})
    spread_sources.extend(source for trade in trades for source in trade.get("spread_sources", []) if source not in spread_sources)
    if not spread_sources:
        fallback = execution_config.get("spread", {}).get("fixed_fallback_pips")
        has_historical = any("spread_pips" in bars.columns and bars.spread_pips.notna().any() for bars in bars_by_symbol.values())
        spread_sources = ["HISTORICAL_SPREAD"] if has_historical else ["FIXED_CONFIGURED_SPREAD"] if fallback is not None else ["NO_SPREAD_DATA"]
    events_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for event in state_events:
        events_by_candidate.setdefault(event["candidate_id"], []).append(event)
    for candidate_event in events:
        candidate_event["trading_date"] = pd.Timestamp(candidate_event["sweep_confirmation_timestamp"]).tz_convert(reference_zone).date().isoformat()
        candidate_event["setup_start_timestamp"] = candidate_event.get("sweep_timestamp")
        candidate_event["setup_confirmation_timestamp"] = candidate_event.get("actual_signal_time", candidate_event.get("sweep_confirmation_timestamp"))
        candidate_event["rejection_reason"] = _normalized_rejection(candidate_event.get("candidate_status"))
        candidate_event["rejection_timestamp"] = candidate_event.get("rejection_timestamp") or (candidate_event.get("actual_execution_time") or candidate_event.get("actual_signal_time", candidate_event.get("sweep_confirmation_timestamp")) if candidate_event["rejection_reason"] else None)
        own_events = events_by_candidate.setdefault(candidate_event["candidate_id"], [])
        if candidate_event.get("candidate_status") == "EXECUTED":
            candidate_event["current_state"] = "EXECUTED"
        elif candidate_event["rejection_reason"] and candidate_event.get("state") not in {"INVALIDATED", "EXPIRED"}:
            candidate_event["current_state"] = "REJECTED"
            reason_timestamp = candidate_event["rejection_timestamp"] or candidate_event["sweep_confirmation_timestamp"]
            rejection_event = {"event_id": _stable_id(f"{candidate_event['candidate_id']}|REJECTED|{reason_timestamp}|{candidate_event['rejection_reason']}"),
                               "candidate_id": candidate_event["candidate_id"], "state": "REJECTED",
                               "sequence_index": len(own_events),
                               "timestamp": reason_timestamp, "detection_timestamp": reason_timestamp,
                               "reason": candidate_event["rejection_reason"]}
            state_events.append(rejection_event)
            own_events.append(rejection_event)
        else:
            candidate_event["current_state"] = candidate_event.get("state", "REJECTED")
        candidate_event["event_sequence"] = list(own_events)
    state_events.sort(key=lambda item: (item["timestamp"], item["candidate_id"], item.get("sequence_index", 999)))
    zone_events.sort(key=lambda event: (event["detection_timestamp"], event["zone_id"], event["new_state"]))
    report("done", 1.0)
    return {"strategy_version": strategy_config["strategy_version"], "strategy_status": strategy_config["status"],
            "symbols": sorted(bars_by_symbol), "candidate_count": len(events), "signal_count": len(trades), "trades": trades,
            "events": events, "state_events": state_events, "spread_sources": spread_sources,
            "liquidity_events": liquidity_events, "zone_events": zone_events,
            "daily_contexts": daily_contexts, "config_hash": canonical_config_hash(strategy_config, execution_config),
            "strategy_config_hash": canonical_config_hash(strategy_config), "execution_config_hash": canonical_config_hash(execution_config),
            "dataset_hash": dataset_hash, "timezone_database_version": timezone_database_version(),
            "ending_equity_normalized": equity}


def run_v1_backtest(m1_bars: pd.DataFrame, symbol: str, strategy_config: dict[str, Any], execution_config: dict[str, Any],
                    dataset_hash: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Single-symbol convenience wrapper; portfolio callers should pass both symbols together."""
    result = run_v1_portfolio({symbol: m1_bars}, strategy_config, execution_config, dataset_hash, **kwargs)
    result["symbol"] = symbol
    return result
