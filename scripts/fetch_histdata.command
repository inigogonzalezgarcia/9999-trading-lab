#!/bin/bash
# Double-click on macOS: downloads HistData M1 bars for 2022-2023 (EURUSD, GBPUSD), converts them and builds the PORTFOLIO files.
cd "$(dirname "$0")/.." || exit 1
if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi
python3 scripts/fetch_histdata.py --years ${YEARS:-2022 2023} --symbols ${SYMBOLS:-EURUSD GBPUSD} || { echo "FAILED"; exit 1; }
for y in ${YEARS:-2022 2023}; do
  python -m backend.cli merge EURUSD=data/raw/EURUSD_$y.csv GBPUSD=data/raw/GBPUSD_$y.csv --out data/raw/PORTFOLIO_$y.csv
  python -m backend.cli validate data/raw/EURUSD_$y.csv | head -20
done
echo "=== done"
