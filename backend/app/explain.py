"""Per-trade explainers: the M1 candles of a setup plus every rule event, ready to draw and to read.

Educational purpose: a learner should see *why* the engine entered, where each rule fired, and
where the trade ended, on the same chart. Everything here is derived from data the engine already
emits (candidate events + trades); nothing is recomputed from the rules.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from .strategy.frames import Bars

MAX_BARS = 1500
BEFORE_MINUTES = 90
AFTER_MINUTES = 30


def _seconds(stamp: str | None) -> int | None:
    if not stamp:
        return None
    return int(pd.Timestamp(stamp).timestamp())


def _fmt(stamp: str | None, zone: str) -> str:
    return "—" if not stamp else pd.Timestamp(stamp).tz_convert(zone).strftime("%Y-%m-%d %H:%M")


def explain_trade(trade: dict[str, Any], candidate: dict[str, Any], bars: pd.DataFrame, strategy_config: dict[str, Any]) -> dict[str, Any]:
    """Build the explainer payload for one executed trade from its candidate event and the symbol's M1 bars."""
    zone_name = strategy_config["timezones"]["reference"]
    zone = candidate.get("zone", {}) or {}
    displacement = candidate.get("displacement", {}) or {}
    anchors = [candidate.get("sweep_timestamp"), zone.get("source_timestamp"), zone.get("creation_timestamp")]
    starts = [pd.Timestamp(stamp) for stamp in anchors if stamp]
    start = (min(starts) if starts else pd.Timestamp(trade["entry_timestamp"])) - pd.Timedelta(minutes=BEFORE_MINUTES)
    end = pd.Timestamp(trade["exit_timestamp"]) + pd.Timedelta(minutes=AFTER_MINUTES)
    window = bars.loc[(bars.timestamp >= start) & (bars.timestamp <= end)]
    if len(window) > MAX_BARS:
        window = window.iloc[-MAX_BARS:]
    view = Bars(window.reset_index(drop=True))
    candles = [{"time": int(t // 1_000_000_000), "open": float(o), "high": float(h), "low": float(lo), "close": float(c)}
               for t, o, h, lo, c in zip(view.ts, view.open, view.high, view.low, view.close)]

    direction = trade["direction"]
    levels = [
        {"id": "liquidity", "price": trade["liquidity_price"], "label": "Liquidity level swept", "style": "dashed", "color": "#8a8f98"},
        {"id": "sweep_extreme", "price": trade["sweep_price"], "label": "Sweep extreme", "style": "dotted", "color": "#8a8f98"},
        {"id": "zone_proximal", "price": zone.get("proximal"), "label": "Zone proximal", "style": "solid", "color": "#e0a458"},
        {"id": "zone_distal", "price": zone.get("distal"), "label": "Zone distal", "style": "solid", "color": "#e0a458"},
        {"id": "bos", "price": candidate.get("bos_level"), "label": "Structure broken (BOS level)", "style": "dashed", "color": "#8ab4f8"},
        {"id": "entry", "price": trade["entry_price"], "label": "Entry (incl. half spread + slippage)", "style": "solid", "color": "#2457c5"},
        {"id": "stop", "price": trade["stop_price"], "label": "Stop", "style": "solid", "color": "#c2544b"},
        {"id": "target", "price": trade["target_price"], "label": "Target", "style": "solid", "color": "#2a9d8f"},
    ]
    levels = [level for level in levels if level["price"] is not None]

    steps = [
        ("sweep", candidate.get("sweep_timestamp"), "Liquidity sweep", f"An M1 bar traded through the {'low' if direction == 'LONG' else 'high'} liquidity level at {trade['liquidity_price']:.5f}; extreme {trade['sweep_price']:.5f}."),
        ("sweep_confirmed", candidate.get("sweep_confirmation_timestamp"), "Sweep confirmed", "The containing M15 candle closed back through the level, so the touch counts as a sweep (close-back rule)."),
        ("zone", zone.get("source_timestamp"), "Zone source candle", f"Last opposite-direction M15 candle before the displacement defines the {'demand' if direction == 'LONG' else 'supply'} zone {zone.get('distal')}–{zone.get('proximal')}."),
        ("displacement_start", displacement.get("start"), "Displacement starts", "First M15 candle of the directional move away from the sweep."),
        ("displacement_end", displacement.get("end"), "Displacement qualifies", f"Move of {displacement.get('atr_multiple', 0):.2f} ATR (minimum {strategy_config['displacement']['minimum_atr']}) that also broke M15 structure; zone confirmed."),
        ("retracement", candidate.get("retracement_timestamp"), "Retracement", f"Pullback into the {strategy_config['two_leg'][direction.lower()]['retracement_range']} range of leg 1."),
        ("leg2", candidate.get("leg2_timestamp"), "Second leg", "A second directional leg of at least 0.50 ATR confirms the two-leg structure."),
        ("bos", candidate.get("bos_timestamp"), "Break of structure", f"M15 close beyond {candidate.get('bos_level')}: the setup is complete and tradeable only inside an observation window."),
        ("entry", trade["entry_timestamp"], "Entry", f"{direction} at {trade['entry_price']:.5f} on the first executable M1 price after the BOS (spread {trade['spread_pips']} pips, slippage {trade['slippage_pips']} pips). Stop {trade['stop_price']:.5f}, target {trade['target_price']:.5f} ({strategy_config['target']['baseline']})."),
        ("exit", trade["exit_timestamp"], f"Exit — {trade['exit_reason'].replace('_', ' ').title()}", f"{trade['r_multiple']:+.2f}R at {trade['exit_price']:.5f}. MFE {trade['mfe']:+.2f}R, MAE {trade['mae']:+.2f}R."),
    ]
    markers = []
    for key, stamp, title, text in steps:
        if not stamp:
            continue
        markers.append({"id": key, "time": _seconds(stamp), "timestamp": stamp, "local": _fmt(stamp, zone_name), "title": title, "text": text,
                        "position": "belowBar" if direction == "LONG" else "aboveBar"})
    # Entry and exit markers always face the price action.
    for marker in markers:
        if marker["id"] == "exit":
            marker["position"] = "aboveBar" if trade["r_multiple"] >= 0 else "belowBar"
    return {"trade_id": trade["trade_id"], "candidate_id": trade["candidate_id"], "symbol": trade["symbol"], "direction": direction,
            "timezone": zone_name, "timeframe": "M1", "candles": candles, "levels": levels, "steps": markers,
            "window": {"start": window.timestamp.min().isoformat() if len(window) else None, "end": window.timestamp.max().isoformat() if len(window) else None, "bars": len(window)},
            "rules": {"stop_reference": candidate.get("stop_reference", "sweep_extreme"), "atr_at_setup": candidate.get("atr_at_setup"),
                      "stop_distance_atr": (abs(trade["entry_price"] - trade["stop_price"]) / candidate["atr_at_setup"]) if candidate.get("atr_at_setup") else None,
                      "observation_window": trade.get("observation_window"), "scheduled_observation_time": trade.get("scheduled_observation_time")},
            "notice": "Simulated trade on historical data for educational purposes; not a recommendation."}


def explain_all(trades: list[dict[str, Any]], events: list[dict[str, Any]], data_by_symbol: dict[str, pd.DataFrame], strategy_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_candidate = {event["candidate_id"]: event for event in events}
    out: dict[str, dict[str, Any]] = {}
    for trade in trades:
        candidate = by_candidate.get(trade["candidate_id"])
        bars = data_by_symbol.get(trade["symbol"])
        if candidate is None or bars is None:
            continue
        try:
            out[trade["trade_id"]] = explain_trade(trade, candidate, bars, strategy_config)
        except Exception as exc:  # noqa: BLE001 - an explainer must never break a run
            out[trade["trade_id"]] = {"trade_id": trade["trade_id"], "error": str(exc)}
    return out
