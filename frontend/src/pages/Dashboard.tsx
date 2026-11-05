import { useState } from 'react';
import { LEVELS } from '../content/sim';
import { useT } from '../i18n';
import { readSim } from '../progress';
import { Link } from '../router';

/** /app — the learner's panel: itinerary with progress, next level, locked Lab Pro levels. */
export function DashboardPage() {
  const { lang, pick } = useT();
  const es = lang === 'es';
  const [progress] = useState(readSim());
  const done = LEVELS.filter((l) => progress[String(l.n)]?.completed).length;
  const next = LEVELS.find((l) => l.ready && !progress[String(l.n)]?.completed) ?? null;
  const freeCount = LEVELS.filter((l) => !l.pro).length;
  return (
    <main className="prose app">
      <p className="kicker">{es ? 'Tu panel' : 'Your dashboard'}</p>
      <h1 className="page-title">{es ? 'Itinerario: de la vela al protocolo' : 'Itinerary: from the candle to the protocol'}</h1>
      <p className="lead">{es ? `Nueve niveles sobre resultados reales del laboratorio. Los ${freeCount} primeros son gratis y no piden cuenta; tu progreso se guarda en este navegador.` : `Nine levels on real lab results. The first ${freeCount} are free and need no account; your progress is saved in this browser.`}</p>
      <div className="tiles app-tiles">
        <div className="tile"><div className="tile-label">{es ? 'Niveles completados' : 'Levels completed'}</div><div className="tile-value mono">{done}/{LEVELS.length}</div></div>
        <div className="tile"><div className="tile-label">{es ? 'Siguiente paso' : 'Next step'}</div><div className="tile-value">{next ? `${es ? 'Nivel' : 'Level'} ${next.n}` : (es ? 'Lab Pro' : 'Lab Pro')}</div><div className="small muted">{next ? pick(next.title) : (es ? 'Los niveles 3–8 llegan el 23 de noviembre' : 'Levels 3–8 arrive on 23 November')}</div></div>
        <div className="tile"><div className="tile-label">{es ? 'Plan' : 'Plan'}</div><div className="tile-value">{es ? 'Gratis' : 'Free'}</div><div className="small muted"><Link to="/planes">{es ? 'Ver planes →' : 'See plans →'}</Link></div></div>
      </div>
      {next && <p><Link to={`/app/sim/${next.n}`} className="button">{progress[String(next.n)]?.score ? (es ? `Continuar nivel ${next.n}` : `Continue level ${next.n}`) : (es ? `Empezar nivel ${next.n}` : `Start level ${next.n}`)} →</Link></p>}
      <ol className="level-list">
        {LEVELS.map((level) => {
          const p = progress[String(level.n)];
          const locked = level.pro && !level.ready;
          const prevDone = level.n === 0 || progress[String(level.n - 1)]?.completed;
          return (
            <li key={level.n} className={`level-card ${p?.completed ? 'done' : ''} ${locked ? 'locked' : ''}`}>
              <span className="lesson-no" aria-hidden="true">{level.n}</span>
              <div className="level-body">
                <div className="lesson-meta">
                  <span className={`badge ${level.pro ? '' : 'soft'}`}>{level.pro ? 'Lab Pro' : (es ? 'Gratis' : 'Free')}</span>
                  <span className="muted small">{level.minutes} min</span>
                  {p?.completed && <span className="good small">✓ {es ? 'completado' : 'completed'}{p.score ? ` · ${p.score.ok}/${p.score.total}` : ''}</span>}
                  {!p?.completed && p?.score && <span className="warn-text small">{p.score.ok}/{p.score.total} · {es ? 'repite el cuestionario' : 'retake the quiz'}</span>}
                </div>
                <h3>{pick(level.title)}</h3>
                <p className="muted">{pick(level.summary)}</p>
                {level.ready
                  ? <Link to={`/app/sim/${level.n}`} className={`button ${prevDone ? '' : 'ghost'}`}>{p?.completed ? (es ? 'Repasar' : 'Review') : (es ? 'Entrar' : 'Enter')}</Link>
                  : <span className="muted small">{es ? 'Lab Pro · disponible el 23 de noviembre' : 'Lab Pro · available 23 November'} · <Link to="/planes">{es ? 'planes' : 'plans'}</Link></span>}
              </div>
            </li>
          );
        })}
      </ol>
      <p className="muted small">{es ? 'Progreso guardado solo en este navegador (sin cuenta). Con Lab Pro podrás iniciar sesión con Google o con tu correo y llevarlo a cualquier dispositivo.' : 'Progress is saved only in this browser (no account). With Lab Pro you will sign in with Google or your email and carry it to any device.'}</p>
    </main>
  );
}
