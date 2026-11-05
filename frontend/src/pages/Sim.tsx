import { Level0, Level1, Level2 } from '../components/sim/Levels';
import { LEVELS } from '../content/sim';
import { useT } from '../i18n';
import { Link } from '../router';

/** /app/sim/:n — one simulator level. Levels not implemented yet show their card and the plans link. */
export function SimPage({ n }: { n: string }) {
  const { lang, pick } = useT();
  const es = lang === 'es';
  const index = Number(n);
  const level = LEVELS[index];
  if (!level) {
    return <main className="prose"><p className="kicker">404</p><h1 className="page-title">{es ? 'Ese nivel no existe' : 'That level does not exist'}</h1><p><Link to="/app">{es ? '← Panel' : '← Dashboard'}</Link></p></main>;
  }
  if (index === 0) return <Level0 />;
  if (index === 1) return <Level1 />;
  if (index === 2) return <Level2 />;
  return (
    <main className="prose sim">
      <p className="kicker">{es ? `Nivel ${index} · Lab Pro · ${level.minutes} min` : `Level ${index} · Lab Pro · ${level.minutes} min`}</p>
      <h1 className="page-title">{pick(level.title)}</h1>
      <p className="lead">{pick(level.summary)}</p>
      <div className="notice-box">
        <p><strong>{es ? 'Disponible el 23 de noviembre con Lab Pro.' : 'Available on 23 November with Lab Pro.'}</strong> {es ? 'Mientras tanto, los niveles 0–2 son gratis y las lecciones y el laboratorio completo siguen abiertos sin cuenta.' : 'Meanwhile, levels 0–2 are free and the lessons and the whole lab remain open without an account.'}</p>
        <div className="row-actions"><Link to="/planes" className="button">{es ? 'Ver planes' : 'See plans'}</Link><Link to="/app" className="button ghost">{es ? '← Panel' : '← Dashboard'}</Link></div>
      </div>
    </main>
  );
}
