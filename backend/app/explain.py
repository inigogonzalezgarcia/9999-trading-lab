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
        {"id": "liquidity", "price": trade["liquidity_price"], "label": "Liquidity level swept", "label_es": "Nivel de liquidez barrido", "style": "dashed", "color": "#8a9199"},
        {"id": "sweep_extreme", "price": trade["sweep_price"], "label": "Sweep extreme", "label_es": "Extremo del barrido", "style": "dotted", "color": "#8a9199"},
        {"id": "zone_proximal", "price": zone.get("proximal"), "label": "Zone proximal", "label_es": "Zona (lado proximal)", "style": "solid", "color": "#9a6a1f"},
        {"id": "zone_distal", "price": zone.get("distal"), "label": "Zone distal", "label_es": "Zona (lado distal)", "style": "solid", "color": "#9a6a1f"},
        {"id": "bos", "price": candidate.get("bos_level"), "label": "Structure broken (BOS level)", "label_es": "Ruptura de estructura (nivel BOS)", "style": "dashed", "color": "#5c6670"},
        {"id": "entry", "price": trade["entry_price"], "label": "Entry (incl. half spread + slippage)", "label_es": "Entrada (con medio spread + deslizamiento)", "style": "solid", "color": "#c4672b"},
        {"id": "stop", "price": trade["stop_price"], "label": "Stop", "label_es": "Stop", "style": "solid", "color": "#b5443a"},
        {"id": "target", "price": trade["target_price"], "label": "Target", "label_es": "Objetivo", "style": "solid", "color": "#2f7d6b"},
    ]
    levels = [level for level in levels if level["price"] is not None]
    side_es = "mínimo" if direction == "LONG" else "máximo"
    zone_es = "demanda" if direction == "LONG" else "oferta"
    exit_es = {"take_profit": "Objetivo alcanzado", "stop_loss": "Stop ejecutado", "session_expiry": "Cierre de sesión"}.get(trade["exit_reason"], trade["exit_reason"].replace("_", " "))
    spanish = {
        "sweep": ("Barrido de liquidez", f"Una vela M1 atravesó el {side_es} de liquidez en {trade['liquidity_price']:.5f}; extremo en {trade['sweep_price']:.5f}."),
        "sweep_confirmed": ("Barrido confirmado", "La vela M15 que lo contiene cerró de vuelta al otro lado del nivel, así que el toque cuenta como barrido (regla de cierre de vuelta)."),
        "zone": ("Vela origen de la zona", f"La última vela M15 de sentido contrario antes del impulso define la zona de {zone_es} {zone.get('distal')}–{zone.get('proximal')}."),
        "displacement_start": ("Empieza el impulso", "Primera vela M15 del movimiento direccional que se aleja del barrido."),
        "displacement_end": ("El impulso cumple", f"Movimiento de {displacement.get('atr_multiple', 0):.2f} ATR (mínimo {strategy_config['displacement']['minimum_atr']}) que además rompió estructura M15; zona confirmada."),
        "retracement": ("Retroceso", f"Vuelta al rango {strategy_config['two_leg'][direction.lower()]['retracement_range']} del tramo 1."),
        "leg2": ("Segundo tramo", "Un segundo tramo direccional de al menos 0,50 ATR confirma la estructura de dos tramos."),
        "bos": ("Ruptura de estructura", f"Cierre M15 más allá de {candidate.get('bos_level')}: el setup está completo y solo es operable dentro de una ventana de observación."),
        "entry": ("Entrada", f"{direction} a {trade['entry_price']:.5f} al primer precio M1 ejecutable tras el BOS (spread {trade['spread_pips']} pips, deslizamiento {trade['slippage_pips']} pips). Stop {trade['stop_price']:.5f}, objetivo {trade['target_price']:.5f} ({strategy_config['target']['baseline']})."),
        "exit": (f"Salida — {exit_es}", f"{trade['r_multiple']:+.2f}R a {trade['exit_price']:.5f}. MFE {trade['mfe']:+.2f}R, MAE {trade['mae']:+.2f}R."),
    }

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
        title_es, text_es = spanish.get(key, (title, text))
        markers.append({"id": key, "time": _seconds(stamp), "timestamp": stamp, "local": _fmt(stamp, zone_name), "title": title, "text": text,
                        "title_es": title_es, "text_es": text_es, "position": "belowBar" if direction == "LONG" else "aboveBar"})
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
