import { useEffect, useMemo, useState } from 'react';
import { formatR } from '../../api';
import type { Question } from '../../content/lessons';
import { useT } from '../../i18n';
import { DATA_BASE } from '../../site';
import { Sparkline } from '../Visuals';
import { LevelFrame } from './Levels';

/* The grid precomputed by scripts/export_grid.py: every combination of the five knobs, run with the real engine
   and all costs on 2019–2026. The browser never backtests; it looks up the cell. */
interface Axis { id: string; label: { es: string; en: string }; values: (string | number)[] }
interface ComboRow { id: string; choice: Record<string, string | number>; trades: number; total_r: number; expectancy_r: number | null; years_positive: number; years: number; worst_year_r: number | null; best_year_r: number | null }
interface GridIndex { years: number[]; axes: Axis[]; baseline: Record<string, string | number>; baseline_id: string; combos: ComboRow[]; notice: string }
interface YearSummary { trades: number; total_r: number; expectancy_r: number; win_rate: number; profit_factor: number | null; max_drawdown_r: number; trades_r: number[]; exit_reasons: Record<string, number> }
interface ComboFile { id: string; choice: Record<string, string | number>; years: Record<string, YearSummary> }

const VALUE_LABEL: Record<string, { es: string; en: string }> = {
  sweep_extreme: { es: 'extremo del barrido', en: 'sweep extreme' },
  zone_distal: { es: 'borde lejano de la zona', en: 'zone far edge' },
  leg1_origin: { es: 'origen del primer tramo', en: 'origin of leg 1' },
  london: { es: 'Londres (09:00–13:00)', en: 'London (09:00–13:00)' },
  new_york: { es: 'Nueva York (15:00–19:00)', en: 'New York (15:00–19:00)' },
};
const label = (v: string | number, lang: 'es' | 'en') => VALUE_LABEL[String(v)]?.[lang] ?? String(v);
const sameChoice = (a: Record<string, string | number>, b: Record<string, string | number>) => Object.keys(a).every((k) => String(a[k]) === String(b[k]));

export function Level8() {
  const { lang } = useT();
  const es = lang === 'es';
  const [index, setIndex] = useState<GridIndex | null>(null);
  const [error, setError] = useState('');
  const [choice, setChoice] = useState<Record<string, string | number> | null>(null);
  const [cell, setCell] = useState<ComboFile | null>(null);
  const [revealRank, setRevealRank] = useState(false);

  useEffect(() => {
    fetch(`${DATA_BASE}grid/index.json`).then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
      .then((data: GridIndex) => { setIndex(data); setChoice(data.baseline); })
      .catch(() => setError('index'));
  }, []);

  const row = useMemo(() => (index && choice ? index.combos.find((c) => sameChoice(c.choice, choice)) ?? null : null), [index, choice]);
  const baselineRow = useMemo(() => index?.combos.find((c) => c.id === index.baseline_id) ?? null, [index]);
  const ranked = useMemo(() => (index ? [...index.combos].sort((a, b) => b.total_r - a.total_r) : []), [index]);
  const rank = row ? ranked.findIndex((c) => c.id === row.id) + 1 : 0;
  const positive = index ? index.combos.filter((c) => c.total_r > 0).length : 0;

  useEffect(() => {
    if (!row) return;
    setCell(null);
    fetch(`${DATA_BASE}grid/${row.id}.json`).then((r) => r.json()).then(setCell).catch(() => setCell(null));
  }, [row]);

  if (error) return <main className="prose sim"><p className="muted">{es ? 'La rejilla de resultados todavía no está publicada.' : 'The results grid is not published yet.'}</p></main>;
  if (!index || !choice) return <main className="prose sim"><p className="muted">{es ? 'Cargando la rejilla (162 versiones ya calculadas)…' : 'Loading the grid (162 versions already computed)…'}</p></main>;

  const isBaseline = row?.id === index.baseline_id;
  const yearsSorted = cell ? Object.keys(cell.years).sort() : [];
  const curve = cell ? yearsSorted.reduce<number[]>((acc, y) => { const last = acc[acc.length - 1] ?? 0; return [...acc, last + cell.years[y].total_r]; }, [0]) : [];

  const questions: Question[] = [
    { id: 'l8q1', prompt: { es: `De las ${index.combos.length} versiones de la rejilla, ¿cuántas acaban en positivo en ocho años?`, en: `Of the ${index.combos.length} versions in the grid, how many end positive over eight years?` },
      options: { es: [`${positive}`, 'Alrededor de la mitad', 'Casi todas si se elige bien el stop'], en: [`${positive}`, 'About half', 'Almost all if the stop is chosen well'] }, answer: 0,
      explanation: { es: `${positive}. Mover cinco mandos entre valores razonables no produce una versión rentable: la hipótesis no tiene ventaja que afinar.`, en: `${positive}. Moving five knobs among reasonable values does not produce a profitable version: the hypothesis has no edge to tune.` } },
    { id: 'l8q2', prompt: { es: `La mejor celda de la rejilla hace ${formatR(ranked[0]?.total_r ?? 0)} en ocho años. Si la publicaras como "V1.2 optimizada", ¿qué estarías haciendo?`, en: `The best cell of the grid makes ${formatR(ranked[0]?.total_r ?? 0)} over eight years. If you published it as "optimised V1.2", what would you be doing?` },
      options: { es: ['Sobreajuste: elegir a posteriori la celda que mejor quedó en estos mismos datos', 'Investigación: la mejor celda es la verdadera estrategia', 'Nada malo si documentas el cambio'], en: ['Overfitting: picking after the fact the cell that happened to look best on this same data', 'Research: the best cell is the true strategy', 'Nothing wrong if you document the change'] }, answer: 0,
      explanation: { es: 'Con 162 intentos sobre los mismos datos, alguna celda tenía que quedar arriba por azar. Una elección así solo valdría si se formuló antes de mirar y se confirma fuera de muestra (nivel 7).', en: 'With 162 tries on the same data, some cell had to land on top by chance. Such a choice would only count if it was stated before looking and confirmed out of sample (level 7).' } },
    { id: 'l8q3', prompt: { es: '¿Cuál es la decisión correcta para el log tras ver la rejilla?', en: 'What is the right log decision after seeing the grid?' },
      options: { es: ['Descartar la familia V1.x y formular una hipótesis distinta antes de tocar más parámetros', 'Añadir más valores a cada mando hasta encontrar una celda positiva', 'Operar la mejor celda en demo'], en: ['Discard the V1.x family and formulate a different hypothesis before touching more parameters', 'Add more values to each knob until a positive cell appears', 'Trade the best cell on demo'] }, answer: 0,
      explanation: { es: 'Más valores solo multiplican los intentos (y el sobreajuste). Lo que el laboratorio registró el 2026-11-06: ninguna celda positiva; V1.x descartada.', en: 'More values only multiply the tries (and the overfitting). What the lab logged on 2026-11-06: no positive cell; V1.x discarded.' } },
  ];

  return (
    <LevelFrame n={8} questions={questions}
      intro={<p>{es ? 'Aquí diseñas tu propia versión de la hipótesis: cinco mandos, cada combinación ya corrida por el motor real con todos los costes sobre EUR/USD 2019–2026 (162 versiones, 90 minutos de cálculo). Empiezas en la V1.1 publicada. Mueve lo que quieras y mira qué pasa con ocho años de datos, no con uno.' : 'Here you design your own version of the hypothesis: five knobs, every combination already run by the real engine with all costs on EUR/USD 2019–2026 (162 versions, 90 minutes of compute). You start at the published V1.1. Move whatever you like and watch what happens with eight years of data, not one.'}</p>}
      noteHint={es ? 'Escribe la entrada del log de decisiones de tu versión: qué cambiaste, qué dio, y si lo decidiste antes o después de mirar los resultados.' : 'Write the decision-log entry for your version: what you changed, what it gave, and whether you decided before or after looking at the results.'}>
      <section className="sim-block">
        <div className="knobs">
          {index.axes.map((axis) => (
            <label key={axis.id} className="knob">
              <span className="tile-label">{axis.label[lang]}</span>
              <select value={String(choice[axis.id])} onChange={(e) => { setChoice({ ...choice, [axis.id]: axis.values.find((v) => String(v) === e.target.value) ?? e.target.value }); setRevealRank(false); }}>
                {axis.values.map((v) => <option key={String(v)} value={String(v)}>{label(v, lang)}{String(v) === String(index.baseline[axis.id]) ? (es ? ' · V1.1' : ' · V1.1') : ''}</option>)}
              </select>
            </label>
          ))}
          <button type="button" className="ghost" onClick={() => { setChoice(index.baseline); setRevealRank(false); }}>{es ? 'Volver a V1.1' : 'Back to V1.1'}</button>
        </div>

        {row && (
          <div className="tiles">
            <div className={`tile ${row.total_r > 0 ? 'good' : 'bad'}`}><div className="tile-label">2019–2026</div><div className="tile-value">{formatR(row.total_r)}</div><div className="tile-hint">{row.trades} {es ? 'operaciones' : 'trades'} · {es ? 'esperanza' : 'expectancy'} {row.expectancy_r != null ? formatR(row.expectancy_r) : '—'}</div></div>
            <div className="tile"><div className="tile-label">{es ? 'Años en positivo' : 'Years positive'}</div><div className="tile-value mono">{row.years_positive}/{row.years}</div><div className="tile-hint">{es ? 'peor año' : 'worst year'} {row.worst_year_r != null ? formatR(row.worst_year_r) : '—'} · {es ? 'mejor' : 'best'} {row.best_year_r != null ? formatR(row.best_year_r) : '—'}</div></div>
            {baselineRow && !isBaseline && <div className="tile"><div className="tile-label">{es ? 'Frente a V1.1' : 'Versus V1.1'}</div><div className="tile-value mono">{formatR(row.total_r - baselineRow.total_r)}</div><div className="tile-hint">V1.1: {formatR(baselineRow.total_r)} · {baselineRow.trades} {es ? 'op.' : 'trades'}</div></div>}
            {isBaseline && <div className="tile"><div className="tile-label">{es ? 'Esta es V1.1' : 'This is V1.1'}</div><div className="tile-value mono">{es ? 'base' : 'baseline'}</div><div className="tile-hint">{es ? 'la versión publicada en el laboratorio' : 'the version published in the lab'}</div></div>}
            <div className="tile"><div className="tile-label">{es ? 'Puesto en la rejilla' : 'Rank in the grid'}</div><div className="tile-value mono">{revealRank ? `${rank}/${index.combos.length}` : '?'}</div><div className="tile-hint">{revealRank ? (es ? `${positive} versiones positivas de ${index.combos.length}` : `${positive} positive versions of ${index.combos.length}`) : <button type="button" className="link-button" onClick={() => setRevealRank(true)}>{es ? 'revelar (lee antes el aviso)' : 'reveal (read the warning first)'}</button>}</div></div>
          </div>
        )}

        {cell && (
          <div className="grid-years">
            <Sparkline values={curve} width={320} height={60} />
            <table className="plan-table small">
              <thead><tr><th>{es ? 'Año' : 'Year'}</th><th>{es ? 'Op.' : 'Trades'}</th><th>R</th><th>{es ? 'Acierto' : 'Win rate'}</th><th>{es ? 'Drawdown' : 'Drawdown'}</th></tr></thead>
              <tbody>
                {yearsSorted.map((y) => { const s = cell.years[y]; return <tr key={y}><td className="mono">{y}</td><td>{s.trades}</td><td className={s.total_r > 0 ? 'good' : s.total_r < 0 ? 'bad' : ''}>{formatR(s.total_r)}</td><td>{s.trades ? `${Math.round(s.win_rate * 100)} %` : '—'}</td><td>{s.trades ? formatR(-s.max_drawdown_r) : '—'}</td></tr>; })}
              </tbody>
            </table>
          </div>
        )}

        <aside className="notice-box">
          <strong>{es ? 'Aviso de sobreajuste.' : 'Overfitting warning.'}</strong> {es ? `Cada versión que pruebas es un intento más sobre los mismos ocho años. Con ${index.combos.length} intentos, alguna tenía que quedar la primera por puro azar; que sea la mejor de la rejilla no la convierte en estrategia. La única versión que cuenta es la que escribiste en el log antes de mirar.` : `Every version you try is one more attempt on the same eight years. With ${index.combos.length} attempts, some had to come first by pure chance; being the best of the grid does not make it a strategy. The only version that counts is the one you wrote in the log before looking.`}
        </aside>
      </section>
    </LevelFrame>
  );
}
