"""Generate a clearly labelled SYNTHETIC M1 dataset for performance testing (never research).

Usage::

    python scripts/make_stress_dataset.py --months 3 --symbol EURUSD --out data/stress/EURUSD_3m.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.stress import LABEL, make_stress_bars  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", default="2024-01-01T00:00:00Z")
    parser.add_argument("--months", type=int, default=3)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--symbol", default="EURUSD", choices=["EURUSD", "GBPUSD"])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    frame = make_stress_bars(args.start, args.months, args.seed, 1.10 if args.symbol == "EURUSD" else 1.27)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out, index=False)
    print(f"{LABEL}: wrote {len(frame):,} M1 rows to {args.out}")


if __name__ == "__main__":
    main()
