import { useEffect, useState } from 'react';
import { api, formatPercent, formatR } from '../api';
import { Subscribe } from '../components/Subscribe';
import { SetupIllustration, Sparkline, StepIcon } from '../components/Visuals';
import { LESSONS } from '../content/lessons';
import { useT } from '../i18n';
import { readProgress } from '../progress';
import { Link } from '../router';
import type { RunRow } from '../types';

const IS = {
  es: ['Un motor de backtesting causal: velas solo al cierre, entrada al siguiente precio, costes en cada operación.', 'Una hipótesis intradía escrita y congelada en un fichero, con versiones nombradas (V1, V1.1).', 'Un protocolo: periodos independientes, walk-forward, Monte Carlo, sensibilidad, benchmark aleatorio.', 'Resultados reales sobre datos reales, con su hash, publicados tal cual salieron.', 'Lecciones que te enseñan a leer todo lo anterior.'],
  en: ['A causal backtesting engine: candles only at close, entry at the next price, costs on every trade.', 'An intraday hypothesis written and frozen in a file, with named versions (V1, V1.1).', 'A protocol: independent periods, walk-forward, Monte Carlo, sensitivity, random benchmark.', 'Real results on real data, with their hash, published as they came out.', 'Lessons that teach you to read all of the above.'],
};
const ISNT = {
  es: ['No es asesoramiento de inversión ni una recomendación de operar.', 'No da señales, alertas ni "setups del día".', 'No se conecta a ningún bróker ni ejecuta órdenes.', 'No promete rentabilidad: de hecho, hasta hoy no ha encontrado ninguna.', 'No sustituye a un asesor regulado ni a tu propio criterio.'],
  en: ['Not investment advice nor a recommendation to trade.', 'No signals, alerts or "setups of the day".', 'No broker connection, no order execution.', 'No promise of profitability: so far it has found none.', 'No substitute for a regulated adviser or your own judgement.'],
};
const HOW: { icon: 'write' | 'run' | 'protocol' | 'log'; es: [string, string]; en: [string, string] }[] = [
  { icon: 'write', es: ['Escribe la hipótesis', 'Reglas explícitas en un fichero, con su hash. Cambiar una regla es crear otra versión.'], en: ['Write the hypothesis', 'Explicit rules in a file, with their hash. Changing a rule means creating another version.'] },
  { icon: 'run', es: ['Ejecútala sin trampas', 'El motor solo sabe lo que ya ha cerrado y paga spread, deslizamiento y comisión.'], en: ['Run it with no shortcuts', 'The engine only knows what has already closed and pays spread, slippage and commission.'] },
  { icon: 'protocol', es: ['Pásala por el protocolo', 'Azar, fragilidad y fuera de muestra: tres preguntas antes de creerte un número.'], en: ['Put it through the protocol', 'Chance, fragility and out-of-sample: three questions before believing a number.'] },
  { icon: 'log', es: ['Decide y registra', 'Un log de decisiones y un informe reproducible. Casi siempre: "todavía no sabemos".'], en: ['Decide and log', 'A decision log and a reproducible report. Almost always: "we do not know yet".'] },
];

export function HomePage() {
  const { t, pick, lang } = useT();
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [progress, setProgress] = useState<Record<string, { completed?: boolean }>>({});
  useEffect(() => {
    api.runs('backtest').then(setRuns).catch(() => setRuns([]));
    setProgress(readProgress());
  }, []);
  const featured = runs.slice(0, 2);
  return (
    <main className="home">
      <section className="hero">
        <div className="hero-copy">
          <p className="kicker">{t('home.kicker')}</p>
          <h1 className="hero-title">{t('home.title')}</h1>
          <p className="lead">{t('home.lead')}</p>
          <div className="row-actions hero-actions">
            <Link to="/lessons" className="button">{t('home.ctaLessons')}</Link>
            <Link to="/lab" className="button ghost">{t('home.ctaLab')}</Link>
          </div>
        </div>
        <div className="hero-art">
          <SetupIllustration />
          <p className="muted small art-caption">{lang === 'es' ? 'La hipótesis V1 en una imagen. Cada número es una regla; cada regla tiene una hora exacta.' : 'The V1 hypothesis in one picture. Every number is a rule; every rule has an exact time.'}</p>
        </div>
      </section>

      {featured.length === 2 && (
        <section className="evidence" aria-label="evidence">
          {featured.map((run) => {
            const total = run.summary.total_r as number;
            return (
              <div key={run.id} className="ev">
                <span className="ev-label">{pick(run.labels)}</span>
                <span className={`ev-value ${total > 0 ? 'good' : total < 0 ? 'bad' : ''}`}>{formatR(total)}</span>
                <span className="ev-note">{String(run.summary.trades ?? '—')} {t('home.trades')} · {formatPercent(run.summary.win_rate as number)} {lang === 'es' ? 'acierto' : 'win rate'}</span>
                {run.sparkline && <Sparkline values={run.sparkline} width={200} height={40} />}
              </div>
            );
          })}
          <div className="ev verdict">
            <span className="ev-label">{lang === 'es' ? 'Veredicto del protocolo' : 'Protocol verdict'}</span>
            <span className="ev-value">{lang === 'es' ? 'Sin evidencia' : 'No evidence'}</span>
            <span className="ev-note">{lang === 'es' ? 'Un año de datos reales. Y eso es lo que te enseñamos a comprobar.' : 'One year of real data. And that is what we teach you to check.'}</span>
          </div>
        </section>
      )}

      <section className="two-col is-isnt">
        <div className="card is"><h2>{t('home.isTitle')}</h2><ul className="checklist">{IS[lang].map((line) => <li key={line}>{line}</li>)}</ul></div>
        <div className="card isnt"><h2>{t('home.isntTitle')}</h2><ul className="checklist no">{ISNT[lang].map((line) => <li key={line}>{line}</li>)}</ul></div>
      </section>

      <section className="how">
        <h2 className="section-title">{t('home.howTitle')}</h2>
        <ol className="steps-grid">
          {HOW.map((step, index) => {
            const [title, text] = step[lang];
            return (
              <li key={step.icon}>
                <div className="step-head"><span className="step-icon"><StepIcon kind={step.icon} /></span><span className="step-no">0{index + 1}</span></div>
                <strong>{title}</strong>
                <p className="muted">{text}</p>
              </li>
            );
          })}
        </ol>
      </section>

      {runs.length > 0 && (
        <section>
          <h2 className="section-title">{t('home.resultsTitle')}</h2>
          <p className="muted lead-small">{t('home.resultsLead')}</p>
          <div className="result-cards">
            {runs.map((run) => {
              const total = run.summary.total_r as number;
              return (
                <Link key={run.id} to={`/lab/${run.id}`} className="card result-card">
                  <div className="result-top">
                    <strong>{pick(run.labels) ?? run.label}</strong>
                    <span className={`result-r mono ${total > 0 ? 'good' : total < 0 ? 'bad' : ''}`}>{formatR(total)}</span>
                  </div>
                  {run.sparkline && <Sparkline values={run.sparkline} width={320} height={56} className="wide" />}
                  <div className="small muted">{pick(run.description)}</div>
                  <div className="result-numbers mono small">
                    <span>{String(run.summary.trades ?? '—')} {t('home.trades')}</span>
                    {run.summary.win_rate != null && <span>{formatPercent(run.summary.win_rate as number)} {lang === 'es' ? 'acierto' : 'win rate'}</span>}
                    <span className="link-like">{t('home.openRun')} →</span>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      <section>
        <h2 className="section-title">{t('home.lessonsTitle')}</h2>
        <p className="muted lead-small">{t('home.lessonsLead')}</p>
        <ol className="lesson-cards">
          {LESSONS.map((lesson) => (
            <li key={lesson.slug} className={`lesson-card ${progress[lesson.slug]?.completed ? 'done' : ''}`}>
              <span className="lesson-no" aria-hidden="true">{lesson.order}</span>
              <div className="lesson-meta"><span className="badge soft">{t('lessons.free')}</span><span className="muted small">{t('lessons.minutes', { n: lesson.minutes })}</span>{progress[lesson.slug]?.completed && <span className="good small">✓ {t('lessons.done')}</span>}</div>
              <h3>{pick(lesson.title)}</h3>
              <p className="muted">{pick(lesson.summary)}</p>
              <Link to={`/lessons/${lesson.slug}`} className="button">{progress[lesson.slug]?.completed ? t('lessons.review') : t('lessons.start')}</Link>
            </li>
          ))}
        </ol>
      </section>

      <Subscribe />

    </main>
  );
}
