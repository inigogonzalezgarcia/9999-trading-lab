#!/bin/bash
# Double-click on macOS (or run from a shell) to download Dukascopy tick history and build M1 CSVs.
# Resumable: every completed month is checkpointed under data/raw/<SYMBOL>_<YEAR>.parts/.
# Edit YEARS / SYMBOLS below. Keeps the Mac awake while it runs (caffeinate).
cd "$(dirname "$0")/.." || exit 1
YEARS="${YEARS:-2022 2023}"
SYMBOLS="${SYMBOLS:-EURUSD GBPUSD}"
LOG="data/fetch_history.log"
mkdir -p data/raw
if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi
echo "FX Research Lab — downloading $SYMBOLS for $YEARS (log: $LOG). Close this window to stop; relaunch to resume."
nohup caffeinate -i sh -c "
for y in $YEARS; do
  for s in $SYMBOLS; do
    out=data/raw/\${s}_\${y}.csv
    if [ -s \"\$out\" ]; then echo \"skip \$out (exists)\"; continue; fi
    echo \"=== \$s \$y \$(date)\"
    python -m backend.cli fetch dukascopy --symbol \$s --start \${y}-01-01 --end \$((y+1))-01-01 --out \"\$out\" || echo \"FAILED \$s \$y\"
  done
done
echo \"=== done \$(date)\"
" >> "$LOG" 2>&1 &
echo "Started in the background (PID $!). Follow progress with: tail -f $LOG"
