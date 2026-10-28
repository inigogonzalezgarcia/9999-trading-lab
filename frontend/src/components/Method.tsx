import { useT } from '../i18n';

const TEXT = {
  es: {
    tab: 'Aviso / Método',
    noticeTitle: 'Aviso legal',
    notice: [
      'FX Research Lab es una herramienta educativa de investigación y backtesting. No constituye asesoramiento de inversión, no es un servicio de señales ni alertas, y no tiene conexión con ningún bróker ni ejecución real de órdenes.',
      'Todos los resultados son simulaciones sobre datos históricos obtenidas con las hipótesis de estrategia y ejecución registradas. Los resultados simulados no son evidencia de una ventaja rentable y el rendimiento histórico no garantiza resultados futuros.',
      'El autor no es un asesor financiero autorizado ni registrado. La operativa en divisas con apalancamiento conlleva un alto riesgo de pérdida. Nada en este software, su documentación o los informes que genera debe utilizarse para operar con dinero real. El software se distribuye "tal cual" bajo licencia MIT, sin garantía de ningún tipo.',
    ],
    whatTitle: '¿Qué hace esta herramienta?',
    what: 'Toma velas de un minuto de un par de divisas, aplica unas reglas escritas de antemano (la "hipótesis") y simula qué habría pasado si alguien las hubiera seguido al pie de la letra, pagando spread, deslizamiento y comisión en cada operación. Después mide el resultado en R: cada operación arriesga 1R, así que +2R significa que se ganó el doble de lo arriesgado y −1R que se perdió lo arriesgado.',
    hypothesisTitle: 'La hipótesis V1, en lenguaje llano',
    hypothesis: [
      ['Barrido de liquidez', 'El precio atraviesa un máximo o mínimo reciente donde suele haber stops acumulados y la vela M15 que lo contiene cierra de vuelta al otro lado. Es el "disparador": sin barrido no hay candidato.'],
      ['Zona', 'La última vela M15 de sentido contrario antes del impulso define una zona de oferta o demanda. Es donde se espera que el precio vuelva.'],
      ['Impulso (tramo 1)', 'Un movimiento direccional de al menos cierto múltiplo del ATR que además rompe la estructura M15. Si el movimiento es flojo, el candidato se descarta.'],
      ['Retroceso y tramo 2', 'El precio retrocede una fracción concreta del tramo 1 y vuelve a impulsarse en la misma dirección. Dos tramos, no uno.'],
      ['Ruptura de estructura (BOS)', 'Un cierre M15 más allá del último pivote confirma el patrón. Solo cuenta si ocurre dentro de una ventana horaria de observación configurada.'],
      ['Entrada, stop y objetivo', 'Se entra al primer precio M1 ejecutable tras el BOS; el stop se coloca según la regla de la versión (extremo del barrido en V1, lado distal de la zona en V1.1) y el objetivo es un múltiplo fijo del riesgo. Si el stop queda demasiado lejos en ATR, no se opera.'],
    ],
    causalityTitle: 'Sin mirar el futuro',
    causality: 'Una vela solo existe para el motor cuando ha cerrado, y un pivote solo cuando la vela que lo confirma ha cerrado. Las entradas se ejecutan al precio siguiente disponible, nunca al precio en que se detectó la señal. Esto hace los resultados peores que en un gráfico "a posteriori", y es intencionado.',
    protocolTitle: 'El protocolo de investigación',
    protocol: [
      ['Backtest base', 'Un pase completo sobre los datos con la configuración congelada. Da el punto de partida, nunca la conclusión.'],
      ['Periodos independientes', 'Los datos se cortan en tramos cronológicos (p. ej. semestres) y se comprueba si el resultado se mantiene en cada uno o depende de unos pocos meses.'],
      ['Walk-forward', 'Se simula lo que haría un investigador honesto: observa un tramo de entrenamiento, y luego mide el tramo siguiente que no ha visto. Se repite deslizando la ventana. Solo cuentan los tramos "fuera de muestra".'],
      ['Monte Carlo', 'Se barajan miles de veces las operaciones reales para ver qué rachas y drawdowns son esperables por puro azar con esa misma distribución de resultados.'],
      ['Sensibilidad', 'Se cambia un parámetro a la vez (ventana horaria, ATR mínimo, distancia del stop…) y se mira si el resultado se derrumba. Una estrategia que solo funciona con un valor exacto suele estar sobreajustada.'],
      ['Benchmark aleatorio', 'Operaciones al azar con la misma frecuencia, horarios y costes. Si la hipótesis no supera claramente a tirar una moneda, no hay evidencia.'],
    ],
    readingTitle: 'Cómo leer un resultado',
    reading: [
      'Pocas operaciones (menos de 30–50) no permiten concluir nada; el error estadístico es enorme.',
      'Un total positivo en un año puede deberse a dos o tres operaciones; mira la mediana, el percentil frente al benchmark y la curva por tramos.',
      'Los costes importan: con spread y deslizamiento realistas muchas ideas intradía pasan de positivas a negativas.',
      'Si cambiar un poco un parámetro cambia mucho el resultado, desconfía.',
      'Los informes y CSV incluyen el hash del fichero de datos y de la configuración para que cualquiera pueda reproducir exactamente lo que ves.',
    ],
    stateTitle: 'Estado actual de la investigación',
    state: 'Con datos reales de 2024 la hipótesis V1 genera muy pocas operaciones y un resultado neto negativo; la variante V1.1 (ventanas de Londres, stop distal) genera más operaciones pero no supera con claridad al benchmark aleatorio. Es decir: a día de hoy no hay evidencia de ventaja. Esta herramienta sirve para aprender a comprobar eso con rigor, no para operar.',
  },
  en: {
    tab: 'Notice / Method',
    noticeTitle: 'Legal notice',
    notice: [
      'FX Research Lab is an educational research and backtesting tool. It is not investment advice, not a trading signal or alert service, and it has no broker connection or live order execution.',
      'All results are simulations on historical data produced with the recorded strategy and execution assumptions. Simulated results are not evidence of a profitable edge and historical performance does not guarantee future results.',
      'The author is not a licensed or registered financial adviser. Trading leveraged foreign exchange involves a high risk of loss. Nothing in this software, its documentation or any report it produces should be used to place real trades. The software is provided "as is" under the MIT License, without warranty of any kind.',
    ],
    whatTitle: 'What does this tool do?',
    what: 'It takes one-minute candles of a currency pair, applies rules written in advance (the "hypothesis") and simulates what would have happened to someone who followed them to the letter, paying spread, slippage and commission on every trade. It then measures the outcome in R: every trade risks 1R, so +2R means twice the risk was earned and −1R means the risk was lost.',
    hypothesisTitle: 'The V1 hypothesis in plain words',
    hypothesis: [
      ['Liquidity sweep', 'Price trades through a recent high or low where stops tend to cluster, and the M15 candle containing it closes back on the other side. This is the trigger: no sweep, no candidate.'],
      ['Zone', 'The last opposite-direction M15 candle before the impulse defines a supply or demand zone, where price is expected to return.'],
      ['Displacement (leg 1)', 'A directional move of at least a given ATR multiple that also breaks M15 structure. A weak move discards the candidate.'],
      ['Retracement and leg 2', 'Price pulls back a specific fraction of leg 1 and pushes again in the same direction. Two legs, not one.'],
      ['Break of structure (BOS)', 'An M15 close beyond the last pivot confirms the pattern. It only counts inside a configured observation window.'],
      ['Entry, stop and target', 'Entry at the first executable M1 price after the BOS; the stop follows the version rule (sweep extreme in V1, distal side of the zone in V1.1) and the target is a fixed multiple of the risk. If the stop is too far in ATR terms, no trade.'],
    ],
    causalityTitle: 'No peeking at the future',
    causality: 'A candle exists for the engine only once it has closed, and a pivot only once its confirming candle has closed. Entries fill at the next available price, never at the price where the signal was detected. This makes results worse than on a hindsight chart, on purpose.',
    protocolTitle: 'The research protocol',
    protocol: [
      ['Baseline backtest', 'One full pass over the data with the frozen configuration. The starting point, never the conclusion.'],
      ['Independent periods', 'The data is cut into chronological chunks (e.g. half-years) to check whether the result holds in each or depends on a few months.'],
      ['Walk-forward', 'Simulates an honest researcher: observe a training period, then measure the following period never seen before, sliding the window forward. Only out-of-sample periods count.'],
      ['Monte Carlo', 'The real trades are reshuffled thousands of times to see which streaks and drawdowns are expected by chance alone with that outcome distribution.'],
      ['Sensitivity', 'One parameter at a time is changed (time window, minimum ATR, stop distance…) to see whether the result collapses. A strategy that only works at one exact value is usually overfitted.'],
      ['Random benchmark', 'Random trades with the same frequency, hours and costs. If the hypothesis does not clearly beat a coin flip, there is no evidence.'],
    ],
    readingTitle: 'How to read a result',
    reading: [
      'Few trades (under 30–50) support no conclusion; the statistical error is huge.',
      'A positive yearly total can come from two or three trades; look at the median, the percentile against the benchmark and the per-period curve.',
      'Costs matter: with realistic spread and slippage many intraday ideas turn from positive to negative.',
      'If a small parameter change moves the result a lot, be suspicious.',
      'Reports and CSVs include the hash of the data file and of the configuration so anyone can reproduce exactly what you see.',
    ],
    stateTitle: 'Current state of the research',
    state: 'On real 2024 data the V1 hypothesis produces very few trades and a negative net result; the V1.1 variant (London windows, distal stop) produces more trades but does not clearly beat the random benchmark. In other words: as of today there is no evidence of an edge. This tool exists to learn how to check that rigorously, not to trade.',
  },
};

export function MethodPage() {
  const { lang } = useT();
  const t = TEXT[lang];
  return (
    <article className="method">
      <h1 className="page-title">{t.tab}</h1>
      <h2>{t.noticeTitle}</h2>
      <div className="notice-box">{t.notice.map((p) => <p key={p.slice(0, 20)}>{p}</p>)}</div>
      <h2>{t.whatTitle}</h2>
      <p>{t.what}</p>
      <h2>{t.hypothesisTitle}</h2>
      <ol className="method-steps">{t.hypothesis.map(([title, text]) => <li key={title}><strong>{title}.</strong> {text}</li>)}</ol>
      <h2>{t.causalityTitle}</h2>
      <p>{t.causality}</p>
      <h2>{t.protocolTitle}</h2>
      <ol className="method-steps">{t.protocol.map(([title, text]) => <li key={title}><strong>{title}.</strong> {text}</li>)}</ol>
      <h2>{t.readingTitle}</h2>
      <ul>{t.reading.map((line) => <li key={line.slice(0, 20)}>{line}</li>)}</ul>
      <h2>{t.stateTitle}</h2>
      <p>{t.state}</p>
      <p className="muted small">DISCLAIMER.md · docs/BACKTESTING.md · docs/FIRST_REAL_RUN.md · docs/DECISION_LOG.md</p>
    </article>
  );
}
