import { useMemo, useState } from 'react';
import { formatR } from '../api';
import { EquityChart } from '../components/Charts';
import { useRun } from '../components/LessonWidgets';
import { KpiTiles } from '../components/Results';
import { CandleStrip } from '../components/sim/CandleStrip';
import { ExplainerChart } from '../components/TradeExplainer';
import { LEVELS, SIM_RUN } from '../content/sim';
import { useT } from '../i18n';
import { Link } from '../router';
import type { BacktestResult, ResearchReport } from '../types';

const RESEARCH_RUN = 'eurusd-2024-v1_1-research';

type Screen = { id: string; title: { es: string; en: string }; text: { es: string; en: string } };

const SCREENS: Screen[] = [
  { id: 'candles', title: { es: '1 · Datos reales, minuto a minuto', en: '1 · Real data, minute by minute' },
    text: { es: 'Todo el laboratorio corre sobre velas M1 reales de EUR/USD y GBP/USD (2019–2026), con su hash publicado. Nada está dibujado a mano: estas son las velas del día de la primera operación de 2024.', en: 'The whole lab runs on real EUR/USD and GBP/USD M1 candles (2019–2026), with their published hash. Nothing is hand-drawn: these are the candles of the day of the first 2024 trade.' } },
  { id: 'trade', title: { es: '2 · Cada operación, explicada en su gráfico', en: '2 · Every trade, explained on its chart' },
    text: { es: 'Barrido, zona, impulso, retroceso, ruptura, entrada, salida: cada paso tiene su minuto y su regla en el fichero de la hipótesis. Aquí, la mejor operación del año.', en: 'Sweep, zone, displacement, retracement, break, entry, exit: every step has its minute and its rule in the hypothesis file. Here, the best trade of the year.' } },
  { id: 'equity', title: { es: '3 · El resultado del año, con todos los costes', en: '3 · The year\'s result, all costs included' },
    text: { es: 'Spread, deslizamiento y comisión pagados en cada operación. La curva de 2024 de V1.1 acabó en positivo: doce operaciones, +2,35R. Parece bueno. La pregunta es si significa algo.', en: 'Spread, slippage and commission paid on every trade. V1.1\'s 2024 curve ended positive: twelve trades, +2.35R. Looks good. The question is whether it means anything.' } },
  { id: 'research', title: { es: '4 · El protocolo que responde a esa pregunta', en: '4 · The protocol that answers that question' },
    text: { es: 'Monte Carlo, benchmark aleatorio, sensibilidad, walk-forward y ocho años de datos. El veredicto está en el laboratorio: en 2022 la misma regla perdió −8,01R y en ocho años acumula −2,04R. No hay ventaja. Y eso es lo que hay que saber leer.', en: 'Monte Carlo, random benchmark, sensitivity, walk-forward and eight years of data. The verdict is in the lab: in 2022 the same rule lost −8.01R and over eight years it adds up to −2.04R. No edge. And that is what one has to learn to read.' } },
  { id: 'sim', title: { es: '5 · El simulador: nueve niveles sobre estos datos', en: '5 · The simulator: nine levels on this data' },
    text: { es: 'De leer una vela (nivel 0) a diseñar tu propia versión y recibir su protocolo (nivel 8). Cada nivel trabaja sobre operaciones reales, con cuestionario y una nota de laboratorio escrita por ti. Los tres primeros son gratis.', en: 'From reading a candle (level 0) to designing your own version and getting its protocol (level 8). Every level works on real trades, with a quiz and a lab note you write. The first three are free.' } },
  { id: 'go', title: { es: '6 · Empieza por el nivel 0', en: '6 · Start at level 0' },
    text: { es: 'Seis minutos, sin cuenta. Si al terminar los tres niveles gratis quieres seguir, Lab Pro abre el 23 de noviembre con los seis niveles restantes.', en: 'Six minutes, no account. If after the three free levels you want to go on, Lab Pro opens on 23 November with the remaining six levels.' } },
];

/** /tour — six screens showing what the platform is, with the live components (no screenshots). */
export function TourPage() {
  const { lang, pick } = useT();
  const es = lang === 'es';
  const [i, setI] = useState(0);
  const { run } = useRun(SIM_RUN);
  const { run: research } = useRun(RESEARCH_RUN);
  const result = run?.kind === 'backtest' ? run.data : null;
  const report = research?.kind === 'research' ? (research.data as ResearchReport) : null;
  const screen = SCREENS[i];
  return (
    <main className="prose tour">
      <p className="kicker">{es ? 'Qué vas a ver' : 'What you will see'}</p>
      <h1 className="page-title">{es ? 'Un laboratorio de verdad, en seis pantallas' : 'A real lab, in six screens'}</h1>
      <ol className="tour-dots" aria-label="screens">
        {SCREENS.map((s, k) => <li key={s.id}><button type="button" className={k === i ? 'active' : ''} onClick={() => setI(k)} aria-label={s.title.en}>{k + 1}</button></li>)}
      </ol>
      <section className="tour-screen">
        <h2>{pick(screen.title)}</h2>
        <p>{pick(screen.text)}</p>
        <div className="tour-live">
          {screen.id === 'candles' && (result ? <TourCandles result={result} /> : <p className="muted">…</p>)}
          {screen.id === 'trade' && (result ? <TourTrade result={result} lang={lang} /> : <p className="muted">…</p>)}
          {screen.id === 'equity' && (result ? <>{result.metrics && <KpiTiles metrics={result.metrics} />}{result.equity_curve && <EquityChart points={result.equity_curve} />}</> : <p className="muted">…</p>)}
          {screen.id === 'research' && <TourResearch report={report} es={es} />}
          {screen.id === 'sim' && (
            <ol className="tour-levels">
              {LEVELS.map((l) => <li key={l.n} className={l.pro ? 'pro' : ''}><span className="lesson-no" aria-hidden="true">{l.n}</span><div><strong>{pick(l.title)}</strong><span className="muted small"> · {l.pro ? 'Lab Pro' : (es ? 'gratis' : 'free')} · {l.minutes} min</span></div></li>)}
            </ol>
          )}
          {screen.id === 'go' && (
            <div className="row-actions">
              <Link to="/app" className="button">{es ? 'Empezar gratis' : 'Start free'}</Link>
              <Link to="/planes" className="button ghost">{es ? 'Ver planes' : 'See plans'}</Link>
              <Link to="/lab" className="button ghost">{es ? 'Ir al laboratorio' : 'Go to the lab'}</Link>
            </div>
          )}
        </div>
        <div className="row-actions tour-nav">
          <button type="button" className="ghost" disabled={i === 0} onClick={() => setI(i - 1)}>← {es ? 'Anterior' : 'Previous'}</button>
          {i < SCREENS.length - 1 ? <button type="button" onClick={() => setI(i + 1)}>{es ? 'Siguiente' : 'Next'} →</button> : <Link to="/app" className="button">{es ? 'Empezar gratis' : 'Start free'} →</Link>}
        </div>
      </section>
    </main>
  );
}

function TourCandles({ result }: { result: BacktestResult }) {
  const candles = useMemo(() => {
    const ex = result.trade_explainers?.[result.trades[0]?.trade_id];
    if (!ex) return [];
    const entry = ex.steps.find((s) => s.id === 'entry')?.time ?? 0;
    const idx = Math.max(0, ex.candles.findIndex((c) => c.time >= entry) - 30);
    return ex.candles.slice(idx, idx + 60);
  }, [result]);
  return candles.length ? <CandleStrip candles={candles} height={220} /> : <p className="muted">—</p>;
}

function TourTrade({ result, lang }: { result: BacktestResult; lang: 'es' | 'en' }) {
  const best = useMemo(() => [...result.trades].sort((a, b) => b.r_multiple - a.r_multiple)[0], [result]);
  const ex = best ? result.trade_explainers?.[best.trade_id] : undefined;
  if (!ex) return <p className="muted">—</p>;
  return <><ExplainerChart explainer={ex} focus="entry" lang={lang} /><p className="muted small mono">{best.date} · {best.direction} · {formatR(best.r_multiple)} · {best.exit_reason}</p></>;
}

function TourResearch({ report, es }: { report: ResearchReport | null; es: boolean }) {
  if (!report) return <p className="muted">…</p>;
  const mc = report.monte_carlo; const bm = report.benchmark; const wf = report.walk_forward;
  return (
    <div className="tiles">
      {mc && <div className="tile"><div className="tile-label">Monte Carlo</div><div className="tile-value mono">{mc.probability_losing != null ? `${Math.round(mc.probability_losing * 100)} %` : '—'}</div><div className="tile-hint">{es ? `probabilidad de acabar en pérdida con ${mc.trades_per_path} operaciones` : `probability of ending at a loss with ${mc.trades_per_path} trades`}</div></div>}
      {bm?.baseline_percentile_vs_random != null && <div className="tile"><div className="tile-label">{es ? 'Frente al azar' : 'Versus chance'}</div><div className="tile-value mono">p{Math.round(bm.baseline_percentile_vs_random)}</div><div className="tile-hint">{es ? `percentil de la regla entre ${bm.simulations} entradas aleatorias` : `rule percentile among ${bm.simulations} random entries`}</div></div>}
      {wf && <div className="tile"><div className="tile-label">Walk-forward</div><div className="tile-value mono">{wf.out_of_sample_concatenated.folds_positive}/{wf.out_of_sample_concatenated.folds_with_trades}</div><div className="tile-hint">{es ? 'ventanas fuera de muestra en positivo' : 'out-of-sample windows positive'}</div></div>}
      <div className="tile bad"><div className="tile-label">2019–2026</div><div className="tile-value">−2,04R</div><div className="tile-hint">{es ? '67 operaciones · sin ventaja' : '67 trades · no edge'}</div></div>
    </div>
  );
}
