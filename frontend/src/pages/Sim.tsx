import { isPro, useAuth } from '../auth';
import { ProBanner } from '../components/ProBanner';
import { Level8 } from '../components/sim/Level8';
import { Level0, Level1, Level2 } from '../components/sim/Levels';
import { Level3, Level4 } from '../components/sim/Levels34';
import { Level5, Level6 } from '../components/sim/Levels56';
import { Level7 } from '../components/sim/Level7';
import { LEVELS } from '../content/sim';
import { useT } from '../i18n';
import { Link } from '../router';

/** /app/sim/:n — one simulator level. Levels not implemented yet show their card and the plans link. */
export function SimPage({ n }: { n: string }) {
  const { lang, pick } = useT();
  const { user, configured } = useAuth();
  const es = lang === 'es';
  const index = Number(n);
  const level = LEVELS[index];
  if (!level) {
    return <main className="prose"><p className="kicker">404</p><h1 className="page-title">{es ? 'Ese nivel no existe' : 'That level does not exist'}</h1><p><Link to="/app">{es ? '← Panel' : '← Dashboard'}</Link></p></main>;
  }
  if (index === 0) return <Level0 />;
  if (index === 1) return <Level1 />;
  if (index === 2) return <Level2 />;
  const pro = isPro(user) || !configured;
  if (index === 3 && pro) return <Level3 />;
  if (index === 4 && pro) return <Level4 />;
  if (index === 5 && pro) return <Level5 />;
  if (index === 6 && pro) return <Level6 />;
  if (index === 7 && pro) return <Level7 />;
  if (index === 8 && pro) return <Level8 />;
  return (
    <main className="prose sim">
      <p className="kicker">{es ? `Nivel ${index} · Lab Pro · ${level.minutes} min` : `Level ${index} · Lab Pro · ${level.minutes} min`}</p>
      <h1 className="page-title">{pick(level.title)}</h1>
      <p className="lead">{pick(level.summary)}</p>
      {isPro(user)
        ? <div className="notice-box"><p><strong>{es ? 'Este nivel se publica próximamente.' : 'This level is coming soon.'}</strong> {es ? 'Tu plan Lab Pro ya lo incluye; te avisaremos por correo.' : 'Your Lab Pro plan already includes it; we will email you.'}</p></div>
        : <ProBanner variant="level" />}
      <p><Link to="/app" className="button ghost">{es ? '← Panel' : '← Dashboard'}</Link></p>
    </main>
  );
}
