import { Subscribe } from '../components/Subscribe';
import { useT } from '../i18n';
import { Link } from '../router';
import { KIT_PRICE, KIT_URL, PRO_OPEN, PRO_URLS } from '../site';

export const PRO_PRICES = { month: '12 €', year: '89 €', life: '149 €' };
export const PRO_LAUNCH = { es: '23 de noviembre de 2026', en: '23 November 2026' };

type Avail = boolean | { es: string; en: string };
const ROWS: { es: string; en: string; free: Avail; pro: Avail }[] = [
  { es: 'Laboratorio completo: 27 ejecuciones reales 2019–2026', en: 'Full lab: 27 real runs 2019–2026', free: true, pro: true },
  { es: 'Cada operación explicada en su gráfico', en: 'Every trade explained on its chart', free: true, pro: true },
  { es: 'Tres lecciones con cuestionario y nota evaluada', en: 'Three lessons with quiz and graded note', free: true, pro: true },
  { es: 'Simulador: niveles 0–2 (vela, backtest, una operación)', en: 'Simulator: levels 0–2 (candle, backtest, one trade)', free: true, pro: true },
  { es: 'Simulador: niveles 3–8 (cifras, costes, Monte Carlo, azar, fragilidad, tu versión)', en: 'Simulator: levels 3–8 (numbers, costs, Monte Carlo, chance, fragility, your version)', free: false, pro: true },
  { es: 'Nivel 8: diseña tu V1.x y recibe su backtest y protocolo sobre ocho años', en: 'Level 8: design your V1.x and get its backtest and protocol over eight years', free: false, pro: true },
  { es: 'Informe PDF de tu itinerario y tus notas de laboratorio', en: 'PDF report of your itinerary and lab notes', free: false, pro: true },
  { es: 'Cuenta (Google o correo) y progreso en cualquier dispositivo', en: 'Account (Google or email) and progress on any device', free: false, pro: true },
  { es: 'Datasets 2019–2026 con SHA-256 y comandos para reproducirlo todo', en: '2019–2026 datasets with SHA-256 and commands to reproduce everything', free: { es: 'en el kit', en: 'in the kit' }, pro: true },
  { es: 'Novedades mensuales: datos nuevos, hipótesis nuevas, decisiones en el log', en: 'Monthly updates: new data, new hypotheses, decisions in the log', free: false, pro: true },
];

function Cell({ value, lang }: { value: Avail; lang: 'es' | 'en' }) {
  if (value === true) return <td className="good">✓</td>;
  if (value === false) return <td className="muted">—</td>;
  return <td className="muted small">{value[lang]}</td>;
}

/** /planes — what is free, what Lab Pro adds, what the kit is. Lab Pro opens on PRO_LAUNCH; until then the waitlist. */
export function PlansPage() {
  const { lang } = useT();
  const es = lang === 'es';
  return (
    <main className="prose plans">
      <p className="kicker">{es ? 'Planes' : 'Plans'}</p>
      <h1 className="page-title">{es ? 'Gratis lo que ya hay. Lab Pro para recorrer el itinerario entero.' : 'Free what is already here. Lab Pro to walk the whole itinerary.'}</h1>
      <p className="lead">{es ? 'El laboratorio, las lecciones y los tres primeros niveles del simulador son gratis y no piden cuenta. Lab Pro añade los seis niveles que convierten un resultado en una decisión, y un informe de tu recorrido.' : 'The lab, the lessons and the first three simulator levels are free and need no account. Lab Pro adds the six levels that turn a result into a decision, and a report of your path.'}</p>

      <div className="plan-grid">
        <section className="plan">
          <h2>{es ? 'Gratis' : 'Free'}</h2>
          <p className="plan-price">0 €</p>
          <p className="muted">{es ? 'Sin cuenta. Progreso en tu navegador.' : 'No account. Progress in your browser.'}</p>
          <Link to="/app" className="button ghost">{es ? 'Empezar el nivel 0' : 'Start level 0'}</Link>
        </section>
        <section className="plan featured">
          <p className="badge">{PRO_OPEN ? (es ? 'Disponible' : 'Available') : (es ? 'Abre el 23 de noviembre' : 'Opens 23 November')}</p>
          <h2>Lab Pro</h2>
          <p className="plan-price">{PRO_PRICES.month}<span className="muted small"> / {es ? 'mes' : 'month'}</span></p>
          <p className="muted small">{es ? `o ${PRO_PRICES.year} al año (dos meses gratis) · o ${PRO_PRICES.life} de por vida` : `or ${PRO_PRICES.year} a year (two months free) · or ${PRO_PRICES.life} lifetime`}</p>
          <p className="muted">{es ? 'Los seis niveles avanzados, tu V1.x sobre ocho años, informe PDF, cuenta y novedades mensuales. Cancela cuando quieras.' : 'The six advanced levels, your V1.x over eight years, PDF report, account and monthly updates. Cancel any time.'}</p>
          {PRO_OPEN
            ? <div className="row-actions"><a className="button" href={PRO_URLS.membership} target="_blank" rel="noopener">{es ? 'Suscribirme' : 'Subscribe'}</a><a className="button ghost" href={PRO_URLS.lifetime} target="_blank" rel="noopener">{es ? 'De por vida · 149 €' : 'Lifetime · 149 €'}</a></div>
            : <a href="#avisame" className="button">{es ? 'Avísame cuando abra' : 'Tell me when it opens'}</a>}
        </section>
        <section className="plan">
          <h2>{es ? 'Kit' : 'Kit'}</h2>
          <p className="plan-price">{KIT_PRICE}<span className="muted small"> {es ? 'pago único' : 'one-off'}</span></p>
          <p className="muted">{es ? 'Guía de 14 páginas, plantilla de informe, checklist y datasets. Para aplicar el método a cualquier backtest, tuyo o ajeno.' : '14-page guide, report template, checklist and datasets. To apply the method to any backtest, yours or someone else\'s.'}</p>
          <a className="button ghost" href={KIT_URL} target="_blank" rel="noopener">{es ? 'Comprar en Gumroad' : 'Buy on Gumroad'}</a>
        </section>
      </div>

      <table className="plan-table">
        <thead><tr><th>{es ? 'Qué incluye' : 'What is included'}</th><th>{es ? 'Gratis' : 'Free'}</th><th>Lab Pro</th></tr></thead>
        <tbody>
          {ROWS.map((row) => <tr key={row.en}><td>{es ? row.es : row.en}</td><Cell value={row.free} lang={lang} /><Cell value={row.pro} lang={lang} /></tr>)}
        </tbody>
      </table>

      <section className="faq">
        <h2>{es ? 'Preguntas frecuentes' : 'Frequently asked questions'}</h2>
        <dl>
          <dt>{es ? '¿Hay señales, alertas o una estrategia que funcione?' : 'Are there signals, alerts or a strategy that works?'}</dt>
          <dd>{es ? 'No. Esto es un laboratorio educativo. La hipótesis que estudiamos no tiene ventaja demostrada y lo decimos en la portada: el valor está en aprender a comprobarlo.' : 'No. This is an educational lab. The hypothesis we study has no demonstrated edge and we say so on the home page: the value is in learning to check it.'}</dd>
          <dt>{es ? '¿Qué pasa con mi progreso gratis si me suscribo?' : 'What happens to my free progress if I subscribe?'}</dt>
          <dd>{es ? 'Al iniciar sesión por primera vez lo importamos desde el navegador a tu cuenta.' : 'On your first sign-in we import it from the browser into your account.'}</dd>
          <dt>{es ? '¿Cómo se paga y se cancela?' : 'How do I pay and cancel?'}</dt>
          <dd>{es ? 'Pago seguro en Gumroad (tarjeta o PayPal), IVA incluido. Cancelas desde Gumroad con un clic; conservas el acceso hasta el fin del periodo pagado.' : 'Secure checkout on Gumroad (card or PayPal), VAT included. Cancel from Gumroad in one click; you keep access until the end of the paid period.'}</dd>
          <dt>{es ? '¿Por qué no está ya disponible?' : 'Why is it not available yet?'}</dt>
          <dd>{es ? `Los niveles 3–8 se están construyendo sobre los mismos datos y el mismo motor que el laboratorio. Lab Pro abre el ${PRO_LAUNCH.es}; déjanos tu correo y te avisamos ese día, con el precio de lanzamiento.` : `Levels 3–8 are being built on the same data and engine as the lab. Lab Pro opens on ${PRO_LAUNCH.en}; leave your email and we will tell you that day, with the launch price.`}</dd>
        </dl>
      </section>

      <div id="avisame"><Subscribe /></div>
      <p className="muted small">{es ? 'Material educativo. No es asesoramiento de inversión. Sin señales ni ejecución real.' : 'Educational material. Not investment advice. No signals, no live execution.'}</p>
    </main>
  );
}
