import { useMemo, useState } from 'react';
import { formatR } from '../../api';
import type { Question } from '../../content/lessons';
import { SIM_RUN } from '../../content/sim';
import { useT } from '../../i18n';
import type { BacktestResult, Trade } from '../../types';
import { useRun } from '../LessonWidgets';
import { Sparkline } from '../Visuals';
import { LevelFrame } from './Levels';

const COMPARE_RUN = 'eurusd-2022-v1_1';

function useBacktest(id: string): { result: BacktestResult | null; error: string } {
  const { run, error } = useRun(id);
  return { result: run?.kind === 'backtest' ? run.data : null, error };
}

/** The five numbers from a list of R multiples, computed in the open so the learner can check every one. */
export function fiveNumbers(rs: number[]) {
  const wins = rs.filter((r) => r > 0); const losses = rs.filter((r) => r <= 0);
  const winRate = rs.length ? wins.length / rs.length : 0;
  const avgWin = wins.length ? wins.reduce((a, b) => a + b, 0) / wins.length : 0;
  const avgLoss = losses.length ? Math.abs(losses.reduce((a, b) => a + b, 0) / losses.length) : 0;
  const expectancy = rs.length ? rs.reduce((a, b) => a + b, 0) / rs.length : 0;
  const grossWin = wins.reduce((a, b) => a + b, 0); const grossLoss = Math.abs(losses.reduce((a, b) => a + b, 0));
  const profitFactor = grossLoss > 0 ? grossWin / grossLoss : null;
  let peak = 0, cum = 0, dd = 0;
  for (const r of rs) { cum += r; peak = Math.max(peak, cum); dd = Math.max(dd, peak - cum); }
  return { n: rs.length, wins: wins.length, winRate, avgWin, avgLoss, expectancy, profitFactor, maxDrawdown: dd, total: cum };
}

const pct = (x: number) => `${Math.round(x * 100)} %`;
const num = (x: number | null, d = 2) => (x == null ? '—' : x.toFixed(d));

function NumberCheck({ label, expected, tolerance, unit, lang, hint }: { label: string; expected: number; tolerance: number; unit?: string; lang: 'es' | 'en'; hint: string }) {
  const [value, setValue] = useState('');
  const [state, setState] = useState<'idle' | 'ok' | 'ko' | 'shown'>('idle');
  const es = lang === 'es';
  const check = () => { const v = Number(value.replace(',', '.')); setState(Number.isFinite(v) && Math.abs(v - expected) <= tolerance ? 'ok' : 'ko'); };
  return (
    <div className={`calc-row ${state}`}>
      <div><strong>{label}</strong><div className="muted small">{hint}</div></div>
      <div className="row-actions">
        <input className="mono" inputMode="decimal" placeholder={unit ?? ''} value={value} onChange={(e) => { setValue(e.target.value); setState('idle'); }} disabled={state === 'ok' || state === 'shown'} />
        {state !== 'ok' && state !== 'shown' && <button type="button" onClick={check}>{es ? 'Comprobar' : 'Check'}</button>}
        {state === 'ko' && <button type="button" className="ghost" onClick={() => setState('shown')}>{es ? 'Ver' : 'Show'}</button>}
        {(state === 'ok' || state === 'shown') && <span className={`mono ${state === 'ok' ? 'good' : 'muted'}`}>{state === 'ok' ? '✓ ' : '= '}{expected.toFixed(2)}{unit ?? ''}</span>}
        {state === 'ko' && <span className="bad small">{es ? 'No cuadra; revisa el cálculo.' : 'Does not match; check the arithmetic.'}</span>}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- level 3: the five numbers */

export function Level3() {
  const { lang } = useT();
  const es = lang === 'es';
  const { result, error } = useBacktest(SIM_RUN);
  const { result: other } = useBacktest(COMPARE_RUN);
  const rs = useMemo(() => result?.trades.map((t) => t.r_multiple) ?? [], [result]);
  const f = useMemo(() => fiveNumbers(rs), [rs]);
  const g = useMemo(() => fiveNumbers(other?.trades.map((t) => t.r_multiple) ?? []), [other]);
  if (!result) return <main className="prose sim"><p className="muted">{error ? (es ? 'No se pudo cargar la ejecución real.' : 'Could not load the real run.') : '…'}</p></main>;
  const curve = rs.reduce<number[]>((acc, r) => [...acc, (acc[acc.length - 1] ?? 0) + r], [0]);
  const questions: Question[] = [
    { id: 'l3q1', prompt: { es: `Acierto ${pct(f.winRate)}, ganancia media ${f.avgWin.toFixed(2)}R, pérdida media ${f.avgLoss.toFixed(2)}R. ¿Qué cifra resume si la regla gana dinero por operación?`, en: `Win rate ${pct(f.winRate)}, average win ${f.avgWin.toFixed(2)}R, average loss ${f.avgLoss.toFixed(2)}R. Which number sums up whether the rule makes money per trade?` },
      options: { es: ['La esperanza: acierto × ganancia media − fallo × pérdida media', 'El acierto: por encima del 50 % es rentable', 'La ganancia media'], en: ['Expectancy: win rate × average win − loss rate × average loss', 'Win rate: above 50 % is profitable', 'Average win'] }, answer: 0,
      explanation: { es: 'Un 40 % de acierto con 2R de ganancia y 1R de pérdida gana; un 70 % con 0,3R y 1R pierde. Solo la esperanza combina las dos cosas.', en: 'A 40 % win rate with 2R wins and 1R losses makes money; 70 % with 0.3R and 1R loses. Only expectancy combines both.' } },
    { id: 'l3q2', prompt: { es: `El profit factor de 2024 es ${num(f.profitFactor)}. ¿Qué dice?`, en: `The 2024 profit factor is ${num(f.profitFactor)}. What does it say?` },
      options: { es: ['Cuánto se ganó en total por cada unidad perdida en total', 'Cuántas operaciones ganadoras hay por cada perdedora', 'El beneficio en porcentaje'], en: ['How much was won in total per unit lost in total', 'How many winning trades per losing trade', 'Profit as a percentage'] }, answer: 0,
      explanation: { es: 'Suma de ganancias dividida por suma de pérdidas. Por debajo de 1, la regla pierde; cerca de 1, cualquier coste extra la hunde (nivel 4).', en: 'Sum of wins divided by sum of losses. Below 1 the rule loses; near 1, any extra cost sinks it (level 4).' } },
    { id: 'l3q3', prompt: { es: `Las mismas cinco cifras en 2022: ${g.n} operaciones, acierto ${pct(g.winRate)}, esperanza ${g.expectancy.toFixed(2)}R, total ${formatR(g.total)}. ¿Qué concluyes de 2024 (${formatR(f.total)}) a la luz de 2022?`, en: `The same five numbers in 2022: ${g.n} trades, win rate ${pct(g.winRate)}, expectancy ${g.expectancy.toFixed(2)}R, total ${formatR(g.total)}. What do you conclude about 2024 (${formatR(f.total)}) in the light of 2022?` },
      options: { es: ['Que doce operaciones de un año no bastan para distinguir ventaja de azar', 'Que 2022 fue un año anómalo y 2024 es el representativo', 'Que la regla funciona en años alcistas'], en: ['That twelve trades in one year cannot tell edge from chance', 'That 2022 was anomalous and 2024 is the representative year', 'That the rule works in bullish years'] }, answer: 0,
      explanation: { es: 'Con tan pocas operaciones, las cinco cifras bailan de un año a otro. Cuántas hacen falta y cómo se mide lo verás en el nivel 5 (Monte Carlo).', en: 'With so few trades the five numbers swing from one year to the next. How many are needed and how to measure it comes in level 5 (Monte Carlo).' } },
  ];
  return (
    <LevelFrame n={3} questions={questions}
      intro={<p>{es ? `Estas son las ${f.n} operaciones reales de V1.1 en EUR/USD 2024, en R. Calcula tú las cinco cifras a partir de la lista (una calculadora basta) y comprueba cada una. Después verás las mismas cinco en 2022.` : `These are the ${f.n} real V1.1 trades on EUR/USD 2024, in R. Compute the five numbers yourself from the list (a calculator is enough) and check each one. Then you will see the same five for 2022.`}</p>}
      noteHint={es ? '¿Cuál de las cinco cifras mirarías primero en un backtest ajeno y por qué? ¿Cuál es la más fácil de maquillar?' : 'Which of the five would you look at first in someone else\'s backtest and why? Which is easiest to dress up?'}>
      <section className="sim-block">
        <div className="r-list mono">
          {rs.map((r, i) => <span key={i} className={r > 0 ? 'good' : 'bad'}>{r >= 0 ? '+' : ''}{r.toFixed(2)}</span>)}
        </div>
        <Sparkline values={curve} width={320} height={60} />
        <div className="calc">
          <NumberCheck lang={lang} label={es ? '1 · Acierto (%)' : '1 · Win rate (%)'} expected={Math.round(f.winRate * 1000) / 10} tolerance={0.6} unit="%" hint={es ? `operaciones con R > 0 dividido por ${f.n}` : `trades with R > 0 divided by ${f.n}`} />
          <NumberCheck lang={lang} label={es ? '2 · Ganancia media (R)' : '2 · Average win (R)'} expected={f.avgWin} tolerance={0.02} unit="R" hint={es ? 'media de las positivas' : 'mean of the positive ones'} />
          <NumberCheck lang={lang} label={es ? '3 · Pérdida media (R)' : '3 · Average loss (R)'} expected={f.avgLoss} tolerance={0.02} unit="R" hint={es ? 'media de las negativas, en valor absoluto (menor que 1: las salidas por sesión recortan pérdidas)' : 'mean of the negative ones, absolute value (below 1: session exits cut losses)'} />
          <NumberCheck lang={lang} label={es ? '4 · Esperanza (R por operación)' : '4 · Expectancy (R per trade)'} expected={f.expectancy} tolerance={0.02} unit="R" hint={es ? 'media de todas las R; o acierto × ganancia media − (1 − acierto) × pérdida media' : 'mean of all R; or win rate × avg win − (1 − win rate) × avg loss'} />
          <NumberCheck lang={lang} label={es ? '5 · Profit factor' : '5 · Profit factor'} expected={f.profitFactor ?? 0} tolerance={0.03} hint={es ? 'suma de ganancias ÷ suma de pérdidas' : 'sum of wins ÷ sum of losses'} />
          <NumberCheck lang={lang} label={es ? 'Extra · Drawdown máximo (R)' : 'Extra · Max drawdown (R)'} expected={f.maxDrawdown} tolerance={0.05} unit="R" hint={es ? 'mayor caída desde un máximo de la curva acumulada' : 'largest fall from a peak of the cumulative curve'} />
        </div>
        {other && (
          <div className="tiles">
            <div className="tile"><div className="tile-label">2024</div><div className="tile-value">{formatR(f.total)}</div><div className="tile-hint">{f.n} op. · {pct(f.winRate)} · PF {num(f.profitFactor)} · DD {f.maxDrawdown.toFixed(1)}R</div></div>
            <div className="tile bad"><div className="tile-label">2022 · {es ? 'misma regla' : 'same rule'}</div><div className="tile-value">{formatR(g.total)}</div><div className="tile-hint">{g.n} op. · {pct(g.winRate)} · PF {num(g.profitFactor)} · DD {g.maxDrawdown.toFixed(1)}R</div></div>
          </div>
        )}
      </section>
    </LevelFrame>
  );
}

/* ---------------------------------------------------------------- level 4: costs */

const PIP = 0.0001;
const riskPips = (t: Trade) => Math.abs(t.entry_price - t.stop_price) / PIP;

export function Level4() {
  const { lang } = useT();
  const es = lang === 'es';
  const { result, error } = useBacktest(SIM_RUN);
  const [spread, setSpread] = useState<number | null>(null);
  const [slippage, setSlippage] = useState<number | null>(null);
  const trades = result?.trades ?? [];
  const paid = useMemo(() => {
    if (!trades.length) return { spread: 0, slippage: 0, risk: 0 };
    const avg = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;
    return { spread: avg(trades.map((t) => t.spread_pips)), slippage: avg(trades.map((t) => t.slippage_pips)), risk: avg(trades.map(riskPips)) };
  }, [trades]);
  const s = spread ?? paid.spread; const sl = slippage ?? paid.slippage;
  // Linear approximation: each extra pip of spread or slippage costs 1/risk_pips R on that trade (paid once per round trip).
  const adjusted = useMemo(() => trades.map((t) => t.r_multiple - ((s - t.spread_pips) + (sl - t.slippage_pips)) / riskPips(t)), [trades, s, sl]);
  const free = useMemo(() => trades.map((t) => t.r_multiple + (t.spread_pips + t.slippage_pips) / riskPips(t)), [trades]);
  if (!result) return <main className="prose sim"><p className="muted">{error ? (es ? 'No se pudo cargar la ejecución real.' : 'Could not load the real run.') : '…'}</p></main>;
  const actual = fiveNumbers(trades.map((t) => t.r_multiple)); const adj = fiveNumbers(adjusted); const noCost = fiveNumbers(free);
  const breakEvenSpread = (() => { // spread at which the year's total hits zero, slippage as paid
    const sens = trades.reduce((a, t) => a + 1 / riskPips(t), 0); // R lost per extra pip across the year
    return paid.spread + actual.total / sens;
  })();
  const questions: Question[] = [
    { id: 'l4q1', prompt: { es: `Sin ningún coste, 2024 habría dado ${formatR(noCost.total)}; con los costes reales dio ${formatR(actual.total)}. ¿Qué parte del resultado bruto se llevaron los costes?`, en: `With no costs, 2024 would have given ${formatR(noCost.total)}; with real costs it gave ${formatR(actual.total)}. What share of the gross result did costs take?` },
      options: { es: [`${Math.round((1 - actual.total / noCost.total) * 100)} %`, 'Menos del 5 %', 'Nada: el spread solo afecta a scalping'], en: [`${Math.round((1 - actual.total / noCost.total) * 100)} %`, 'Under 5 %', 'None: spread only matters for scalping'] }, answer: 0,
      explanation: { es: `Con stops de ${paid.risk.toFixed(0)} pips de media, cada pip de coste es ${(1 / paid.risk).toFixed(3)}R por operación. Parece poco; multiplicado por doce operaciones y restado a un total pequeño, es la mitad del resultado.`, en: `With stops of ${paid.risk.toFixed(0)} pips on average, every pip of cost is ${(1 / paid.risk).toFixed(3)}R per trade. Sounds small; times twelve trades and taken from a small total, it is half the result.` } },
    { id: 'l4q2', prompt: { es: `¿Con qué spread medio el año 2024 pasa a cero (deslizamiento como el pagado)?`, en: `At what average spread does 2024 go to zero (slippage as paid)?` },
      options: { es: [`Alrededor de ${breakEvenSpread.toFixed(1)} pips`, 'Nunca: la regla es rentable con cualquier spread', '10 pips'], en: [`Around ${breakEvenSpread.toFixed(1)} pips`, 'Never: the rule is profitable at any spread', '10 pips'] }, answer: 0,
      explanation: { es: 'Mueve el control y compruébalo. Un bróker minorista en horas de poca liquidez puede dar más que eso: un backtest sin la cifra de spread usada no es evaluable.', en: 'Move the control and check it. A retail broker in thin hours can be worse than that: a backtest that does not state the spread used cannot be evaluated.' } },
    { id: 'l4q3', prompt: { es: 'Un backtest publica +35 % anual y no menciona spread, deslizamiento ni comisión. ¿Qué haces?', en: 'A backtest reports +35 % a year and mentions no spread, slippage or commission. What do you do?' },
      options: { es: ['Pedir los supuestos de costes y reconstruir el resultado con cifras realistas antes de creer nada', 'Restar un 5 % y seguir', 'Asumir que ya están incluidos'], en: ['Ask for the cost assumptions and rebuild the result with realistic figures before believing anything', 'Subtract 5 % and move on', 'Assume they are included'] }, answer: 0,
      explanation: { es: 'El laboratorio registra en cada operación el spread pagado y su fuente (columna del proveedor en 2024; 0,3 pips fijos en los años HistData). Sin eso, el número no significa nada.', en: 'The lab records on every trade the spread paid and its source (provider column in 2024; 0.3 pips fixed in HistData years). Without that, the number means nothing.' } },
  ];
  return (
    <LevelFrame n={4} questions={questions}
      intro={<p>{es ? `Cada operación de 2024 pagó spread (${paid.spread.toFixed(2)} pips de media, de la columna real del proveedor), deslizamiento (${paid.slippage.toFixed(1)} pips); la comisión de este proveedor va dentro del spread. Con stops de ${paid.risk.toFixed(0)} pips de media, cada pip vale ${(1 / paid.risk).toFixed(3)}R. Mueve los costes y mira qué le pasa al año.` : `Every 2024 trade paid spread (${paid.spread.toFixed(2)} pips on average, from the provider's real column), slippage (${paid.slippage.toFixed(1)} pips); this provider's commission is inside the spread. With stops of ${paid.risk.toFixed(0)} pips on average, each pip is worth ${(1 / paid.risk).toFixed(3)}R. Move the costs and watch what happens to the year.`}</p>}
      noteHint={es ? 'Escribe los supuestos de costes que exigirías ver en cualquier backtest antes de leer su resultado.' : 'Write the cost assumptions you would demand to see in any backtest before reading its result.'}>
      <section className="sim-block">
        <div className="knobs">
          <label className="knob"><span className="tile-label">{es ? 'Spread medio (pips)' : 'Average spread (pips)'} · {s.toFixed(1)}</span><input type="range" min={0} max={4} step={0.1} value={s} onChange={(e) => setSpread(Number(e.target.value))} /></label>
          <label className="knob"><span className="tile-label">{es ? 'Deslizamiento (pips)' : 'Slippage (pips)'} · {sl.toFixed(1)}</span><input type="range" min={0} max={3} step={0.1} value={sl} onChange={(e) => setSlippage(Number(e.target.value))} /></label>
          <button type="button" className="ghost" onClick={() => { setSpread(null); setSlippage(null); }}>{es ? 'Costes reales' : 'Real costs'}</button>
          <button type="button" className="ghost" onClick={() => { setSpread(0); setSlippage(0); }}>{es ? 'Sin costes' : 'No costs'}</button>
        </div>
        <div className="tiles">
          <div className={`tile ${adj.total > 0 ? 'good' : 'bad'}`}><div className="tile-label">2024 {es ? 'con estos costes' : 'with these costs'}</div><div className="tile-value">{formatR(adj.total)}</div><div className="tile-hint">{es ? 'esperanza' : 'expectancy'} {adj.expectancy.toFixed(2)}R · PF {num(adj.profitFactor)}</div></div>
          <div className="tile"><div className="tile-label">{es ? 'Con los costes reales' : 'With real costs'}</div><div className="tile-value">{formatR(actual.total)}</div><div className="tile-hint">{es ? 'lo que publica el laboratorio' : 'what the lab publishes'}</div></div>
          <div className="tile"><div className="tile-label">{es ? 'Sin costes' : 'No costs'}</div><div className="tile-value">{formatR(noCost.total)}</div><div className="tile-hint">{es ? 'lo que publicaría un backtest ingenuo' : 'what a naive backtest would publish'}</div></div>
          <div className="tile"><div className="tile-label">{es ? 'Spread de equilibrio' : 'Break-even spread'}</div><div className="tile-value mono">{breakEvenSpread.toFixed(1)} pips</div><div className="tile-hint">{es ? 'donde el año pasa a 0R' : 'where the year goes to 0R'}</div></div>
        </div>
        <p className="muted small">{es ? 'Aproximación lineal sobre las operaciones reales: cada pip extra resta 1/stop(pips) R a esa operación. El motor real recalcula entradas y salidas con el spread de cada minuto; para enseñar la sensibilidad, esta aproximación basta.' : 'Linear approximation on the real trades: each extra pip takes 1/stop(pips) R from that trade. The real engine recomputes entries and exits with each minute\'s spread; to show the sensitivity, this approximation is enough.'}</p>
      </section>
    </LevelFrame>
  );
}
