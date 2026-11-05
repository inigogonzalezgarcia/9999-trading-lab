#!/usr/bin/env python3
"""Precompute the parameter grid behind simulator level 8 ("Diseña tu versión").

Every combination of the grid below is run with the real engine on every year listed, exactly like the
sensitivity study (one frozen configuration per combination, all costs included). The browser never
computes a backtest: it only looks up the combination the learner chose.

    python3 scripts/export_grid.py                       # all years, resumable
    python3 scripts/export_grid.py --years 2024 2025     # subset

Output: frontend/public/data/grid/<combo-id>.json (per combination: per-year summary + pooled totals +
trades R list) and frontend/public/data/grid/index.json (axes, combos, baseline id). Resumable: an existing
combo file with all requested years is skipped, so the run can be interrupted and relaunched.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import service  # noqa: E402
from app.research import _set_path, _summary, run_period  # noqa: E402

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
STRATEGY = "strategy_v1_1.yaml"
FIXED_SPREAD = {2024: None}  # Dukascopy spread column in 2024; the rest use 0.3 pips (HistData has no spread)

# The axes the learner can move. Values are the ones already declared as experiments in the YAML, so the grid
# is a product of known one-at-a-time variants, not a new search.
AXES: list[dict[str, Any]] = [
    {"id": "stop", "scope": "strategy", "path": "stop.reference", "values": ["sweep_extreme", "zone_distal", "leg1_origin"],
     "label": {"es": "Referencia del stop", "en": "Stop reference"}},
    {"id": "maxatr", "scope": "strategy", "path": "stop.max_distance_atr", "values": [3.0, 4.0, 5.0],
     "label": {"es": "Distancia máxima del stop (ATR)", "en": "Max stop distance (ATR)"}},
    {"id": "life", "scope": "strategy", "path": "setup.lifetime_m15_bars_from_sweep_confirmation", "values": [6, 8, 12],
     "label": {"es": "Vida del setup (velas M15)", "en": "Setup lifetime (M15 bars)"}},
    {"id": "target", "scope": "strategy", "path": "target.baseline", "values": ["1.5R", "2.0R", "3.0R"],
     "label": {"es": "Objetivo", "en": "Target"}},
    {"id": "session", "scope": "multi", "path": "session", "values": [
        {"label": "london", "changes": [
            {"scope": "strategy", "path": "observation.windows", "value": [{"start": "09:00", "end": "09:45"}, {"start": "09:45", "end": "10:30"}]},
            {"scope": "strategy", "path": "observation.scheduled_times", "value": ["09:30", "10:00"]},
            {"scope": "strategy", "path": "execution.session_end", "value": "13:00"}]},
        {"label": "new_york", "changes": [
            {"scope": "strategy", "path": "observation.windows", "value": [{"start": "15:00", "end": "15:45"}, {"start": "15:45", "end": "16:30"}]},
            {"scope": "strategy", "path": "observation.scheduled_times", "value": ["15:30", "16:00"]},
            {"scope": "strategy", "path": "execution.session_end", "value": "19:00"}]}],
     "label": {"es": "Sesión", "en": "Session"}},
]
BASELINE = {"stop": "zone_distal", "maxatr": 3.0, "life": 8, "target": "2.0R", "session": "london"}


def combo_id(choice: dict[str, Any]) -> str:
    raw = "|".join(f"{k}={choice[k]}" for k in sorted(choice))
    return hashlib.sha1(raw.encode()).hexdigest()[:10]


def apply_choice(strategy: dict[str, Any], execution: dict[str, Any], choice: dict[str, Any]) -> None:
    for axis in AXES:
        value = choice[axis["id"]]
        if axis["scope"] == "multi":
            option = next(v for v in axis["values"] if v["label"] == value)
            for change in option["changes"]:
                _set_path(strategy if change["scope"] == "strategy" else execution, change["path"], change["value"])
        else:
            _set_path(strategy if axis["scope"] == "strategy" else execution, axis["path"], value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", nargs="+", type=int, default=YEARS)
    parser.add_argument("--out", type=Path, default=ROOT / "frontend" / "public" / "data" / "grid")
    parser.add_argument("--data-root", type=Path, default=ROOT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    axis_values = [[v["label"] if isinstance(v, dict) else v for v in axis["values"]] for axis in AXES]
    combos = [dict(zip([a["id"] for a in AXES], values)) for values in itertools.product(*axis_values)]
    print(f"{len(combos)} combinations × {len(args.years)} years")

    datasets: dict[int, Any] = {}
    started = time.time()
    for index, choice in enumerate(combos, 1):
        cid = combo_id(choice)
        path = args.out / f"{cid}.json"
        record: dict[str, Any] = {"id": cid, "choice": choice, "years": {}}
        if path.exists():
            record = json.loads(path.read_text())
        missing = [y for y in args.years if str(y) not in record["years"]]
        if not missing:
            continue
        for year in missing:
            if year not in datasets:
                datasets[year] = service.load_dataset(args.data_root / "data" / "raw" / f"EURUSD_{year}.csv")
            dataset = datasets[year]
            strategy, execution, _ = service.load_configs(FIXED_SPREAD.get(year, 0.3), STRATEGY)
            strategy, execution = copy.deepcopy(strategy), copy.deepcopy(execution)
            apply_choice(strategy, execution, choice)
            data_by_symbol = service.split_by_symbol(dataset, "EURUSD", strategy)
            result = run_period(data_by_symbol, strategy, execution, dataset_hash=dataset.version)
            summary = _summary(result)
            summary["trades_r"] = [round(t["r_multiple"], 3) for t in result["trades"]]
            summary["exit_reasons"] = result["metrics"].get("exit_reasons", {})
            summary["dataset_hash"] = dataset.version
            record["years"][str(year)] = summary
            path.write_text(json.dumps(record, default=str))  # checkpoint after every year
        elapsed = time.time() - started
        print(f"  [{index}/{len(combos)}] {cid} {choice} · {elapsed / 60:.0f} min")

    # ---- index: pooled totals per combo so the browser can rank and compare without opening 162 files
    rows = []
    for path in sorted(args.out.glob("*.json")):
        if path.name == "index.json":
            continue
        record = json.loads(path.read_text())
        years = record["years"]
        trades = sum(y["trades"] for y in years.values())
        total = sum(y["total_r"] for y in years.values())
        rows.append({"id": record["id"], "choice": record["choice"], "trades": trades, "total_r": round(total, 3),
                     "expectancy_r": round(total / trades, 4) if trades else None,
                     "years_positive": sum(1 for y in years.values() if y["total_r"] > 0), "years": len(years),
                     "worst_year_r": round(min(y["total_r"] for y in years.values()), 3) if years else None,
                     "best_year_r": round(max(y["total_r"] for y in years.values()), 3) if years else None})
    index = {"strategy": STRATEGY, "years": args.years, "fixed_spread_pips": 0.3, "spread_note": "2024 uses the provider spread column; other years 0.3 pips fixed",
             "axes": [{"id": a["id"], "label": a["label"], "values": [v["label"] if isinstance(v, dict) else v for v in a["values"]]} for a in AXES],
             "baseline": BASELINE, "baseline_id": combo_id(BASELINE), "combos": rows,
             "notice": "Educational grid: every combination is a hypothesis run on the same engine with costs. Picking the best cell after the fact is overfitting; that is the lesson."}
    (args.out / "index.json").write_text(json.dumps(index, separators=(",", ":")))
    print(f"index written: {len(rows)} combos")


if __name__ == "__main__":
    main()
