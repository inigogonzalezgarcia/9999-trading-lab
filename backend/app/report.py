"""PDF research report (reportlab): cover, data, results, breakdowns, research protocol, limitations.

The document is deliberately sober: tables and simple charts drawn with reportlab's own graphics,
the educational notice on the cover and in the footer of every page, and no claim that the engine
cannot support. Works for backtest results and for research reports.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .service import EDUCATIONAL_NOTICE, SOFTWARE_VERSION

INK = colors.HexColor("#0e1a24")
MUTED = colors.HexColor("#5c6670")
LINE = colors.HexColor("#e1dacd")
ACCENT = colors.HexColor("#c4672b")
GOOD = colors.HexColor("#2f7d6b")
BAD = colors.HexColor("#b5443a")
WARN = colors.HexColor("#b26d12")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontSize=22, leading=26, alignment=TA_LEFT, textColor=INK, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontSize=11, leading=14, textColor=MUTED, spaceAfter=10),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontSize=15, leading=18, textColor=INK, spaceBefore=10, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=12, leading=15, textColor=INK, spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=9.5, leading=13, textColor=INK),
        "small": ParagraphStyle("small", parent=base["Normal"], fontSize=8, leading=10.5, textColor=MUTED),
        "notice": ParagraphStyle("notice", parent=base["Normal"], fontSize=8.5, leading=11.5, textColor=colors.HexColor("#5c4200"),
                                 backColor=colors.HexColor("#fff6e0"), borderPadding=6, spaceBefore=6, spaceAfter=10),
        "mono": ParagraphStyle("mono", parent=base["Code"], fontSize=7.5, leading=9.5, textColor=INK),
    }


def _r(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:+.{digits}f}R"


def _num(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.0f} %"


def _table(rows: list[list[Any]], widths: list[float] | None = None, header: bool = True, zebra: bool = True, font_size: float = 8.5) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), font_size), ("TEXTCOLOR", (0, 0), (-1, -1), INK),
             ("LINEBELOW", (0, 0), (-1, -1), 0.25, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if header:
        style += [("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("TEXTCOLOR", (0, 0), (-1, 0), MUTED), ("LINEBELOW", (0, 0), (-1, 0), 0.75, MUTED)]
    if zebra:
        for row in range(1 if header else 0, len(rows)):
            if row % 2 == 0:
                style.append(("BACKGROUND", (0, row), (-1, row), colors.HexColor("#f6f7f9")))
    table.setStyle(TableStyle(style))
    return table


def _line_chart(points: list[tuple[float, float]], width: float = 170 * mm, height: float = 55 * mm, title: str = "") -> Drawing:
    drawing = Drawing(width, height)
    plot = LinePlot()
    plot.x, plot.y, plot.width, plot.height = 35, 18, width - 45, height - 30
    plot.data = [points if points else [(0, 0)]]
    plot.lines[0].strokeColor = ACCENT
    plot.lines[0].strokeWidth = 1.2
    plot.xValueAxis.visibleGrid = False
    plot.yValueAxis.visibleGrid = True
    plot.yValueAxis.gridStrokeColor = LINE
    plot.xValueAxis.labels.fontSize = 7
    plot.yValueAxis.labels.fontSize = 7
    plot.xValueAxis.labelTextFormat = lambda value: f"#{int(value)}"
    plot.yValueAxis.labelTextFormat = lambda value: f"{value:+.1f}R"
    drawing.add(plot)
    if title:
        drawing.add(String(0, height - 8, title, fontSize=8, fillColor=MUTED))
    return drawing


def _bar_chart(labels: list[str], values: list[float], width: float = 170 * mm, height: float = 50 * mm, title: str = "", color=ACCENT, fmt: str = "{:.0f}") -> Drawing:
    drawing = Drawing(width, height)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 35, 20, width - 45, height - 34
    chart.data = [values if values else [0]]
    chart.categoryAxis.categoryNames = labels if labels else [""]
    chart.categoryAxis.labels.fontSize = 6.5
    chart.categoryAxis.labels.angle = 0 if len(labels) <= 14 else 90
    chart.categoryAxis.labels.dy = -2 if len(labels) <= 14 else -12
    # Keep category labels under the plot even when the value axis crosses zero inside it.
    chart.categoryAxis.joinAxisMode = "bottom"
    chart.categoryAxis.labels.boxAnchor = "n" if len(labels) <= 14 else "e"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.visibleGrid = True
    chart.valueAxis.gridStrokeColor = LINE
    chart.valueAxis.labelTextFormat = lambda value: fmt.format(value)
    # Bars must always start at zero; otherwise a small positive bucket disappears below the axis.
    chart.valueAxis.valueMin = min(0.0, min(values)) if values else 0.0
    chart.valueAxis.valueMax = max(0.0, max(values)) * 1.05 if values and max(values) > 0 else 0.0
    chart.bars[0].fillColor = color
    chart.bars[0].strokeColor = None
    if any(value < 0 for value in values):
        # Signed charts: losses in red, gains in the given colour.
        for index, value in enumerate(values):
            chart.bars[(0, index)].fillColor = BAD if value < 0 else color
    chart.barSpacing = 1
    drawing.add(chart)
    if title:
        drawing.add(String(0, height - 8, title, fontSize=8, fillColor=MUTED))
    return drawing


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "FX Research Lab · educational tool · simulated historical results, not investment advice · past performance does not guarantee future results")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"page {doc.page}")
    canvas.restoreState()


def build_pdf(result: dict[str, Any], kind: str = "backtest", meta: dict[str, Any] | None = None) -> bytes:
    """Render a backtest result or a research report to PDF bytes."""
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                            title="FX Research Lab report", author="FX Research Lab")
    story: list[Any] = []
    repro = result.get("reproducibility", {}) or {}
    period = repro.get("dataset_date_range_utc", {}) or {}
    symbol = result.get("symbol") or ", ".join(result.get("symbols", [])) or "PORTFOLIO"
    label = (meta or {}).get("label") or (meta or {}).get("dataset_name") or ""

    # ---------------------------------------------------------------- cover
    story.append(Paragraph("FX Research Lab — " + ("research protocol report" if kind == "research" else "backtest report"), styles["title"]))
    story.append(Paragraph(f"Strategy {repro.get('strategy_version', '?')} ({repro.get('strategy_file', 'strategy_v1.yaml')}) · {symbol} · "
                           f"{str(period.get('start', ''))[:10]} → {str(period.get('end', ''))[:10]} · generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC"
                           + (f" · {label}" if label else ""), styles["subtitle"]))
    story.append(Paragraph(f"<b>{EDUCATIONAL_NOTICE['title']}.</b> " + " ".join(EDUCATIONAL_NOTICE["lines"]), styles["notice"]))
    story.append(Paragraph("Reproducibility", styles["h2"]))
    story.append(_table([["Field", "Value"],
                         ["Dataset SHA-256", str(repro.get("dataset_hash", "—"))], ["Configuration hash", str(repro.get("config_hash", "—"))],
                         ["Execution model", str(repro.get("execution_model", "—"))], ["Spread sources", ", ".join(repro.get("spread_source", []) or []) or "—"],
                         ["Slippage", str((repro.get("slippage_model") or {}).get("baseline_pips", "—")) + " pips"],
                         ["Timezone database", str((repro.get("timezone_database_version") or {}).get("version", "—"))],
                         ["Software", f"{repro.get('software_version', SOFTWARE_VERSION)} · {repro.get('software_revision', '—')}"]],
                        widths=[45 * mm, 125 * mm], zebra=False, font_size=7.5))

    quality = result.get("quality") or {}
    if quality:
        story.append(Paragraph("Data", styles["h2"]))
        story.append(_table([["Rows", "Gaps", "Duplicates", "Invalid", "Weekend rows", "Spread column", "Source timezone"],
                             [quality.get("rows"), quality.get("gap_count"), quality.get("duplicate_timestamps"), quality.get("invalid_rows"),
                              quality.get("weekend_rows"), "yes" if quality.get("spread_available") else "no", quality.get("source_timezone")]],
                            zebra=False))
        for warning in quality.get("warnings", []) or []:
            story.append(Paragraph(f"⚠ {warning}", styles["small"]))

    if kind == "research":
        story += _research_sections(result, styles)
    else:
        story += _backtest_sections(result, styles)

    story.append(PageBreak())
    story.append(Paragraph("Limitations", styles["h1"]))
    limitations = result.get("limitations") or [
        "Simulated fills on historical M1 data; no live execution was involved.",
        "Costs follow the recorded execution configuration; provider spreads are used when present.",
        "A positive result in one period is not evidence of a robust edge; sample sizes in intraday setups are small.",
        "Historical performance does not guarantee future results.",
    ]
    for item in limitations:
        story.append(Paragraph(f"• {item}", styles["body"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(" ".join(EDUCATIONAL_NOTICE["lines"]), styles["notice"]))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _backtest_sections(result: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    story: list[Any] = []
    m = result.get("metrics") or {}
    story.append(PageBreak())
    story.append(Paragraph("Results", styles["h1"]))
    if not m or result.get("backtest_blocked"):
        story.append(Paragraph(result.get("blocked_reason") or "No metrics available.", styles["body"]))
        return story
    daily = m.get("daily") or {}
    story.append(_table([["Trades", "Win rate", "Expectancy", "Total", "Profit factor", "Max drawdown", "Sharpe (ann.)", "Sharpe / trade"],
                         [m.get("total_trades"), _pct(m.get("win_rate")), _r(m.get("expectancy_r")), _r(m.get("total_r")), _num(m.get("profit_factor")),
                          _r(m.get("max_drawdown_r")), _num(daily.get("annualized_sharpe")), _num(m.get("sharpe_per_trade"))]], zebra=False))
    story.append(Paragraph(f"{result.get('candidate_count', 0)} candidates tracked · {daily.get('trading_days', 0)} weekdays in range · "
                           f"{daily.get('days_with_trades', 0)} days with trades. Per-trade statistics are not annualised; the annualised Sharpe uses the daily sum of R.", styles["small"]))
    curve = result.get("equity_curve") or []
    if curve:
        story.append(Spacer(1, 6))
        story.append(_line_chart([(i + 1, p["cumulative_r"]) for i, p in enumerate(curve)], title="Cumulative R by trade"))
    report = result.get("report") or {}
    rejections = report.get("rejections") or {}
    if rejections:
        story.append(Paragraph("Why candidates did not become trades", styles["h2"]))
        total = max(1, sum(rejections.values()))
        story.append(_table([["Reason", "Count", "Share"]] + [[k, v, f"{v / total * 100:.0f} %"] for k, v in rejections.items()], widths=[90 * mm, 25 * mm, 25 * mm]))
    timing = report.get("timing") or {}
    if timing.get("complete_setups_by_hour"):
        hours = timing["complete_setups_by_hour"]
        story.append(KeepTogether([Paragraph(f"When the pattern completes ({timing.get('timezone')}) — {timing.get('complete_setups')} complete setups, {timing.get('complete_setups_outside_windows')} outside the observation windows", styles["h2"]),
                                   _bar_chart(list(hours), [float(v) for v in hours.values()], title="Complete setups by local hour")]))
    for key, title in (("by_hour", "R by entry hour"), ("by_weekday", "R by weekday"), ("by_month", "R by month")):
        groups = m.get(key) or {}
        if groups:
            story.append(KeepTogether([Paragraph(title, styles["h2"]),
                                       _bar_chart(list(groups), [g["total_r"] for g in groups.values()], title="Total R", color=GOOD, fmt="{:+.1f}"),
                                       _table([["Bucket", "Trades", "Total R", "Expectancy", "Win rate"]] + [[k, g["trades"], _r(g["total_r"]), _r(g["expectancy_r"]), _pct(g["win_rate"])] for k, g in groups.items()],
                                              widths=[35 * mm, 25 * mm, 30 * mm, 30 * mm, 25 * mm])]))
    trades = result.get("trades") or []
    if trades:
        story.append(PageBreak())
        story.append(Paragraph(f"Trades ({len(trades)})", styles["h1"]))
        rows = [["Date", "Symbol", "Side", "Entry (UTC)", "Entry", "Stop", "Exit (UTC)", "Exit reason", "Spread", "R"]]
        for t in trades[:120]:
            rows.append([t["date"], t["symbol"], t["direction"], t["entry_timestamp"][11:16], f"{t['entry_price']:.5f}", f"{t['stop_price']:.5f}",
                         t["exit_timestamp"][5:16].replace("T", " "), t["exit_reason"].replace("_", " ").lower(), f"{t['spread_pips']:.1f}", _r(t["r_multiple"])])
        story.append(_table(rows, font_size=7))
        if len(trades) > 120:
            story.append(Paragraph(f"… {len(trades) - 120} more trades in the CSV export.", styles["small"]))
    return story


def _summary_rows(summaries: dict[str, dict[str, Any]]) -> list[list[Any]]:
    rows = [["Period", "Trades", "Expectancy", "Total", "Win rate", "PF", "Max DD", "Sharpe (ann.)"]]
    for name, s in summaries.items():
        rows.append([name, s.get("trades"), _r(s.get("expectancy_r")), _r(s.get("total_r")), _pct(s.get("win_rate")), _num(s.get("profit_factor")), _r(s.get("max_drawdown_r")), _num(s.get("annualized_sharpe"))])
    return rows


def _research_sections(result: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    story: list[Any] = []
    story.append(PageBreak())
    story.append(Paragraph("Research protocol", styles["h1"]))
    story.append(Paragraph("Fixed-rule baseline evaluated on independent periods, rolling out-of-sample folds, a bootstrap of the trade sequence, "
                           "one-at-a-time parameter variations and random entries that pay the same costs. Only out-of-sample figures may be quoted, "
                           "always next to the random-benchmark percentile and the sensitivity table.", styles["body"]))
    story.append(Paragraph("Baseline", styles["h2"]))
    story.append(_table(_summary_rows({"full sample": result.get("baseline", {})}), zebra=False))
    splits = result.get("splits")
    if splits:
        story.append(Paragraph("Independent chronological periods", styles["h2"]))
        story.append(_table(_summary_rows(splits["results"])))
        story.append(Paragraph(splits.get("note", ""), styles["small"]))
    wf = result.get("walk_forward")
    if wf:
        story.append(Paragraph("Rolling out-of-sample (walk-forward)", styles["h2"]))
        c = wf["out_of_sample_concatenated"]
        story.append(Paragraph(f"{wf['fold_count']} folds · train {wf['parameters']['train_days']} d, test {wf['parameters']['test_days']} d. Concatenated OOS: {c['trades']} trades, "
                               f"{_r(c['total_r'])}, expectancy {_r(c['expectancy_r'])}, {c['folds_positive']}/{c['folds_with_trades']} folds positive.", styles["body"]))
        rows = {f"fold {f['fold']} OOS": f["out_of_sample"] for f in wf["folds"]}
        story.append(_table(_summary_rows(rows), font_size=7.5))
    mc = result.get("monte_carlo")
    if mc and mc.get("trades_per_path"):
        story.append(Paragraph("Monte Carlo (trade-sequence bootstrap)", styles["h2"]))
        story.append(_table([["Paths", "Trades / path", "p(losing)", "Final R p5", "p50", "p95", "Max DD p50", "Max DD p95"],
                             [mc["simulations"], mc["trades_per_path"], _pct(mc.get("probability_losing")), _r(mc["final_r_percentiles"].get("5")), _r(mc["final_r_percentiles"].get("50")),
                              _r(mc["final_r_percentiles"].get("95")), _r(mc["max_drawdown_r_percentiles"].get("50")), _r(mc["max_drawdown_r_percentiles"].get("95"))]], zebra=False))
    bench = result.get("benchmark")
    if bench and bench.get("random_expectancy_percentiles"):
        story.append(Paragraph("Cost-matched random benchmark", styles["h2"]))
        story.append(Paragraph(f"Baseline expectancy {_r(bench.get('baseline_expectancy_r'))} sits at percentile {bench.get('baseline_percentile_vs_random', 0) * 100:.0f} of {bench['simulations']} "
                               f"simulations of random entries with identical stop distance, target, costs and session expiry (random median {_r(bench['random_expectancy_percentiles'].get('50'))}/trade). "
                               "Below the 95th percentile the result is indistinguishable from random timing.", styles["body"]))
    sens = result.get("sensitivity")
    if sens:
        story.append(Paragraph("Parameter sensitivity (one change at a time)", styles["h2"]))
        rows = [["Parameter", "Value", "Trades", "Expectancy", "Total", "Max DD"]]
        b = sens["baseline"]
        rows.append(["baseline", "—", b.get("trades"), _r(b.get("expectancy_r")), _r(b.get("total_r")), _r(b.get("max_drawdown_r"))])
        for v in sens["variants"]:
            rows.append([f"{v.get('scope')}:{v.get('parameter')}", str(v.get("value")), v.get("trades", "—"), _r(v.get("expectancy_r")), _r(v.get("total_r")), _r(v.get("max_drawdown_r")) if v.get("error") is None else v["error"][:40]])
        story.append(_table(rows, font_size=7.5, widths=[60 * mm, 32 * mm, 18 * mm, 22 * mm, 22 * mm, 22 * mm]))
        story.append(Paragraph(sens.get("note", ""), styles["small"]))
    return story
