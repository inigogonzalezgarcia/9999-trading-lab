/** The guided simulator: nine levels from reading a candle to designing and testing a hypothesis.
 *  Levels 0–2 are free; 3–8 belong to Lab Pro. Every level works on real lab results (no invented data). */
import type { L } from './lessons';

export interface Level {
  n: number;
  slug: string;
  title: L;
  summary: L;
  minutes: number;
  pro: boolean;
  /** Implemented in the app today; the rest are announced on the dashboard. */
  ready: boolean;
}

export const LEVELS: Level[] = [
  { n: 0, slug: 'vela', minutes: 6, pro: false, ready: true,
    title: { es: 'Leer una vela y un gráfico', en: 'Read a candle and a chart' },
    summary: { es: 'Apertura, cierre, máximo y mínimo en velas reales de EUR/USD. Cuántas M1 caben en una M15 y por qué importa.', en: 'Open, close, high and low on real EUR/USD candles. How many M1 bars fit in an M15 and why it matters.' } },
  { n: 1, slug: 'backtest', minutes: 8, pro: false, ready: true,
    title: { es: 'Qué es un backtest (y la trampa)', en: 'What a backtest is (and the trap)' },
    summary: { es: 'Mueve el reloj y ve exactamente qué sabe el motor en cada minuto. La vela sin cerrar es la trampa más común.', en: 'Move the clock and see exactly what the engine knows each minute. The unclosed candle is the most common trap.' } },
  { n: 2, slug: 'operacion', minutes: 10, pro: false, ready: true,
    title: { es: 'Una operación de principio a fin', en: 'One trade from start to finish' },
    summary: { es: 'Los diez pasos de una operación real, revelados uno a uno. Predice la salida antes de verla.', en: 'The ten steps of a real trade, revealed one by one. Predict the exit before you see it.' } },
  { n: 3, slug: 'cifras', minutes: 10, pro: true, ready: true,
    title: { es: 'Las cinco cifras', en: 'The five numbers' },
    summary: { es: 'Calcula N, esperanza, acierto, factor de beneficio y drawdown de doce operaciones reales. El simulador corrige.', en: 'Compute N, expectancy, win rate, profit factor and drawdown of twelve real trades. The simulator marks it.' } },
  { n: 4, slug: 'costes', minutes: 8, pro: true, ready: true,
    title: { es: 'Costes: de positivo a negativo', en: 'Costs: from positive to negative' },
    summary: { es: 'Sube el spread y el deslizamiento y ve en qué momento el año cambia de signo.', en: 'Raise spread and slippage and watch the year flip sign.' } },
  { n: 5, slug: 'montecarlo', minutes: 12, pro: true, ready: true,
    title: { es: 'Doce operaciones no demuestran nada', en: 'Twelve trades prove nothing' },
    summary: { es: 'Baraja y remuestrea con tus manos. Construye tu Monte Carlo y compáralo con el del laboratorio.', en: 'Shuffle and resample yourself. Build your Monte Carlo and compare it with the lab\'s.' } },
  { n: 6, slug: 'azar', minutes: 10, pro: true, ready: true,
    title: { es: '¿Lo haría igual el azar?', en: 'Would chance do the same?' },
    summary: { es: 'Doscientas entradas aleatorias con las mismas salidas y costes. Sitúa la regla en su percentil.', en: 'Two hundred random entries with the same exits and costs. Place the rule at its percentile.' } },
  { n: 7, slug: 'fragilidad', minutes: 12, pro: true, ready: true,
    title: { es: 'Fragilidad y fuera de muestra', en: 'Fragility and out of sample' },
    summary: { es: 'Un parámetro cada vez sobre ocho años. Walk-forward con ventanas rodantes.', en: 'One parameter at a time over eight years. Walk-forward with rolling windows.' } },
  { n: 8, slug: 'tu-version', minutes: 15, pro: true, ready: true,
    title: { es: 'Diseña tu versión', en: 'Design your version' },
    summary: { es: 'Elige stop, objetivo, vida del setup y sesión. Backtest y protocolo de tu V1.x al instante sobre 2019–2026, y una decisión escrita en el log.', en: 'Pick stop, target, setup lifetime and session. Backtest and protocol of your V1.x instantly over 2019–2026, and a decision written in the log.' } },
];

/** Real run used by the free levels (explainers, candles, trades). */
export const SIM_RUN = 'eurusd-2024-v1_1';
