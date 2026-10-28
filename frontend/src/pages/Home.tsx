import { useEffect, useState } from 'react';
import { api, formatPercent, formatR } from '../api';
import { Subscribe } from '../components/Subscribe';
import { LESSONS } from '../content/lessons';
import { useT } from '../i18n';
import { Link } from '../router';
import { REPO_URL } from '../site';
import type { RunRow } from '../types';

const IS = {
  es: ['Un motor de backtesting causal (velas solo al cierre, entrada al siguiente precio, costes en cada operación).', 'Una hipótesis intradía escrita y congelada en un fichero, con versiones nombradas (V1, V1.1).', 'Un protocolo de investigación: periodos independientes, walk-forward, Monte Carlo, sensibilidad, benchmark aleatorio.', 'Resultados reales sobre datos reales, con su hash, publicados tal cual salieron.', 'Lecciones que te enseñan a leer todo lo anterior.'],
  en: ['A causal backtesting engine (candles only at close, entry at the next price, costs on every trade).', 'An intraday hypothesis written and frozen in a file, with named versions (V1, V1.1).', 'A research protocol: independent periods, walk-forward, Monte Carlo, sensitivity, random benchmark.', 'Real results on real data, with their hash, published as they came out.', 'Lessons that teach you to read all of the above.'],
};
const ISNT = {
  es: ['No es asesoramiento de inversión ni una recomendación de operar.', 'No da señales, alertas ni "setups del día".', 'No se conecta a ningún bróker ni ejecuta órdenes.', 'No promete rentabilidad: de hecho, hasta hoy no ha encontrado ninguna.', 'No sustituye a un asesor regulado ni a tu propio criterio.'],
  en: ['Not investment advice nor a recommendation to trade.', 'No signals, alerts or "setups of the day".', 'No broker connection, no order execution.', 'No promise of profitability: so far it has found none.', 'No substitute for a regulated adviser or your own judgement.'],
};
const HOW = {
  es: [['1', 'Escribe la hipótesis', 'Reglas explícitas en YAML, con su hash. Cambiar una regla es crear otra versión.'], ['2', 'Ejecútala sin trampas', 'El motor solo sabe lo que ya ha cerrado y paga spread, deslizamiento y comisión.'], ['3', 'Pásala por el protocolo', 'Azar, fragilidad y fuera de muestra. Tres preguntas antes de creerte un número.'], ['4', 'Decide y registra', 'Un log de decisiones y un informe reproducible. Casi siempre: "todavía no sabemos".']],
  en: [['1', 'Write the hypothesis', 'Explicit rules in YAML, with their hash. Changing a rule means creating another version.'], ['2', 'Run it with no shortcuts', 'The engine only knows what has already closed and pays spread, slippage and commission.'], ['3', 'Put it through the protocol', 'Chance, fragility and out-of-sample. Three questions before believing a number.'], ['4', 'Decide and log', 'A decision log and a reproducible report. Almost always: "we do not know yet".']],
};

export function HomePage() {
  const { t, pick, lang } = useT();
  const [runs, setRuns] = useState<RunRow[]>([]);
  useEffect(() => { api.runs('backtest').then(setRuns).catch(() => setRuns([])); }, []);
  return (
    <main className="home">
      <section className="hero">
        <p className="kicker">{t('home.kicker')}</p>
        <h1 className="hero-title">{t('home.title')}</h1>
        <p className="lead">{t('home.lead')}</p>
        <div className="row-actions hero-actions">
          <Link to="/lessons" className="button">{t('home.ctaLessons')}</Link>
          <Link to="/lab" className="button ghost">{t('home.ctaLab')}</Link>
        </div>
      </section>

      <section className="two-col is-isnt">
        <div className="card"><h2>{t('home.isTitle')}</h2><ul>{IS[lang].map((line) => <li key={line}>{line}</li>)}</ul></div>
        <div className="card"><h2>{t('home.isntTitle')}</h2><ul>{ISNT[lang].map((line) => <li key={line}>{line}</li>)}</ul></div>
      </section>

      <section>
        <h2 className="section-title">{t('home.howTitle')}</h2>
        <ol className="steps-grid">
          {HOW[lang].map(([n, title, text]) => <li key={n}><span className="step-index">{n}</span><div><strong>{title}</strong><p className="muted small">{text}</p></div></li>)}
        </ol>
      </section>

      {runs.length > 0 && (
        <section>
          <h2 className="section-title">{t('home.resultsTitle')}</h2>
          <p className="muted">{t('home.resultsLead')}</p>
          <div className="result-cards">
            {runs.map((run) => {
              const total = run.summary.total_r as number;
              return (
                <Link key={run.id} to={`/lab/${run.id}`} className="card result-card">
                  <div className="small muted">{pick(run.description)}</div>
                  <strong>{pick(run.labels) ?? run.label}</strong>
                  <div className="result-numbers">
                    <span className="mono">{String(run.summary.trades ?? '—')} {t('home.trades')}</span>
                    <span className={`mono strong ${total > 0 ? 'good' : total < 0 ? 'bad' : ''}`}>{formatR(total)}</span>
                    {run.summary.win_rate != null && <span className="mono">{formatPercent(run.summary.win_rate as number)}</span>}
                  </div>
                  <span className="small">{t('home.openRun')} →</span>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <h2 className="section-title">{t('home.lessonsTitle')}</h2>
        <p className="muted">{t('home.lessonsLead')}</p>
        <ol className="lesson-cards">
          {LESSONS.map((lesson) => (
            <li key={lesson.slug} className="lesson-card">
              <div className="lesson-meta"><span className="badge soft">{t('lessons.free')}</span><span className="muted small">{t('lessons.minutes', { n: lesson.minutes })}</span></div>
              <h2>{lesson.order}. {pick(lesson.title)}</h2>
              <p className="muted">{pick(lesson.summary)}</p>
              <Link to={`/lessons/${lesson.slug}`} className="button">{t('lessons.start')}</Link>
            </li>
          ))}
        </ol>
      </section>

      <Subscribe />

      <p className="muted small">{lang === 'es' ? 'Todo el código es libre (MIT):' : 'All the code is open source (MIT):'} <a href={REPO_URL} target="_blank" rel="noreferrer">{REPO_URL.replace('https://', '')}</a></p>
    </main>
  );
}
