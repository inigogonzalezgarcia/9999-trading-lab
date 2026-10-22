"""Converters from free data sources to the canonical M1 CSV, verified on tiny synthetic fixtures."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from backend.app import ingest
from backend.app.data import load_market_data


def test_histdata_est_timestamps_become_utc_bar_opens(tmp_path):
    source = tmp_path / "DAT_ASCII_EURUSD_M1_2024.csv"
    # HistData is EST without DST: 2024-07-01 00:00 EST == 05:00 UTC even in summer.
    source.write_text("20240701 000000;1.07100;1.07120;1.07090;1.07110;0\n20240701 000100;1.07110;1.07130;1.07100;1.07125;0\n")
    out = tmp_path / "EURUSD.csv"
    report = ingest.convert_histdata(source, out, "EURUSD")
    frame = pd.read_csv(out)
    assert list(frame.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert frame.timestamp.tolist() == ["2024-07-01T05:00:00Z", "2024-07-01T05:01:00Z"]
    assert report["spread_pips_present"] is False and report["rows"] == 2
    dataset = load_market_data(out, timestamp_semantics="bar_open")
    assert dataset.bars.timestamp.iloc[0].isoformat() == "2024-07-01T05:01:00+00:00"  # internal close time


def test_dukascopy_csv_merge_derives_spread_from_ask(tmp_path):
    bid = tmp_path / "bid.csv"
    ask = tmp_path / "ask.csv"
    bid.write_text("Gmt time,Open,High,Low,Close,Volume\n02.01.2024 00:00:00.000,1.10400,1.10420,1.10390,1.10410,120.5\n02.01.2024 00:01:00.000,1.10410,1.10430,1.10400,1.10425,98\n")
    ask.write_text("Gmt time,Open,High,Low,Close,Volume\n02.01.2024 00:00:00.000,1.10409,1.10429,1.10399,1.10419,120.5\n")
    report = ingest.convert_dukascopy_csv(bid, tmp_path / "out.csv", ask, "EURUSD")
    frame = report["frame"]
    assert frame.timestamp.tolist() == ["2024-01-02T00:00:00Z", "2024-01-02T00:01:00Z"]
    assert frame.spread_pips.iloc[0] == 0.9
    assert pd.isna(frame.spread_pips.iloc[1])  # no ask bar -> engine reports SPREAD_DATA_UNAVAILABLE


def test_bi5_round_trip_and_m1_aggregation():
    hour = datetime(2024, 1, 2, 7, tzinfo=timezone.utc)
    ticks = [(0, 1.10010, 1.10000, 1.0, 2.0), (30_000, 1.10030, 1.10020, 1.0, 1.0), (59_999, 1.09995, 1.09985, 1.0, 3.0),
             (60_000, 1.10050, 1.10040, 1.0, 1.0), (119_000, 1.10060, 1.10045, 1.0, 1.0)]
    payload = ingest.encode_bi5(ticks, 100_000)
    decoded = ingest.decode_bi5(payload, hour, 100_000)
    assert len(decoded) == 5
    assert decoded.timestamp.iloc[0] == pd.Timestamp("2024-01-02T07:00:00Z")
    assert decoded.bid.iloc[2] == 1.09985
    bars = ingest.ticks_to_m1(decoded, "EURUSD")
    assert bars.timestamp.tolist() == ["2024-01-02T07:00:00Z", "2024-01-02T07:01:00Z"]
    first = bars.iloc[0]
    assert (first.open, first.high, first.low, first.close) == (1.10000, 1.10020, 1.09985, 1.09985)
    assert first.volume == 6.0 and first.spread_pips == 1.0  # median of 1.0, 1.0, 1.0 pips
    assert ingest.decode_bi5(b"", hour, 100_000).empty


def test_dukascopy_fetch_uses_zero_based_months_and_skips_weekends():
    requested = []

    def fake_fetch(url: str) -> bytes:
        requested.append(url)
        return b""

    report = ingest.fetch_dukascopy_ticks("EURUSD", datetime(2024, 3, 1, 22, tzinfo=timezone.utc), datetime(2024, 3, 4, 1, tzinfo=timezone.utc), fetch=fake_fetch, pause_seconds=0)
    # Friday 22:00 onwards, Saturday, and Sunday before 21:00 are skipped.
    assert all("/2024/02/" in url for url in requested)  # March is month index 02
    assert any(url.endswith("/2024/02/03/21h_ticks.bi5") for url in requested)
    assert not any("/2024/02/02/" in url for url in requested)
    assert report["rows"] == 0 and report["hours_without_data"] == len(requested)
    assert ingest.dukascopy_hour_url("EURUSD", datetime(2024, 1, 2, 7)) == "https://datafeed.dukascopy.com/datafeed/EURUSD/2024/00/02/07h_ticks.bi5"


def test_bi5_bundle_round_trip(tmp_path):
    payload = ingest.encode_bi5([(0, 1.10010, 1.10000, 1.0, 2.0), (61_000, 1.10030, 1.10020, 1.0, 1.0)], 100_000)
    bundle = tmp_path / "fxlab_EURUSD_2024-01.bundle"
    bundle.write_bytes(b"EURUSD/2024/00/02/07h_ticks.bi5 " + str(len(payload)).encode() + b"\n" + payload
                       + b"EURUSD/2024/00/02/08h_ticks.bi5 0\n")
    ticks = ingest.read_bi5_bundle(bundle, "EURUSD")
    assert len(ticks) == 2 and ticks.timestamp.iloc[1] == pd.Timestamp("2024-01-02T07:01:01Z")
    report = ingest.convert_bi5_bundles([bundle], tmp_path / "out.csv", "EURUSD")
    assert report["rows"] == 2 and report["ticks"] == 2 and report["spread_pips_present"]


def test_portfolio_csv_with_symbol_column_is_not_flagged_as_duplicates(tmp_path):
    rows = ["symbol,timestamp,open,high,low,close,volume,spread_pips"]
    for clock in ("07:00", "07:01", "07:03"):
        rows.append(f"EURUSD,2024-01-02T{clock}:00Z,1.1000,1.1002,1.0999,1.1001,10,0.3")
        rows.append(f"GBPUSD,2024-01-02T{clock}:00Z,1.2700,1.2702,1.2699,1.2701,10,0.5")
    path = tmp_path / "portfolio.csv"
    path.write_text("\n".join(rows) + "\n")
    dataset = load_market_data(path, timestamp_semantics="bar_open")
    assert dataset.quality["duplicate_timestamps"] == 0
    assert dataset.quality["gap_count"] == 2  # one gap per symbol between 07:01 and 07:03
    assert dataset.quality["symbols"] == ["EURUSD", "GBPUSD"]
    assert dataset.quality["input_chronological"] is True
    single = tmp_path / "single.csv"
    single.write_text("\n".join(r.split(",", 1)[1] for r in rows[:3]) + "\n")
    with pytest.raises(Exception):
        load_market_data(single, timestamp_semantics="bar_open")  # same timestamp twice without symbol -> duplicate


def test_dukascopy_fetch_aggregates_real_payloads_month_by_month():
    hour = datetime(2024, 1, 31, 23, tzinfo=timezone.utc)
    payloads = {ingest.dukascopy_hour_url("EURUSD", hour): ingest.encode_bi5([(0, 1.10010, 1.10000, 1.0, 2.0)], 100_000),
                ingest.dukascopy_hour_url("EURUSD", hour + timedelta(hours=1)): ingest.encode_bi5([(5_000, 1.10110, 1.10100, 1.0, 1.0)], 100_000)}
    report = ingest.fetch_dukascopy_ticks("EURUSD", hour, hour + timedelta(hours=2), fetch=lambda url: payloads.get(url, b""), pause_seconds=0)
    frame = report["frame"]
    assert report["ticks"] == 2 and frame.timestamp.tolist() == ["2024-01-31T23:00:00Z", "2024-02-01T00:00:00Z"]
