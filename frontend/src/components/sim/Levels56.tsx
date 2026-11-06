import { useEffect, useMemo, useState } from 'react';
import { api, formatR } from '../../api';
import type { Question } from '../../content/lessons';
import { SIM_RUN } from '../../content/sim';
import { useT } from '../../i18n';
import type { ResearchReport } from '../../types';
import { useRun } from '../LessonWidgets';
import { LevelFrame } from './Levels';

const YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
const researchId = (y: number) => `eurusd-${y}-v1_1-research`;

/* ---------------------------------------------------------------- tiny deterministic PRNG so a seed reproduces a picture */
function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => { a += 0x6d2b79f5; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const quantile = (sorted: number[], q: number) => sorted[Math.min(sorted.length - 1, Math.max(0, Math.floor(q * sorted.length)))];

/* ---------------------------------------------------------------- level 5: Monte Carlo */

export function Level5() {
  const { lang } = useT();
  const es = lang === 'es';
  const { run, error } = useRun(SIM_RUN);
  const { run: research } = useRun(researchId(2024));
  const rs = useMemo(() => (run?.kind === 'backtest' ? run.data.trades.map((t) => t.r_multiple) : []), [run]);
  const report = research?.kind === 'research' ? (research.data as ResearchReport) : null;
  const [n, setN] = useState(12);
  const [seed, setSeed] = useState(1);
  const sim = useMemo(() => {
    if (!rs.length) return null;
    const rnd = mulberry32(seed);
    const paths: number[][] = []; const finals: number[] = []; const dds: number[] = [];
    for (let p = 0; p < 2000; p++) {
      let cum = 0, peak = 0, dd = 0; const path = [0];
      for (let i = 0; i < n; i++) { cum += rs[Math.floor(rnd() * rs.length)]; peak = Math.max(peak, cum); dd = Math.max(dd, peak - cum); if (p < 60) path.push(cum); }
      finals.push(cum); dds.push(dd); if (p < 60) paths.push(path);
    }
    finals.sort((a, b) => a - b); dds.sort((a, b) => a - b);
    return { paths, finals, dds, pLoss: finals.filter((f) => f <= 0).length / finals.length, p5: quantile(finals, 0.05), p50: quantile(finals, 0.5), p95: quantile(finals, 0.95), dd95: quantile(dds, 0.95) };
  }, [rs, n, seed]);
  if (!sim) return <main className="prose sim"><p className="muted">{error ? (es ? 'No se pudo cargar la ejecución real.' : 'Could not load the real run.') : '…'}</p></main>;
  const observed = rs.reduce((a, b) => a + b, 0);
  const lab = report?.monte_carlo;
  const questions: Question[] = [
    { id: 'l5q1', prompt: { es: `Remuestreando las 12 operaciones reales de 2024, ${Math.round(sim.pLoss * 100)} % de los caminos de ${n} operaciones acaban en pérdida. ¿Qué significa?`, en: `Resampling the 12 real 2024 trades, ${Math.round(sim.pLoss * 100)} % of the ${n}-trade paths end at a loss. What does it mean?` },
      options: { es: ['Que con el mismo proceso y otro orden/muestra de operaciones, perder era perfectamente posible: el +2,35R es una realización entre muchas', 'Que la regla pierde dinero', 'Que Monte Carlo demuestra la rentabilidad'], en: ['That with the same process and another order/sample of trades, losing was perfectly possible: +2.35R is one realisation among many', 'That the rule loses money', 'That Monte Carlo proves profitability'] }, answer: 0,
      explanation: { es: 'Monte Carlo no dice si hay ventaja; dice cuánta variación cabe esperar del mismo proceso. Un resultado dentro de esa nube no demuestra nada por sí solo.', en: 'Monte Carlo does not say whether there is an edge; it says how much variation to expect from the same process. A result inside that cloud proves nothing by itself.' } },
    { id: 'l5q2', prompt: { es: 'Sube el número de operaciones por camino de 12 a 200. ¿Qué pasa con la banda 5–95 % en términos de R por operación?', en: 'Raise the trades per path from 12 to 200. What happens to the 5–95 % band in R per trade?' },
      options: { es: ['Se estrecha: con más operaciones la media se acerca a la esperanza real (y aquí sigue siendo pequeña)', 'Se ensancha porque hay más riesgo', 'No cambia'], en: ['It narrows: with more trades the mean approaches the true expectancy (still small here)', 'It widens because there is more risk', 'It does not change'] }, answer: 0,
      explanation: { es: 'La suma crece con n, pero la media se estabiliza como 1/√n. Por eso doce operaciones no distinguen una esperanza de +0,2R de una de −0,1R; hacen falta cientos.', en: 'The sum grows with n, but the mean stabilises like 1/√n. That is why twelve trades cannot tell a +0.2R expectancy from −0.1R; hundreds are needed.' } },
    { id: 'l5q3', prompt: { es: `El drawdown en el percentil 95 de tus caminos es ${sim.dd95.toFixed(1)}R. ¿Para qué sirve esa cifra?`, en: `The 95th-percentile drawdown of your paths is ${sim.dd95.toFixed(1)}R. What is that number for?` },
      options: { es: ['Para dimensionar el riesgo por operación antes de operar nada: si 1R fuera el 2 % de la cuenta, ese drawdown sería un ' + Math.round(sim.dd95 * 2) + ' %', 'Para saber el beneficio esperado', 'Para elegir el mejor año'], en: ['To size risk per trade before trading anything: if 1R were 2 % of the account, that drawdown would be ' + Math.round(sim.dd95 * 2) + ' %', 'To know the expected profit', 'To pick the best year'] }, answer: 0,
      explanation: { es: 'El tamaño de posición se decide con el drawdown plausible, no con el observado. Aun con esperanza positiva, un R demasiado grande convierte una mala racha normal en la ruina.', en: 'Position size is decided from the plausible drawdown, not the observed one. Even with positive expectancy, too large an R turns a normal losing streak into ruin.' } },
  ];
  const width = 320, height = 120;
  const maxAbs = Math.max(1, ...sim.paths.flat().map(Math.abs));
  const y = (v: number) => height / 2 - (v / maxAbs) * (height / 2 - 6);
  return (
    <LevelFrame n={5} questions={questions}
      intro={<p>{es ? 'Las 12 operaciones de 2024 son una muestra. Monte Carlo pregunta: si el proceso fuera exactamente este, ¿qué otros resultados habrían sido igual de normales? Aquí se remuestrean las R reales con reemplazo, 2.000 caminos, en tu navegador. Elige cuántas operaciones por camino y cambia la semilla.' : 'The 12 trades of 2024 are a sample. Monte Carlo asks: if the process were exactly this, which other outcomes would have been just as normal? Here the real R values are resampled with replacement, 2,000 paths, in your browser. Choose how many trades per path and change the seed.'}</p>}
      noteHint={es ? 'Explica en dos frases por qué un resultado que cae dentro de la banda 5–95 % de su propio Monte Carlo no es evidencia de ventaja.' : 'Explain in two sentences why a result that falls inside the 5–95 % band of its own Monte Carlo is not evidence of an edge.'}>
      <section className="sim-block">
        <div className="knobs">
          <label className="knob"><span className="tile-label">{es ? 'Operaciones por camino' : 'Trades per path'} · {n}</span><input type="range" min={5} max={200} step={1} value={n} onChange={(e) => setN(Number(e.target.value))} /></label>
          <button type="button" className="ghost" onClick={() => setSeed(seed + 1)}>{es ? 'Otra semilla' : 'Another seed'} (#{seed})</button>
          <button type="button" className="ghost" onClick={() => setN(12)}>12 · {es ? 'como 2024' : 'as in 2024'}</button>
        </div>
        <svg viewBox={`0 0 ${width} ${height}`} className="mc-fan" role="img" aria-label="Monte Carlo paths">
          <line x1="0" x2={width} y1={y(0)} y2={y(0)} stroke="var(--line)" />
          {sim.paths.map((p, k) => <polyline key={k} fill="none" stroke={p[p.length - 1] > 0 ? 'var(--good)' : 'var(--bad)'} strokeOpacity="0.35" strokeWidth="1" points={p.map((v, i) => `${(i / n) * width},${y(v)}`).join(' ')} />)}
          {n === 12 && <polyline fill="none" stroke="var(--ink)" strokeWidth="2" points={rs.reduce<number[]>((acc, r) => [...acc, (acc[acc.length - 1] ?? 0) + r], [0]).map((v, i) => `${(i / n) * width},${y(v)}`).join(' ')} />}
        </svg>
        <div className="tiles">
          <div className={`tile ${sim.pLoss > 0.3 ? 'bad' : ''}`}><div className="tile-label">{es ? 'Caminos en pérdida' : 'Losing paths'}</div><div className="tile-value mono">{Math.round(sim.pLoss * 100)} %</div><div className="tile-hint">{es ? `de 2.000 caminos de ${n} operaciones` : `of 2,000 paths of ${n} trades`}</div></div>
          <div className="tile"><div className="tile-label">{es ? 'Banda 5–95 %' : '5–95 % band'}</div><div className="tile-value mono">{formatR(sim.p5)} … {formatR(sim.p95)}</div><div className="tile-hint">{es ? 'mediana' : 'median'} {formatR(sim.p50)} · {es ? 'por operación' : 'per trade'} {(sim.p5 / n).toFixed(2)} … {(sim.p95 / n).toFixed(2)}</div></div>
          <div className="tile"><div className="tile-label">{es ? 'Drawdown p95' : 'Drawdown p95'}</div><div className="tile-value mono">{sim.dd95.toFixed(1)}R</div><div className="tile-hint">{es ? 'lo que hay que poder aguantar' : 'what one must be able to sit through'}</div></div>
          <div className="tile"><div className="tile-label">{es ? 'Observado 2024' : 'Observed 2024'}</div><div className="tile-value">{formatR(observed)}</div><div className="tile-hint">{lab ? (es ? `laboratorio: ${Math.round((lab.probability_losing ?? 0) * 100)} % de ${lab.simulations} caminos en pérdida` : `lab: ${Math.round((lab.probability_losing ?? 0) * 100)} % of ${lab.simulations} paths losing`) : ''}</div></div>
        </div>
        <p className="muted small">{es ? 'La línea negra es la curva real de 2024 (solo con 12 operaciones por camino). El laboratorio hace el mismo remuestreo en el motor (informe de investigación de 2024); las cifras deben parecerse salvo el azar de la semilla.' : 'The black line is the real 2024 curve (only with 12 trades per path). The lab does the same resampling in the engine (2024 research report); the numbers should look alike up to the seed.'}</p>
      </section>
    </LevelFrame>
  );
}

/* ---------------------------------------------------------------- level 6: versus chance */

function useReports(): Record<number, ResearchReport | null> {
  const [reports, setReports] = useState<Record<number, ResearchReport | null>>({});
  useEffect(() => {
    let alive = true;
    (async () => {
      for (const y of YEARS) {
        try {
          const { result } = await api.run(researchId(y));
          if (alive) setReports((r) => ({ ...r, [y]: result as ResearchReport }));
        } catch {
          if (alive) setReports((r) => ({ ...r, [y]: null }));
        }
      }
    })();
    return () => { alive = false; };
  }, []);
  return reports;
}

export function Level6() {
  const { lang } = useT();
  const es = lang === 'es';
  const reports = useReports();
  const [guess, setGuess] = useState<number | null>(null);
  const r24 = reports[2024]?.benchmark;
  const rows = YEARS.map((y) => ({ y, b: reports[y]?.benchmark, base: reports[y]?.baseline }));
  const loaded = Object.keys(reports).length;
  const pctl = (v: number | undefined) => (v == null ? null : Math.round(v * 100));
  const consistent = rows.filter((r) => r.b?.baseline_percentile_vs_random != null && r.b.baseline_percentile_vs_random >= 0.95).length;
  const questions: Question[] = [
    { id: 'l6q1', prompt: { es: `En 2024 la regla quedó en el percentil ${pctl(r24?.baseline_percentile_vs_random) ?? '…'} frente a ${r24?.simulations ?? 200} entradas aleatorias con las mismas salidas y costes. ¿Qué dice eso?`, en: `In 2024 the rule landed at percentile ${pctl(r24?.baseline_percentile_vs_random) ?? '…'} versus ${r24?.simulations ?? 200} random entries with the same exits and costs. What does that say?` },
      options: { es: ['Que una de cada cuatro reglas sin ninguna información habría hecho lo mismo o mejor: no es evidencia de ventaja', 'Que la regla es mejor que el azar con un 75 % de confianza y se puede operar', 'Que el azar pierde siempre'], en: ['That one in four rules with no information at all would have done the same or better: not evidence of an edge', 'That the rule beats chance with 75 % confidence and can be traded', 'That chance always loses'] }, answer: 0,
      explanation: { es: 'Para hablar de ventaja se pide al menos el percentil 95 (p < 0,05), y repetido en varios años. Un 75 % en un año es lo que cabe esperar de una regla sin información que tuvo un año bueno.', en: 'To talk about an edge one asks for at least the 95th percentile (p < 0.05), repeated over several years. 75 % in one year is what to expect from an uninformed rule that had a good year.' } },
    { id: 'l6q2', prompt: { es: `Mira la tabla de ocho años. ¿En cuántos la regla supera el percentil 95 frente al azar?`, en: `Look at the eight-year table. In how many does the rule beat the 95th percentile versus chance?` },
      options: { es: [`${consistent}`, 'En todos los años positivos', 'En cinco'], en: [`${consistent}`, 'In every positive year', 'In five'] }, answer: 0,
      explanation: { es: 'Una regla con ventaja debería quedar alta casi todos los años. Esta sube y baja como lo haría el azar: en 2022 queda por debajo de casi todas las entradas aleatorias.', en: 'A rule with an edge should land high almost every year. This one goes up and down as chance would: in 2022 it lands below almost every random entry.' } },
    { id: 'l6q3', prompt: { es: '¿Por qué el benchmark usa las mismas salidas y costes y solo cambia el momento de entrada?', en: 'Why does the benchmark keep the same exits and costs and change only the entry moment?' },
      options: { es: ['Para aislar lo que la hipótesis afirma aportar: que su entrada tiene información. Si el azar entra igual de bien, la entrada no aporta', 'Para que el azar pierda', 'Porque las salidas no importan'], en: ['To isolate what the hypothesis claims to add: that its entry carries information. If chance enters just as well, the entry adds nothing', 'So that chance loses', 'Because exits do not matter'] }, answer: 0,
      explanation: { es: 'Un benchmark mal elegido (comprar y mantener, o entradas sin costes) haría parecer buena a cualquier regla. Compara contra lo que la regla dice mejorar.', en: 'A poorly chosen benchmark (buy and hold, or cost-free entries) would make any rule look good. Compare against what the rule claims to improve.' } },
  ];
  return (
    <LevelFrame n={6} questions={questions}
      intro={<p>{es ? 'El laboratorio corre, para cada año, 200 versiones de la regla en las que la entrada se decide al azar dentro de la misma sesión, con las mismas salidas, el mismo stop y los mismos costes. Antes de ver la respuesta: ¿en qué percentil crees que quedó V1.1 en 2024 (+2,35R)?' : 'For each year, the lab runs 200 versions of the rule where the entry is decided at random inside the same session, with the same exits, stop and costs. Before seeing the answer: at what percentile do you think V1.1 landed in 2024 (+2.35R)?'}</p>}
      noteHint={es ? 'Escribe cómo diseñarías un benchmark aleatorio para una estrategia tuya: qué mantendrías fijo y qué dejarías al azar.' : 'Write how you would design a random benchmark for a strategy of yours: what you would keep fixed and what you would leave to chance.'}>
      <section className="sim-block">
        {guess == null ? (
          <div className="row-actions">
            {[50, 75, 90, 99].map((g) => <button key={g} type="button" className="ghost" onClick={() => setGuess(g)}>{es ? `Percentil ${g}` : `Percentile ${g}`}</button>)}
          </div>
        ) : (
          <p className={guess === 75 ? 'good' : 'muted'}>{es ? `Tu apuesta: percentil ${guess}. Real: ${pctl(r24?.baseline_percentile_vs_random) ?? '…'}.` : `Your guess: percentile ${guess}. Actual: ${pctl(r24?.baseline_percentile_vs_random) ?? '…'}.`} {es ? 'Un 75 significa que 50 de las 200 entradas aleatorias hicieron igual o mejor.' : '75 means 50 of the 200 random entries did as well or better.'}</p>
        )}
        {r24?.random_expectancy_percentiles && guess != null && (
          <PercentileBar lang={lang} percentiles={r24.random_expectancy_percentiles} baseline={r24.baseline_expectancy_r ?? 0} />
        )}
        {guess != null && (
          <table className="plan-table small">
            <thead><tr><th>{es ? 'Año' : 'Year'}</th><th>{es ? 'Op.' : 'Trades'}</th><th>R</th><th>{es ? 'Esperanza' : 'Expectancy'}</th><th>{es ? 'Percentil vs azar' : 'Percentile vs chance'}</th></tr></thead>
            <tbody>
              {rows.map(({ y, b, base }) => <tr key={y}><td className="mono">{y}{y === 2026 ? '*' : ''}</td><td>{base?.trades ?? '…'}</td><td className={base && base.total_r > 0 ? 'good' : base && base.total_r < 0 ? 'bad' : ''}>{base ? formatR(base.total_r) : '…'}</td><td className="mono">{base ? base.expectancy_r.toFixed(2) : '…'}</td><td className={`mono ${pctl(b?.baseline_percentile_vs_random) != null && pctl(b?.baseline_percentile_vs_random)! >= 95 ? 'good' : ''}`}>{pctl(b?.baseline_percentile_vs_random) ?? (loaded < YEARS.length ? '…' : '—')}</td></tr>)}
            </tbody>
          </table>
        )}
        <p className="muted small">{es ? '* 2026 hasta octubre. Percentil = porcentaje de entradas aleatorias que la regla supera ese año. Umbral habitual de evidencia: 95, repetido.' : '* 2026 to October. Percentile = share of random entries the rule beats that year. Usual evidence threshold: 95, repeated.'}</p>
      </section>
    </LevelFrame>
  );
}

function PercentileBar({ percentiles, baseline, lang }: { percentiles: Record<string, number>; baseline: number; lang: 'es' | 'en' }) {
  const es = lang === 'es';
  const keys = Object.keys(percentiles).map(Number).sort((a, b) => a - b);
  const lo = Math.min(percentiles[String(keys[0])], baseline) - 0.1; const hi = Math.max(percentiles[String(keys[keys.length - 1])], baseline) + 0.1;
  const x = (v: number) => ((v - lo) / (hi - lo || 1)) * 320;
  return (
    <svg viewBox="0 0 320 70" className="mc-fan" role="img" aria-label={es ? 'Esperanza de 200 entradas aleatorias' : 'Expectancy of 200 random entries'}>
      <rect x={x(percentiles['5'])} y="22" width={x(percentiles['95']) - x(percentiles['5'])} height="16" fill="var(--line)" />
      <rect x={x(percentiles['25'])} y="22" width={x(percentiles['75']) - x(percentiles['25'])} height="16" fill="var(--muted)" opacity="0.5" />
      <line x1={x(percentiles['50'])} x2={x(percentiles['50'])} y1="18" y2="42" stroke="var(--ink)" strokeWidth="2" />
      <line x1={x(baseline)} x2={x(baseline)} y1="10" y2="50" stroke="var(--accent)" strokeWidth="3" />
      <text x={x(baseline)} y="62" fontSize="10" textAnchor="middle" fill="var(--accent)" className="mono">V1.1 {baseline.toFixed(2)}R</text>
      <text x={x(percentiles['5'])} y="14" fontSize="9" fill="var(--muted)" className="mono">p5</text>
      <text x={x(percentiles['95'])} y="14" fontSize="9" textAnchor="end" fill="var(--muted)" className="mono">p95</text>
      <text x={x(percentiles['50'])} y="14" fontSize="9" textAnchor="middle" fill="var(--muted)" className="mono">{es ? 'mediana del azar' : 'chance median'}</text>
    </svg>
  );
}
