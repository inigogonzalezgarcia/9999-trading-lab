"""Supply/demand zone lifecycle observed from completed M15 candles only."""
from __future__ import annotations

from typing import Any

import pandas as pd

from .frames import Bars
from .ids import _stable_id
from .structure import _as_bars


def _zone_event(zone_id: str, symbol: str, direction: str, previous: str | None, new: str,
                created: pd.Timestamp, detected: pd.Timestamp, displaced: pd.Timestamp,
                sweep_id: str, proximal: float, distal: float) -> dict[str, Any]:
    return {"event_id": _stable_id(f"{zone_id}|{new}|{detected.isoformat()}"),
            "zone_id": zone_id, "symbol": symbol, "direction": direction, "previous_state": previous,
            "new_state": new, "creation_timestamp": created.isoformat(),
            "detection_timestamp": detected.isoformat(),
            "displacement_timestamp": displaced.isoformat(), "sweep_id": sweep_id,
            "proximal": proximal, "distal": distal}


def build_zone_lifecycle(m15: pd.DataFrame | Bars, symbol: str, direction: str, source_index: int,
                         confirmation_index: int, proximal: float, distal: float,
                         sweep_id: str, expiry_bars: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Describe a zone's observable lifecycle using completed M15 candles only."""
    view = _as_bars(m15)
    source_time = view.stamp(source_index)
    confirmed_time = view.stamp(confirmation_index)
    zone_id = _stable_id(f"zone|{symbol}|{direction}|{source_time.isoformat()}|{proximal}|{distal}|{sweep_id}")
    events = [_zone_event(zone_id, symbol, direction, None, "CREATED", source_time, confirmed_time, confirmed_time, sweep_id, proximal, distal),
              _zone_event(zone_id, symbol, direction, "CREATED", "CONFIRMED", source_time, confirmed_time, confirmed_time, sweep_id, proximal, distal)]
    mitigation_time = invalidation_time = expiry_time = None
    final_state = "CONFIRMED"
    expiry_index = confirmation_index + expiry_bars
    upper, lower = max(proximal, distal), min(proximal, distal)
    for index in range(confirmation_index + 1, min(len(view), expiry_index + 1)):
        close = float(view.close[index])
        invalid = close < distal if direction == "LONG" else close > distal
        mitigated = float(view.low[index]) <= upper and float(view.high[index]) >= lower
        timestamp = view.stamp(index)
        if invalid:
            invalidation_time, final_state = timestamp, "INVALIDATED"
            break
        if mitigated:
            mitigation_time, final_state = timestamp, "MITIGATED"
            break
    if final_state == "CONFIRMED" and len(view) > expiry_index:
        expiry_time, final_state = view.stamp(expiry_index), "EXPIRED"
    terminal_time = invalidation_time or mitigation_time or expiry_time
    if terminal_time is not None:
        events.append(_zone_event(zone_id, symbol, direction, "CONFIRMED", final_state, source_time, terminal_time, confirmed_time, sweep_id, proximal, distal))
    zone = {"zone_id": zone_id, "symbol": symbol, "direction": direction,
            "proximal": proximal, "distal": distal, "creation_timestamp": source_time.isoformat(),
            "displacement_timestamp": confirmed_time.isoformat(),
            "confirmation_timestamp": confirmed_time.isoformat(),
            "mitigation_timestamp": None if mitigation_time is None else mitigation_time.isoformat(),
            "invalidation_timestamp": None if invalidation_time is None else invalidation_time.isoformat(),
            "expiry_timestamp": None if expiry_time is None else expiry_time.isoformat(),
            "current_state": final_state, "sweep_id": sweep_id}
    return zone, events
