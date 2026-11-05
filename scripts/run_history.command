#!/bin/bash
# Double-click on macOS: runs the EUR/USD backtests listed in ONLY (default: 2019-2021 and 2025) and protocols for the public site (config/web_runs.yaml)
# and rebuilds frontend/public/data. Takes 10-30 minutes; keeps the Mac awake. Relaunch to redo only what failed.
cd "$(dirname "$0")/.." || exit 1
if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi
LOG="data/run_history.log"
ONLY="${ONLY:-eurusd-2026-v1 eurusd-2026-v1_1 eurusd-2026-v1_1-research}"
echo "FX Research Lab — exporting: $ONLY (log: $LOG)"
caffeinate -i python -m backend.cli export-web --only $ONLY 2>&1 | tee -a "$LOG"
echo "=== done $(date)"
