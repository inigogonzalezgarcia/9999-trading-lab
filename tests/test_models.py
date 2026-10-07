from datetime import datetime, timezone

import pytest

from backend.app.models import Candle, Timeframe


def test_candle_requires_close_time_availability():
    stamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
    candle = Candle(symbol="EURUSD", timeframe=Timeframe.M1, timestamp=stamp, available_at=stamp,
                    open=1.0, high=1.1, low=0.9, close=1.05, volume=0)
    assert candle.timestamp == stamp


def test_candle_rejects_availability_before_close():
    stamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        Candle(symbol="EURUSD", timeframe=Timeframe.M1, timestamp=stamp,
               available_at=datetime(2023, 12, 31, 23, 59, tzinfo=timezone.utc),
               open=1.0, high=1.1, low=0.9, close=1.05, volume=0)
