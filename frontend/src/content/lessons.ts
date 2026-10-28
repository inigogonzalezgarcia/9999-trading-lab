/** Free lessons. Each one is built on a precomputed run of the lab (see config/web_runs.yaml). */

export type L<T = string> = { es: T; en: T };

export type Widget =
  | { type: 'kpis'; run: string }
  | { type: 'equity'; run: string }
  | { type: 'rejections'; run: string }
  | { type: 'timing'; run: string }
  | { type: 'explainer'; run: string; trade: 'best' | 'worst' | number }
  | { type: 'breakdowns'; run: string }
  | { type: 'research'; run: string; parts: ('benchmark' | 'montecarlo' | 'sensitivity' | 'walkforward')[] };

export interface Section {
  heading: L;
  paragraphs: L<string[]>;
  widget?: Widget;
  callout?: L;
}

export interface Question {
  id: string;
  prompt: L;
  options: L<string[]>;
  answer: number;
  explanation: L;
}

export interface RubricItem {
  id: string;
  label: L;
  keywords: L<string[]>;
}

export interface Lesson {
  slug: string;
  order: number;
  minutes: number;
  free: boolean;
  title: L;
  summary: L;
  runs: string[];
  sections: Section[];
  quiz: Question[];
  labNote: { prompt: L; rubric: RubricItem[]; example: L };
}

export const LESSONS: Lesson[] = [
  {
    slug: 'backtest-honesto',
    order: 1,
    minutes: 12,
    free: true,
    title: { es: 'Qué es un backtest honesto', en: 'What an honest backtest is' },
    summary: {
      es: 'Por qué casi todos los backtests que verás por ahí están mal, y las cuatro reglas que hacen que uno valga algo. Con el resultado real de la hipótesis V1 sobre 2024.',
      en: 'Why most backtests you will see around are wrong, and the four rules that make one worth anything. With the real result of the V1 hypothesis on 2024.',
    },
    runs: ['eurusd-2024-v1'],
    sections: [
      {
        heading: { es: 'La trampa del gráfico a posteriori', en: 'The hindsight-chart trap' },
        paragraphs: {
          es: [
            'Cualquier patrón parece funcionar cuando lo miras en un gráfico ya cerrado. Ves el barrido, ves el impulso, ves la ruptura y ves el precio llegar al objetivo. Lo que no ves es todo lo que, en ese momento, todavía no se sabía: que la vela que "confirma" aún no había cerrado, que había otros tres setups parecidos ese mismo día que fallaron, y que el spread a esa hora era el doble de lo que suponías.',
            'Un backtest honesto es una máquina que te obliga a vivir el pasado como si fuera presente: solo conoce lo que ya ha cerrado, paga cada coste y apunta todo lo que descarta. Si eso te suena menos emocionante que un gráfico con flechas, es exactamente la idea.',
          ],
          en: [
            'Any pattern seems to work when you look at it on a closed chart. You see the sweep, the impulse, the break and the price reaching the target. What you do not see is everything that was not yet known at that moment: that the "confirming" candle had not closed, that three similar setups failed that same day, and that the spread at that hour was twice what you assumed.',
            'An honest backtest is a machine that forces you to live the past as if it were the present: it only knows what has already closed, it pays every cost and it records everything it discards. If that sounds less exciting than a chart with arrows, that is exactly the point.',
          ],
        },
      },
      {
        heading: { es: 'Las cuatro reglas', en: 'The four rules' },
        paragraphs: {
          es: [
            '1. Hipótesis congelada. Las reglas se escriben antes de ver los resultados y no se tocan después. En el laboratorio viven en un fichero de configuración (strategy_v1.yaml) cuyo hash aparece en cada resultado. Si cambias una regla, es otra versión (V1.1, V1.2), con su propio nombre y su propio resultado.',
            '2. Causalidad. Una vela existe solo cuando ha cerrado; un pivote solo cuando la vela que lo confirma ha cerrado; una entrada se ejecuta al siguiente precio disponible, nunca al precio donde "viste" la señal. Esto hace los resultados peores que en el gráfico a posteriori. A propósito.',
            '3. Costes reales. Spread de ese minuto (si los datos lo traen), deslizamiento y comisión en cada operación. Muchas ideas intradía son positivas sin costes y negativas con ellos.',
            '4. Registro completo. No solo las operaciones: también los candidatos que no llegaron a serlo y por qué. Un backtest que solo enseña las operaciones ganadoras es una selección, no una prueba.',
          ],
          en: [
            '1. Frozen hypothesis. The rules are written before seeing results and never touched afterwards. In the lab they live in a configuration file (strategy_v1.yaml) whose hash appears in every result. Change a rule and it is another version (V1.1, V1.2), with its own name and its own result.',
            '2. Causality. A candle exists only once it has closed; a pivot only once its confirming candle has closed; an entry fills at the next available price, never at the price where you "saw" the signal. This makes results worse than on the hindsight chart. On purpose.',
            '3. Real costs. The spread of that minute (when the data carries it), slippage and commission on every trade. Many intraday ideas are positive without costs and negative with them.',
            '4. Complete record. Not only the trades: also the candidates that never became one, and why. A backtest that only shows the winning trades is a selection, not a test.',
          ],
        },
      },
      {
        heading: { es: 'Lo que salió: V1 sobre EUR/USD 2024', en: 'What came out: V1 on EUR/USD 2024' },
        paragraphs: {
          es: [
            'Estos son los números reales de la hipótesis original sobre un año de velas de un minuto. Fíjate primero en el número de operaciones y solo después en la R total. Con tan pocas operaciones, el total es casi anecdótico: lo que importa es entender por qué hubo tan pocas.',
          ],
          en: [
            'These are the real numbers of the original hypothesis on one year of one-minute candles. Look at the number of trades first and only then at the total R. With so few trades the total is almost anecdotal: what matters is understanding why there were so few.',
          ],
        },
        widget: { type: 'kpis', run: 'eurusd-2024-v1' },
      },
      {
        heading: { es: 'Por qué miles de candidatos acaban en un puñado de operaciones', en: 'Why thousands of candidates end up as a handful of trades' },
        paragraphs: {
          es: [
            'El motor siguió más de tres mil candidatos. Cada barra que muestra un motivo de rechazo es una regla haciendo su trabajo: el barrido se invalidó, el sesgo cambió, el setup caducó, el stop quedaba demasiado lejos. Un backtest que no te enseña esto te está escondiendo la parte más importante del resultado.',
            'La conclusión no es "la estrategia es mala". La conclusión es que, tal y como está escrita, la hipótesis apenas produce operaciones en sus ventanas horarias, y que por tanto no hay evidencia ni a favor ni en contra. Eso también es un resultado, y es más útil que un +30 % inventado.',
          ],
          en: [
            'The engine tracked more than three thousand candidates. Every bar showing a rejection reason is a rule doing its job: the sweep was invalidated, the bias changed, the setup timed out, the stop was too far away. A backtest that does not show you this is hiding the most important part of the result.',
            'The conclusion is not "the strategy is bad". The conclusion is that, as written, the hypothesis barely produces trades in its time windows, and that therefore there is no evidence for or against it. That is a result too, and a more useful one than a made-up +30 %.',
          ],
        },
        widget: { type: 'rejections', run: 'eurusd-2024-v1' },
      },
      {
        heading: { es: 'Qué significa R', en: 'What R means' },
        paragraphs: {
          es: [
            'Cada operación arriesga 1R: la distancia entre la entrada y el stop. Si gana el doble de lo que arriesgó, es +2R; si toca el stop, −1R. Medir en R permite comparar operaciones con stops de distinto tamaño y hablar de resultados sin hablar de dinero, que depende de cada cuenta.',
            'La "esperanza" es la R media por operación. Es el número que de verdad describe una hipótesis, y necesita muchas operaciones para ser fiable. Lo veremos en la lección 3.',
          ],
          en: [
            'Every trade risks 1R: the distance between entry and stop. If it earns twice what it risked, that is +2R; if it hits the stop, −1R. Measuring in R lets you compare trades with stops of different sizes and talk about results without talking about money, which depends on each account.',
            '"Expectancy" is the mean R per trade. It is the number that truly describes a hypothesis, and it needs many trades to be reliable. We will see that in lesson 3.',
          ],
        },
        callout: {
          es: 'Nada de esto es una recomendación de operar. Es un ejercicio de método sobre datos históricos.',
          en: 'None of this is a recommendation to trade. It is an exercise in method on historical data.',
        },
      },
    ],
    quiz: [
      {
        id: 'q1',
        prompt: { es: 'Un backtest entra "al precio donde se detecta la señal". ¿Qué regla incumple?', en: 'A backtest enters "at the price where the signal is detected". Which rule does it break?' },
        options: { es: ['Hipótesis congelada', 'Causalidad', 'Costes reales', 'Ninguna'], en: ['Frozen hypothesis', 'Causality', 'Real costs', 'None'] },
        answer: 1,
        explanation: { es: 'La señal se conoce cuando la vela cierra; el primer precio ejecutable es el siguiente. Entrar antes es mirar el futuro.', en: 'The signal is known when the candle closes; the first executable price is the next one. Entering earlier is peeking at the future.' },
      },
      {
        id: 'q2',
        prompt: { es: 'Tras ver que el resultado es negativo, cambias la ventana horaria y vuelves a ejecutar. ¿Qué has hecho?', en: 'After seeing a negative result you change the time window and run again. What have you done?' },
        options: { es: ['Optimizar correctamente', 'Crear una nueva versión que hay que nombrar y registrar', 'Nada reprochable', 'Validar la hipótesis'], en: ['Optimised correctly', 'Created a new version that must be named and logged', 'Nothing wrong', 'Validated the hypothesis'] },
        answer: 1,
        explanation: { es: 'No está prohibido cambiar reglas; está prohibido hacerlo en silencio. Cada cambio es una versión nueva con su propio resultado y su propia fragilidad.', en: 'Changing rules is not forbidden; doing it silently is. Every change is a new version with its own result and its own fragility.' },
      },
      {
        id: 'q3',
        prompt: { es: 'V1 produjo 5 operaciones en todo 2024. ¿Cuál es la lectura correcta?', en: 'V1 produced 5 trades in all of 2024. What is the correct reading?' },
        options: { es: ['Pierde dinero: descartar', 'Gana dinero: operar', 'No hay evidencia en ningún sentido; hay que entender por qué produce tan pocas', 'Hay que subir el riesgo por operación'], en: ['It loses money: discard', 'It makes money: trade it', 'There is no evidence either way; understand why it produces so few', 'Raise the risk per trade'] },
        answer: 2,
        explanation: { es: 'Cinco operaciones no permiten concluir nada estadísticamente. El dato útil está en los rechazos.', en: 'Five trades support no statistical conclusion. The useful information is in the rejections.' },
      },
      {
        id: 'q4',
        prompt: { es: 'Una operación arriesga 12 pips y gana 18. ¿Cuánto es en R?', en: 'A trade risks 12 pips and earns 18. How much is that in R?' },
        options: { es: ['+18R', '+1,5R', '+0,67R', '+6R'], en: ['+18R', '+1.5R', '+0.67R', '+6R'] },
        answer: 1,
        explanation: { es: '18 / 12 = 1,5 veces el riesgo asumido.', en: '18 / 12 = 1.5 times the risk taken.' },
      },
      {
        id: 'q5',
        prompt: { es: '¿Para qué sirve el hash del fichero de datos que aparece en cada resultado?', en: 'What is the dataset hash shown in every result for?' },
        options: { es: ['Decoración', 'Para que cualquiera pueda reproducir exactamente el mismo resultado con los mismos datos', 'Para cifrar las operaciones', 'Para acelerar el motor'], en: ['Decoration', 'So anyone can reproduce exactly the same result with the same data', 'To encrypt the trades', 'To speed up the engine'] },
        answer: 1,
        explanation: { es: 'Mismo hash de datos + mismo hash de configuración + misma versión de software = mismo resultado. Sin eso, un número no es comprobable.', en: 'Same data hash + same config hash + same software version = same result. Without that, a number cannot be checked.' },
      },
    ],
    labNote: {
      prompt: {
        es: 'Escribe la nota de laboratorio de este resultado (V1, EUR/USD 2024) en 4–8 líneas: qué hipótesis se probó, cómo se garantizó que la prueba era honesta, qué salió y qué decides hacer a continuación.',
        en: 'Write the lab note for this result (V1, EUR/USD 2024) in 4–8 lines: which hypothesis was tested, how the test was kept honest, what came out and what you decide to do next.',
      },
      rubric: [
        { id: 'hypothesis', label: { es: 'Nombra la hipótesis y su versión', en: 'Names the hypothesis and its version' }, keywords: { es: ['v1', 'hipótesis', 'hipotesis', 'versión', 'version'], en: ['v1', 'hypothesis', 'version'] } },
        { id: 'data', label: { es: 'Identifica los datos (par, periodo o hash)', en: 'Identifies the data (pair, period or hash)' }, keywords: { es: ['2024', 'eur/usd', 'eurusd', 'hash', 'datos'], en: ['2024', 'eur/usd', 'eurusd', 'hash', 'data'] } },
        { id: 'causality', label: { es: 'Menciona la causalidad o los costes', en: 'Mentions causality or costs' }, keywords: { es: ['causal', 'cierre', 'cerrad', 'coste', 'spread', 'deslizamiento', 'comisión', 'comision'], en: ['causal', 'close', 'cost', 'spread', 'slippage', 'commission'] } },
        { id: 'trades', label: { es: 'Da el número de operaciones y lo valora', en: 'Gives the number of trades and weighs it' }, keywords: { es: ['operacion', 'operación', 'trades', 'pocas', 'cinco', '5 '], en: ['trade', 'few', 'five', '5 '] } },
        { id: 'rejections', label: { es: 'Cita los rechazos o el motivo de que haya pocas', en: 'Cites the rejections or why there are so few' }, keywords: { es: ['rechaz', 'candidat', 'ventana', 'stop'], en: ['reject', 'candidate', 'window', 'stop'] } },
        { id: 'decision', label: { es: 'Termina con una decisión concreta', en: 'Ends with a concrete decision' }, keywords: { es: ['decid', 'siguiente', 'próximo', 'proximo', 'v1.1', 'v1.2', 'más datos', 'mas datos', 'multianual'], en: ['decide', 'next', 'v1.1', 'v1.2', 'more data', 'multi-year'] } },
      ],
      example: {
        es: 'Hipótesis V1 (strategy_v1.yaml, hash 4be8…) sobre EUR/USD 2024, velas M1 Dukascopy (hash 65a7…). Motor causal: velas disponibles al cierre, entrada al siguiente precio M1, spread histórico + 0,1 pips de deslizamiento. Resultado: 3.138 candidatos, 5 operaciones, −2,61R. Con 5 operaciones no hay evidencia en ningún sentido; el dato relevante es que el 95 % de los candidatos se rechaza por invalidación del barrido o del sesgo y que casi ningún setup completo cae en las ventanas 02:15–04:15. Decisión: no tocar V1; registrar como experimento V1.1 un cambio de ventanas a la apertura de Londres y repetir el protocolo completo antes de sacar conclusiones.',
        en: 'Hypothesis V1 (strategy_v1.yaml, hash 4be8…) on EUR/USD 2024, Dukascopy M1 candles (hash 65a7…). Causal engine: candles available at close, entry at the next M1 price, historical spread + 0.1 pips slippage. Result: 3,138 candidates, 5 trades, −2.61R. With 5 trades there is no evidence either way; the relevant finding is that 95 % of candidates are rejected on sweep or bias invalidation and that almost no complete setup falls inside the 02:15–04:15 windows. Decision: leave V1 untouched; log a window change to the London open as experiment V1.1 and repeat the full protocol before drawing conclusions.',
      },
    },
  },
  {
    slug: 'leer-una-operacion',
    order: 2,
    minutes: 15,
    free: true,
    title: { es: 'Lee una operación paso a paso', en: 'Read a trade step by step' },
    summary: {
      es: 'Barrido, zona, impulso, retroceso, segundo tramo, ruptura, entrada, stop, salida. Una operación real de V1.1 dibujada sobre sus velas de un minuto, regla a regla.',
      en: 'Sweep, zone, displacement, retracement, second leg, break, entry, stop, exit. A real V1.1 trade drawn on its one-minute candles, rule by rule.',
    },
    runs: ['eurusd-2024-v1_1'],
    sections: [
      {
        heading: { es: 'La operación no es una flecha, es una cadena de reglas', en: 'A trade is not an arrow, it is a chain of rules' },
        paragraphs: {
          es: [
            'En el laboratorio cada operación guarda el momento exacto en que se cumplió cada regla. Eso permite dibujarla sobre sus velas de un minuto y responder a la única pregunta que importa cuando aprendes: ¿por qué entró aquí y no en otro sitio?',
            'Abajo tienes la mejor operación de V1.1 en 2024. Lee la lista de pasos de arriba abajo mientras miras el gráfico. Los niveles horizontales son lo que el motor "sabía" en cada momento; los marcadores, cuándo lo supo.',
          ],
          en: [
            'In the lab every trade stores the exact moment each rule was satisfied. That lets us draw it on its one-minute candles and answer the only question that matters when you are learning: why did it enter here and not somewhere else?',
            'Below is the best V1.1 trade of 2024. Read the list of steps top to bottom while looking at the chart. The horizontal levels are what the engine "knew" at each moment; the markers, when it knew it.',
          ],
        },
        widget: { type: 'explainer', run: 'eurusd-2024-v1_1', trade: 'best' },
      },
      {
        heading: { es: 'Los nueve pasos', en: 'The nine steps' },
        paragraphs: {
          es: [
            '1. Barrido de liquidez: una vela M1 atraviesa un máximo o mínimo reciente donde suelen acumularse stops. 2. Confirmación: la vela M15 que lo contiene cierra de vuelta al otro lado; sin este cierre, no cuenta. 3. Zona: la última vela M15 de sentido contrario antes del impulso define la zona de oferta o demanda. 4. Impulso: un movimiento de al menos cierto múltiplo del ATR que además rompe estructura M15. 5. Retroceso: el precio vuelve una fracción concreta del tramo 1. 6. Segundo tramo: vuelve a impulsarse en la misma dirección. 7. Ruptura de estructura (BOS): un cierre M15 más allá del último pivote, y solo dentro de una ventana de observación. 8. Entrada: primer precio M1 ejecutable tras el BOS, con spread y deslizamiento. 9. Salida: objetivo, stop o cierre de sesión.',
            'Cada paso tiene una hora exacta. Si dos pasos ocurren en la misma vela, el motor sigue respetando el orden: nada se usa antes de que exista.',
          ],
          en: [
            '1. Liquidity sweep: an M1 candle trades through a recent high or low where stops tend to cluster. 2. Confirmation: the containing M15 candle closes back on the other side; without that close it does not count. 3. Zone: the last opposite-direction M15 candle before the impulse defines the supply or demand zone. 4. Displacement: a move of at least a given ATR multiple that also breaks M15 structure. 5. Retracement: price pulls back a specific fraction of leg 1. 6. Second leg: it pushes again in the same direction. 7. Break of structure (BOS): an M15 close beyond the last pivot, and only inside an observation window. 8. Entry: first executable M1 price after the BOS, with spread and slippage. 9. Exit: target, stop or session close.',
            'Every step has an exact time. If two steps happen in the same candle the engine still respects the order: nothing is used before it exists.',
          ],
        },
      },
      {
        heading: { es: 'Ahora una que salió mal', en: 'Now one that went wrong' },
        paragraphs: {
          es: [
            'Misma cadena de reglas, distinto desenlace. Compara dónde quedó el stop respecto a la zona y cuánto recorrió el precio a favor antes de volverse (MFE) y en contra (MAE). Una operación perdedora que cumplió todas las reglas no es un error del método: es el coste normal de una hipótesis. Un error del método sería una operación que no debería haber existido.',
          ],
          en: [
            'Same chain of rules, different ending. Compare where the stop sat relative to the zone and how far price travelled in favour before turning (MFE) and against (MAE). A losing trade that followed every rule is not a method error: it is the normal cost of a hypothesis. A method error would be a trade that should never have existed.',
          ],
        },
        widget: { type: 'explainer', run: 'eurusd-2024-v1_1', trade: 'worst' },
      },
      {
        heading: { es: 'Costes: lo que el gráfico nunca enseña', en: 'Costs: what the chart never shows' },
        paragraphs: {
          es: [
            'En el bloque "Reglas aplicadas" de cada operación verás spread, deslizamiento y comisión. El precio de entrada ya los incluye. Con stops de pocos pips, un spread de 0,3 pips más 0,1 de deslizamiento es un porcentaje relevante del riesgo: por eso una idea intradía puede ser positiva "en bruto" y negativa en neto.',
          ],
          en: [
            'In the "Rules applied" block of each trade you will see spread, slippage and commission. The entry price already includes them. With stops of a few pips, a 0.3-pip spread plus 0.1 of slippage is a relevant share of the risk: that is why an intraday idea can be positive "gross" and negative net.',
          ],
        },
        callout: {
          es: 'Operación simulada sobre datos históricos con fines educativos. No es una recomendación.',
          en: 'Simulated trade on historical data for educational purposes. Not a recommendation.',
        },
      },
    ],
    quiz: [
      {
        id: 'q1',
        prompt: { es: 'El precio atraviesa un mínimo reciente pero la vela M15 cierra por debajo. ¿Hay barrido válido?', en: 'Price trades through a recent low but the M15 candle closes below it. Is there a valid sweep?' },
        options: { es: ['Sí, el mínimo se ha superado', 'No: falta el cierre de vuelta', 'Depende del volumen', 'Solo si es en Londres'], en: ['Yes, the low was taken', 'No: the close-back is missing', 'It depends on volume', 'Only during London'] },
        answer: 1,
        explanation: { es: 'La regla exige que la vela M15 cierre de vuelta al otro lado del nivel. Sin ese cierre es una ruptura, no un barrido.', en: 'The rule requires the M15 candle to close back on the other side of the level. Without that close it is a breakout, not a sweep.' },
      },
      {
        id: 'q2',
        prompt: { es: '¿A qué precio entra el motor tras la ruptura de estructura?', en: 'At what price does the engine enter after the break of structure?' },
        options: { es: ['Al precio de cierre de la vela que rompe', 'Al nivel exacto del BOS', 'Al primer precio M1 ejecutable después, con spread y deslizamiento', 'Al mejor precio del minuto siguiente'], en: ['At the close of the breaking candle', 'At the exact BOS level', 'At the first executable M1 price afterwards, with spread and slippage', 'At the best price of the next minute'] },
        answer: 2,
        explanation: { es: 'Regla de causalidad: la ruptura se conoce al cierre; la primera ejecución posible es después, pagando costes.', en: 'Causality rule: the break is known at close; the first possible fill comes afterwards, paying costs.' },
      },
      {
        id: 'q3',
        prompt: { es: 'Una operación cumple todas las reglas y toca el stop. ¿Qué es?', en: 'A trade follows every rule and hits the stop. What is it?' },
        options: { es: ['Un error del método', 'El coste normal de una hipótesis', 'Una señal falsa que hay que filtrar', 'Un fallo de los datos'], en: ['A method error', 'The normal cost of a hypothesis', 'A false signal to filter out', 'A data error'] },
        answer: 1,
        explanation: { es: 'Las pérdidas que respetan las reglas forman parte de la distribución. "Filtrarlas" a posteriori es sobreajustar.', en: 'Losses that follow the rules are part of the distribution. "Filtering" them in hindsight is overfitting.' },
      },
      {
        id: 'q4',
        prompt: { es: '¿Qué mide el MFE de una operación?', en: 'What does a trade\'s MFE measure?' },
        options: { es: ['Lo máximo que el precio fue a favor antes de salir', 'Lo máximo que fue en contra', 'El beneficio final', 'El spread medio'], en: ['The furthest price went in favour before exit', 'The furthest it went against', 'The final profit', 'The average spread'] },
        answer: 0,
        explanation: { es: 'MFE: máxima excursión favorable. MAE: máxima excursión adversa. Juntas dicen si el objetivo y el stop están bien colocados.', en: 'MFE: maximum favourable excursion. MAE: maximum adverse excursion. Together they tell whether target and stop are well placed.' },
      },
    ],
    labNote: {
      prompt: {
        es: 'Describe la operación perdedora que has visto como lo haría un revisor: qué reglas se cumplieron y cuándo, dónde quedó el stop y por qué, y si cambiarías algo en la hipótesis (y cómo lo registrarías).',
        en: 'Describe the losing trade you saw as a reviewer would: which rules fired and when, where the stop sat and why, and whether you would change anything in the hypothesis (and how you would log it).',
      },
      rubric: [
        { id: 'sweep', label: { es: 'Menciona el barrido y su confirmación', en: 'Mentions the sweep and its confirmation' }, keywords: { es: ['barrido', 'sweep', 'confirm'], en: ['sweep', 'confirm'] } },
        { id: 'structure', label: { es: 'Menciona impulso, tramos o ruptura de estructura', en: 'Mentions displacement, legs or break of structure' }, keywords: { es: ['impulso', 'tramo', 'ruptura', 'bos', 'estructura'], en: ['displacement', 'leg', 'break', 'bos', 'structure'] } },
        { id: 'stop', label: { es: 'Habla del stop y de su distancia', en: 'Discusses the stop and its distance' }, keywords: { es: ['stop', 'atr', 'distancia'], en: ['stop', 'atr', 'distance'] } },
        { id: 'excursion', label: { es: 'Usa MFE/MAE o los costes', en: 'Uses MFE/MAE or the costs' }, keywords: { es: ['mfe', 'mae', 'spread', 'coste', 'deslizamiento'], en: ['mfe', 'mae', 'spread', 'cost', 'slippage'] } },
        { id: 'versioning', label: { es: 'Propone el cambio como versión nueva (o decide no cambiar)', en: 'Proposes the change as a new version (or decides not to change)' }, keywords: { es: ['versión', 'version', 'v1.2', 'v1.1', 'experimento', 'no cambiar', 'registrar'], en: ['version', 'v1.2', 'v1.1', 'experiment', 'not change', 'log'] } },
      ],
      example: {
        es: 'Operación SHORT del 13-02-2024 (V1.1). Barrido del máximo de las 08:45 confirmado por cierre M15 de las 09:00; zona de oferta en la última vela alcista previa; impulso de 1,4 ATR con ruptura de estructura; retroceso al 50 % y segundo tramo; BOS a las 09:15 dentro de la ventana de Londres. Entrada al primer M1 tras el BOS con 0,2 pips de spread. Stop en el lado distal de la zona (2,1 ATR de la entrada). MFE +0,4R, MAE −1R: el precio nunca llegó a avanzar y el stop se ejecutó a las 10:07. No propongo cambiar la hipótesis por una operación; si tras el protocolo completo la distancia del stop sigue siendo el factor limitante, se registrará como experimento V1.2.',
        en: 'SHORT trade on 2024-02-13 (V1.1). Sweep of the 08:45 high confirmed by the 09:00 M15 close; supply zone at the last bullish candle before it; 1.4 ATR displacement with structure break; 50 % retracement and second leg; BOS at 09:15 inside the London window. Entry at the first M1 after the BOS with 0.2 pips spread. Stop at the distal side of the zone (2.1 ATR from entry). MFE +0.4R, MAE −1R: price never advanced and the stop filled at 10:07. I do not propose changing the hypothesis over one trade; if after the full protocol the stop distance remains the binding factor, it will be logged as experiment V1.2.',
      },
    },
  },
  {
    slug: 'doce-operaciones',
    order: 3,
    minutes: 18,
    free: true,
    title: { es: 'Doce operaciones no demuestran nada', en: 'Twelve trades prove nothing' },
    summary: {
      es: 'V1.1 ganó +2,35R en 2024. Parece bueno hasta que lo pasas por el protocolo: azar, fragilidad y fuera de muestra. Así es como se separa una ventaja de un golpe de suerte.',
      en: 'V1.1 made +2.35R in 2024. It looks good until you run it through the protocol: chance, fragility and out-of-sample. This is how an edge is told apart from luck.',
    },
    runs: ['eurusd-2024-v1_1', 'eurusd-2024-v1_1-research'],
    sections: [
      {
        heading: { es: 'Un resultado positivo', en: 'A positive result' },
        paragraphs: {
          es: [
            'V1.1 es un experimento registrado: mismas reglas que V1 salvo tres cambios (ventanas en la apertura de Londres, stop en el lado distal de la zona, caducidad de los niveles de liquidez). Sobre 2024 produjo doce operaciones y un total positivo. Si esto fuera un anuncio, aquí terminaría la historia.',
          ],
          en: [
            'V1.1 is a logged experiment: the same rules as V1 except three changes (London-open windows, stop at the distal side of the zone, expiry of liquidity levels). On 2024 it produced twelve trades and a positive total. If this were an advert, the story would end here.',
          ],
        },
        widget: { type: 'kpis', run: 'eurusd-2024-v1_1' },
      },
      {
        heading: { es: 'Mira de dónde sale el total', en: 'Look where the total comes from' },
        paragraphs: {
          es: [
            'Antes de cualquier estadística, mira la curva y los desgloses. Dos o tres operaciones ganadoras hacen todo el resultado; varios meses son negativos; por día de la semana y por hora los cubos tienen una o dos operaciones. Nada de esto es "malo": es lo que se ve cuando la muestra es pequeña.',
          ],
          en: [
            'Before any statistic, look at the curve and the breakdowns. Two or three winning trades make the whole result; several months are negative; by weekday and by hour the buckets hold one or two trades. None of this is "bad": it is what you see when the sample is small.',
          ],
        },
        widget: { type: 'equity', run: 'eurusd-2024-v1_1' },
      },
      {
        heading: { es: 'Pregunta 1: ¿lo haría igual el azar?', en: 'Question 1: would chance do the same?' },
        paragraphs: {
          es: [
            'El benchmark aleatorio ejecuta cientos de "estrategias" que entran al azar con la misma frecuencia, en las mismas horas y pagando los mismos costes. Después mira en qué percentil queda la hipótesis real. Un percentil 95 o más sería una señal; un percentil 75 significa que una de cada cuatro estrategias aleatorias lo habría hecho igual o mejor.',
          ],
          en: [
            'The random benchmark runs hundreds of "strategies" that enter at random with the same frequency, at the same hours and paying the same costs. Then it checks which percentile the real hypothesis lands in. A percentile of 95 or more would be a signal; a 75th percentile means one in four random strategies would have done the same or better.',
          ],
        },
        widget: { type: 'research', run: 'eurusd-2024-v1_1-research', parts: ['benchmark'] },
      },
      {
        heading: { es: 'Pregunta 2: ¿qué rachas son normales?', en: 'Question 2: which streaks are normal?' },
        paragraphs: {
          es: [
            'Monte Carlo baraja miles de veces las mismas doce operaciones y mira qué totales y qué drawdowns aparecen solo por el orden. Si el peor 5 % de los caminos pierde varias R, eso es lo que debes esperar en algún momento aunque la hipótesis fuera buena.',
          ],
          en: [
            'Monte Carlo reshuffles the same twelve trades thousands of times and looks at which totals and drawdowns appear from the order alone. If the worst 5 % of paths lose several R, that is what you should expect at some point even if the hypothesis were good.',
          ],
        },
        widget: { type: 'research', run: 'eurusd-2024-v1_1-research', parts: ['montecarlo'] },
      },
      {
        heading: { es: 'Pregunta 3: ¿sobrevive a un cambio pequeño?', en: 'Question 3: does it survive a small change?' },
        paragraphs: {
          es: [
            'La sensibilidad cambia un parámetro a la vez: la distancia máxima del stop, la referencia del stop, la caducidad de los niveles, la sesión. Si el signo del resultado se da la vuelta con cambios vecinos, lo que tienes no es una ventaja: es un punto afortunado en una superficie ruidosa.',
            'Esto es lo que pasa con V1.1: con stop máximo de 4 ATR en vez de 3 el total se vuelve negativo; con el stop en el origen del tramo 1, más negativo todavía; en la sesión de Nueva York, claramente negativo. Un resultado así no se publica como "estrategia rentable". Se publica como lo que es: un experimento que no ha pasado el protocolo.',
          ],
          en: [
            'Sensitivity changes one parameter at a time: the maximum stop distance, the stop reference, the level expiry, the session. If the sign of the result flips with neighbouring changes, what you have is not an edge: it is a lucky point on a noisy surface.',
            'That is what happens with V1.1: with a 4 ATR maximum stop instead of 3 the total turns negative; with the stop at the origin of leg 1, more negative still; in the New York session, clearly negative. A result like this is not published as a "profitable strategy". It is published as what it is: an experiment that has not passed the protocol.',
          ],
        },
        widget: { type: 'research', run: 'eurusd-2024-v1_1-research', parts: ['sensitivity', 'walkforward'] },
      },
      {
        heading: { es: 'Qué se decide con esto', en: 'What gets decided from this' },
        paragraphs: {
          es: [
            'La decisión registrada en el laboratorio fue: V1 se congela; V1.1 queda como experimento documentado, no como evidencia; el factor que de verdad limita es la colocación del stop respecto a la entrada (más de la mitad de los setups completos se rechazan por distancia), y eso se estudiará como V1.2 con datos de varios años, no de uno. Eso es investigar: la mayoría de las veces el resultado es "todavía no sabemos", y saberlo con rigor es lo que vale.',
          ],
          en: [
            'The decision logged in the lab was: V1 stays frozen; V1.1 remains a documented experiment, not evidence; the truly binding factor is the stop placement relative to entry (more than half of the complete setups are rejected on distance), and that will be studied as V1.2 on several years of data, not one. That is research: most of the time the result is "we do not know yet", and knowing that rigorously is what is worth something.',
          ],
        },
        callout: {
          es: 'Si alguien te enseña un backtest con doce operaciones y una curva bonita, ya sabes qué tres preguntas hacer.',
          en: 'If someone shows you a backtest with twelve trades and a pretty curve, you now know which three questions to ask.',
        },
      },
    ],
    quiz: [
      {
        id: 'q1',
        prompt: { es: 'La hipótesis queda en el percentil 75 frente al benchmark aleatorio. ¿Qué significa?', en: 'The hypothesis lands at the 75th percentile against the random benchmark. What does it mean?' },
        options: { es: ['Es rentable con un 75 % de probabilidad', 'Una de cada cuatro estrategias aleatorias lo hizo igual o mejor: no hay evidencia de ventaja', 'Supera al 75 % de los traders', 'Hay que subir el objetivo'], en: ['It is profitable with 75 % probability', 'One in four random strategies did the same or better: no evidence of an edge', 'It beats 75 % of traders', 'Raise the target'] },
        answer: 1,
        explanation: { es: 'El percentil compara con el azar en igualdad de condiciones (frecuencia, horas, costes). 75 está lejos del 95 que se exigiría.', en: 'The percentile compares against chance on equal terms (frequency, hours, costs). 75 is far from the 95 you would demand.' },
      },
      {
        id: 'q2',
        prompt: { es: '¿Qué pregunta responde Monte Carlo sobre una secuencia de operaciones?', en: 'Which question does Monte Carlo answer about a sequence of trades?' },
        options: { es: ['Si la estrategia funcionará el año que viene', 'Qué rachas y drawdowns son esperables solo por el orden de las mismas operaciones', 'Cuál es el mejor parámetro', 'Si los datos son correctos'], en: ['Whether the strategy will work next year', 'Which streaks and drawdowns are expected from the order of the same trades alone', 'Which parameter is best', 'Whether the data is correct'] },
        answer: 1,
        explanation: { es: 'Baraja las mismas operaciones; no inventa operaciones nuevas ni predice el futuro.', en: 'It reshuffles the same trades; it neither invents new ones nor predicts the future.' },
      },
      {
        id: 'q3',
        prompt: { es: 'Cambiar el stop máximo de 3 a 4 ATR convierte +2,35R en un total negativo. ¿Qué indica?', en: 'Changing the maximum stop from 3 to 4 ATR turns +2.35R into a negative total. What does it indicate?' },
        options: { es: ['Que 3 ATR es el valor óptimo y hay que fijarlo', 'Fragilidad: el resultado depende de un valor concreto, señal típica de sobreajuste o de muestra pequeña', 'Que los datos tienen huecos', 'Nada relevante'], en: ['That 3 ATR is optimal and should be fixed', 'Fragility: the result depends on one specific value, a typical sign of overfitting or a small sample', 'That the data has gaps', 'Nothing relevant'] },
        answer: 1,
        explanation: { es: 'Una ventaja real suele degradarse suavemente con cambios vecinos, no darse la vuelta.', en: 'A real edge usually degrades smoothly with neighbouring changes; it does not flip.' },
      },
      {
        id: 'q4',
        prompt: { es: '¿Cuál es la decisión correcta tras estos resultados?', en: 'What is the right decision after these results?' },
        options: { es: ['Operar V1.1 en real con poco riesgo', 'Publicar V1.1 como estrategia rentable', 'Registrar V1.1 como experimento sin evidencia y estudiar el factor limitante con más datos', 'Abandonar la investigación'], en: ['Trade V1.1 live with small risk', 'Publish V1.1 as a profitable strategy', 'Log V1.1 as an experiment without evidence and study the binding factor with more data', 'Abandon the research'] },
        answer: 2,
        explanation: { es: '"Todavía no sabemos" es un resultado legítimo; lo que no es legítimo es operar o vender sobre doce operaciones.', en: '"We do not know yet" is a legitimate result; trading or selling on twelve trades is not.' },
      },
      {
        id: 'q5',
        prompt: { es: '¿Qué es el walk-forward?', en: 'What is walk-forward?' },
        options: { es: ['Ejecutar la estrategia en tiempo real', 'Observar un tramo de entrenamiento y medir el tramo siguiente, que no se ha visto, deslizando la ventana', 'Optimizar sobre todo el histórico', 'Un tipo de orden'], en: ['Running the strategy in real time', 'Observing a training period and measuring the next, unseen period, sliding the window forward', 'Optimising over the whole history', 'An order type'] },
        answer: 1,
        explanation: { es: 'Solo cuentan los tramos fuera de muestra. Con pocas operaciones por tramo, el walk-forward de un solo año dice poco: por eso hacen falta varios años.', en: 'Only the out-of-sample periods count. With few trades per period, one year of walk-forward says little: that is why several years are needed.' },
      },
    ],
    labNote: {
      prompt: {
        es: 'Escribe la conclusión del protocolo sobre V1.1 (EUR/USD 2024) como la enviarías a alguien que tiene que decidir si invertir más tiempo en esta hipótesis: resultado bruto, las tres pruebas, veredicto y siguiente paso.',
        en: 'Write the protocol conclusion on V1.1 (EUR/USD 2024) as you would send it to someone who must decide whether to invest more time in this hypothesis: raw result, the three tests, verdict and next step.',
      },
      rubric: [
        { id: 'raw', label: { es: 'Da el resultado bruto con su número de operaciones', en: 'Gives the raw result with its trade count' }, keywords: { es: ['12', 'doce', '2,35', '2.35', 'operacion', 'operación'], en: ['12', 'twelve', '2.35', 'trade'] } },
        { id: 'benchmark', label: { es: 'Interpreta el benchmark aleatorio / percentil', en: 'Interprets the random benchmark / percentile' }, keywords: { es: ['azar', 'aleatori', 'percentil', 'benchmark'], en: ['chance', 'random', 'percentile', 'benchmark'] } },
        { id: 'montecarlo', label: { es: 'Menciona Monte Carlo o las rachas/drawdown', en: 'Mentions Monte Carlo or streaks/drawdown' }, keywords: { es: ['monte carlo', 'racha', 'drawdown', 'barajar'], en: ['monte carlo', 'streak', 'drawdown', 'reshuffle'] } },
        { id: 'sensitivity', label: { es: 'Cita la fragilidad ante cambios de parámetros', en: 'Cites fragility under parameter changes' }, keywords: { es: ['sensibilidad', 'frágil', 'fragil', 'se da la vuelta', 'parámetro', 'parametro', 'atr'], en: ['sensitivity', 'fragile', 'flip', 'parameter', 'atr'] } },
        { id: 'verdict', label: { es: 'Da un veredicto explícito: no hay evidencia', en: 'Gives an explicit verdict: no evidence' }, keywords: { es: ['no hay evidencia', 'sin evidencia', 'no es evidencia', 'no demuestra', 'no concluy'], en: ['no evidence', 'not evidence', 'does not prove', 'inconclusive'] } },
        { id: 'next', label: { es: 'Propone el siguiente paso (más datos, V1.2, stop)', en: 'Proposes the next step (more data, V1.2, stop)' }, keywords: { es: ['más datos', 'mas datos', 'años', 'anos', 'v1.2', 'stop', 'siguiente'], en: ['more data', 'years', 'v1.2', 'stop', 'next'] } },
      ],
      example: {
        es: 'V1.1 sobre EUR/USD 2024: 12 operaciones, +2,35R, acierto 42 %. Benchmark aleatorio con costes iguales: percentil 75 (p ≈ 0,25), es decir, una de cada cuatro estrategias al azar lo iguala. Monte Carlo sobre las 12 operaciones: el 5 % peor de los caminos termina por debajo de −3R y un drawdown de 3R es normal solo por el orden. Sensibilidad: el total cambia de signo con stop máximo de 4 ATR, con la referencia leg1_origin y en la sesión de Nueva York; walk-forward con un solo tramo con operaciones. Veredicto: no hay evidencia de ventaja; el resultado es compatible con el azar y es frágil. Siguiente paso: datos 2022–2024, y estudiar la colocación del stop como experimento V1.2 antes de cualquier otra variante.',
        en: 'V1.1 on EUR/USD 2024: 12 trades, +2.35R, 42 % win rate. Cost-matched random benchmark: 75th percentile (p ≈ 0.25), i.e. one in four random strategies matches it. Monte Carlo on the 12 trades: the worst 5 % of paths end below −3R and a 3R drawdown is normal from the order alone. Sensitivity: the total changes sign with a 4 ATR maximum stop, with the leg1_origin reference and in the New York session; walk-forward has a single fold with trades. Verdict: no evidence of an edge; the result is consistent with chance and fragile. Next step: 2022–2024 data, and study stop placement as experiment V1.2 before any other variant.',
      },
    },
  },
];

export const UPCOMING: { title: L; summary: L }[] = [
  { title: { es: 'Costes: de positivo a negativo', en: 'Costs: from positive to negative' }, summary: { es: 'Spread, deslizamiento, comisión y cómo un cambio de 0,2 pips reordena todo.', en: 'Spread, slippage, commission and how a 0.2-pip change reorders everything.' } },
  { title: { es: 'Periodos independientes y walk-forward', en: 'Independent periods and walk-forward' }, summary: { es: 'Cómo partir los datos para no engañarte, y cuánto dato hace falta.', en: 'How to split the data so you do not fool yourself, and how much data it takes.' } },
  { title: { es: 'Diseñar V1.2: una decisión registrada', en: 'Designing V1.2: a logged decision' }, summary: { es: 'Del hallazgo (el stop) a la hipótesis nueva, sin tocar la vieja.', en: 'From the finding (the stop) to the new hypothesis, without touching the old one.' } },
  { title: { es: 'Documentar e informar', en: 'Documenting and reporting' }, summary: { es: 'Log de decisiones, informes reproducibles y cómo contar un resultado negativo.', en: 'Decision log, reproducible reports and how to tell a negative result.' } },
];
