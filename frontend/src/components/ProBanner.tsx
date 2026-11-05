import { isPro, useAuth } from '../auth';
import { useT } from '../i18n';
import { Link } from '../router';

/** Internal upsell: shown in the free parts (lab, lessons, free levels, dashboard) to users who are not Pro.
 *  `variant` picks the message for the place. Hidden for Pro users. */
export function ProBanner({ variant = 'generic', compact = false }: { variant?: 'generic' | 'lab' | 'lesson' | 'level' | 'dashboard'; compact?: boolean }) {
  const { lang } = useT();
  const { user } = useAuth();
  if (isPro(user)) return null;
  const es = lang === 'es';
  const copy = {
    generic: { es: ['Lab Pro: los seis niveles que convierten un resultado en una decisión.', 'Cifras, costes, Monte Carlo, azar, fragilidad y tu propia V1.x sobre ocho años.'], en: ['Lab Pro: the six levels that turn a result into a decision.', 'Numbers, costs, Monte Carlo, chance, fragility and your own V1.x over eight years.'] },
    lab: { es: ['¿Sabrías decir si este resultado significa algo?', 'En Lab Pro recorres el protocolo entero con tus manos: Monte Carlo, azar, fragilidad y fuera de muestra sobre estas mismas operaciones.'], en: ['Could you tell whether this result means anything?', 'In Lab Pro you walk the whole protocol yourself: Monte Carlo, chance, fragility and out of sample on these very trades.'] },
    lesson: { es: ['Las lecciones te enseñan a leer. El simulador te hace calcular.', 'Lab Pro: seis niveles guiados sobre operaciones reales, con tu informe PDF al final.'], en: ['The lessons teach you to read. The simulator makes you calculate.', 'Lab Pro: six guided levels on real trades, with your PDF report at the end.'] },
    level: { es: ['Este nivel es de Lab Pro.', 'Abre el 23 de noviembre: 12 € al mes, 89 € al año o 149 € de por vida. Déjanos tu correo y te avisamos con el precio de lanzamiento.'], en: ['This level belongs to Lab Pro.', 'Opens 23 November: 12 € a month, 89 € a year or 149 € lifetime. Leave your email and we will tell you with the launch price.'] },
    dashboard: { es: ['Niveles 3–8: Lab Pro.', 'Cuando termines los tres gratis, el resto del itinerario te espera: desde las cinco cifras hasta diseñar tu propia versión.'], en: ['Levels 3–8: Lab Pro.', 'When you finish the three free ones, the rest of the itinerary is waiting: from the five numbers to designing your own version.'] },
  }[variant][lang];
  return (
    <aside className={`pro-banner ${compact ? 'compact' : ''}`} aria-label="Lab Pro">
      <div>
        <p className="kicker">Lab Pro · {es ? 'abre el 23 de noviembre' : 'opens 23 November'}</p>
        <strong>{copy[0]}</strong>
        {!compact && <p className="muted">{copy[1]}</p>}
      </div>
      <div className="row-actions">
        <Link to="/planes" className="button">{es ? 'Ver Lab Pro' : 'See Lab Pro'}</Link>
        {!user && <Link to="/entrar" className="button ghost">{es ? 'Crear cuenta gratis' : 'Create a free account'}</Link>}
      </div>
    </aside>
  );
}
