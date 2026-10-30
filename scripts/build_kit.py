#!/usr/bin/env python3
"""Build the paid kit "Cómo leer un backtest" from the lab's own results.

Output (default ``dist/kit``):

    kit-como-leer-un-backtest/
      LEEME.txt · README.txt
      01-guia/   guia-como-leer-un-backtest-ES.pdf · guide-how-to-read-a-backtest-EN.pdf
      02-plantilla/  plantilla-informe-backtest-ES.md · backtest-report-template-EN.md (+ PDF)
      03-checklist/  checklist-decision-ES.md · decision-checklist-EN.md
      04-datasets/   <run>/trades.csv · equity_curve.csv · metrics.json · sensitivity.csv · monte_carlo.json
                     SHA256SUMS.txt · COMO-DESCARGAR-DATOS.md
    kit-como-leer-un-backtest.zip

Usage (from the repo root):

    python3 scripts/build_kit.py                       # uses results/*.json
    python3 scripts/build_kit.py --out dist/kit --results results

Everything in the guide is computed from the result files, so the numbers in the text are the
numbers in the datasets. The guide never claims an edge: it teaches how to check for one.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer  # noqa: E402

from app.report import ACCENT, BAD, GOOD, INK, LINE, MUTED, _bar_chart, _line_chart, _styles, _table  # noqa: E402

KIT_VERSION = "1.0"
SITE = "https://fx-trading-lab.pages.dev"
REPO = "https://github.com/inigogonzalezgarcia/9999-trading-lab"
DISCLAIMER_URL = f"{SITE}/legal/aviso"


# --------------------------------------------------------------------------- data


def load_results(results_dir: Path) -> dict[str, dict[str, Any]]:
    """Pick the runs the guide is written around: V1 and V1.1 on EUR/USD 2024, backtest + research."""
    runs: dict[str, dict[str, Any]] = {}
    for name, candidates in {
        "v1_backtest": ["EURUSD_2024_backtest.json", "EURUSD_2024_v1_backtest.json"],
        "v1_research": ["EURUSD_2024_research.json", "EURUSD_2024_v1_research.json"],
        "v1_1_backtest": ["EURUSD_2024_v1_1_backtest.json"],
        "v1_1_research": ["EURUSD_2024_v1_1_research.json"],
    }.items():
        for candidate in candidates:
            path = results_dir / candidate
            if path.exists():
                runs[name] = json.loads(path.read_text())
                break
    missing = [k for k in ("v1_research", "v1_1_backtest", "v1_1_research") if k not in runs]
    if missing:
        raise SystemExit(f"missing result files for {missing} in {results_dir}")
    return runs


def r(value: Any, digits: int = 2) -> str:
    return "—" if value is None else f"{float(value):+.{digits}f}R"


def num(value: Any, digits: int = 2) -> str:
    return "—" if value is None else f"{float(value):.{digits}f}"


def pct(value: Any) -> str:
    return "—" if value is None else f"{float(value) * 100:.0f} %"


def baseline(research: dict[str, Any]) -> dict[str, Any]:
    return research["baseline"]


def sensitivity_rows(research: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for v in research["sensitivity"]["variants"]:
        if v.get("error"):
            continue
        rows.append({"parameter": v["parameter"], "value": str(v["value"]), "trades": v["trades"], "total_r": v["total_r"], "expectancy_r": v["expectancy_r"], "win_rate": v["win_rate"], "max_drawdown_r": v["max_drawdown_r"]})
    return rows


# --------------------------------------------------------------------------- text (ES / EN)

L = dict[str, str]


def T(es: str, en: str) -> L:
    return {"es": es, "en": en}


def guide_content(runs: dict[str, dict[str, Any]], lang: str) -> list[tuple[str, Any]]:
    """Return the guide as a list of (kind, payload) blocks. kind: title, h1, h2, p, bullets, table, chart, notice, pagebreak."""
    v1 = baseline(runs["v1_research"])
    v11 = baseline(runs["v1_1_research"])
    bt = runs["v1_1_backtest"]
    m = bt["metrics"]
    mc1, mc11 = runs["v1_research"]["monte_carlo"], runs["v1_1_research"]["monte_carlo"]
    bm1, bm11 = runs["v1_research"]["benchmark"], runs["v1_1_research"]["benchmark"]
    wf1, wf11 = runs["v1_research"]["walk_forward"]["out_of_sample_concatenated"], runs["v1_1_research"]["walk_forward"]["out_of_sample_concatenated"]
    sp11 = runs["v1_1_research"]["splits"]["results"]
    sens = sensitivity_rows(runs["v1_1_research"])
    repro = bt["reproducibility"]
    es = lang == "es"
    t = lambda a, b: a if es else b  # noqa: E731

    def tr(name: str, value: Any) -> Any:
        return value

    equity = [(i + 1, p["cumulative_r"]) for i, p in enumerate(bt["equity_curve"])]
    equity_points = [(0, 0.0)] + equity

    blocks: list[tuple[str, Any]] = []
    A = blocks.append

    # ------------------------------------------------------------------ cover
    A(("title", t("Cómo leer un backtest", "How to read a backtest")))
    A(("subtitle", t(f"Guía práctica con datos reales · FX Research Lab · kit v{KIT_VERSION} · generada {datetime.now(timezone.utc):%Y-%m-%d}",
                     f"A practical guide on real data · FX Research Lab · kit v{KIT_VERSION} · generated {datetime.now(timezone.utc):%Y-%m-%d}")))
    A(("notice", t("Material educativo. No es asesoramiento de inversión ni una recomendación de operar. Todos los números son resultados simulados sobre datos históricos; "
                   "el rendimiento pasado no garantiza resultados futuros. Las hipótesis que aparecen aquí no han demostrado ninguna ventaja; se usan precisamente para enseñar a comprobarlo. "
                   f"Aviso completo: {DISCLAIMER_URL}",
                   "Educational material. Not investment advice nor a recommendation to trade. Every number is a simulated result on historical data; past performance does not guarantee "
                   f"future results. The hypotheses shown here have demonstrated no edge; they are used precisely to teach how to check for one. Full notice: {DISCLAIMER_URL}")))
    A(("p", t("Esta guía usa dos versiones de una misma hipótesis intradía sobre EUR/USD durante 2024, V1 y V1.1, ejecutadas con el mismo motor, los mismos datos y los mismos costes. "
              "Una perdió. La otra ganó un poco. La pregunta de todo el documento es si esa diferencia significa algo, y cómo lo sabrías.",
              "This guide uses two versions of the same intraday hypothesis on EUR/USD during 2024, V1 and V1.1, run with the same engine, the same data and the same costs. "
              "One lost. The other won a little. The question running through the whole document is whether that difference means anything, and how you would know.")))
    A(("h2", t("Qué hay en el kit", "What is in the kit")))
    A(("bullets", [
        t("01 · Esta guía (ES y EN).", "01 · This guide (ES and EN)."),
        t("02 · Plantilla de informe de backtest, en Markdown y PDF, con las secciones que usamos en el laboratorio.", "02 · Backtest report template, Markdown and PDF, with the sections we use in the lab."),
        t("03 · Checklist de decisión: las preguntas que pasamos antes de creernos un número.", "03 · Decision checklist: the questions we go through before believing a number."),
        t("04 · Datasets: operaciones, curva de capital, métricas, sensibilidad y Monte Carlo de cada ejecución, con su SHA-256, más las instrucciones para descargar las velas M1 originales y reproducirlo todo.",
          "04 · Datasets: trades, equity curve, metrics, sensitivity and Monte Carlo for each run, with their SHA-256, plus the instructions to download the original M1 candles and reproduce everything."),
    ]))
    A(("h2", t("Cómo usarla", "How to use it")))
    A(("p", t("Léela una vez de corrido (unos 40 minutos). Después, abre el laboratorio en el navegador, elige una ejecución y vuelve a recorrer los capítulos 2 a 8 con la pantalla delante: cada capítulo te dice exactamente qué mirar. "
              "Cuando quieras evaluar un backtest ajeno, usa la checklist del capítulo 9; cuando quieras documentar uno propio, usa la plantilla.",
              "Read it once straight through (about 40 minutes). Then open the lab in your browser, pick a run and go through chapters 2 to 8 again with the screen in front of you: each chapter tells you exactly what to look at. "
              "To evaluate someone else's backtest, use the checklist in chapter 9; to document your own, use the template.")))

    # ------------------------------------------------------------------ 1
    A(("h1", t("1. Qué es un backtest honesto (y qué no)", "1. What an honest backtest is (and is not)")))
    A(("p", t("Un backtest es una simulación: coges unas reglas, las aplicas a datos del pasado y apuntas qué habría pasado. Es barato, rápido y por eso mismo peligroso: el ordenador te da un número con dos decimales aunque el procedimiento esté roto. "
              "Un backtest honesto cumple cuatro condiciones, y si falla una, el número no vale nada.",
              "A backtest is a simulation: you take some rules, apply them to past data and write down what would have happened. It is cheap, fast and for that very reason dangerous: the computer gives you a number with two decimals even when the procedure is broken. "
              "An honest backtest meets four conditions, and if one fails, the number is worthless.")))
    A(("bullets", [
        t("<b>Causalidad.</b> En cada instante el motor solo sabe lo que ya ha cerrado. Una vela M15 no existe hasta las 09:15:00; la decisión se toma entonces y la ejecución ocurre al siguiente precio disponible, nunca al mismo.",
          "<b>Causality.</b> At every instant the engine only knows what has already closed. A 09:00 M15 candle does not exist until 09:15:00; the decision is made then and execution happens at the next available price, never the same one."),
        t("<b>Costes en cada operación.</b> Spread (el del proveedor si existe, si no uno fijo), deslizamiento y comisión. Sin costes, casi cualquier regla intradía parece rentable.",
          "<b>Costs on every trade.</b> Spread (the provider's when available, otherwise a fixed one), slippage and commission. Without costs almost any intraday rule looks profitable."),
        t("<b>Hipótesis congelada.</b> Las reglas viven en un fichero con su hash. Cambiar una regla es crear otra versión (V1.1), no retocar V1 hasta que el número guste.",
          "<b>Frozen hypothesis.</b> The rules live in a file with its hash. Changing a rule means creating another version (V1.1), not nudging V1 until the number looks nice."),
        t("<b>Reproducibilidad.</b> Hash del dataset, versión de la estrategia, configuración de ejecución, semilla, versión del software. Si otra persona no puede obtener el mismo número, no es un resultado: es una anécdota.",
          "<b>Reproducibility.</b> Dataset hash, strategy version, execution configuration, seed, software version. If someone else cannot obtain the same number, it is not a result: it is an anecdote."),
    ]))
    A(("p", t("Las dos ejecuciones de esta guía cumplen las cuatro. Por eso sus números se pueden discutir. Lo que viene a continuación es la discusión.",
              "Both runs in this guide meet all four. That is why their numbers can be discussed. What follows is the discussion.")))
    A(("table", {"rows": [[t("Campo", "Field"), t("Valor (V1.1, EUR/USD 2024)", "Value (V1.1, EUR/USD 2024)")],
                          [t("Hash del dataset (SHA-256)", "Dataset hash (SHA-256)"), repro["dataset_hash"]],
                          [t("Hash de la configuración", "Configuration hash"), repro["config_hash"]],
                          [t("Modelo de ejecución", "Execution model"), str(repro.get("execution_model", "—"))],
                          [t("Deslizamiento", "Slippage"), f"{(repro.get('slippage_model') or {}).get('baseline_pips', '—')} pips"],
                          [t("Software", "Software"), f"{repro.get('software_version', '—')} · {repro.get('software_revision', '—')}"]],
                 "widths": [45 * mm, 125 * mm], "font": 7.5}))

    # ------------------------------------------------------------------ 2
    A(("h1", t("2. Las cinco cifras que importan", "2. The five numbers that matter")))
    A(("p", t("Un resumen de backtest suele traer veinte métricas. Cinco bastan para la primera lectura, y conviene mirarlas siempre en este orden.",
              "A backtest summary usually comes with twenty metrics. Five are enough for the first reading, and it pays to always look at them in this order.")))
    A(("table", {"rows": [[t("Métrica", "Metric"), "V1", "V1.1", t("Qué te dice", "What it tells you")],
                          [t("Operaciones (N)", "Trades (N)"), str(v1["trades"]), str(v11["trades"]), t("Cuánta evidencia hay. Todo lo demás se lee a la luz de N.", "How much evidence there is. Everything else is read in the light of N.")],
                          [t("Esperanza (R por operación)", "Expectancy (R per trade)"), r(v1["expectancy_r"]), r(v11["expectancy_r"]), t("Lo que gana o pierde, de media, cada vez que arriesga 1R.", "What it wins or loses, on average, each time it risks 1R.")],
                          [t("Acierto", "Win rate"), pct(v1["win_rate"]), pct(v11["win_rate"]), t("Solo tiene sentido junto al ratio ganancia/pérdida.", "Only meaningful next to the payoff ratio.")],
                          [t("Factor de beneficio", "Profit factor"), num(v1["profit_factor"]), num(v11["profit_factor"]), t("Ganancia bruta / pérdida bruta. Por debajo de 1 pierde dinero.", "Gross profit / gross loss. Below 1 it loses money.")],
                          [t("Drawdown máximo (R)", "Max drawdown (R)"), num(v1["max_drawdown_r"]), num(v11["max_drawdown_r"]), t("La peor racha, medida en unidades de riesgo, no en euros.", "The worst run, measured in risk units, not in euros.")]],
                 "widths": [40 * mm, 18 * mm, 18 * mm, 94 * mm]}))
    A(("h2", t("Por qué todo está en R", "Why everything is in R")))
    A(("p", t("R es la distancia al stop de cada operación. Ganar +1,8R significa haber ganado 1,8 veces lo que arriesgaste en esa operación; perder -1R es perder exactamente el riesgo previsto. "
              "Medir en R hace comparables operaciones con stops distintos y quita del medio el tamaño de la cuenta y el apalancamiento, que son decisiones de otro nivel. "
              "Cuando un backtest te enseña porcentajes de rentabilidad anual, pide los R: un +40 % puede ser +4R con un 10 % de riesgo por operación, es decir, una cuenta que habría saltado por los aires en la primera mala racha.",
              "R is the distance to the stop on each trade. Winning +1.8R means you made 1.8 times what you risked on that trade; losing -1R is losing exactly the planned risk. "
              "Measuring in R makes trades with different stops comparable and takes account size and leverage, which are decisions at another level, out of the way. "
              "When a backtest shows you annual return percentages, ask for the R: a +40 % may be +4R at 10 % risk per trade, i.e. an account that would have blown up in the first bad streak.")))
    A(("h2", t("Acierto y ratio ganancia/pérdida van juntos", "Win rate and payoff go together")))
    A(("p", t(f"V1.1 acierta el {pct(m['win_rate'])} de las veces. Suena mal hasta que ves que la ganancia media es {r(m['average_win_r'])} y la pérdida media {r(m['average_loss_r'])}: "
              f"un ratio de {num(m['payoff_ratio'])}. Con ese ratio, basta acertar un 32 % para no perder. La pérdida media es menor que 1R porque {m['exit_reasons'].get('SESSION_EXPIRY', 0)} de las {m['total_trades']} operaciones "
              "se cerraron por fin de sesión, no por stop: el motor no deja operaciones abiertas de un día para otro, y eso corta pérdidas pero también ganancias.",
              f"V1.1 wins {pct(m['win_rate'])} of the time. That sounds bad until you see the average win is {r(m['average_win_r'])} and the average loss {r(m['average_loss_r'])}: "
              f"a payoff ratio of {num(m['payoff_ratio'])}. With that ratio, winning 32 % is enough to break even. The average loss is smaller than 1R because {m['exit_reasons'].get('SESSION_EXPIRY', 0)} of the {m['total_trades']} trades "
              "were closed at session end, not at the stop: the engine never holds a trade overnight, which cuts losses but also cuts gains.")))
    A(("table", {"rows": [[t("Motivo de salida", "Exit reason"), t("Operaciones", "Trades")]] + [[k.replace("_", " ").lower(), str(v)] for k, v in sorted(m["exit_reasons"].items())], "widths": [60 * mm, 30 * mm]}))

    # ------------------------------------------------------------------ 3
    A(("h1", t("3. La curva de capital: qué mirar", "3. The equity curve: what to look at")))
    A(("chart", {"kind": "line", "points": equity_points, "title": t("V1.1 · R acumulado por operación (EUR/USD 2024)", "V1.1 · cumulative R per trade (EUR/USD 2024)")}))
    A(("p", t("La curva de capital es la métrica más mirada y la peor leída. Tres cosas antes de sacar conclusiones:",
              "The equity curve is the most looked-at metric and the worst read. Three things before drawing conclusions:")))
    A(("bullets", [
        t("<b>El eje X son operaciones, no tiempo.</b> Doce escalones en doce meses. Si la curva fuera por fecha verías once meses de línea plana y un par de saltos. Ambas vistas son verdad; la segunda es más honesta sobre cuánto tiempo pasas sin hacer nada.",
          "<b>The X axis is trades, not time.</b> Twelve steps across twelve months. On a date axis you would see eleven months of flat line and a couple of jumps. Both views are true; the second is more honest about how long you spend doing nothing."),
        t(f"<b>Dónde está el drawdown.</b> El máximo ({num(m['max_drawdown_r'])}R) ocurre con {m['max_consecutive_losses']} pérdidas seguidas. Con N = 12 eso no es una racha rara: es lo normal, como verás en el capítulo 4.",
          f"<b>Where the drawdown is.</b> The maximum ({num(m['max_drawdown_r'])}R) comes with {m['max_consecutive_losses']} consecutive losses. With N = 12 that is not a rare streak: it is the norm, as chapter 4 shows."),
        t("<b>Cuántas operaciones explican el resultado.</b> Quita la mejor operación y vuelve a sumar. Si el total cambia de signo, el resultado depende de un día concreto.",
          "<b>How many trades explain the result.</b> Remove the best trade and add up again. If the total changes sign, the result depends on one particular day."),
    ]))
    best = max(bt["trades"], key=lambda x: x["r_multiple"])
    A(("p", t(f"Hagamos lo último con V1.1: la mejor operación fue {r(best['r_multiple'])} el {best['date']}. Sin ella, el total pasa de {r(m['total_r'])} a {r(m['total_r'] - best['r_multiple'])}. "
              "Una sola operación cambia el signo del año. Apúntalo: es el dato más importante de todo el informe, y no aparece en ninguna tabla de métricas.",
              f"Let us do the last one with V1.1: the best trade was {r(best['r_multiple'])} on {best['date']}. Without it the total goes from {r(m['total_r'])} to {r(m['total_r'] - best['r_multiple'])}. "
              "A single trade flips the sign of the year. Write that down: it is the most important fact in the whole report, and it appears in no metrics table.")))

    # ------------------------------------------------------------------ 4
    A(("h1", t("4. Doce operaciones no demuestran nada: Monte Carlo", "4. Twelve trades prove nothing: Monte Carlo")))
    A(("p", t("Si barajas el orden de las doce operaciones de V1.1 obtienes el mismo total pero drawdowns distintos. Si en vez de barajar remuestreas (coges doce operaciones al azar de las doce, con repetición) obtienes totales distintos. "
              "Hazlo mil veces y tendrás una distribución de lo que la misma estrategia podría haber dado con la misma suerte y otra secuencia. Eso es un Monte Carlo, y su lectura es esta tabla.",
              "If you shuffle the order of V1.1's twelve trades you get the same total but different drawdowns. If instead of shuffling you resample (draw twelve trades at random from the twelve, with replacement) you get different totals. "
              "Do it a thousand times and you have a distribution of what the same strategy could have produced with the same luck and another sequence. That is a Monte Carlo, and this table is how to read it.")))
    A(("table", {"rows": [[t("Percentil", "Percentile"), t("R final · V1", "Final R · V1"), t("R final · V1.1", "Final R · V1.1"), t("Drawdown máx. · V1.1", "Max drawdown · V1.1")]]
                         + [[f"P{p}", r(mc1["final_r_percentiles"][p]), r(mc11["final_r_percentiles"][p]), num(mc11["max_drawdown_r_percentiles"][p]) + "R"] for p in ("5", "25", "50", "75", "95")]
                         + [[t("Observado", "Observed"), r(mc1["observed"]["final_r"]), r(mc11["observed"]["final_r"]), num(mc11["observed"]["max_drawdown_r"]) + "R"],
                            [t("Prob. de acabar en pérdidas", "Probability of ending negative"), pct(mc1["probability_losing"]), pct(mc11["probability_losing"]), ""]],
                 "widths": [50 * mm, 35 * mm, 35 * mm, 45 * mm]}))
    A(("p", t(f"Lee la columna de V1.1: entre P5 y P95 el resultado va de {r(mc11['final_r_percentiles']['5'])} a {r(mc11['final_r_percentiles']['95'])}. Esa es la anchura de lo que no sabes. "
              f"Una estrategia que ganó {r(v11['total_r'])} en 2024 tenía un {pct(mc11['probability_losing'])} de probabilidad de acabar el año en negativo con las mismas operaciones en otro orden o con una muestra parecida. "
              f"V1 es el caso contrario: {pct(mc1['probability_losing'])} de probabilidad de perder. Ahí el Monte Carlo no te dice que V1 sea mala; te dice que, con cinco operaciones, casi cualquier cosa es compatible con lo observado.",
              f"Read the V1.1 column: between P5 and P95 the outcome runs from {r(mc11['final_r_percentiles']['5'])} to {r(mc11['final_r_percentiles']['95'])}. That is the width of what you do not know. "
              f"A strategy that made {r(v11['total_r'])} in 2024 had a {pct(mc11['probability_losing'])} chance of ending the year negative with the same trades in another order or a similar sample. "
              f"V1 is the opposite case: {pct(mc1['probability_losing'])} probability of losing. There the Monte Carlo does not tell you V1 is bad; it tells you that, with five trades, almost anything is compatible with what was observed.")))
    A(("p", t("<b>Regla práctica.</b> Si P25 está por debajo de cero, el backtest no ha demostrado nada todavía, gane lo que gane el caso observado. Y la anchura entre P5 y P95 solo se estrecha con más operaciones: no con más métricas, no con más gráficos.",
              "<b>Rule of thumb.</b> If P25 is below zero, the backtest has not shown anything yet, whatever the observed case made. And the width between P5 and P95 only narrows with more trades: not with more metrics, not with more charts.")))

    # ------------------------------------------------------------------ 5
    A(("h1", t("5. ¿Lo haría igual el azar? El benchmark aleatorio", "5. Would chance do the same? The random benchmark")))
    A(("p", t("La pregunta más incómoda: ¿qué habría pasado entrando al azar dentro de las mismas ventanas horarias, con el mismo stop, el mismo objetivo, los mismos costes y la misma salida por fin de sesión? "
              "El laboratorio lo simula 200 veces. Si la estrategia no bate claramente a esas entradas aleatorias, lo que estás viendo es el comportamiento del mercado en esa hora, no la regla.",
              "The most uncomfortable question: what would have happened entering at random inside the same time windows, with the same stop, the same target, the same costs and the same session-end exit? "
              "The lab simulates it 200 times. If the strategy does not clearly beat those random entries, what you are looking at is the market's behaviour at that hour, not the rule.")))
    A(("table", {"rows": [["", "V1", "V1.1"],
                          [t("Esperanza de la estrategia", "Strategy expectancy"), r(bm1["baseline_expectancy_r"]), r(bm11["baseline_expectancy_r"])],
                          [t("Esperanza aleatoria · P50", "Random expectancy · P50"), r(bm1["random_expectancy_percentiles"]["50"]), r(bm11["random_expectancy_percentiles"]["50"])],
                          [t("Esperanza aleatoria · P95", "Random expectancy · P95"), r(bm1["random_expectancy_percentiles"]["95"]), r(bm11["random_expectancy_percentiles"]["95"])],
                          [t("Percentil de la estrategia frente al azar", "Strategy percentile vs random"), num(bm1["baseline_percentile_vs_random"] * 100, 0) + " %", num(bm11["baseline_percentile_vs_random"] * 100, 0) + " %"],
                          [t("p-valor empírico (una cola)", "Empirical p-value (one-sided)"), num(bm1["empirical_p_value_one_sided"]), num(bm11["empirical_p_value_one_sided"])]],
                 "widths": [80 * mm, 40 * mm, 40 * mm]}))
    A(("p", t(f"V1.1 queda en el percentil {num(bm11['baseline_percentile_vs_random'] * 100, 0)} de las entradas aleatorias: mejor que tres de cada cuatro, peor que una de cada cuatro. Un p-valor de {num(bm11['empirical_p_value_one_sided'])} significa que una de cada cuatro estrategias que entran al azar lo habría hecho igual de bien. "
              "Nadie publicaría eso como evidencia en ningún campo serio. La barra habitual (p < 0,05) exigiría estar por encima del 95 % de las entradas aleatorias, y aun así con N = 12 habría que repetirlo en otro año.",
              f"V1.1 sits at the {num(bm11['baseline_percentile_vs_random'] * 100, 0)}th percentile of random entries: better than three out of four, worse than one in four. A p-value of {num(bm11['empirical_p_value_one_sided'])} means one in four strategies entering at random would have done just as well. "
              "Nobody would publish that as evidence in any serious field. The usual bar (p < 0.05) would require beating 95 % of random entries, and even then with N = 12 it would need repeating in another year.")))
    A(("p", t("<b>Lo que sí aprendes aquí.</b> La esperanza aleatoria mediana es negativa en las dos versiones: entrar al azar en la apertura de Londres con esos costes pierde dinero. Es la línea base contra la que hay que medir cualquier regla; sin ella, un +0,19R parece mucho y no sabes respecto a qué.",
              "<b>What you do learn here.</b> The median random expectancy is negative in both versions: entering at random at the London open with those costs loses money. That is the baseline any rule must be measured against; without it, +0.19R looks like a lot and you do not know relative to what.")))

    # ------------------------------------------------------------------ 6
    A(("h1", t("6. Fragilidad: la prueba de sensibilidad", "6. Fragility: the sensitivity test")))
    A(("p", t("Una regla robusta se parece a sí misma cuando mueves un parámetro un poco. Una regla frágil cambia de signo. El laboratorio reejecuta la hipótesis variando un parámetro cada vez y deja el resto fijo. Así queda V1.1:",
              "A robust rule looks like itself when you move a parameter a little. A fragile rule flips sign. The lab re-runs the hypothesis changing one parameter at a time and keeping the rest fixed. This is V1.1:")))
    sens_rows = [[t("Parámetro", "Parameter"), t("Valor", "Value"), "N", t("Total R", "Total R"), t("Esperanza", "Expectancy")]] + [[s["parameter"], s["value"], str(s["trades"]), r(s["total_r"]), r(s["expectancy_r"])] for s in sens]
    A(("table", {"rows": sens_rows, "widths": [60 * mm, 32 * mm, 14 * mm, 28 * mm, 28 * mm], "font": 7.5}))
    key = [s for s in sens if s["parameter"] in ("stop.reference", "setup.lifetime_m15_bars_from_sweep_confirmation", "session", "stop.max_distance_atr")]
    short = {"stop.reference": "stop", "setup.lifetime_m15_bars_from_sweep_confirmation": "lifetime", "session": "session", "stop.max_distance_atr": "maxATR"}
    A(("chart", {"kind": "bar", "labels": [f"{short[s['parameter']]} {s['value'].split('_')[0][:8]}" for s in key], "values": [s["total_r"] for s in key],
                 "title": t("V1.1 · total R al cambiar un parámetro (el resto fijo)", "V1.1 · total R when one parameter changes (rest fixed)"), "fmt": "{:+.1f}R"}))
    A(("p", t("Cómo leer la tabla: busca las filas en las que el resultado cambia de signo o se multiplica.",
              "How to read the table: look for the rows where the result flips sign or multiplies.")))
    A(("bullets", [
        t("<b>stop.reference.</b> Con el stop en el extremo del barrido o en el origen del impulso, V1.1 pasa a ganar casi nada o a perder. El resultado positivo depende de una sola elección de stop. Es el hallazgo más importante de 2024 y por eso V1.1 existe (V1 usaba otro stop).",
          "<b>stop.reference.</b> With the stop at the sweep extreme or at the impulse origin, V1.1 makes almost nothing or loses. The positive result depends on a single stop choice. It is the most important finding of 2024 and the reason V1.1 exists (V1 used another stop)."),
        t("<b>setup.lifetime.</b> Seis velas de vida en vez de ocho: negativo. Doce: el doble. Un parámetro que no sale de ninguna teoría decide el signo.",
          "<b>setup.lifetime.</b> Six candles of lifetime instead of eight: negative. Twelve: double. A parameter that comes from no theory decides the sign."),
        t("<b>session.</b> La misma regla en la apertura de Nueva York pierde con claridad. No es una estrategia: es, como mucho, una observación sobre la apertura de Londres.",
          "<b>session.</b> The same rule at the New York open clearly loses. It is not a strategy: it is, at most, an observation about the London open."),
        t("<b>Lo que no cambia nada</b> (target, riesgo por operación, expiración de zonas) tampoco es buena señal: significa que esos parámetros casi nunca intervienen con doce operaciones.",
          "<b>What changes nothing</b> (target, risk per trade, zone expiry) is not good news either: it means those parameters almost never come into play with twelve trades."),
    ]))
    A(("p", t("Regla práctica: si al mover un parámetro un paso el total cambia de signo, apunta ese parámetro en el log de decisiones como <i>no resuelto</i> y no optimices sobre él. Optimizar un parámetro frágil con doce operaciones es ajustar ruido.",
              "Rule of thumb: if moving a parameter one step flips the sign of the total, log that parameter in the decision log as <i>unresolved</i> and do not optimise on it. Optimising a fragile parameter on twelve trades is fitting noise.")))

    # ------------------------------------------------------------------ 7
    A(("h1", t("7. Fuera de muestra: particiones y walk-forward", "7. Out of sample: splits and walk-forward")))
    A(("p", t("Todo lo anterior se calcula sobre el año completo, que es también el año en el que se diseñó la regla. La única manera de saber si una regla aguanta datos que no vio es reservar un tramo y no tocarlo hasta el final. "
              "El laboratorio hace dos cosas: una partición cronológica (entrenamiento, validación y fuera de muestra) y un walk-forward con ventanas rodantes.",
              "Everything above is computed on the full year, which is also the year the rule was designed on. The only way to know whether a rule holds on data it never saw is to set aside a stretch and not touch it until the end. "
              "The lab does two things: a chronological split (train, validation and out-of-sample) and a walk-forward with rolling windows.")))
    A(("table", {"rows": [[t("Tramo (V1.1)", "Segment (V1.1)"), t("Días", "Days"), "N", t("Total R", "Total R"), t("Esperanza", "Expectancy")]]
                         + [[k.replace("_", " "), str(v["trading_days"]), str(v["trades"]), r(v["total_r"]), r(v["expectancy_r"])] for k, v in sp11.items()],
                 "widths": [50 * mm, 20 * mm, 14 * mm, 30 * mm, 30 * mm]}))
    A(("table", {"rows": [[t("Walk-forward (fuera de muestra concatenado)", "Walk-forward (concatenated out-of-sample)"), "V1", "V1.1"],
                          [t("Operaciones", "Trades"), str(wf1["trades"]), str(wf11["trades"])],
                          [t("Total R", "Total R"), r(wf1["total_r"]), r(wf11["total_r"])],
                          [t("Ventanas con operaciones / positivas", "Windows with trades / positive"), f"{wf1['folds_with_trades']} / {wf1['folds_positive']}", f"{wf11['folds_with_trades']} / {wf11['folds_positive']}"],
                          [t("Consistencia", "Consistency"), pct(wf1["consistency"]), pct(wf11["consistency"])]],
                 "widths": [90 * mm, 35 * mm, 35 * mm]}))
    A(("p", t(f"El tramo fuera de muestra de V1.1 tiene {sp11['out_of_sample']['trades']} operación. Una. No se puede concluir nada, y eso es exactamente lo que hay que escribir en el informe. "
              f"El walk-forward da {wf11['trades']} operaciones fuera de muestra con {wf11['folds_positive']} ventanas positivas de {wf11['folds_with_trades']}: una moneda al aire. "
              "Una estrategia intradía con doce operaciones al año necesita varios años de datos solo para que la partición fuera de muestra tenga sentido. Es el motivo por el que el siguiente paso del laboratorio es 2022-2023, no otra métrica.",
              f"V1.1's out-of-sample segment has {sp11['out_of_sample']['trades']} trade. One. Nothing can be concluded, and that is exactly what must be written in the report. "
              f"The walk-forward yields {wf11['trades']} out-of-sample trades with {wf11['folds_positive']} positive windows out of {wf11['folds_with_trades']}: a coin toss. "
              "An intraday strategy with twelve trades a year needs several years of data just for the out-of-sample split to make sense. That is why the lab's next step is 2022-2023, not another metric.")))

    # ------------------------------------------------------------------ 8
    A(("h1", t("8. Costes: de positivo a negativo", "8. Costs: from positive to negative")))
    slip = [s for s in sens if s["parameter"] == "slippage.baseline_pips"]
    A(("table", {"rows": [[t("Deslizamiento (pips)", "Slippage (pips)"), "N", t("Total R", "Total R"), t("Esperanza", "Expectancy")]] + [[s["value"], str(s["trades"]), r(s["total_r"]), r(s["expectancy_r"])] for s in slip],
                 "widths": [45 * mm, 14 * mm, 30 * mm, 30 * mm]}))
    A(("p", t("Aquí V1.1 se comporta bien: pasar de 0 a 0,5 pips de deslizamiento resta unos 0,4R en doce operaciones, porque el stop está lejos (varios ATR) y los costes son pequeños en relación al riesgo. "
              "En estrategias con stops de pocos pips la misma tabla suele cambiar de signo en la segunda fila. Pide siempre esta tabla; si no existe, asume el peor caso.",
              "Here V1.1 behaves well: going from 0 to 0.5 pips of slippage takes about 0.4R off twelve trades, because the stop is far (several ATR) and costs are small relative to risk. "
              "In strategies with stops of a few pips the same table usually flips sign on the second row. Always ask for this table; if it does not exist, assume the worst case.")))
    A(("p", t("Tres preguntas sobre costes que hay que poder responder leyendo el informe: ¿de dónde sale el spread (histórico del proveedor o un número fijo)? ¿Se aplica el deslizamiento también al stop? ¿La comisión está en la misma unidad que el riesgo?",
              "Three cost questions you must be able to answer by reading the report: where does the spread come from (provider history or a fixed number)? Is slippage applied to the stop as well? Is commission in the same unit as the risk?")))

    # ------------------------------------------------------------------ 9
    A(("h1", t("9. La checklist de decisión", "9. The decision checklist")))
    A(("p", t("Doce preguntas. Si alguna de las cinco primeras falla, deja de leer el informe. Si fallan dos de las restantes, el veredicto es <i>todavía no sabemos</i>, que es el veredicto de casi todos los backtests honestos.",
              "Twelve questions. If any of the first five fails, stop reading the report. If two of the rest fail, the verdict is <i>we do not know yet</i>, which is the verdict of almost every honest backtest.")))
    A(("bullets", checklist_items(lang)))
    A(("p", t("La checklist está también como fichero aparte (03-checklist) para imprimirla o pegarla al final de cada informe.",
              "The checklist is also a separate file (03-checklist) to print or paste at the end of every report.")))

    # ------------------------------------------------------------------ 10
    A(("h1", t("10. Cómo contar un resultado (sobre todo si es negativo)", "10. How to tell a result (especially a negative one)")))
    A(("p", t("Un informe de backtest no es un folleto. Su trabajo es que otra persona pueda rehacerlo y discrepar con datos. La plantilla del kit (02-plantilla) tiene estas secciones, en este orden, y cada una tiene un motivo:",
              "A backtest report is not a brochure. Its job is to let someone else redo it and disagree with data. The kit's template (02-plantilla) has these sections, in this order, and each has a reason:")))
    A(("bullets", [
        t("<b>Hipótesis y versión.</b> Qué regla, en qué fichero, con qué hash. Qué cambió respecto a la versión anterior y por qué (enlace al log de decisiones).", "<b>Hypothesis and version.</b> Which rule, in which file, with which hash. What changed from the previous version and why (link to the decision log)."),
        t("<b>Datos.</b> Proveedor, símbolo, rango, zona horaria, hash, huecos y filas inválidas.", "<b>Data.</b> Provider, symbol, range, timezone, hash, gaps and invalid rows."),
        t("<b>Ejecución y costes.</b> Modelo de relleno, spread, deslizamiento, comisión, riesgo por operación.", "<b>Execution and costs.</b> Fill model, spread, slippage, commission, risk per trade."),
        t("<b>Resultado.</b> Las cinco cifras, la curva en R, los motivos de salida. Y el total sin la mejor operación.", "<b>Result.</b> The five numbers, the R curve, the exit reasons. And the total without the best trade."),
        t("<b>Protocolo.</b> Monte Carlo, benchmark aleatorio, sensibilidad, particiones y walk-forward, cada uno con su tabla.", "<b>Protocol.</b> Monte Carlo, random benchmark, sensitivity, splits and walk-forward, each with its table."),
        t("<b>Limitaciones.</b> Las que ya sabes y las que te ha enseñado el protocolo.", "<b>Limitations.</b> The ones you already knew and the ones the protocol taught you."),
        t("<b>Decisión.</b> Una de tres: descartar, seguir investigando (con qué dato nuevo), o pasar a la siguiente versión (con qué cambio exacto). Nunca <i>operar</i>: eso no es una decisión de investigación.",
          "<b>Decision.</b> One of three: discard, keep researching (with which new data), or move to the next version (with which exact change). Never <i>trade it</i>: that is not a research decision."),
    ]))
    A(("p", t("Un resultado negativo bien documentado vale más que uno positivo sin protocolo: te ahorra repetir el error y le ahorra a otros creerse el número. V1 perdió; de su informe salió el hallazgo del stop y, de ahí, V1.1. Esa cadena, y no el +2,35R, es el producto del laboratorio.",
              "A well-documented negative result is worth more than an undocumented positive one: it saves you repeating the mistake and saves others believing the number. V1 lost; from its report came the stop finding and, from there, V1.1. That chain, not the +2.35R, is the lab's product.")))

    # ------------------------------------------------------------------ 11
    A(("h1", t("11. Glosario", "11. Glossary")))
    A(("table", {"rows": [[t("Término", "Term"), t("Significado", "Meaning")]] + glossary(lang), "widths": [40 * mm, 130 * mm], "font": 8}))

    # ------------------------------------------------------------------ 12
    A(("h1", t("12. Reproducir estos números", "12. Reproducing these numbers")))
    A(("p", t("Todo el código es público. Los datasets del kit (04-datasets) contienen las operaciones, la curva, las métricas, la sensibilidad y el Monte Carlo de cada ejecución, con el SHA-256 de cada fichero. "
              "Las velas M1 originales no se incluyen porque pertenecen al proveedor; el fichero COMO-DESCARGAR-DATOS.md explica cómo bajarlas con el script del repositorio y comprobar que su hash coincide con el de esta guía.",
              "All the code is public. The kit's datasets (04-datasets) contain the trades, the curve, the metrics, the sensitivity and the Monte Carlo of each run, with the SHA-256 of every file. "
              "The original M1 candles are not included because they belong to the provider; the file COMO-DESCARGAR-DATOS.md explains how to download them with the repository script and check that their hash matches the one in this guide.")))
    A(("table", {"rows": [[t("Recurso", "Resource"), "URL"], [t("Laboratorio (gratis)", "Lab (free)"), SITE], [t("Código", "Code"), REPO], [t("Aviso legal y método", "Legal notice and method"), DISCLAIMER_URL]], "widths": [50 * mm, 120 * mm], "font": 8}))
    A(("notice", t("Material educativo. No es asesoramiento de inversión. El rendimiento pasado no garantiza resultados futuros.",
                   "Educational material. Not investment advice. Past performance does not guarantee future results.")))
    return blocks


def checklist_items(lang: str) -> list[str]:
    es = lang == "es"
    items = [
        ("¿Están publicados el hash del dataset, la versión de la estrategia y la configuración de ejecución?", "Are the dataset hash, strategy version and execution configuration published?"),
        ("¿El motor decide solo con velas cerradas y ejecuta al siguiente precio?", "Does the engine decide only on closed candles and execute at the next price?"),
        ("¿Hay spread, deslizamiento y comisión en cada operación, y se dice de dónde salen?", "Are spread, slippage and commission applied to every trade, and is their source stated?"),
        ("¿Las reglas estaban escritas antes de ver el resultado (fichero con hash, versión nombrada)?", "Were the rules written before seeing the result (hashed file, named version)?"),
        ("¿Se puede reproducir el número con el código y los datos indicados?", "Can the number be reproduced with the code and data indicated?"),
        ("¿Cuántas operaciones hay? ¿Qué pasa con el total si quitas la mejor?", "How many trades are there? What happens to the total if you remove the best one?"),
        ("Monte Carlo: ¿P25 está por encima de cero? ¿Cuál es la probabilidad de acabar en pérdidas?", "Monte Carlo: is P25 above zero? What is the probability of ending negative?"),
        ("Benchmark aleatorio: ¿la estrategia supera al 95 % de las entradas al azar con los mismos costes?", "Random benchmark: does the strategy beat 95 % of random entries with the same costs?"),
        ("Sensibilidad: ¿algún parámetro cambia el signo del total al moverlo un paso?", "Sensitivity: does any parameter flip the sign of the total when moved one step?"),
        ("Fuera de muestra: ¿hay un tramo reservado con operaciones suficientes para decir algo?", "Out of sample: is there a reserved segment with enough trades to say anything?"),
        ("Costes: ¿el resultado sobrevive a 0,5 pips más de deslizamiento?", "Costs: does the result survive 0.5 pips more slippage?"),
        ("¿El informe termina con una decisión de investigación (descartar, seguir, nueva versión) y no con una invitación a operar?", "Does the report end with a research decision (discard, continue, new version) and not with an invitation to trade?"),
    ]
    return [f"{i + 1}. {a if es else b}" for i, (a, b) in enumerate(items)]


def glossary(lang: str) -> list[list[str]]:
    es = lang == "es"
    rows = [
        ("R", "Unidad de riesgo: la distancia al stop de cada operación. +2R = dos veces el riesgo asumido.", "Risk unit: the distance to the stop on each trade. +2R = twice the risk taken."),
        ("Esperanza", "R medio por operación. Positiva no significa rentable si N es pequeño.", "Average R per trade. Positive does not mean profitable when N is small."),
        ("Factor de beneficio", "Suma de ganancias / suma de pérdidas (en valor absoluto).", "Sum of gains / sum of losses (absolute value)."),
        ("Drawdown", "Caída desde el máximo anterior de la curva de capital, aquí en R.", "Fall from the previous peak of the equity curve, here in R."),
        ("MFE / MAE", "Máxima excursión favorable / adversa de una operación antes de cerrarse, en R.", "Maximum favourable / adverse excursion of a trade before it closes, in R."),
        ("Monte Carlo", "Remuestreo de las operaciones para ver la distribución de resultados posibles.", "Resampling of the trades to see the distribution of possible outcomes."),
        ("Benchmark aleatorio", "Entradas al azar con las mismas reglas de salida y costes; la línea base contra la que se mide la regla.", "Random entries with the same exit rules and costs; the baseline the rule is measured against."),
        ("Sensibilidad", "Reejecución cambiando un parámetro cada vez.", "Re-run changing one parameter at a time."),
        ("Walk-forward", "Ventanas rodantes: se ajusta en una y se evalúa en la siguiente, sin solapar.", "Rolling windows: fit on one, evaluate on the next, without overlap."),
        ("Fuera de muestra", "Tramo de datos reservado que no se usa para diseñar ni ajustar la regla.", "Reserved stretch of data not used to design or tune the rule."),
        ("Look-ahead", "Usar información que todavía no existía en el momento de decidir. Invalida el backtest.", "Using information that did not yet exist at decision time. Invalidates the backtest."),
        ("Hash (SHA-256)", "Huella del fichero. Si cambia un byte, cambia el hash: permite saber que dos personas usaron los mismos datos.", "File fingerprint. If one byte changes, the hash changes: it lets you know two people used the same data."),
    ]
    return [[term, a if es else b] for term, a, b in rows]


# --------------------------------------------------------------------------- PDF rendering


def _footer_factory(lang: str):
    text = ("FX Research Lab · material educativo · resultados simulados, no es asesoramiento de inversión · el pasado no garantiza el futuro"
            if lang == "es" else "FX Research Lab · educational material · simulated results, not investment advice · the past does not guarantee the future")

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, text)
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, ("página" if lang == "es" else "page") + f" {doc.page}")
        canvas.restoreState()

    return footer


def render_pdf(blocks: list[tuple[str, Any]], title: str, lang: str) -> bytes:
    styles = _styles()
    # A guide is read, not scanned: slightly larger body text than the lab reports.
    styles["body"].fontSize, styles["body"].leading = 10.5, 15
    styles["h1"].fontSize, styles["h1"].leading = 18, 22
    styles["h2"].fontSize, styles["h2"].leading = 13, 16
    styles["title"].fontSize, styles["title"].leading = 30, 34
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm, title=title, author="FX Research Lab")
    story: list[Any] = []
    for kind, payload in blocks:
        if kind == "title":
            story.append(Spacer(1, 40 * mm))
            story.append(Paragraph(payload, styles["title"]))
        elif kind == "subtitle":
            story.append(Paragraph(payload, styles["subtitle"]))
        elif kind == "h1":
            story.append(PageBreak())
            story.append(Paragraph(payload, styles["h1"]))
        elif kind == "h2":
            story.append(Paragraph(payload, styles["h2"]))
        elif kind == "p":
            story.append(Paragraph(payload, styles["body"]))
            story.append(Spacer(1, 4))
        elif kind == "notice":
            story.append(Paragraph(payload, styles["notice"]))
        elif kind == "bullets":
            for item in payload:
                story.append(Paragraph(f"• {item}", styles["body"]))
            story.append(Spacer(1, 4))
        elif kind == "table":
            story.append(_table(payload["rows"], widths=payload.get("widths"), font_size=payload.get("font", 8.5)))
            story.append(Spacer(1, 6))
        elif kind == "chart":
            if payload["kind"] == "line":
                story.append(KeepTogether(_line_chart(payload["points"], title=payload["title"])))
            else:
                story.append(KeepTogether(_bar_chart(payload["labels"], payload["values"], title=payload["title"], fmt=payload.get("fmt", "{:.0f}"))))
            story.append(Spacer(1, 6))
        elif kind == "pagebreak":
            story.append(PageBreak())
    doc.build(story, onFirstPage=_footer_factory(lang), onLaterPages=_footer_factory(lang))
    return buffer.getvalue()


# --------------------------------------------------------------------------- template + checklist (Markdown)


def template_md(lang: str) -> str:
    es = lang == "es"
    if es:
        return f"""# Informe de backtest — <hipótesis> <versión>

> Material educativo. Resultados simulados sobre datos históricos. No es asesoramiento de inversión. El rendimiento pasado no garantiza resultados futuros.

| Campo | Valor |
|---|---|
| Fecha del informe | AAAA-MM-DD |
| Autor | |
| Versión de la estrategia | V_._ (`fichero.yaml`, hash `…`) |
| Cambios respecto a la versión anterior | … (enlace al log de decisiones) |
| Software | versión · revisión |

## 1. Hipótesis
Qué afirma la regla, en una frase. Qué mercado, qué horario, qué dirección. Qué debería verse si es cierta y qué debería verse si es falsa.

## 2. Datos
| Campo | Valor |
|---|---|
| Proveedor y tipo | (p. ej. ticks agregados a M1) |
| Símbolo(s) | |
| Rango (UTC) | |
| Zona horaria de las reglas | (p. ej. Europe/Madrid, tzdata …) |
| SHA-256 del dataset | |
| Filas · huecos · duplicadas · inválidas | |
| Columna de spread disponible | sí / no |

## 3. Ejecución y costes
| Campo | Valor |
|---|---|
| Modelo de relleno | (decisión al cierre, ejecución al siguiente precio) |
| Spread | origen y valor |
| Deslizamiento | pips, ¿también en el stop? |
| Comisión | |
| Riesgo por operación | fracción del capital |
| Expiración por sesión | sí / no, hora |

## 4. Resultado
| Métrica | Valor |
|---|---|
| Operaciones (N) | |
| Esperanza (R) | |
| Acierto | |
| Ganancia media / pérdida media (R) | |
| Factor de beneficio | |
| Drawdown máximo (R) | |
| Total R | |
| **Total R sin la mejor operación** | |

Motivos de salida: stop … · objetivo … · fin de sesión …

Curva de capital (en R, eje X = operaciones): *insertar figura*.

## 5. Protocolo
### 5.1 Monte Carlo
| Percentil | R final | Drawdown máx. |
|---|---|---|
| P5 | | |
| P25 | | |
| P50 | | |
| P75 | | |
| P95 | | |

Probabilidad de acabar en pérdidas: … %. Simulaciones: … · semilla: …

### 5.2 Benchmark aleatorio
Esperanza de la regla … R · esperanza aleatoria P50 … R · P95 … R · percentil de la regla … % · p-valor empírico …

### 5.3 Sensibilidad
| Parámetro | Valor | N | Total R | Esperanza |
|---|---|---|---|---|
| | | | | |

Parámetros que cambian el signo: …

### 5.4 Particiones y walk-forward
| Tramo | Días | N | Total R | Esperanza |
|---|---|---|---|---|
| entrenamiento | | | | |
| validación | | | | |
| fuera de muestra | | | | |

Walk-forward: ventanas … · con operaciones … · positivas … · total fuera de muestra … R

## 6. Limitaciones
- Relleno simulado sobre datos históricos; sin ejecución real.
- …

## 7. Decisión
Una de: **descartar** / **seguir investigando** (con qué dato nuevo) / **nueva versión** (con qué cambio exacto, y por qué).

Entrada en el log de decisiones: `AAAA-MM-DD — …`

## 8. Checklist
Pegar aquí la checklist del kit (03-checklist) con cada pregunta respondida.
"""
    return f"""# Backtest report — <hypothesis> <version>

> Educational material. Simulated results on historical data. Not investment advice. Past performance does not guarantee future results.

| Field | Value |
|---|---|
| Report date | YYYY-MM-DD |
| Author | |
| Strategy version | V_._ (`file.yaml`, hash `…`) |
| Changes from the previous version | … (link to the decision log) |
| Software | version · revision |

## 1. Hypothesis
What the rule claims, in one sentence. Which market, which hours, which direction. What you should see if it is true and what you should see if it is false.

## 2. Data
| Field | Value |
|---|---|
| Provider and type | (e.g. ticks aggregated to M1) |
| Symbol(s) | |
| Range (UTC) | |
| Rules timezone | (e.g. Europe/Madrid, tzdata …) |
| Dataset SHA-256 | |
| Rows · gaps · duplicates · invalid | |
| Spread column available | yes / no |

## 3. Execution and costs
| Field | Value |
|---|---|
| Fill model | (decision at close, execution at the next price) |
| Spread | source and value |
| Slippage | pips, also on the stop? |
| Commission | |
| Risk per trade | fraction of equity |
| Session expiry | yes / no, time |

## 4. Result
| Metric | Value |
|---|---|
| Trades (N) | |
| Expectancy (R) | |
| Win rate | |
| Average win / average loss (R) | |
| Profit factor | |
| Max drawdown (R) | |
| Total R | |
| **Total R without the best trade** | |

Exit reasons: stop … · target … · session expiry …

Equity curve (in R, X axis = trades): *insert figure*.

## 5. Protocol
### 5.1 Monte Carlo
| Percentile | Final R | Max drawdown |
|---|---|---|
| P5 | | |
| P25 | | |
| P50 | | |
| P75 | | |
| P95 | | |

Probability of ending negative: … %. Simulations: … · seed: …

### 5.2 Random benchmark
Rule expectancy … R · random expectancy P50 … R · P95 … R · rule percentile … % · empirical p-value …

### 5.3 Sensitivity
| Parameter | Value | N | Total R | Expectancy |
|---|---|---|---|---|
| | | | | |

Parameters that flip the sign: …

### 5.4 Splits and walk-forward
| Segment | Days | N | Total R | Expectancy |
|---|---|---|---|---|
| train | | | | |
| validation | | | | |
| out of sample | | | | |

Walk-forward: windows … · with trades … · positive … · out-of-sample total … R

## 6. Limitations
- Simulated fills on historical data; no live execution.
- …

## 7. Decision
One of: **discard** / **keep researching** (with which new data) / **new version** (with which exact change, and why).

Decision-log entry: `YYYY-MM-DD — …`

## 8. Checklist
Paste the kit checklist here (03-checklist) with every question answered.
"""


def checklist_md(lang: str) -> str:
    es = lang == "es"
    head = "# Checklist de decisión — leer un backtest\n\nSi falla una de las cinco primeras, deja de leer. Si fallan dos de las restantes, el veredicto es «todavía no sabemos».\n\n" if es else \
        "# Decision checklist — reading a backtest\n\nIf one of the first five fails, stop reading. If two of the rest fail, the verdict is \"we do not know yet\".\n\n"
    body = "\n".join(f"- [ ] {item}" for item in checklist_items(lang))
    tail = ("\n\n**Veredicto:** descartar / seguir investigando / nueva versión\n\n_Material educativo. No es asesoramiento de inversión._\n" if es
            else "\n\n**Verdict:** discard / keep researching / new version\n\n_Educational material. Not investment advice._\n")
    return head + body + tail


def md_to_blocks(markdown: str) -> list[tuple[str, Any]]:
    """Tiny Markdown-to-blocks converter for the template PDF (headings, paragraphs, tables, bullets, quotes)."""
    blocks: list[tuple[str, Any]] = []
    table: list[list[str]] = []
    paragraph: list[str] = []

    def flush() -> None:
        nonlocal table, paragraph
        if table:
            blocks.append(("table", {"rows": table, "font": 8}))
            table = []
        if paragraph:
            blocks.append(("p", " ".join(paragraph)))
            paragraph = []

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            table.append([c.replace("**", "").replace("`", "") for c in cells])
            continue
        flush()
        if not line:
            continue
        if line.startswith("# "):
            blocks.append(("title", line[2:]))
        elif line.startswith("## "):
            blocks.append(("h2", line[3:]))
        elif line.startswith("### "):
            blocks.append(("h2", line[4:]))
        elif line.startswith("> "):
            blocks.append(("notice", line[2:]))
        elif line.startswith("- "):
            blocks.append(("bullets", [line[2:].replace("[ ]", "☐") if False else line[2:].replace("[ ] ", "")]))
        else:
            paragraph.append(line.replace("**", "").replace("*", "").replace("`", ""))
    flush()
    return blocks


# --------------------------------------------------------------------------- datasets


TRADE_COLUMNS = ["trade_id", "symbol", "date", "direction", "observation_window", "entry_timestamp", "entry_price", "stop_price", "target_price", "exit_timestamp", "exit_price", "exit_reason",
                 "spread_pips", "slippage_pips", "commission", "r_multiple", "mfe", "mae"]


def write_datasets(runs: dict[str, dict[str, Any]], out: Path) -> list[Path]:
    written: list[Path] = []
    for name, data in runs.items():
        folder = out / name
        folder.mkdir(parents=True, exist_ok=True)
        if "trades" in data:
            with (folder / "trades.csv").open("w", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=TRADE_COLUMNS, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(data["trades"])
            written.append(folder / "trades.csv")
            with (folder / "equity_curve.csv").open("w", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=["timestamp", "trade_id", "symbol", "r_multiple", "cumulative_r", "drawdown_r"], extrasaction="ignore")
                writer.writeheader()
                writer.writerows(data["equity_curve"])
            written.append(folder / "equity_curve.csv")
            (folder / "metrics.json").write_text(json.dumps({k: v for k, v in data["metrics"].items() if k != "daily"}, indent=2))
            written.append(folder / "metrics.json")
        if "sensitivity" in data:
            rows = sensitivity_rows(data)
            with (folder / "sensitivity.csv").open("w", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            written.append(folder / "sensitivity.csv")
            (folder / "monte_carlo.json").write_text(json.dumps(data["monte_carlo"], indent=2))
            (folder / "benchmark.json").write_text(json.dumps(data["benchmark"], indent=2))
            (folder / "walk_forward.json").write_text(json.dumps(data["walk_forward"], indent=2))
            (folder / "splits.json").write_text(json.dumps(data["splits"], indent=2))
            (folder / "baseline.json").write_text(json.dumps(data["baseline"], indent=2))
            written += [folder / n for n in ("monte_carlo.json", "benchmark.json", "walk_forward.json", "splits.json", "baseline.json")]
        repro = data.get("reproducibility", {})
        (folder / "reproducibility.json").write_text(json.dumps(repro, indent=2))
        written.append(folder / "reproducibility.json")
    return written


def download_instructions(runs: dict[str, dict[str, Any]]) -> str:
    repro = runs["v1_1_backtest"]["reproducibility"]
    return f"""# Cómo descargar los datos originales y reproducir las ejecuciones · How to download the original data and reproduce the runs

Las velas M1 de EUR/USD 2024 no se incluyen en el kit: pertenecen a su proveedor (Dukascopy) y no se pueden redistribuir.
Se descargan gratis con el script del repositorio y se comprueba el hash.

The EUR/USD 2024 M1 candles are not included in the kit: they belong to their provider (Dukascopy) and cannot be redistributed.
They are downloaded for free with the repository script and the hash is checked.

```bash
git clone {REPO}.git
cd 9999-trading-lab
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# 1) descargar · download (ticks -> M1, con reanudación por meses · resumable month by month)
python -m backend.cli fetch dukascopy --symbol EURUSD --start 2024-01-01 --end 2025-01-01 --out data/raw/EURUSD_2024.csv
#    (o haz doble clic en scripts/fetch_history.command con YEARS="2024" · or double-click scripts/fetch_history.command with YEARS="2024")

# 2) comprobar la calidad y el hash · check quality and hash (dataset_hash debe ser · must be)
#    {repro['dataset_hash']}
python -m backend.cli validate data/raw/EURUSD_2024.csv

# 3) reproducir · reproduce (V1 = config/strategy_v1.yaml, V1.1 = config/strategy_v1_1.yaml)
python -m backend.cli backtest data/raw/EURUSD_2024.csv --strategy config/strategy_v1_1.yaml --out results/EURUSD_2024_v1_1_backtest.json
python -m backend.cli research data/raw/EURUSD_2024.csv --strategy config/strategy_v1_1.yaml --seed 7 --out results/EURUSD_2024_v1_1_research.json
```

`python -m backend.cli --help` lista todos los subcomandos; el README del repositorio es la referencia.
`python -m backend.cli --help` lists every subcommand; the repository README is the reference.

Versión del software usada en el kit · software version used in the kit: {repro.get('software_version', '—')} · {repro.get('software_revision', '—')}
Hash de configuración · configuration hash: {repro['config_hash']}

Si Dukascopy limita tu IP (429/503), el script espera y reanuda por meses; deja el proceso abierto o relánzalo más tarde.
If Dukascopy rate-limits your IP (429/503), the script waits and resumes month by month; leave it running or relaunch later.
"""


def readme(lang: str) -> str:
    es = lang == "es"
    if es:
        return f"""KIT · CÓMO LEER UN BACKTEST · FX Research Lab · v{KIT_VERSION}
=================================================================

Material educativo. No es asesoramiento de inversión ni una recomendación de operar.
Todos los números son resultados simulados sobre datos históricos; el rendimiento pasado
no garantiza resultados futuros. Aviso completo: {DISCLAIMER_URL}

Contenido
  01-guia/        La guía (PDF, ES y EN). Empieza por aquí.
  02-plantilla/   Plantilla de informe de backtest (Markdown y PDF).
  03-checklist/   Checklist de decisión (Markdown).
  04-datasets/    Operaciones, curva, métricas, sensibilidad, Monte Carlo, benchmark,
                  walk-forward y reproducibilidad de cada ejecución, con SHA256SUMS.txt
                  y las instrucciones para descargar las velas originales.

Licencia
  Guía, plantilla y checklist: uso personal; no redistribuir ni revender.
  Datasets derivados: puedes usarlos y citarlos; las velas originales son del proveedor.
  Código del laboratorio: MIT, en {REPO}

Soporte y versiones
  {SITE}  ·  Las actualizaciones del kit se entregan por Gumroad sin coste.
"""
    return f"""KIT · HOW TO READ A BACKTEST · FX Research Lab · v{KIT_VERSION}
=================================================================

Educational material. Not investment advice nor a recommendation to trade.
Every number is a simulated result on historical data; past performance does not
guarantee future results. Full notice: {DISCLAIMER_URL}

Contents
  01-guia/        The guide (PDF, ES and EN). Start here.
  02-plantilla/   Backtest report template (Markdown and PDF).
  03-checklist/   Decision checklist (Markdown).
  04-datasets/    Trades, curve, metrics, sensitivity, Monte Carlo, benchmark,
                  walk-forward and reproducibility of each run, with SHA256SUMS.txt
                  and the instructions to download the original candles.

Licence
  Guide, template and checklist: personal use; do not redistribute or resell.
  Derived datasets: you may use and cite them; the original candles belong to the provider.
  Lab code: MIT, at {REPO}

Support and versions
  {SITE}  ·  Kit updates are delivered through Gumroad at no cost.
"""


# --------------------------------------------------------------------------- main


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(results_dir: Path, out_dir: Path) -> Path:
    runs = load_results(results_dir)
    kit = out_dir / "kit-como-leer-un-backtest"
    if kit.exists():
        shutil.rmtree(kit)
    for sub in ("01-guia", "02-plantilla", "03-checklist", "04-datasets"):
        (kit / sub).mkdir(parents=True)

    (kit / "01-guia" / "guia-como-leer-un-backtest-ES.pdf").write_bytes(render_pdf(guide_content(runs, "es"), "Cómo leer un backtest", "es"))
    (kit / "01-guia" / "guide-how-to-read-a-backtest-EN.pdf").write_bytes(render_pdf(guide_content(runs, "en"), "How to read a backtest", "en"))

    for lang, name in (("es", "plantilla-informe-backtest-ES"), ("en", "backtest-report-template-EN")):
        md = template_md(lang)
        (kit / "02-plantilla" / f"{name}.md").write_text(md)
        (kit / "02-plantilla" / f"{name}.pdf").write_bytes(render_pdf(md_to_blocks(md), name, lang))
    for lang, name in (("es", "checklist-decision-ES"), ("en", "decision-checklist-EN")):
        (kit / "03-checklist" / f"{name}.md").write_text(checklist_md(lang))

    data_dir = kit / "04-datasets"
    files = write_datasets(runs, data_dir)
    (data_dir / "COMO-DESCARGAR-DATOS.md").write_text(download_instructions(runs))
    (data_dir / "SHA256SUMS.txt").write_text("".join(f"{sha256(p)}  {p.relative_to(data_dir)}\n" for p in sorted(files)))

    (kit / "LEEME.txt").write_text(readme("es"))
    (kit / "README.txt").write_text(readme("en"))

    zip_path = out_dir / "kit-como-leer-un-backtest.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(kit.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(out_dir))
    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", default=str(ROOT / "results"))
    parser.add_argument("--out", default=str(ROOT / "dist" / "kit"))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    zip_path = build(Path(args.results), out)
    print(f"kit written to {zip_path} ({zip_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
