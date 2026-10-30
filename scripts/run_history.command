#!/bin/bash
# Double-click on macOS: runs the 2022-2023 EUR/USD backtests and protocols for the public site (config/web_runs.yaml)
# and rebuilds frontend/public/data. Takes 10-30 minutes; keeps the Mac awake. Relaunch to redo only what failed.
cd "$(dirname "$0")/.." || exit 1
if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi
LOG="data/run_history.log"
ONLY="${ONLY:-eurusd-2022-v1 eurusd-2022-v1_1 eurusd-2022-v1_1-research eurusd-2023-v1 eurusd-2023-v1_1 eurusd-2023-v1_1-research}"
echo "FX Research Lab — exporting: $ONLY (log: $LOG)"
caffeinate -i python -m backend.cli export-web --only $ONLY 2>&1 | tee -a "$LOG"
echo "=== done $(date)"
