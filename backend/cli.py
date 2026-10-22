"""Command-line interface for the FX Research Lab (educational research only).

Examples::

    python -m backend.cli fetch dukascopy --symbol EURUSD --start 2024-01-01 --end 2024-04-01 --out data/raw/EURUSD_2024Q1.csv
    python -m backend.cli convert histdata data/raw/DAT_ASCII_EURUSD_M1_2024.csv data/raw/EURUSD_2024.csv --symbol EURUSD
    python -m backend.cli validate data/raw/EURUSD_2024.csv
    python -m backend.cli backtest data/raw/EURUSD_2024.csv --symbol EURUSD --out results/EURUSD_2024.json
    python -m backend.cli research data/raw/EURUSD_2024.csv --symbol EURUSD --out results/EURUSD_2024_research.json
    python -m backend.cli runs list
    python -m backend.cli stress --months 3 --out data/stress/EURUSD_3m.csv
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.app import ingest, service
from backend.app.instruments import known_instruments
from backend.app.store import RunStore, dumps
from backend.app.stress import LABEL as STRESS_LABEL, make_stress_bars


def _print_notice() -> None:
    print("NOTICE: educational research tool. Simulated historical results; not investment advice.", file=sys.stderr)


def _progress(stage: str, fraction: float) -> None:
    print(f"\r  [{fraction * 100:5.1f}%] {stage:<48}", end="", file=sys.stderr, flush=True)


def _write(payload, out: Path | None) -> None:
    text = dumps(payload)
    if out is None:
        print(text)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"\nwrote {out} ({len(text) / 1e6:.1f} MB)", file=sys.stderr)


def _parse_date(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def cmd_fetch(args) -> int:
    if args.provider != "dukascopy":
        print("Only the Dukascopy tick feed can be fetched automatically; HistData requires a browser download.", file=sys.stderr)
        return 2
    report = ingest.fetch_dukascopy_ticks(args.symbol, _parse_date(args.start), _parse_date(args.end), args.out,
                                          progress=lambda text: print(f"\r  {text:<40}", end="", file=sys.stderr, flush=True))
    report.pop("frame", None)
    print()
    print(json.dumps(report, indent=2, default=str))
    return 0


def cmd_convert(args) -> int:
    if args.source == "histdata":
        report = ingest.convert_histdata(args.input, args.out, args.symbol)
    elif args.source == "bundle":
        report = ingest.convert_bi5_bundles([args.input, *args.more], args.out, args.symbol)
    else:
        report = ingest.convert_dukascopy_csv(args.input, args.out, args.ask, args.symbol)
    report.pop("frame", None)
    print(json.dumps(report, indent=2, default=str))
    if not report["spread_pips_present"]:
        print("No spread column: set spread.fixed_fallback_pips in config/execution.yaml or pass --fixed-spread-pips to backtest/research.", file=sys.stderr)
    return 0


def cmd_merge(args) -> int:
    """Stack canonical single-symbol CSVs into one PORTFOLIO file with a symbol column."""
    import pandas as pd

    frames = []
    for item in args.inputs:
        symbol, _, path = item.partition("=")
        if not path:
            print("use SYMBOL=path.csv for each input", file=sys.stderr)
            return 2
        frame = pd.read_csv(path)
        frame.insert(0, "symbol", symbol.upper())
        frames.append(frame)
    merged = pd.concat(frames, ignore_index=True)
    columns = ["symbol", "timestamp", "open", "high", "low", "close", "volume"] + (["spread_pips"] if "spread_pips" in merged.columns else [])
    merged = merged[columns].sort_values(["timestamp", "symbol"]).reset_index(drop=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.out, index=False)
    print(json.dumps({"output": str(args.out), "rows": int(len(merged)), "symbols": sorted(merged.symbol.unique().tolist())}, indent=2))
    return 0


def cmd_validate(args) -> int:
    dataset = service.load_dataset(args.input, source_timezone=args.source_timezone)
    print(json.dumps(dataset.quality, indent=2, default=str))
    return 0


def _maybe_save(kind: str, result, args, symbol: str) -> None:
    if args.no_save:
        return
    store = RunStore(args.db)
    run_id = store.save(kind, result, service.summarize(result, kind), symbol, Path(args.input).name, args.label)
    store.close()
    print(f"saved run {run_id} to {store.path}", file=sys.stderr)


def cmd_backtest(args) -> int:
    _print_notice()
    started = time.time()
    dataset = service.load_dataset(args.input, source_timezone=args.source_timezone)
    print(f"loaded {dataset.quality['rows']:,} rows, {dataset.quality['gap_count']} gaps, spread column: {dataset.quality['spread_available']}", file=sys.stderr)
    result = service.run_backtest(dataset, args.symbol, {"daily_contexts": args.daily_contexts, "fixed_spread_pips": args.fixed_spread_pips, "strategy": args.strategy,
                                                         "include_chart": not args.no_chart,
                                                         "context_detail": "full" if args.full_contexts else "summary"}, progress=_progress)
    print(file=sys.stderr)
    m = result["metrics"]
    print(f"strategy={result['strategy_version']} candidates={result['candidate_count']} trades={m['total_trades']} expectancy={m['expectancy_r']:+.3f}R total={m['total_r']:+.2f}R "
          f"win_rate={m['win_rate']:.0%} max_dd={m['max_drawdown_r']:.2f}R annualised_sharpe={m['daily']['annualized_sharpe']} ({time.time() - started:.0f}s)", file=sys.stderr)
    print("rejections:", json.dumps(result["report"]["rejections"]), file=sys.stderr)
    _maybe_save("backtest", result, args, args.symbol)
    _write(result, args.out)
    return 0


def cmd_research(args) -> int:
    _print_notice()
    started = time.time()
    dataset = service.load_dataset(args.input, source_timezone=args.source_timezone)
    options = {"fixed_spread_pips": args.fixed_spread_pips, "strategy": args.strategy, "train_days": args.train_days, "test_days": args.test_days,
               "anchored": args.anchored, "mc_simulations": args.mc_simulations, "benchmark_simulations": args.benchmark_simulations,
               "warmup_days": args.warmup_days, "seed": args.seed,
               "splits": not args.skip_splits, "walk_forward": not args.skip_walk_forward, "monte_carlo": not args.skip_monte_carlo,
               "sensitivity": not args.skip_sensitivity, "benchmark": not args.skip_benchmark}
    report = service.run_research(dataset, args.symbol, options, progress=_progress)
    print(file=sys.stderr)
    base = report["baseline"]
    print(f"baseline trades={base['trades']} expectancy={base['expectancy_r']:+.3f}R total={base['total_r']:+.2f}R ({time.time() - started:.0f}s)", file=sys.stderr)
    if "walk_forward" in report:
        print("walk-forward OOS:", json.dumps(report["walk_forward"]["out_of_sample_concatenated"]), file=sys.stderr)
    if "benchmark" in report and "baseline_percentile_vs_random" in report["benchmark"]:
        print(f"vs cost-matched random: percentile {report['benchmark']['baseline_percentile_vs_random']:.2f}", file=sys.stderr)
    _maybe_save("research", report, args, args.symbol)
    _write(report, args.out)
    return 0


def cmd_report(args) -> int:
    """Render a saved run or a result JSON file to PDF."""
    from backend.app.report import build_pdf

    if args.json:
        result = json.loads(Path(args.json).read_text(encoding="utf-8"))
        kind = "research" if "baseline" in result and "splits" in result or "walk_forward" in result else "backtest"
        meta = {"dataset_name": Path(args.json).name}
    else:
        store = RunStore(args.db)
        result = store.get(args.run_id)
        meta = store.meta(args.run_id) or {}
        store.close()
        if result is None:
            print("unknown run", file=sys.stderr)
            return 1
        kind = meta.get("kind", "backtest")
    payload = build_pdf(result, kind, meta)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(payload)
    print(f"wrote {args.out} ({len(payload) / 1024:.0f} KB)")
    return 0


def cmd_runs(args) -> int:
    store = RunStore(args.db)
    if args.action == "list":
        for row in store.list(limit=args.limit):
            print(f"{row['id']}  {row['created_at']}  {row['kind']:<9} {row['symbol'] or '':<9} {row['dataset_name'] or '':<32} {json.dumps(row['summary'])}")
    elif args.action == "show":
        result = store.get(args.run_id)
        if result is None:
            print("unknown run", file=sys.stderr)
            return 1
        _write(result, args.out)
    elif args.action == "delete":
        print("deleted" if store.delete(args.run_id) else "unknown run")
    store.close()
    return 0


def cmd_stress(args) -> int:
    frame = make_stress_bars(args.start, args.months, args.seed, 1.10 if args.symbol == "EURUSD" else 1.27)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out, index=False)
    print(f"{STRESS_LABEL}: wrote {len(frame):,} synthetic M1 rows to {args.out} (performance testing only, never research evidence)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fxlab", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="download historical data (needs network)")
    fetch.add_argument("provider", choices=["dukascopy"])
    fetch.add_argument("--symbol", default="EURUSD", choices=known_instruments())
    fetch.add_argument("--start", required=True, help="UTC start, e.g. 2024-01-01")
    fetch.add_argument("--end", required=True, help="UTC end (exclusive), e.g. 2024-04-01")
    fetch.add_argument("--out", type=Path, required=True)
    fetch.set_defaults(func=cmd_fetch)

    convert = sub.add_parser("convert", help="convert a provider file to the canonical CSV")
    convert.add_argument("source", choices=["histdata", "dukascopy", "bundle"], help="bundle = Dukascopy .bi5 files packed by a browser download")
    convert.add_argument("input", type=Path)
    convert.add_argument("out", type=Path)
    convert.add_argument("--more", type=Path, nargs="*", default=[], help="additional bundle files (bundle source only)")
    convert.add_argument("--symbol", default="EURUSD", choices=known_instruments())
    convert.add_argument("--ask", type=Path, help="Dukascopy ask export to derive spread_pips")
    convert.set_defaults(func=cmd_convert)

    merge = sub.add_parser("merge", help="combine single-symbol CSVs into a PORTFOLIO file (SYMBOL=path ...)")
    merge.add_argument("inputs", nargs="+", help="e.g. EURUSD=data/raw/EURUSD_2024.csv GBPUSD=data/raw/GBPUSD_2024.csv")
    merge.add_argument("--out", type=Path, required=True)
    merge.set_defaults(func=cmd_merge)

    validate = sub.add_parser("validate", help="data-quality report for a canonical CSV/Parquet file")
    validate.add_argument("input", type=Path)
    validate.add_argument("--source-timezone")
    validate.set_defaults(func=cmd_validate)

    for name, func in (("backtest", cmd_backtest), ("research", cmd_research)):
        run = sub.add_parser(name, help=f"run the V1 {name} on a canonical dataset")
        run.add_argument("input", type=Path)
        run.add_argument("--symbol", default="EURUSD", choices=[*known_instruments(), "PORTFOLIO"], help="an instrument listed by the strategy, or PORTFOLIO for a multi-symbol file")
        run.add_argument("--source-timezone")
        run.add_argument("--fixed-spread-pips", type=float, help="explicit fixed spread when the data has no spread_pips column")
        run.add_argument("--strategy", default=service.DEFAULT_STRATEGY, help="config/strategy_*.yaml to run (default strategy_v1.yaml; strategy_v1_1.yaml is the logged experiment)")
        run.add_argument("--out", type=Path, help="write the JSON result here (default: stdout)")
        run.add_argument("--label")
        run.add_argument("--no-save", action="store_true", help="do not persist the run in the SQLite history")
        run.add_argument("--db", help="SQLite path (default FXLAB_DB or data/fxlab.sqlite3)")
        if name == "backtest":
            run.add_argument("--daily-contexts", default="lookback:30", help="full | none | lookback:<days>")
            run.add_argument("--no-chart", action="store_true")
            run.add_argument("--full-contexts", action="store_true", help="keep every structure point and level in each daily context (large output)")
        else:
            run.add_argument("--train-days", type=int, default=120)
            run.add_argument("--test-days", type=int, default=30)
            run.add_argument("--anchored", action="store_true")
            run.add_argument("--warmup-days", type=int, default=15)
            run.add_argument("--mc-simulations", type=int, default=1000)
            run.add_argument("--benchmark-simulations", type=int, default=200)
            run.add_argument("--seed", type=int, default=7)
            for flag in ("splits", "walk-forward", "monte-carlo", "sensitivity", "benchmark"):
                run.add_argument(f"--skip-{flag}", action="store_true")
        run.set_defaults(func=func)

    runs = sub.add_parser("runs", help="inspect the persisted run history")
    runs.add_argument("action", choices=["list", "show", "delete"])
    runs.add_argument("run_id", nargs="?")
    runs.add_argument("--limit", type=int, default=50)
    runs.add_argument("--out", type=Path)
    runs.add_argument("--db")
    runs.set_defaults(func=cmd_runs)

    report = sub.add_parser("report", help="render a saved run (or a result JSON) to a PDF report")
    report.add_argument("run_id", nargs="?")
    report.add_argument("--json", type=Path, help="result/report JSON file instead of a run id")
    report.add_argument("--out", type=Path, required=True)
    report.add_argument("--db")
    report.set_defaults(func=cmd_report)

    stress = sub.add_parser("stress", help="generate labelled synthetic data for performance testing")
    stress.add_argument("--months", type=int, default=3)
    stress.add_argument("--symbol", default="EURUSD", choices=["EURUSD", "GBPUSD"])
    stress.add_argument("--seed", type=int, default=7)
    stress.add_argument("--start", default="2024-01-01T00:00:00Z")
    stress.add_argument("--out", type=Path, required=True)
    stress.set_defaults(func=cmd_stress)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
