import { isPro, useAuth } from '../auth';
import { useT } from '../i18n';
import { Link } from '../router';

/** Internal upsell: shown in the free parts (lab, lessons, free levels, dashboard) to users who are not Pro.
 *  `variant` picks the message for the place. Hidden for Pro users. */
export function ProBanner({ variant = 'generic', compact = false }: { variant?: 'generic' | 'lab' | 'lesson' | 'level' | 'dashboard' | 'report' | 'explainer'; compact?: boolean }) {
  const { lang } = useT();
  const { user } = useAuth();
  if (isPro(user)) return null;
  const es = lang === 'es';
  const copy = {
    generic: { es: ['Lab Pro: los seis niveles que convierten un resultado en una decisión.', 'Cifras, costes, Monte Carlo, azar, fragilidad y tu propia V1.x sobre ocho años.'], en: ['Lab Pro: the six levels that turn a result into a decision.', 'Numbers, costs, Monte Carlo, chance, fragility and your own V1.x over eight years.'] },
    lab: { es: ['¿Sabrías decir si este resultado significa algo?', 'En Lab Pro recorres el protocolo entero con tus manos: Monte Carlo, azar, fragilidad y fuera de muestra sobre estas mismas operaciones.'], en: ['Could you tell whether this result means anything?', 'In Lab Pro you walk the whole protocol yourself: Monte Carlo, chance, fragility and out of sample on these very trades.'] },
    lesson: { es: ['Las lecciones te enseñan a leer. El simulador te hace calcular.', 'Lab Pro: seis niveles guiados sobre operaciones reales, con tu informe PDF al final.'], en: ['The lessons teach you to read. The simulator makes you calculate.', 'Lab Pro: six guided levels on real trades, with your PDF report at the end.'] },
    level: { es: ['Este nivel es de Lab Pro.', '12 € al mes, 89 € al año o 149 € de por vida. Se activa al instante con la clave de Gumroad.'], en: ['This level belongs to Lab Pro.', '12 € a month, 89 € a year or 149 € lifetime. Activates instantly with the Gumroad key.'] },
    report: { es: ['El informe completo del protocolo es de Lab Pro.', 'Periodos independientes, walk-forward, Monte Carlo, benchmark aleatorio y sensibilidad de este año, con el PDF. El resumen y el veredicto de arriba son públicos; el de 2024 está completo como demostración.'], en: ['The full protocol report belongs to Lab Pro.', 'Independent periods, walk-forward, Monte Carlo, random benchmark and sensitivity for this year, with the PDF. The summary and verdict above are public; 2024 is complete as a demo.'] },
    explainer: { es: ['La operación explicada en su gráfico es de Lab Pro.', 'Los diez pasos con su minuto exacto, para todas las operaciones de 2019–2026. Las de 2024 están abiertas como demostración.'], en: ['The trade explained on its chart belongs to Lab Pro.', 'The ten steps with their exact minute, for every trade of 2019–2026. The 2024 ones are open as a demo.'] },
    dashboard: { es: ['Niveles 3–8: Lab Pro.', 'Cuando termines los tres gratis, el resto del itinerario te espera: desde las cinco cifras hasta diseñar tu propia versión.'], en: ['Levels 3–8: Lab Pro.', 'When you finish the three free ones, the rest of the itinerary is waiting: from the five numbers to designing your own version.'] },
  }[variant][lang];
  return (
    <aside className={`pro-banner ${compact ? 'compact' : ''}`} aria-label="Lab Pro">
      <div>
        <p className="kicker">Lab Pro · {es ? 'desde 12 € al mes' : 'from 12 € a month'}</p>
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
