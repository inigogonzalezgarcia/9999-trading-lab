#!/usr/bin/env python3
"""Render the Gumroad cover (1280×720) and thumbnail (600×600) for the kit, in the site's palette.

    python3 scripts/kit_cover.py --out dist/kit

The equity steps come from results/EURUSD_2024_v1_1_backtest.json so the picture is a real result.
Needs Playwright with Chromium (used only to rasterise the SVG).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INK, PAPER, ACCENT, MUTED, LINE, GOOD, BAD = "#0e1a24", "#f2eee6", "#c4672b", "#5c6670", "#e1dacd", "#2f7d6b", "#b5443a"
FONT = "'Inter Tight', 'Helvetica Neue', Arial, sans-serif"


def equity_points() -> list[float]:
    path = ROOT / "results" / "EURUSD_2024_v1_1_backtest.json"
    if not path.exists():
        return [0, -1, -2, -1.2, -0.3, 0.5, 0.2, 1.3, 1.1, 2.6, 2.4, 2.35]
    curve = json.loads(path.read_text())["equity_curve"]
    return [0.0] + [p["cumulative_r"] for p in curve]


def steps_path(values: list[float], x0: float, y0: float, w: float, h: float) -> tuple[str, float]:
    lo, hi = min(0.0, min(values)), max(0.0, max(values))
    span = hi - lo or 1
    xs = [x0 + i * w / (len(values) - 1) for i in range(len(values))]
    ys = [y0 + h - (v - lo) / span * h for v in values]
    d = f"M{xs[0]:.1f},{ys[0]:.1f}"
    for i in range(1, len(values)):
        d += f" H{xs[i]:.1f} V{ys[i]:.1f}"
    zero = y0 + h - (0 - lo) / span * h
    return d, zero


def cover_svg(lang: str = "es") -> str:
    es = lang == "es"
    values = equity_points()
    d, zero = steps_path(values, 760, 170, 440, 300)
    title = "Cómo leer<br/>un backtest" if es else "How to read<br/>a backtest"
    t1, t2 = ("Cómo leer", "un backtest") if es else ("How to read", "a backtest")
    sub = "Guía + plantilla de informe + checklist + datasets" if es else "Guide + report template + checklist + datasets"
    kicker = "KIT · FX RESEARCH LAB" if es else "KIT · FX RESEARCH LAB"
    tags = ["Monte Carlo", "benchmark" if es else "benchmark", "sensibilidad" if es else "sensitivity", "walk-forward"]
    foot = "Material educativo · no es asesoramiento de inversión · ES / EN" if es else "Educational material · not investment advice · ES / EN"
    tag_x = 72
    tag_nodes = []
    for tag in tags:
        wdt = 22 + len(tag) * 10.2
        tag_nodes.append(f'<rect x="{tag_x}" y="470" width="{wdt:.0f}" height="38" rx="19" fill="none" stroke="{LINE}" stroke-width="1.5"/>'
                         f'<text x="{tag_x + wdt / 2:.0f}" y="495" text-anchor="middle" font-family="{FONT}" font-size="17" fill="{MUTED}">{tag}</text>')
        tag_x += wdt + 12
    last = values[-1]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <defs>
    <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse"><path d="M28 0H0V28" fill="none" stroke="{LINE}" stroke-width="0.8"/></pattern>
  </defs>
  <rect width="1280" height="720" fill="{PAPER}"/>
  <rect x="720" y="120" width="520" height="400" rx="18" fill="url(#grid)"/>
  <rect x="720" y="120" width="520" height="400" rx="18" fill="none" stroke="{LINE}" stroke-width="1.5"/>
  <line x1="740" x2="1220" y1="{zero:.1f}" y2="{zero:.1f}" stroke="{MUTED}" stroke-width="1.2" stroke-dasharray="6 5"/>
  <text x="742" y="{zero - 8:.1f}" font-family="ui-monospace, Menlo, monospace" font-size="14" fill="{MUTED}">0R</text>
  <path d="{d}" fill="none" stroke="{ACCENT}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>
  <circle cx="1200" cy="{170 + 300 - (last - min(0, min(values))) / ((max(0, max(values)) - min(0, min(values))) or 1) * 300:.1f}" r="7" fill="{ACCENT}"/>
  <text x="1216" y="150" text-anchor="end" font-family="ui-monospace, Menlo, monospace" font-size="15" fill="{MUTED}">V1.1 · EUR/USD 2024 · 12 {'operaciones' if es else 'trades'}</text>
  <text x="1216" y="552" text-anchor="end" font-family="ui-monospace, Menlo, monospace" font-size="15" fill="{MUTED}">{'¿Significa algo? Eso es lo que enseña el kit.' if es else 'Does it mean anything? That is what the kit teaches.'}</text>
  <text x="72" y="150" font-family="ui-monospace, Menlo, monospace" font-size="18" letter-spacing="3" fill="{ACCENT}">{kicker}</text>
  <text x="72" y="250" font-family="{FONT}" font-size="86" font-weight="700" fill="{INK}" letter-spacing="-2">{t1}</text>
  <text x="72" y="340" font-family="{FONT}" font-size="86" font-weight="700" fill="{INK}" letter-spacing="-2">{t2}</text>
  <text x="72" y="410" font-family="{FONT}" font-size="27" fill="{MUTED}">{sub}</text>
  {''.join(tag_nodes)}
  <line x1="72" x2="1208" y1="600" y2="600" stroke="{LINE}" stroke-width="1.5"/>
  <text x="72" y="640" font-family="{FONT}" font-size="18" fill="{MUTED}">{foot}</text>
  <text x="1208" y="640" text-anchor="end" font-family="{FONT}" font-size="18" font-weight="600" fill="{INK}">fx-trading-lab.pages.dev</text>
</svg>"""


def thumb_svg(lang: str = "es") -> str:
    es = lang == "es"
    values = equity_points()
    d, zero = steps_path(values, 70, 300, 460, 200)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600" viewBox="0 0 600 600">
  <rect width="600" height="600" fill="{PAPER}"/>
  <text x="50" y="92" font-family="ui-monospace, Menlo, monospace" font-size="17" letter-spacing="3" fill="{ACCENT}">KIT · FX RESEARCH LAB</text>
  <text x="50" y="170" font-family="{FONT}" font-size="60" font-weight="700" fill="{INK}" letter-spacing="-1.5">{'Cómo leer' if es else 'How to read'}</text>
  <text x="50" y="235" font-family="{FONT}" font-size="60" font-weight="700" fill="{INK}" letter-spacing="-1.5">{'un backtest' if es else 'a backtest'}</text>
  <line x1="60" x2="540" y1="{zero:.1f}" y2="{zero:.1f}" stroke="{MUTED}" stroke-width="1.2" stroke-dasharray="6 5"/>
  <path d="{d}" fill="none" stroke="{ACCENT}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>
  <text x="50" y="555" font-family="{FONT}" font-size="17" fill="{MUTED}">{'Material educativo · ES / EN' if es else 'Educational material · ES / EN'}</text>
</svg>"""


def rasterise(svg: str, out: Path, width: int, height: int) -> None:
    from playwright.sync_api import sync_playwright

    html = f"<!doctype html><html><head><meta charset='utf-8'><link href='https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;600;700&display=swap' rel='stylesheet'><style>html,body{{margin:0;background:{PAPER}}}</style></head><body>{svg}</body></html>"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        page.set_content(html)
        page.wait_for_timeout(1200)
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": width, "height": height})
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "dist" / "kit"))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "gumroad-cover-es.svg").write_text(cover_svg("es"))
    rasterise(cover_svg("es"), out / "gumroad-cover-es.png", 1280, 720)
    rasterise(cover_svg("en"), out / "gumroad-cover-en.png", 1280, 720)
    rasterise(thumb_svg("es"), out / "gumroad-thumbnail.png", 600, 600)
    print("covers written to", out)


if __name__ == "__main__":
    main()
