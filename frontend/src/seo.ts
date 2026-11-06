/** Per-route <title> and meta description (ES/EN), applied after navigation. The static shell carries the
 *  home values; this keeps the rendered DOM honest for crawlers that run JavaScript and for shared links. */
import { useEffect } from 'react';
import { LESSONS } from './content/lessons';
import { LEGAL } from './content/legal';
import { LEVELS } from './content/sim';
import type { Lang } from './i18n';

export const SITE_URL = 'https://fx-trading-lab.pages.dev';
const SUFFIX = ' · FX Trading Lab';

type Meta = { title: string; description: string };

export function routeMeta(path: string, lang: Lang): Meta {
  const es = lang === 'es';
  const lesson = LESSONS.find((l) => path === `/lessons/${l.slug}`);
  if (lesson) return { title: (es ? lesson.title.es : lesson.title.en) + SUFFIX, description: es ? lesson.summary.es : lesson.summary.en };
  const legal = LEGAL.find((l) => path === `/legal/${l.slug}`);
  if (legal) return { title: (es ? legal.title.es : legal.title.en) + SUFFIX, description: es ? 'Información legal de FX Trading Lab, simulador educativo.' : 'Legal information for FX Trading Lab, an educational simulator.' };
  if (path === '/lab' || path.startsWith('/lab/')) {
    return { title: (es ? 'Laboratorio de backtesting: EUR/USD y GBP/USD 2019–2026' : 'Backtesting lab: EUR/USD and GBP/USD 2019–2026') + SUFFIX,
      description: es ? 'Veintisiete ejecuciones reales de una hipótesis intradía sobre ocho años: curva de capital, cada operación explicada en su gráfico, Monte Carlo, benchmark aleatorio, sensibilidad y walk-forward.' : 'Twenty-seven real runs of an intraday hypothesis over eight years: equity curve, every trade explained on its chart, Monte Carlo, random benchmark, sensitivity and walk-forward.' };
  }
  if (path === '/lessons') {
    return { title: (es ? 'Cómo leer un backtest, paso a paso: lecciones gratis' : 'How to read a backtest, step by step: free lessons') + SUFFIX,
      description: es ? 'Tres lecciones sobre resultados reales: qué es un backtest honesto, cómo leer una operación y por qué doce operaciones no demuestran nada. Con cuestionario y nota evaluada.' : 'Three lessons on real results: what an honest backtest is, how to read a trade and why twelve trades prove nothing. With quiz and graded lab note.' };
  }
  if (path === '/tour') {
    return { title: (es ? 'Qué vas a ver: el laboratorio en seis pantallas' : 'What you will see: the lab in six screens') + SUFFIX,
      description: es ? 'Datos reales minuto a minuto, cada operación explicada, el resultado del año con costes, el protocolo de investigación y el simulador de nueve niveles.' : 'Real minute data, every trade explained, the year result with costs, the research protocol and the nine-level simulator.' };
  }
  if (path === '/planes' || path === '/plans') {
    return { title: (es ? 'Planes: gratis y Lab Pro' : 'Plans: free and Lab Pro') + SUFFIX,
      description: es ? 'Laboratorio, lecciones y niveles 0–2 gratis sin cuenta. Lab Pro: niveles 3–8, tu V1.x sobre ocho años, informe PDF. 12 € al mes, 89 € al año o 149 € de por vida.' : 'Lab, lessons and levels 0–2 free without an account. Lab Pro: levels 3–8, your V1.x over eight years, PDF report. 12 € a month, 89 € a year or 149 € lifetime.' };
  }
  if (path === '/entrar' || path === '/login') {
    return { title: (es ? 'Entra o crea tu cuenta' : 'Sign in or create your account') + SUFFIX,
      description: es ? 'Cuenta gratis con Google o con un enlace por correo. Guarda tu progreso en el simulador y activa Lab Pro cuando quieras.' : 'Free account with Google or an email link. Save your simulator progress and activate Lab Pro when you want.' };
  }
  if (path === '/app' || path.startsWith('/app/')) {
    const level = LEVELS.find((l) => path === `/app/sim/${l.n}`);
    if (level) return { title: (es ? `Nivel ${level.n}: ${level.title.es}` : `Level ${level.n}: ${level.title.en}`) + SUFFIX, description: es ? level.summary.es : level.summary.en };
    return { title: (es ? 'Simulador: de la vela al protocolo, nueve niveles' : 'Simulator: from the candle to the protocol, nine levels') + SUFFIX,
      description: es ? 'Itinerario guiado sobre resultados reales. Niveles 0–2 gratis sin cuenta: leer una vela, qué es un backtest, una operación de principio a fin.' : 'Guided itinerary on real results. Levels 0–2 free without an account: read a candle, what a backtest is, one trade start to finish.' };
  }
  if (path === '/method') {
    return { title: (es ? 'Método: cómo investigamos una estrategia (y aviso legal)' : 'Method: how we research a strategy (and legal notice)') + SUFFIX,
      description: es ? 'Hipótesis congelada, motor causal con costes, protocolo de periodos independientes, walk-forward, Monte Carlo, sensibilidad y benchmark aleatorio. Sin señales ni ejecución real.' : 'Frozen hypothesis, causal engine with costs, protocol of independent periods, walk-forward, Monte Carlo, sensitivity and random benchmark. No signals, no live execution.' };
  }
  return { title: es ? 'FX Trading Lab — simulador educativo de investigación de estrategias' : 'FX Trading Lab — educational strategy research simulator',
    description: es ? 'Simulador educativo: una hipótesis intradía sobre EUR/USD y GBP/USD, un motor de backtesting causal y un protocolo de investigación. Sin señales, sin ejecución real, sin promesas.' : 'Educational simulator: an intraday hypothesis on EUR/USD and GBP/USD, a causal backtesting engine and a research protocol. No signals, no live execution, no promises.' };
}

function setMeta(selector: string, attr: string, value: string) {
  const el = document.head.querySelector<HTMLMetaElement>(selector);
  if (el) el.setAttribute(attr, value);
}

const KNOWN = /^\/(|lab(\/[^/]+)?|lessons(\/[^/]+)?|method|legal\/[^/]+|tour|planes|plans|entrar|login|app|app\/sim\/[0-8])$/;

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
