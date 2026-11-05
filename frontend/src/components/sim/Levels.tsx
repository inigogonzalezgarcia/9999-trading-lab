import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { formatR } from '../../api';
import { LEVELS, SIM_RUN } from '../../content/sim';
import type { Question } from '../../content/lessons';
import { useT } from '../../i18n';
import { readSim, writeSim } from '../../progress';
import { Link } from '../../router';
import type { BacktestResult, Candle, Trade, TradeExplainer } from '../../types';
import { useRun } from '../LessonWidgets';
import { Quiz } from '../Quiz';
import { ExplainerChart } from '../TradeExplainer';
import { BigCandle, CandleStrip, hhmm } from './CandleStrip';

/* ---------------------------------------------------------------- shared frame */

export function LevelFrame({ n, intro, children, questions, noteHint }:
  { n: number; intro: ReactNode; children: ReactNode; questions: Question[]; noteHint: string }) {
  const { lang, pick } = useT();
  const level = LEVELS[n];
  const [progress, setProgress] = useState(readSim());
  const saved = progress[String(n)] ?? {};
  const [note, setNote] = useState(saved.note ?? '');
  const es = lang === 'es';
  const next = LEVELS[n + 1];
  return (
    <main className="prose sim">
      <p className="kicker">{es ? `Nivel ${n} · ${level.pro ? 'Lab Pro' : 'Gratis'} · ${level.minutes} min` : `Level ${n} · ${level.pro ? 'Lab Pro' : 'Free'} · ${level.minutes} min`}</p>
      <h1 className="page-title">{pick(level.title)}</h1>
      <div className="lead">{intro}</div>
      {children}
      {questions.length
        ? <Quiz questions={questions} onScore={(ok, total) => setProgress(writeSim(n, { score: { ok, total, at: new Date().toISOString() } }))} />
        : <p className="notice">{es ? 'El cuestionario se abre cuando llegues a la entrada y hagas tu predicción.' : 'The quiz opens once you reach the entry and make your prediction.'}</p>}
      <section className="labnote">
        <h2>{es ? 'Tu nota de laboratorio' : 'Your lab note'}</h2>
        <p className="muted small">{noteHint}</p>
        <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={4} placeholder={es ? 'Dos o tres frases con tus palabras.' : 'Two or three sentences in your own words.'} />
        <div className="row-actions">
          <button type="button" onClick={() => setProgress(writeSim(n, { note }))}>{es ? 'Guardar nota' : 'Save note'}</button>
          {saved.note && <span className="muted small">{es ? 'Guardada en este navegador.' : 'Saved in this browser.'}</span>}
        </div>
      </section>
      <div className="row-actions sim-nav">
        <Link to="/app" className="button ghost">{es ? '← Panel' : '← Dashboard'}</Link>
        {saved.completed && next && (next.ready
          ? <Link to={`/app/sim/${next.n}`} className="button">{es ? `Siguiente: nivel ${next.n}` : `Next: level ${next.n}`} →</Link>
          : <Link to="/planes" className="button">{es ? `Nivel ${next.n} · Lab Pro` : `Level ${next.n} · Lab Pro`} →</Link>)}
        {!saved.completed && <span className="muted small">{es ? 'Supera el cuestionario (60 %) para desbloquear el siguiente nivel.' : 'Pass the quiz (60 %) to unlock the next level.'}</span>}
      </div>
    </main>
  );
}

function useSimData(): { result: BacktestResult | null; error: string } {
  const { run, error } = useRun(SIM_RUN);
  return { result: run?.kind === 'backtest' ? run.data : null, error };
}

function explainerFor(result: BacktestResult, trade: Trade): TradeExplainer | undefined {
  return result.trade_explainers?.[trade.trade_id];
}

function Loading({ error }: { error: string }) {
  const { lang } = useT();
  return <p className="muted">{error ? (lang === 'es' ? 'No se pudo cargar la ejecución real.' : 'Could not load the real run.') : (lang === 'es' ? 'Cargando datos reales…' : 'Loading real data…')}</p>;
}

/* ---------------------------------------------------------------- level 0: read a candle */

export function Level0() {
  const { lang } = useT();
  const es = lang === 'es';
  const { result, error } = useSimData();
  const [selected, setSelected] = useState<number | null>(null);
  const [reveal, setReveal] = useState(false);
  const data = useMemo(() => {
    if (!result?.trades.length) return null;
    const ex = explainerFor(result, result.trades[0]);
    if (!ex) return null;
    const entryIndex = ex.candles.findIndex((c) => c.time >= (ex.steps.find((s) => s.id === 'entry')?.time ?? 0));
    const start = Math.max(0, entryIndex - 30);
    return { candles: ex.candles.slice(start, start + 48), trade: result.trades[0] };
  }, [result]);
  useEffect(() => { if (data && selected == null) setSelected(20); }, [data, selected]);
  if (!data) return <main className="prose sim"><Loading error={error} /></main>;
  const candle: Candle = data.candles[selected ?? 20];
  const up = candle.close >= candle.open;
  const questions: Question[] = [
    { id: 'l0q1', prompt: { es: `La vela seleccionada (${hhmm(candle.time)}) abre en ${candle.open.toFixed(5)} y cierra en ${candle.close.toFixed(5)}. ¿Es alcista o bajista?`, en: `The selected candle (${hhmm(candle.time)}) opens at ${candle.open.toFixed(5)} and closes at ${candle.close.toFixed(5)}. Bullish or bearish?` },
      options: { es: ['Alcista: cierra por encima de la apertura', 'Bajista: cierra por debajo de la apertura', 'No se puede saber sin el volumen'], en: ['Bullish: closes above the open', 'Bearish: closes below the open', 'Cannot tell without volume'] },
      answer: up ? 0 : 1, explanation: { es: 'Alcista o bajista lo decide solo la relación entre apertura y cierre; las mechas cuentan hasta dónde llegó el precio dentro del minuto.', en: 'Bullish or bearish is decided only by open versus close; the wicks tell how far price travelled within the minute.' } },
    { id: 'l0q2', prompt: { es: '¿Cuántas velas de 1 minuto (M1) forman una vela de 15 minutos (M15)?', en: 'How many 1-minute candles (M1) make one 15-minute candle (M15)?' },
      options: { es: ['4', '15', '60'], en: ['4', '15', '60'] }, answer: 1,
      explanation: { es: 'Quince. La apertura de la M15 es la apertura de la primera M1; el cierre, el de la última; máximo y mínimo, los extremos de las quince.', en: 'Fifteen. The M15 open is the first M1 open; its close, the last M1 close; high and low, the extremes of the fifteen.' } },
    { id: 'l0q3', prompt: { es: 'El motor del laboratorio toma decisiones con velas M15 cerradas. La vela M15 de las 09:00 (hora de Madrid), ¿cuándo existe por primera vez para el motor?', en: 'The lab engine decides on closed M15 candles. When does the 09:00 M15 candle (Madrid time) first exist for the engine?' },
      options: { es: ['A las 09:00:00, cuando abre', 'A las 09:15:00, cuando cierra', 'A las 09:07, a mitad de vela'], en: ['At 09:00:00, when it opens', 'At 09:15:00, when it closes', 'At 09:07, halfway through'] }, answer: 1,
      explanation: { es: 'Hasta que cierra, su máximo, mínimo y cierre no existen. Usarlos antes es mirar el futuro: la trampa del nivel 1.', en: 'Until it closes, its high, low and close do not exist. Using them earlier is looking at the future: the trap of level 1.' } },
  ];
  return (
    <LevelFrame n={0} questions={questions}
      intro={<p>{es ? 'Estas son velas reales de EUR/USD, minuto a minuto, del día de la primera operación de 2024 de la hipótesis V1.1. Pasa el ratón o toca una vela para ver sus cuatro números; pulsa una para estudiarla en grande.' : 'These are real EUR/USD candles, minute by minute, from the day of the first 2024 trade of hypothesis V1.1. Hover or tap a candle to see its four numbers; click one to study it enlarged.'}</p>}
      noteHint={es ? 'Describe con tus palabras qué cuenta una vela y qué no cuenta (por ejemplo: no dice en qué orden se hicieron el máximo y el mínimo).' : 'Describe in your own words what a candle tells and what it does not (for instance: not the order in which high and low were made).'}>
      <section className="sim-block">
        <CandleStrip candles={data.candles} selected={selected} onSelect={(i) => { setSelected(i); setReveal(false); }} />
        <div className="two-col sim-anatomy">
          <BigCandle candle={candle} lang={lang} reveal={reveal} />
          <div>
            <h2>{es ? 'Anatomía de la vela seleccionada' : 'Anatomy of the selected candle'}</h2>
            <p>{es ? 'Cuatro números por minuto: apertura (el primer precio), cierre (el último), máximo y mínimo (hasta dónde llegó). El cuerpo va de apertura a cierre; las mechas, de cuerpo a extremos.' : 'Four numbers per minute: open (the first price), close (the last), high and low (how far it went). The body runs from open to close; the wicks, from body to extremes.'}</p>
            <button type="button" onClick={() => setReveal(!reveal)}>{reveal ? (es ? 'Ocultar etiquetas' : 'Hide labels') : (es ? 'Mostrar etiquetas' : 'Show labels')}</button>
            <p className="muted small">{es ? `Operación real de referencia: ${data.trade.date}, ${data.trade.direction}, ${formatR(data.trade.r_multiple)}. La verás entera en el nivel 2.` : `Reference real trade: ${data.trade.date}, ${data.trade.direction}, ${formatR(data.trade.r_multiple)}. You will see it whole in level 2.`}</p>
          </div>
        </div>
      </section>
    </LevelFrame>
  );
}

/* ---------------------------------------------------------------- level 1: what a backtest is, and look-ahead */

export function Level1() {
  const { lang } = useT();
  const es = lang === 'es';
  const { result, error } = useSimData();
  const data = useMemo(() => {
    if (!result?.trades.length) return null;
    const trade = result.trades[0];
    const ex = explainerFor(result, trade);
    if (!ex) return null;
    const entry = ex.steps.find((s) => s.id === 'entry');
    const entryIndex = ex.candles.findIndex((c) => c.time >= (entry?.time ?? 0));
    const start = Math.max(0, entryIndex - 40);
    const candles = ex.candles.slice(start, start + 70);
    return { candles, trade, ex, entryIndex: entryIndex - start };
  }, [result]);
  const [now, setNow] = useState<number>(10);
  if (!data) return <main className="prose sim"><Loading error={error} /></main>;
  const { candles, ex } = data;
  const nowCandle = candles[Math.min(now, candles.length - 1)];
  const closed = candles.slice(0, now);
  const lastClosed = closed[closed.length - 1];
  const futureHigh = Math.max(...candles.slice(now, now + 15).map((c) => c.high));
  const steps = ex.steps.filter((s) => s.time >= candles[0].time && s.time <= candles[candles.length - 1].time).map((s) => ({ time: s.time, label: es && s.title_es ? s.title_es.split(' ')[0].toLowerCase() : s.id, color: s.id === 'entry' ? 'var(--accent)' : 'var(--muted)' }));
  const questions: Question[] = [
    { id: 'l1q1', prompt: { es: 'Son las 09:15:00 y la vela de las 09:15 acaba de abrir. Un backtest honesto, ¿qué puede usar de esa vela para decidir?', en: 'It is 09:15:00 and the 09:15 candle has just opened. What may an honest backtest use from that candle to decide?' },
      options: { es: ['Solo su apertura', 'Su apertura y su máximo, porque ya se conoce la tendencia', 'Los cuatro valores: están en el fichero de datos'], en: ['Only its open', 'Its open and high, because the trend is known', 'All four values: they are in the data file'] }, answer: 0,
      explanation: { es: 'En el fichero están los cuatro, pero en la vida real a las 09:15:00 solo existía la apertura. El motor del laboratorio solo mira velas cerradas y ejecuta al siguiente precio.', en: 'The file holds all four, but in real life at 09:15:00 only the open existed. The lab engine looks only at closed candles and executes at the next price.' } },
    { id: 'l1q2', prompt: { es: `En la pantalla, con el reloj en ${hhmm(nowCandle.time)}, el máximo de los 15 minutos siguientes es ${futureHigh.toFixed(5)}. Una regla que "entra si el precio va a superar ese máximo" ¿qué es?`, en: `On screen, with the clock at ${hhmm(nowCandle.time)}, the high of the next 15 minutes is ${futureHigh.toFixed(5)}. A rule that "enters if price is going to exceed that high" is what?` },
      options: { es: ['Look-ahead: usa información que aún no existe', 'Una regla válida si se documenta', 'Un filtro de volatilidad'], en: ['Look-ahead: it uses information that does not exist yet', 'A valid rule if documented', 'A volatility filter'] }, answer: 0,
      explanation: { es: 'Cualquier regla que necesite un dato posterior al instante de la decisión invalida el backtest entero, por bien escrita que esté.', en: 'Any rule that needs a datum later than the decision instant invalidates the whole backtest, however well written.' } },
    { id: 'l1q3', prompt: { es: 'Un backtest da +40 % anual sin costes. ¿Qué es lo primero que hay que comprobar?', en: 'A backtest shows +40 % a year with no costs. What is the first thing to check?' },
      options: { es: ['Si el resultado sobrevive a spread, deslizamiento y comisión en cada operación', 'Si el autor tiene seguidores', 'Si el gráfico es bonito'], en: ['Whether it survives spread, slippage and commission on every trade', 'Whether the author has followers', 'Whether the chart looks nice'] }, answer: 0,
      explanation: { es: 'Sin costes casi cualquier regla intradía parece rentable. El laboratorio paga spread, deslizamiento y comisión en cada operación; lo verás en el nivel 4.', en: 'Without costs almost any intraday rule looks profitable. The lab pays spread, slippage and commission on every trade; level 4 shows it.' } },
  ];
  return (
    <LevelFrame n={1} questions={questions}
      intro={<p>{es ? 'Un backtest es un reloj que avanza minuto a minuto por el pasado y solo puede usar lo que ya ha ocurrido. Mueve el reloj: lo que ves es exactamente lo que el motor sabía en ese instante. La vela ámbar es la vela en curso: existe su apertura y nada más.' : 'A backtest is a clock walking minute by minute through the past that may only use what has already happened. Move the clock: what you see is exactly what the engine knew at that instant. The amber candle is the one in progress: its open exists and nothing else.'}</p>}
      noteHint={es ? 'Escribe una regla que parezca razonable pero use información del futuro, y explica por qué es trampa.' : 'Write a rule that sounds reasonable but uses future information, and explain why it is a trap.'}>
      <section className="sim-block">
        <label className="sim-slider">
          <span className="mono">{es ? 'Ahora:' : 'Now:'} {hhmm(nowCandle.time)}</span>
          <input type="range" min={5} max={candles.length - 1} value={now} onChange={(e) => setNow(Number(e.target.value))} />
        </label>
        <CandleStrip candles={candles} revealUntil={nowCandle.time} markers={steps} />
        <div className="tiles sim-tiles">
          <div className="tile"><div className="tile-label">{es ? 'Última vela cerrada' : 'Last closed candle'}</div><div className="tile-value mono">{lastClosed ? hhmm(lastClosed.time) : '—'}</div><div className="small muted">C {lastClosed?.close.toFixed(5)}</div></div>
          <div className="tile"><div className="tile-label">{es ? 'Vela en curso' : 'Candle in progress'}</div><div className="tile-value mono">{hhmm(nowCandle.time)}</div><div className="small muted">{es ? 'solo apertura' : 'open only'} {nowCandle.open.toFixed(5)}</div></div>
          <div className="tile"><div className="tile-label">{es ? 'Lo que el motor NO sabe' : 'What the engine does NOT know'}</div><div className="tile-value mono">{candles.length - now}</div><div className="small muted">{es ? 'velas por venir' : 'candles to come'}</div></div>
        </div>
        <p>{es ? 'Las marcas punteadas son los pasos de la operación real (barrido, zona, impulso, entrada…) y aparecen solo cuando el reloj llega a ellos: el motor los detectó en su momento, con velas cerradas, nunca antes.' : 'The dotted marks are the steps of the real trade (sweep, zone, displacement, entry…) and appear only when the clock reaches them: the engine detected them at the time, on closed candles, never earlier.'}</p>
      </section>
    </LevelFrame>
  );
}

/* ---------------------------------------------------------------- level 2: one trade start to finish */

export function Level2() {
  const { lang } = useT();
  const es = lang === 'es';
  const { result, error } = useSimData();
  const data = useMemo(() => {
    if (!result?.trades.length) return null;
    const trade = [...result.trades].sort((a, b) => b.r_multiple - a.r_multiple)[0];
    const ex = explainerFor(result, trade);
    return ex ? { trade, ex } : null;
  }, [result]);
  const [step, setStep] = useState(0);
  const [guess, setGuess] = useState<string | null>(null);
  if (!data) return <main className="prose sim"><Loading error={error} /></main>;
  const { trade, ex } = data;
  const steps = ex.steps;
  const entryIndex = steps.findIndex((s) => s.id === 'entry');
  const current = steps[Math.min(step, steps.length - 1)];
  const atEntry = step === entryIndex && !guess;
  const seenUntil = Math.max(...steps.slice(0, step + 1).map((s) => s.time));
  const partial: TradeExplainer = { ...ex, candles: ex.candles.filter((c) => c.time <= seenUntil + 60), steps: steps.slice(0, step + 1), levels: step >= entryIndex ? ex.levels : ex.levels.filter((l) => !['entry', 'stop', 'target'].includes(l.id)) };
  const exitReason = trade.exit_reason;
  const expiries = (result?.trades ?? []).filter((t) => t.exit_reason === 'SESSION_EXPIRY').length;
  const total = (result?.trades ?? []).length;
  const questions: Question[] = [
    { id: 'l2q1', prompt: { es: '¿Qué ocurre primero en esta hipótesis?', en: 'What happens first in this hypothesis?' },
      options: { es: ['Un barrido de liquidez: el precio supera un extremo previo y vuelve', 'La entrada', 'La ruptura de estructura (BOS)'], en: ['A liquidity sweep: price exceeds a prior extreme and returns', 'The entry', 'The break of structure (BOS)'] }, answer: 0,
      explanation: { es: 'El orden es fijo y está en el fichero de la hipótesis: barrido → zona → impulso → retroceso → BOS → entrada. Cambiar el orden es otra hipótesis.', en: 'The order is fixed and lives in the hypothesis file: sweep → zone → displacement → retracement → BOS → entry. Changing it is another hypothesis.' } },
    { id: 'l2q2', prompt: { es: `Esta operación salió por ${exitReason === 'TAKE_PROFIT' ? 'objetivo' : exitReason === 'STOP_LOSS' ? 'stop' : 'fin de sesión'} con ${formatR(trade.r_multiple)}. ¿Qué significa ese número?`, en: `This trade exited by ${exitReason === 'TAKE_PROFIT' ? 'target' : exitReason === 'STOP_LOSS' ? 'stop' : 'session expiry'} with ${formatR(trade.r_multiple)}. What does that number mean?` },
      options: { es: ['Veces el riesgo asumido en la operación (distancia al stop)', 'Porcentaje de la cuenta', 'Pips'], en: ['Times the risk taken on the trade (distance to the stop)', 'Percent of the account', 'Pips'] }, answer: 0,
      explanation: { es: 'R es la unidad del laboratorio: +2R es ganar dos veces lo arriesgado; −1R es perder exactamente el riesgo previsto. Hace comparables operaciones con stops distintos.', en: 'R is the lab unit: +2R is winning twice what was risked; −1R is losing exactly the planned risk. It makes trades with different stops comparable.' } },
    { id: 'l2q3', prompt: { es: `En 2024, ${expiries} de las ${total} operaciones cerraron por fin de sesión. ¿Qué implica esa regla?`, en: `In 2024, ${expiries} of the ${total} trades closed at session expiry. What does that rule imply?` },
      options: { es: ['Corta pérdidas y también ganancias: nunca deja operaciones abiertas de un día a otro', 'Garantiza beneficio', 'Es un error del motor'], en: ['It cuts losses and gains alike: never holds a trade overnight', 'It guarantees profit', 'It is an engine bug'] }, answer: 0,
      explanation: { es: 'Por eso la pérdida media es menor que 1R y la ganancia media menor que el objetivo. Es una decisión de diseño, documentada, con su coste.', en: 'That is why the average loss is below 1R and the average win below the target. A documented design decision, with its cost.' } },
  ];
  return (
    <LevelFrame n={2} questions={guess ? questions : []}
      intro={<p>{es ? `Esta es la mejor operación de 2024 de V1.1 (${trade.date}, ${trade.direction}). Avanza paso a paso: el gráfico solo muestra lo que el motor había visto hasta ese momento. En la entrada tendrás que predecir la salida antes de verla.` : `This is V1.1's best trade of 2024 (${trade.date}, ${trade.direction}). Step through it: the chart shows only what the engine had seen by then. At the entry you will have to predict the exit before seeing it.`}</p>}
      noteHint={es ? 'Cuenta la operación en tres frases como si se la explicaras a alguien que no ha visto el gráfico: qué pasó, por qué entró el motor y cómo salió.' : 'Tell the trade in three sentences to someone who has not seen the chart: what happened, why the engine entered and how it exited.'}>
      <section className="sim-block">
        <ExplainerChart explainer={partial} focus={current.id} lang={lang} />
        <div className="sim-step">
          <div className="row-actions">
            <button type="button" className="ghost" disabled={step === 0} onClick={() => setStep(step - 1)}>←</button>
            <strong>{step + 1}/{steps.length} · {es && current.title_es ? current.title_es : current.title}</strong>
            <span className="mono muted small">{current.local}</span>
            <button type="button" disabled={atEntry || step >= steps.length - 1} onClick={() => setStep(step + 1)}>→</button>
          </div>
          <p>{es && current.text_es ? current.text_es : current.text}</p>
          {atEntry && (
            <div className="notice">
              <strong>{es ? 'Antes de seguir: ¿cómo crees que acaba?' : 'Before going on: how do you think it ends?'}</strong>
              <div className="row-actions">
                {(['STOP_LOSS', 'TAKE_PROFIT', 'SESSION_EXPIRY'] as const).map((k) => (
                  <button key={k} type="button" className="ghost" onClick={() => setGuess(k)}>{k === 'STOP_LOSS' ? (es ? 'Toca el stop' : 'Hits the stop') : k === 'TAKE_PROFIT' ? (es ? 'Llega al objetivo' : 'Reaches the target') : (es ? 'Cierra por fin de sesión' : 'Closes at session end')}</button>
                ))}
              </div>
            </div>
          )}
          {guess && step >= entryIndex && (
            <p className={guess === exitReason ? 'good' : 'bad'}>
              {guess === exitReason ? (es ? 'Acertaste. ' : 'Correct. ') : (es ? 'No era eso. ' : 'Not that. ')}
              {es ? `Salida real: ${exitReason === 'TAKE_PROFIT' ? 'objetivo' : exitReason === 'STOP_LOSS' ? 'stop' : 'fin de sesión'}, ${formatR(trade.r_multiple)}. Acertar una no dice nada; en el nivel 5 verás por qué.` : `Real exit: ${exitReason === 'TAKE_PROFIT' ? 'target' : exitReason === 'STOP_LOSS' ? 'stop' : 'session expiry'}, ${formatR(trade.r_multiple)}. Getting one right means nothing; level 5 shows why.`}
            </p>
          )}
        </div>
      </section>
    </LevelFrame>
  );
}
