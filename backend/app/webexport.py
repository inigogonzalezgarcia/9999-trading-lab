"""Export precomputed results for the static web platform (Cloudflare Pages).

The public site has no backend: it reads ``data/runs.json`` (an index) and one trimmed JSON per run.
Trimming keeps everything the UI renders (trades, metrics, equity, chart candles, rejections, timing,
explainers, quality, reproducibility, research sections) and drops the audit streams that make a full
result 25+ MB (candidate events, liquidity/zone/state events, daily contexts).

The educational notice travels with every exported file.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from . import service

BACKTEST_KEYS = [
    "symbol", "symbols", "strategy_version", "strategy_status", "backtest_blocked", "blocked_reason", "dataset_version",
    "dataset_hash", "config_hash", "strategy_config_hash", "execution_config_hash", "timezone_database_version",
    "spread_sources", "candidate_count", "signal_count", "ending_equity_normalized", "trades", "metrics", "equity_curve",
    "report", "quality", "reproducibility", "notice", "chart", "trade_explainers",
]

MAX_CHART_BARS = 30000


def trim_backtest(result: dict[str, Any]) -> dict[str, Any]:
    """Keep only what the site renders; never the raw event streams."""
    out = {key: result[key] for key in BACKTEST_KEYS if key in result}
    chart = out.get("chart")
    if chart and isinstance(chart.get("series"), dict):
        out["chart"] = {"timeframe": chart.get("timeframe", "M15"),
                        "series": {name: candles[-MAX_CHART_BARS:] for name, candles in chart["series"].items()}}
    report = out.get("report") or {}
    out["report"] = {key: report[key] for key in ("rejections", "timing", "daily_contexts", "candidates_tracked") if key in report}
    out["web_export"] = {"trimmed": True, "dropped": ["events", "liquidity_events", "zone_events", "state_events", "scheduled_observations", "daily_contexts"]}
    return out


def trim_research(report: dict[str, Any]) -> dict[str, Any]:
    out = dict(report)
    out.pop("options", None)
    out["web_export"] = {"trimmed": False}
    return out


def load_spec(path: str | Path) -> dict[str, Any]:
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(spec, dict) or "runs" not in spec:
        raise ValueError("web runs spec needs a top-level 'runs' list")
    return spec


def export_site(spec: dict[str, Any], out_dir: str | Path, data_root: str | Path = ".", progress: Callable[[str], None] | None = None,
                pdf: bool = True, only: list[str] | None = None) -> dict[str, Any]:
    """Run every entry of the spec and write ``runs.json`` + ``runs/<id>.json`` (+ ``runs/<id>.pdf``)."""
    out = Path(out_dir)
    (out / "runs").mkdir(parents=True, exist_ok=True)
    datasets: dict[str, Any] = {}
    say = progress or (lambda _text: None)
    failures: dict[str, str] = {}

    for entry in spec["runs"]:
        run_id = entry["id"]
        if only and run_id not in only:
            continue
        try:
            _export_one(entry, out, Path(data_root), datasets, say, pdf)
        except Exception as exc:  # noqa: BLE001 - one failed run must not lose the others
            failures[run_id] = str(exc)
            say(f"[{run_id}] FAILED: {exc}")
        write_index(out)
    index = write_index(out)
    index["failures"] = failures
    return index


def write_index(out: Path) -> dict[str, Any]:
    """Rebuild runs.json from the per-run sidecars, so a crash never loses what was already exported."""
    runs = []
    for sidecar in sorted((out / "runs").glob("*.meta.json")):
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
        if (out / "runs" / f"{meta['id']}.json").exists():
            runs.append(meta)
    runs.sort(key=lambda item: (item.get("order", 0), item["id"]))
    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software_version": service.SOFTWARE_VERSION, "software_revision": service.software_revision(),
        "notice": service.EDUCATIONAL_NOTICE, "strategies": service.available_strategies(),
        "runs": runs,
    }
    (out / "runs.json").write_text(json.dumps(index, indent=1, default=str), encoding="utf-8")
    return index


def _export_one(entry: dict[str, Any], out: Path, data_root: Path, datasets: dict[str, Any], say: Callable[[str], None], pdf: bool) -> None:
    run_id = entry["id"]
    kind = entry.get("kind", "backtest")
    dataset_path = data_root / entry["dataset"]
    say(f"[{run_id}] loading {dataset_path.name}")
    if str(dataset_path) not in datasets:
        datasets[str(dataset_path)] = service.load_dataset(dataset_path, source_timezone=entry.get("source_timezone"))
    dataset = datasets[str(dataset_path)]
    options = {"strategy": entry.get("strategy", "strategy_v1.yaml"), "fixed_spread_pips": entry.get("fixed_spread_pips")}
    if kind == "backtest":
        options.update({"daily_contexts": entry.get("daily_contexts", "none"), "include_chart": True, "include_explainers": True})
        say(f"[{run_id}] backtest {entry['symbol']} {options['strategy']}")
        result = service.run_backtest(dataset, entry["symbol"], options, progress=lambda text, *_rest: say(f"[{run_id}] {text}"))
        payload = trim_backtest(result)
    else:
        options.update({key: entry[key] for key in ("train_days", "test_days", "anchored", "mc_simulations", "benchmark_simulations", "warmup_days", "seed",
                                                      "splits", "walk_forward", "monte_carlo", "sensitivity", "benchmark") if key in entry})
        say(f"[{run_id}] research {entry['symbol']} {options['strategy']}")
        result = service.run_research(dataset, entry["symbol"], options, progress=lambda text, *_rest: say(f"[{run_id}] {text}"))
        payload = trim_research(result)
    payload["run_id"] = run_id
    (out / "runs" / f"{run_id}.json").write_text(json.dumps(payload, default=str, separators=(",", ":")), encoding="utf-8")
    summary = service.summarize(result, kind)
    meta = {
        "id": run_id, "kind": kind, "symbol": entry["symbol"], "strategy": options["strategy"],
        "dataset_name": dataset_path.name, "dataset_hash": result.get("dataset_hash") or result.get("reproducibility", {}).get("dataset_hash"),
        "label": entry.get("label", {}), "description": entry.get("description", {}), "order": entry.get("order", 0),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "summary": summary,
        "software_version": service.SOFTWARE_VERSION, "pdf": None,
        "size_bytes": (out / "runs" / f"{run_id}.json").stat().st_size,
    }
    if pdf:
        try:
            from .report import build_pdf

            pdf_bytes = build_pdf(result, kind=kind, meta={"dataset_name": dataset_path.name, "symbol": entry["symbol"]})
            (out / "runs" / f"{run_id}.pdf").write_bytes(pdf_bytes)
            meta["pdf"] = f"runs/{run_id}.pdf"
        except Exception as exc:  # noqa: BLE001 - the PDF is optional on machines without reportlab
            say(f"[{run_id}] PDF skipped: {exc}")
    (out / "runs" / f"{run_id}.meta.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    say(f"[{run_id}] written ({meta['size_bytes'] / 1e6:.1f} MB)")
