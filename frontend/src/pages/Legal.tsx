import { LEGAL } from '../content/legal';
import { useT } from '../i18n';
import { Link } from '../router';

export function LegalPage({ slug }: { slug: string }) {
  const { pick, lang } = useT();
  const page = LEGAL.find((item) => item.slug === slug) ?? LEGAL[0];
  return (
    <main className="prose">
      <nav className="legal-nav small">
        {LEGAL.map((item) => <Link key={item.slug} to={`/legal/${item.slug}`}>{pick(item.title)}</Link>)}
      </nav>
      <h1 className="page-title">{pick(page.title)}</h1>
      {page.sections.map((section, index) => (
        <section key={index}>
          <h2>{pick(section.heading)}</h2>
          {section.body[lang].map((paragraph, i) => <p key={i}>{paragraph}</p>)}
        </section>
      ))}
      <p className="muted small">{lang === 'es' ? 'Última actualización: octubre de 2026.' : 'Last updated: October 2026.'}</p>
    </main>
  );
}
