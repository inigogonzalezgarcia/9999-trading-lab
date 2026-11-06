import { useEffect, useMemo, useState } from 'react';
import { api, formatR } from '../../api';
import type { Question } from '../../content/lessons';
import { useT } from '../../i18n';
import type { ResearchReport } from '../../types';
import { LevelFrame } from './Levels';

const YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
const researchId = (y: number) => `eurusd-${y}-v1_1-research`;

const PARAM_LABEL: Record<string, { es: string; en: string }> = {
  'target.baseline': { es: 'Objetivo', en: 'Target' },
  'stop.reference': { es: 'Referencia del stop', en: 'Stop reference' },
  'stop.max_distance_atr': { es: 'Distancia máx. del stop (ATR)', en: 'Max stop distance (ATR)' },
  'setup.lifetime_m15_bars_from_sweep_confirmation': { es: 'Vida del setup (M15)', en: 'Setup lifetime (M15)' },
  'displacement.minimum_atr': { es: 'Impulso mínimo (ATR)', en: 'Minimum displacement (ATR)' },
  'liquidity.level_max_age_m15_bars': { es: 'Edad máx. del nivel (M15)', en: 'Max level age (M15)' },
  'zones.expiry_m15_bars': { es: 'Caducidad de la zona (M15)', en: 'Zone expiry (M15)' },
  'slippage.baseline_pips': { es: 'Deslizamiento (pips)', en: 'Slippage (pips)' },
  'risk.baseline_equity_risk_fraction': { es: 'Riesgo por operación', en: 'Risk per trade' },
  session: { es: 'Sesión', en: 'Session' },
};

type Variant = NonNullable<ResearchReport['sensitivity']>['variants'][number];

export function Level7() {
  const { lang } = useT();
  const es = lang === 'es';
  const [reports, setReports] = useState<Record<number, ResearchReport>>({});
  const [year, setYear] = useState(2024);
  const [param, setParam] = useState('target.baseline');
  useEffect(() => {
    let alive = true;
    (async () => {
      for (const y of [2024, ...YEARS.filter((v) => v !== 2024)]) {
        try { const { result } = await api.run(researchId(y)); if (alive) setReports((r) => ({ ...r, [y]: result as ResearchReport })); } catch { /* year without report */ }
      }
    })();
    return () => { alive = false; };
  }, []);
  const report = reports[year];
  const params = useMemo(() => {
    const seen: string[] = [];
    for (const v of report?.sensitivity?.variants ?? []) if (!seen.includes(v.parameter)) seen.push(v.parameter);
    return seen;
  }, [report]);
  const variants: Variant[] = useMemo(() => (report?.sensitivity?.variants ?? []).filter((v) => v.parameter === param && !v.error), [report, param]);
  const baseline = report?.baseline;
  // Eight-year view of the same parameter: sum of total_r over every loaded year, per value.
  const pooled = useMemo(() => {
    const byValue = new Map<string, { total: number; trades: number; years: number }>();
    for (const r of Object.values(reports)) {
      for (const v of r.sensitivity?.variants ?? []) {
        if (v.parameter !== param || v.error) continue;
        const key = String(v.value);
        const cur = byValue.get(key) ?? { total: 0, trades: 0, years: 0 };
        byValue.set(key, { total: cur.total + (v.total_r ?? 0), trades: cur.trades + (v.trades ?? 0), years: cur.years + 1 });
      }
    }
    const baseTotal = Object.values(reports).reduce((a, r) => a + r.baseline.total_r, 0);
    return { rows: [...byValue.entries()], baseTotal, years: Object.keys(reports).length };
  }, [reports, param]);
  const swing = variants.length ? Math.max(...variants.map((v) => v.total_r ?? 0)) - Math.min(...variants.map((v) => v.total_r ?? 0)) : 0;
  const wf = report?.walk_forward;
  const wfPooled = useMemo(() => Object.values(reports).reduce((a, r) => { const c = r.walk_forward?.out_of_sample_concatenated; return c ? { trades: a.trades + c.trades, total: a.total + c.total_r, folds: a.folds + c.folds_with_trades, positive: a.positive + c.folds_positive } : a; }, { trades: 0, total: 0, folds: 0, positive: 0 }), [reports]);
  if (!report) return <main className="prose sim"><p className="muted">{es ? 'Cargando los informes de investigación…' : 'Loading the research reports…'}</p></main>;
  const pooledPositive = pooled.rows.filter(([, r]) => r.total > 0).length;
  const questions: Question[] = [
    { id: 'l7q1', prompt: { es: `En 2024, cambiar «${PARAM_LABEL['target.baseline'].es}» mueve el año entre ${formatR(Math.min(...(report.sensitivity?.variants.filter((v) => v.parameter === 'target.baseline').map((v) => v.total_r ?? 0) ?? [0])))} y ${formatR(Math.max(...(report.sensitivity?.variants.filter((v) => v.parameter === 'target.baseline').map((v) => v.total_r ?? 0) ?? [0])))}. ¿Qué es la fragilidad?`, en: `In 2024, changing "${PARAM_LABEL['target.baseline'].en}" moves the year between ${formatR(Math.min(...(report.sensitivity?.variants.filter((v) => v.parameter === 'target.baseline').map((v) => v.total_r ?? 0) ?? [0])))} and ${formatR(Math.max(...(report.sensitivity?.variants.filter((v) => v.parameter === 'target.baseline').map((v) => v.total_r ?? 0) ?? [0])))}. What is fragility?` },
      options: { es: ['Que el resultado dependa mucho de un valor concreto de un parámetro: vecinos razonables dan resultados muy distintos', 'Que la regla tenga muchos parámetros', 'Que el resultado sea negativo'], en: ['That the result depends heavily on one specific parameter value: reasonable neighbours give very different results', 'That the rule has many parameters', 'That the result is negative'] }, answer: 0,
      explanation: { es: 'Una ventaja real suele ser una meseta: valores vecinos dan resultados parecidos. Un pico aislado es, casi siempre, azar o sobreajuste.', en: 'A real edge is usually a plateau: neighbouring values give similar results. An isolated peak is, almost always, chance or overfitting.' } },
    { id: 'l7q2', prompt: { es: `Sumando los ${pooled.years} años, ¿cuántos valores de «${PARAM_LABEL[param]?.es ?? param}» acaban en positivo?`, en: `Adding the ${pooled.years} years, how many values of "${PARAM_LABEL[param]?.en ?? param}" end positive?` },
      options: { es: [`${pooledPositive}`, 'Todos los que ganan en 2024', 'La mitad'], en: [`${pooledPositive}`, 'All those that win in 2024', 'Half'] }, answer: 0,
      explanation: { es: 'Lo que parece una mejora en un año desaparece al sumar ocho. Es la misma lección que la rejilla del nivel 8, parámetro a parámetro.', en: 'What looks like an improvement in one year vanishes when eight are added. Same lesson as the level-8 grid, one parameter at a time.' } },
    { id: 'l7q3', prompt: { es: `Walk-forward sumando los ${pooled.years} años: ${wfPooled.trades} operaciones fuera de muestra, ${formatR(wfPooled.total)}, ${wfPooled.positive} de ${wfPooled.folds} ventanas en positivo. ¿Qué pregunta responde el walk-forward que no responde el backtest entero?`, en: `Walk-forward over the ${pooled.years} years: ${wfPooled.trades} out-of-sample trades, ${formatR(wfPooled.total)}, ${wfPooled.positive} of ${wfPooled.folds} windows positive. Which question does walk-forward answer that the whole backtest does not?` },
      options: { es: ['Si lo que funcionó en un tramo sigue funcionando en el tramo siguiente, que nunca se vio al decidir', 'Cuál es el mejor parámetro', 'Cuánto se ganó en total'], en: ['Whether what worked in one stretch keeps working in the next, never seen when deciding', 'Which parameter is best', 'How much was made in total'] }, answer: 0,
      explanation: { es: 'Fuera de muestra es lo único que se parece al futuro. Aquí, la mitad de las ventanas en positivo y un total cerca de cero: lo que cabe esperar del azar.', en: 'Out of sample is the only thing that resembles the future. Here, half the windows positive and a total near zero: what chance would give.' } },
  ];
  const vals = variants.map((v) => v.total_r ?? 0).concat(baseline ? [baseline.total_r] : []);
  const lo = Math.min(0, ...vals), hi = Math.max(0, ...vals);
  const x = (v: number) => ((v - lo) / (hi - lo || 1)) * 100;
  return (
    <LevelFrame n={7} questions={questions}
      intro={<p>{es ? 'Dos pruebas de robustez del laboratorio, con sus datos reales. Primera: mover un parámetro cada vez (con el resto fijo) y ver cuánto se mueve el año; después sumar los ocho años. Segunda: walk-forward, ventanas rodantes de 120 días para decidir y 30 para comprobar, en las que lo comprobado nunca se vio al decidir.' : 'Two robustness checks from the lab, with its real data. First: move one parameter at a time (the rest fixed) and see how much the year moves; then add the eight years. Second: walk-forward, rolling windows of 120 days to decide and 30 to check, where the checked stretch was never seen when deciding.'}</p>}
      noteHint={es ? 'Describe qué forma tendría la tabla de sensibilidad de una regla con ventaja real, y en qué se diferencia de la que ves.' : 'Describe what the sensitivity table of a rule with a real edge would look like, and how it differs from the one you see.'}>
      <section className="sim-block">
        <div className="knobs">
          <label className="knob"><span className="tile-label">{es ? 'Año' : 'Year'}</span><select value={year} onChange={(e) => setYear(Number(e.target.value))}>{YEARS.map((y) => <option key={y} value={y} disabled={!reports[y]}>{y}{y === 2026 ? (es ? ' (hasta oct.)' : ' (to Oct.)') : ''}</option>)}</select></label>
          <label className="knob"><span className="tile-label">{es ? 'Parámetro' : 'Parameter'}</span><select value={param} onChange={(e) => setParam(e.target.value)}>{params.map((p) => <option key={p} value={p}>{PARAM_LABEL[p]?.[lang] ?? p}</option>)}</select></label>
        </div>
        <h2>{es ? `Sensibilidad en ${year}` : `Sensitivity in ${year}`} <span className="muted small">· {es ? 'oscilación' : 'swing'} {swing.toFixed(1)}R</span></h2>
        <div className="sens">
          {baseline && <div className="sens-row base"><span className="sens-label mono">V1.1</span><div className="sens-bar"><span style={{ left: `${Math.min(x(0), x(baseline.total_r))}%`, width: `${Math.abs(x(baseline.total_r) - x(0))}%` }} className={baseline.total_r >= 0 ? 'good-bg' : 'bad-bg'} /></div><span className="mono small">{formatR(baseline.total_r)} · {baseline.trades} op.</span></div>}
          {variants.map((v) => (
            <div key={String(v.value)} className="sens-row"><span className="sens-label mono">{String(v.value)}</span><div className="sens-bar"><span style={{ left: `${Math.min(x(0), x(v.total_r ?? 0))}%`, width: `${Math.abs(x(v.total_r ?? 0) - x(0))}%` }} className={(v.total_r ?? 0) >= 0 ? 'good-bg' : 'bad-bg'} /></div><span className="mono small">{formatR(v.total_r ?? 0)} · {v.trades ?? 0} op.</span></div>
          ))}
        </div>
        <h2>{es ? `El mismo parámetro sumando ${pooled.years} años` : `The same parameter over ${pooled.years} years`}</h2>
        <table className="plan-table small">
          <thead><tr><th>{es ? 'Valor' : 'Value'}</th><th>{es ? 'Op.' : 'Trades'}</th><th>{es ? 'Total R' : 'Total R'}</th><th>{es ? 'Frente a V1.1' : 'Versus V1.1'}</th></tr></thead>
          <tbody>
            <tr className="base"><td className="mono">V1.1</td><td>—</td><td className={pooled.baseTotal > 0 ? 'good' : 'bad'}>{formatR(pooled.baseTotal)}</td><td>—</td></tr>
            {pooled.rows.map(([value, r]) => <tr key={value}><td className="mono">{value}</td><td>{r.trades}</td><td className={r.total > 0 ? 'good' : 'bad'}>{formatR(r.total)}</td><td className="mono">{formatR(r.total - pooled.baseTotal)}</td></tr>)}
          </tbody>
        </table>
        {wf && (
          <>
            <h2>{es ? `Walk-forward en ${year}` : `Walk-forward in ${year}`} <span className="muted small">· {wf.parameters.train_days as number} + {wf.parameters.test_days as number} {es ? 'días' : 'days'}</span></h2>
            <table className="plan-table small">
              <thead><tr><th>{es ? 'Ventana' : 'Window'}</th><th>{es ? 'Decidir (op. · R)' : 'Decide (trades · R)'}</th><th>{es ? 'Comprobar (op. · R)' : 'Check (trades · R)'}</th></tr></thead>
              <tbody>
                {wf.folds.map((f) => <tr key={f.fold}><td className="mono">{f.fold}</td><td className="mono">{f.in_sample.trades} · {formatR(f.in_sample.total_r)}</td><td className={`mono ${f.out_of_sample.trades === 0 ? 'muted' : f.out_of_sample.total_r > 0 ? 'good' : 'bad'}`}>{f.out_of_sample.trades === 0 ? (es ? 'sin op.' : 'no trades') : `${f.out_of_sample.trades} · ${formatR(f.out_of_sample.total_r)}`}</td></tr>)}
              </tbody>
            </table>
            <div className="tiles">
              <div className="tile"><div className="tile-label">{es ? `Fuera de muestra ${year}` : `Out of sample ${year}`}</div><div className="tile-value">{formatR(wf.out_of_sample_concatenated.total_r)}</div><div className="tile-hint">{wf.out_of_sample_concatenated.trades} op. · {wf.out_of_sample_concatenated.folds_positive}/{wf.out_of_sample_concatenated.folds_with_trades} {es ? 'ventanas en positivo' : 'windows positive'}</div></div>
              <div className="tile"><div className="tile-label">{es ? `Fuera de muestra, ${pooled.years} años` : `Out of sample, ${pooled.years} years`}</div><div className="tile-value">{formatR(wfPooled.total)}</div><div className="tile-hint">{wfPooled.trades} op. · {wfPooled.positive}/{wfPooled.folds} {es ? 'ventanas en positivo' : 'windows positive'}</div></div>
            </div>
          </>
        )}
      </section>
    </LevelFrame>
  );
}
