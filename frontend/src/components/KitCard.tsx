import { BASE_URL, KIT_PRICE, KIT_URL } from '../site';
import { useT } from '../i18n';

const POINTS = {
  es: ['Guía de 14 páginas (ES/EN) escrita sobre los resultados reales de V1 y V1.1.', 'Plantilla de informe de backtest y checklist de decisión.', 'Datasets de cada ejecución con su SHA-256 y cómo reproducirlo todo.'],
  en: ['14-page guide (ES/EN) written on the real V1 and V1.1 results.', 'Backtest report template and decision checklist.', 'Datasets of every run with their SHA-256 and how to reproduce it all.'],
};

/** The paid kit, linked from the home page and the lessons index. Checkout happens on Gumroad. */
export function KitCard({ compact = false }: { compact?: boolean }) {
  const { lang } = useT();
  const es = lang === 'es';
  return (
    <section className={`kit ${compact ? 'compact' : ''}`} aria-labelledby="kit-title">
      <div className="kit-copy">
        <p className="kicker">{es ? 'Kit de pago' : 'Paid kit'}</p>
        <h2 id="kit-title" className="section-title">{es ? 'Cómo leer un backtest' : 'How to read a backtest'}</h2>
        <p className="muted">{es ? 'Las lecciones son gratis y lo seguirán siendo. El kit es el material de trabajo para hacerlo por tu cuenta con cualquier backtest, tuyo o ajeno.' : 'The lessons are free and will stay free. The kit is the working material to do it yourself with any backtest, yours or someone else\'s.'}</p>
        <ul className="checklist">{POINTS[lang].map((line) => <li key={line}>{line}</li>)}</ul>
        <div className="row-actions kit-actions">
          <a className="button" href={KIT_URL} target="_blank" rel="noopener">{es ? `Kit (${KIT_PRICE})` : `Kit (${KIT_PRICE})`}</a>
          <span className="muted small">{es ? 'Pago seguro en Gumroad · IVA incluido · descarga inmediata' : 'Secure checkout on Gumroad · VAT included · instant download'}</span>
        </div>
        <p className="muted small kit-note">{es ? 'Material educativo. No es asesoramiento de inversión ni contiene señales.' : 'Educational material. Not investment advice and no signals.'}</p>
      </div>
      {!compact && <img className="kit-cover" src={`${BASE_URL}kit/cover-${lang}.png`} width="1280" height="720" alt={es ? 'Portada del kit: curva de capital de V1.1 en R' : 'Kit cover: V1.1 equity curve in R'} loading="lazy" />}
    </section>
  );
}
