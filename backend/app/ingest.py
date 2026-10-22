"""Convert free historical FX sources into the platform's canonical M1 CSV.

Canonical format (see DATA_SPEC.md)::

    timestamp,open,high,low,close,volume[,spread_pips]

* ``timestamp`` is the ISO-8601 bar **open** time in UTC (``config/data.yaml`` records
  ``source_timestamp_semantics: bar_open``; the loader shifts to close time internally).
* ``spread_pips`` is written only when the source carries bid *and* ask prices. Sources without
  ask data (HistData) get no spread column; execution then requires an explicit
  ``spread.fixed_fallback_pips`` or the candidate is kept as ``SPREAD_DATA_UNAVAILABLE``.

Supported sources
-----------------
HistData.com "Generic ASCII" M1 bars: ``YYYYMMDD HHMMSS;O;H;L;C;V`` in **EST without DST**
(UTC-5 all year). Bid-side prices. Free, one zip per month/year.

Dukascopy historical CSV exports ("Gmt time,Open,High,Low,Close,Volume"; ``dd.MM.yyyy HH:mm:ss.SSS``)
for bid, optionally merged with the matching ask export to derive ``spread_pips``.

Dukascopy raw tick feed (``.bi5``, LZMA-compressed big-endian records) downloaded by
:func:`fetch_dukascopy_ticks`, aggregated into bid M1 bars with the per-minute median spread.

No synthetic candles are ever created; gaps stay gaps.
"""
from __future__ import annotations

import lzma
import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .instruments import dukascopy_point, pip_size
HISTDATA_OFFSET = timezone(timedelta(hours=-5))  # EST, no DST, all year
CANONICAL_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def _finish(frame: pd.DataFrame, out: Path | None, source: str, symbol: str | None) -> dict[str, Any]:
    frame = frame.sort_values("timestamp").drop_duplicates("timestamp", keep="first").reset_index(drop=True)
    columns = CANONICAL_COLUMNS + (["spread_pips"] if "spread_pips" in frame.columns else [])
    frame = frame[columns]
    report = {"source": source, "symbol": symbol, "rows": int(len(frame)),
              "start_utc": frame.timestamp.iloc[0] if len(frame) else None, "end_utc": frame.timestamp.iloc[-1] if len(frame) else None,
              "spread_pips_present": "spread_pips" in frame.columns, "timestamp_semantics": "bar_open"}
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out, index=False)
        report["output"] = str(out)
    report["frame"] = frame
    return report


# --------------------------------------------------------------------------- HistData

def convert_histdata(path: str | Path, out: str | Path | None = None, symbol: str | None = None) -> dict[str, Any]:
    """HistData Generic ASCII M1 (``;``-separated, EST no-DST bar opens) -> canonical UTC CSV."""
    raw = pd.read_csv(path, sep=";", header=None, names=["stamp", "open", "high", "low", "close", "volume"], dtype={"stamp": str})
    local = pd.to_datetime(raw["stamp"], format="%Y%m%d %H%M%S")
    utc = local.dt.tz_localize(HISTDATA_OFFSET).dt.tz_convert("UTC")
    frame = pd.DataFrame({"timestamp": utc.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                          "open": raw.open.astype(float), "high": raw.high.astype(float), "low": raw.low.astype(float),
                          "close": raw.close.astype(float), "volume": pd.to_numeric(raw.volume, errors="coerce").fillna(0).astype(float)})
    return _finish(frame, Path(out) if out else None, "histdata_generic_ascii_m1", symbol)


# --------------------------------------------------------------------------- Dukascopy CSV

def _read_dukascopy_csv(path: str | Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    time_column = next((c for c in raw.columns if "time" in c.lower()), raw.columns[0])
    stamps = pd.to_datetime(raw[time_column], format="%d.%m.%Y %H:%M:%S.%f", errors="coerce")
    if stamps.isna().any():
        stamps = pd.to_datetime(raw[time_column], errors="coerce", utc=False)
    if stamps.isna().any():
        raise ValueError("Unparseable Dukascopy timestamps; export with 'Gmt time' in dd.MM.yyyy HH:mm:ss.SSS")
    utc = stamps.dt.tz_localize("UTC") if stamps.dt.tz is None else stamps.dt.tz_convert("UTC")
    rename = {c: c.strip().lower() for c in raw.columns}
    raw = raw.rename(columns=rename)
    frame = pd.DataFrame({"timestamp": utc.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                          "open": raw["open"].astype(float), "high": raw["high"].astype(float),
                          "low": raw["low"].astype(float), "close": raw["close"].astype(float),
                          "volume": pd.to_numeric(raw.get("volume", 0), errors="coerce").fillna(0).astype(float)})
    return frame


def convert_dukascopy_csv(bid_path: str | Path, out: str | Path | None = None, ask_path: str | Path | None = None,
                          symbol: str = "EURUSD") -> dict[str, Any]:
    """Dukascopy bid CSV export (GMT) -> canonical CSV; merging the ask export adds ``spread_pips``."""
    bid = _read_dukascopy_csv(bid_path)
    if ask_path:
        ask = _read_dukascopy_csv(ask_path)[["timestamp", "open"]].rename(columns={"open": "ask_open"})
        bid = bid.merge(ask, on="timestamp", how="left")
        pip = pip_size(symbol)
        bid["spread_pips"] = ((bid["ask_open"] - bid["open"]) / pip).round(2)
        bid = bid.drop(columns=["ask_open"])
        # Minutes without an ask bar keep NaN: the engine reports them as SPREAD_DATA_UNAVAILABLE.
    return _finish(bid, Path(out) if out else None, "dukascopy_csv_export", symbol)


# --------------------------------------------------------------------------- Dukascopy tick feed

TICK_STRUCT = struct.Struct(">IIIff")  # ms since hour start, ask, bid, ask volume, bid volume


def decode_bi5(payload: bytes, hour_start: datetime, point: int) -> pd.DataFrame:
    """Decode one Dukascopy ``.bi5`` hour file into a tick frame (UTC timestamps)."""
    if not payload:
        return pd.DataFrame(columns=["timestamp", "ask", "bid", "ask_volume", "bid_volume"])
    raw = lzma.decompress(payload)
    if len(raw) % TICK_STRUCT.size:
        raise ValueError("Corrupt bi5 payload: record size mismatch")
    records = list(TICK_STRUCT.iter_unpack(raw))
    frame = pd.DataFrame(records, columns=["ms", "ask", "bid", "ask_volume", "bid_volume"])
    base = pd.Timestamp(hour_start).tz_convert("UTC") if pd.Timestamp(hour_start).tzinfo else pd.Timestamp(hour_start, tz="UTC")
    frame["timestamp"] = base + pd.to_timedelta(frame.pop("ms"), unit="ms")
    frame["ask"] = frame["ask"] / point
    frame["bid"] = frame["bid"] / point
    return frame[["timestamp", "ask", "bid", "ask_volume", "bid_volume"]]


def ticks_to_m1(ticks: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Aggregate bid ticks into M1 bars labelled by bar **open**; spread is the per-minute median."""
    if ticks.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS + ["spread_pips"])
    pip = pip_size(symbol)
    frame = ticks.set_index("timestamp").sort_index()
    frame["spread"] = (frame["ask"] - frame["bid"]) / pip
    bars = frame.resample("1min", label="left", closed="left").agg(
        open=("bid", "first"), high=("bid", "max"), low=("bid", "min"), close=("bid", "last"),
        volume=("bid_volume", "sum"), spread_pips=("spread", "median"))
    bars = bars.dropna(subset=["open"]).reset_index()
    bars["timestamp"] = bars["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    bars["spread_pips"] = bars["spread_pips"].round(2)
    return bars[CANONICAL_COLUMNS + ["spread_pips"]]


def dukascopy_hour_url(symbol: str, moment: datetime) -> str:
    # Dukascopy months are zero-based in the path.
    return f"https://datafeed.dukascopy.com/datafeed/{symbol.upper()}/{moment.year:04d}/{moment.month - 1:02d}/{moment.day:02d}/{moment.hour:02d}h_ticks.bi5"


def fetch_dukascopy_ticks(symbol: str, start: datetime, end: datetime, out: str | Path | None = None,
                          fetch: Callable[[str], bytes] | None = None, progress: Callable[[str], None] | None = None,
                          pause_seconds: float = 0.15, max_retries: int = 6) -> dict[str, Any]:
    """Download hourly tick files for ``[start, end)`` (UTC) and aggregate them into canonical M1 bars.

    ``fetch`` receives a URL and returns the raw bytes (empty bytes for a 404/no-data hour); the
    default uses ``urllib`` with exponential back-off on HTTP 503/429, which Dukascopy returns when a
    client is too aggressive (keep ``pause_seconds`` >= 0.1 and never run several downloads in
    parallel). Weekend hours are skipped. Ticks are aggregated month by month to bound memory.
    """
    if fetch is None:
        import ssl
        import time as _time
        from urllib.error import HTTPError, URLError
        from urllib.request import Request, urlopen

        # python.org builds on macOS ship without a CA bundle; fall back to certifi's when available.
        context = ssl.create_default_context()
        try:
            import certifi

            context = ssl.create_default_context(cafile=certifi.where())
        except ImportError:  # pragma: no cover
            pass

        def fetch(url: str) -> bytes:  # pragma: no cover - network
            delay = 4.0
            for attempt in range(max_retries):
                try:
                    with urlopen(Request(url, headers={"User-Agent": "fx-research-lab/0.4 (educational research)"}), timeout=30, context=context) as response:
                        return response.read()
                except HTTPError as exc:
                    if exc.code == 404:
                        return b""
                    if exc.code not in (429, 503) or attempt == max_retries - 1:
                        raise
                except URLError as exc:
                    if "CERTIFICATE_VERIFY_FAILED" in str(exc):
                        raise RuntimeError("TLS certificates not available to Python. Run 'Install Certificates.command' from the Python folder "
                                           "in /Applications, or 'pip install certifi', then relaunch.") from exc
                    if attempt == max_retries - 1:
                        raise
                _time.sleep(delay)
                delay *= 2
            return b""

    point = dukascopy_point(symbol)
    start = start.replace(minute=0, second=0, microsecond=0, tzinfo=start.tzinfo or timezone.utc)
    end = end.replace(tzinfo=end.tzinfo or timezone.utc)
    hours = []
    moment = start
    while moment < end:
        if not (moment.weekday() == 5 or (moment.weekday() == 6 and moment.hour < 20) or (moment.weekday() == 4 and moment.hour >= 22)):
            hours.append(moment)
        moment += timedelta(hours=1)
    monthly_frames: list[pd.DataFrame] = []
    current_month: tuple[int, int] | None = None
    month_ticks: list[pd.DataFrame] = []
    empty_hours = 0
    tick_count = 0

    def flush() -> None:
        if month_ticks:
            ticks = pd.concat(month_ticks, ignore_index=True)
            monthly_frames.append(ticks_to_m1(ticks, symbol))
            month_ticks.clear()

    for index, hour in enumerate(hours):
        if progress and index % 24 == 0:
            progress(f"{hour:%Y-%m-%d %H:00} ({index + 1}/{len(hours)})")
        if current_month != (hour.year, hour.month):
            flush()
            current_month = (hour.year, hour.month)
        payload = fetch(dukascopy_hour_url(symbol, hour))
        if pause_seconds:
            import time as _time
            _time.sleep(pause_seconds)
        ticks = decode_bi5(payload, hour, point)
        if ticks.empty:
            empty_hours += 1
            continue
        tick_count += int(len(ticks))
        month_ticks.append(ticks)
    flush()
    bars = pd.concat(monthly_frames, ignore_index=True) if monthly_frames else pd.DataFrame(columns=CANONICAL_COLUMNS + ["spread_pips"])
    report = _finish(bars, Path(out) if out else None, "dukascopy_bi5_ticks", symbol)
    report.update({"hours_requested": len(hours), "hours_without_data": empty_hours, "ticks": tick_count})
    return report


def read_bi5_bundle(path: str | Path, symbol: str | None = None) -> pd.DataFrame:
    """Decode a bundle of hourly ``.bi5`` files into one tick frame.

    Bundle layout (written by browser-side downloaders when the shell has no network): repeated
    records of ``<SYMBOL>/<YYYY>/<MM0>/<DD>/<HH>h_ticks.bi5 <length>\n`` followed by ``length`` raw
    bytes. Month folders are zero-based like Dukascopy's own paths. Hours with zero length are
    skipped (no data).
    """
    data = Path(path).read_bytes()
    frames = []
    offset = 0
    while offset < len(data):
        newline = data.index(b"\n", offset)
        header = data[offset:newline].decode("ascii")
        name, length = header.rsplit(" ", 1)
        length = int(length)
        payload = data[newline + 1:newline + 1 + length]
        offset = newline + 1 + length
        parts = name.split("/")
        file_symbol, year, month0, day, hour = parts[0], int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4][:2])
        if symbol and file_symbol.upper() != symbol.upper():
            continue
        if not length:
            continue
        point = dukascopy_point(file_symbol)
        frames.append(decode_bi5(payload, datetime(year, month0 + 1, day, hour, tzinfo=timezone.utc), point))
    if not frames:
        return pd.DataFrame(columns=["timestamp", "ask", "bid", "ask_volume", "bid_volume"])
    return pd.concat(frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)


def convert_bi5_bundles(paths: list[str | Path], out: str | Path | None = None, symbol: str = "EURUSD") -> dict[str, Any]:
    """One or more bundles -> canonical M1 CSV with per-minute median spread.

    Aggregates bundle by bundle: a year of ticks does not fit in memory on small machines, and bundles
    split on hour boundaries so per-bundle M1 aggregation is identical to aggregating all ticks at once.
    """
    frames = []
    tick_count = 0
    for path in paths:
        ticks = read_bi5_bundle(path, symbol)
        tick_count += int(len(ticks))
        if len(ticks):
            frames.append(ticks_to_m1(ticks, symbol))
        del ticks
    bars = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=CANONICAL_COLUMNS + ["spread_pips"])
    report = _finish(bars, Path(out) if out else None, "dukascopy_bi5_bundle", symbol)
    report["ticks"] = tick_count
    return report


def encode_bi5(ticks: list[tuple[int, float, float, float, float]], point: int) -> bytes:
    """Inverse of :func:`decode_bi5` for tests and fixtures (ms, ask, bid, ask_vol, bid_vol)."""
    raw = b"".join(TICK_STRUCT.pack(ms, int(round(ask * point)), int(round(bid * point)), float(av), float(bv)) for ms, ask, bid, av, bv in ticks)
    return lzma.compress(raw)


def stress_dataset(months: int, symbol: str = "EURUSD", seed: int = 7, start: str = "2024-01-01T00:00:00Z") -> pd.DataFrame:
    """Clearly labelled synthetic random-walk M1 data for performance testing only (never research)."""
    from .stress import make_stress_bars

    return make_stress_bars(start, months, seed, 1.10 if symbol == "EURUSD" else 1.27)


__all__ = ["convert_histdata", "convert_dukascopy_csv", "decode_bi5", "encode_bi5", "ticks_to_m1", "fetch_dukascopy_ticks",
           "dukascopy_hour_url", "read_bi5_bundle", "convert_bi5_bundles", "stress_dataset"]
