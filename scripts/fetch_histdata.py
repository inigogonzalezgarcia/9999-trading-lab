#!/usr/bin/env python3
"""Download HistData.com "Generic ASCII" M1 bars for whole years and convert them to canonical CSVs.

    python3 scripts/fetch_histdata.py --years 2022 2023 --symbols EURUSD GBPUSD

Writes data/raw/histdata/DAT_ASCII_<SYMBOL>_M1_<YEAR>.zip (kept) and data/raw/<SYMBOL>_<YEAR>.csv (canonical).
HistData serves bid-only bars in EST without DST and no spread column, so backtests on these files need
``--fixed-spread-pips`` (see README). The site exposes the files through a small form (hidden ``tk`` token,
POST to get.php with the page as Referer); this script fills that form exactly as the browser would.
Runs from a machine with normal internet access (the Mac), not from the sandbox.
"""
from __future__ import annotations

import argparse
import io
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ingest import convert_histdata  # noqa: E402

try:  # python.org builds on macOS do not see the system certificate store; certifi is in backend/requirements.txt
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # pragma: no cover
    SSL_CONTEXT = ssl.create_default_context()

BASE = "https://www.histdata.com"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


def page_url(symbol: str, year: int) -> str:
    return f"{BASE}/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{symbol.lower()}/{year}"


def fetch_year(symbol: str, year: int, out_dir: Path) -> Path:
    zip_path = out_dir / f"DAT_ASCII_{symbol}_M1_{year}.zip"
    if zip_path.exists() and zip_path.stat().st_size > 100_000:
        print(f"  {zip_path.name}: already downloaded")
        return zip_path
    url = page_url(symbol, year)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60, context=SSL_CONTEXT) as resp:
        html = resp.read().decode("utf-8", "replace")
    fields = dict(re.findall(r'<input[^>]+name="(tk|date|datemonth|platform|timeframe|fxpair)"[^>]+value="([^"]*)"', html))
    if "tk" not in fields:
        raise SystemExit(f"could not find the download token on {url}; the page layout may have changed")
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(f"{BASE}/get.php", data=data, headers={"User-Agent": UA, "Referer": url, "Content-Type": "application/x-www-form-urlencoded", "Origin": BASE})
    with urllib.request.urlopen(req, timeout=300, context=SSL_CONTEXT) as resp:
        payload = resp.read()
    if not payload.startswith(b"PK"):
        raise SystemExit(f"{symbol} {year}: the server answered with HTML instead of a zip (token rejected?). Try again in a minute.")
    zip_path.write_bytes(payload)
    print(f"  {zip_path.name}: {len(payload) / 1e6:.1f} MB")
    return zip_path


def convert_year(symbol: str, year: int, zip_path: Path, raw_dir: Path) -> Path:
    with zipfile.ZipFile(io.BytesIO(zip_path.read_bytes())) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        csv_path = zip_path.with_suffix(".csv")
        csv_path.write_bytes(zf.read(name))
    out = raw_dir / f"{symbol}_{year}.csv"
    report = convert_histdata(csv_path, out, symbol=symbol)
    rows = report.get("rows") or report.get("quality", {}).get("rows")
    print(f"  -> {out} ({rows} rows)")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", nargs="+", type=int, default=[2022, 2023])
    parser.add_argument("--symbols", nargs="+", default=["EURUSD", "GBPUSD"])
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args()
    out_dir = args.raw_dir / "histdata"
    out_dir.mkdir(parents=True, exist_ok=True)
    for year in args.years:
        for symbol in args.symbols:
            print(f"== {symbol} {year}")
            zip_path = fetch_year(symbol, year, out_dir)
            convert_year(symbol, year, zip_path, args.raw_dir)
            time.sleep(2)
    print("done. Next: python -m backend.cli validate data/raw/EURUSD_2022.csv  (expect spread_available: no)")


if __name__ == "__main__":
    main()
