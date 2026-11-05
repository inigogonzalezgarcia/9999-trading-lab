/** Per-route <title> and meta description (ES/EN), applied after navigation. The static shell carries the
 *  home values; this keeps the rendered DOM honest for crawlers that run JavaScript and for shared links. */
import { useEffect } from 'react';
import { LESSONS } from './content/lessons';
import { LEGAL } from './content/legal';
import type { Lang } from './i18n';

export const SITE_URL = 'https://fx-trading-lab.pages.dev';
const SUFFIX = ' · FX Research Lab';

type Meta = { title: string; description: string };

export function routeMeta(path: string, lang: Lang): Meta {
  const es = lang === 'es';
  const lesson = LESSONS.find((l) => path === `/lessons/${l.slug}`);
  if (lesson) return { title: (es ? lesson.title.es : lesson.title.en) + SUFFIX, description: es ? lesson.summary.es : lesson.summary.en };
  const legal = LEGAL.find((l) => path === `/legal/${l.slug}`);
  if (legal) return { title: (es ? legal.title.es : legal.title.en) + SUFFIX, description: es ? 'Información legal de FX Research Lab, simulador educativo.' : 'Legal information for FX Research Lab, an educational simulator.' };
  if (path === '/lab' || path.startsWith('/lab/')) {
    return { title: (es ? 'Laboratorio de backtesting: EUR/USD y GBP/USD 2022–2024' : 'Backtesting lab: EUR/USD and GBP/USD 2022–2024') + SUFFIX,
      description: es ? 'Doce ejecuciones reales de una hipótesis intradía: curva de capital, cada operación explicada en su gráfico, Monte Carlo, benchmark aleatorio, sensibilidad y walk-forward.' : 'Twelve real runs of an intraday hypothesis: equity curve, every trade explained on its chart, Monte Carlo, random benchmark, sensitivity and walk-forward.' };
  }
  if (path === '/lessons') {
    return { title: (es ? 'Cómo leer un backtest, paso a paso: lecciones gratis' : 'How to read a backtest, step by step: free lessons') + SUFFIX,
      description: es ? 'Tres lecciones sobre resultados reales: qué es un backtest honesto, cómo leer una operación y por qué doce operaciones no demuestran nada. Con cuestionario y nota evaluada.' : 'Three lessons on real results: what an honest backtest is, how to read a trade and why twelve trades prove nothing. With quiz and graded lab note.' };
  }
  if (path === '/method') {
    return { title: (es ? 'Método: cómo investigamos una estrategia (y aviso legal)' : 'Method: how we research a strategy (and legal notice)') + SUFFIX,
      description: es ? 'Hipótesis congelada, motor causal con costes, protocolo de periodos independientes, walk-forward, Monte Carlo, sensibilidad y benchmark aleatorio. Sin señales ni ejecución real.' : 'Frozen hypothesis, causal engine with costs, protocol of independent periods, walk-forward, Monte Carlo, sensitivity and random benchmark. No signals, no live execution.' };
  }
  return { title: es ? 'FX Research Lab — simulador educativo de investigación de estrategias' : 'FX Research Lab — educational strategy research simulator',
    description: es ? 'Simulador educativo: una hipótesis intradía sobre EUR/USD y GBP/USD, un motor de backtesting causal y un protocolo de investigación. Sin señales, sin ejecución real, sin promesas.' : 'Educational simulator: an intraday hypothesis on EUR/USD and GBP/USD, a causal backtesting engine and a research protocol. No signals, no live execution, no promises.' };
}

function setMeta(selector: string, attr: string, value: string) {
  const el = document.head.querySelector<HTMLMetaElement>(selector);
  if (el) el.setAttribute(attr, value);
}

const KNOWN = /^\/(|lab(\/[^/]+)?|lessons(\/[^/]+)?|method|legal\/[^/]+)$/;

export function useSeo(path: string, lang: Lang) {
  useEffect(() => {
    const meta = routeMeta(path, lang);
    // Unknown routes are rendered by the SPA (Pages serves index.html for every path); keep them out of the index.
    let robots = document.head.querySelector<HTMLMetaElement>('meta[name="robots"]');
    if (!robots) { robots = document.createElement('meta'); robots.name = 'robots'; document.head.appendChild(robots); }
    robots.content = KNOWN.test(path) ? 'index,follow' : 'noindex';
    document.title = meta.title;
    document.documentElement.lang = lang;
    setMeta('meta[name="description"]', 'content', meta.description);
    setMeta('meta[property="og:title"]', 'content', meta.title);
    setMeta('meta[property="og:description"]', 'content', meta.description);
    setMeta('meta[property="og:url"]', 'content', SITE_URL + path);
    const canonical = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (canonical) canonical.href = SITE_URL + path;
  }, [path, lang]);
}
