import { useEffect, useRef, useState } from 'react';
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts';
import { formatR } from '../api';
import { palette } from './Charts';
import type { Trade, TradeExplainer as Explainer } from '../types';
import { useT } from '../i18n';

const STEP_SHAPES: Record<string, { shape: 'circle' | 'square' | 'arrowUp' | 'arrowDown'; color: string; short: string }> = {
  sweep: { shape: 'circle', color: '#8a8f98', short: 'sweep' },
  sweep_confirmed: { shape: 'square', color: '#8a8f98', short: 'confirmed' },
  zone: { shape: 'square', color: '#9a6a1f', short: 'zone' },
  displacement_start: { shape: 'circle', color: '#5c6670', short: 'leg 1' },
  displacement_end: { shape: 'square', color: '#5c6670', short: 'displacement' },
  retracement: { shape: 'circle', color: '#b26d12', short: 'retrace' },
  leg2: { shape: 'circle', color: '#5c6670', short: 'leg 2' },
  bos: { shape: 'square', color: '#c4672b', short: 'BOS' },
  entry: { shape: 'arrowUp', color: '#c4672b', short: 'entry' },
  exit: { shape: 'circle', color: '#2f7d6b', short: 'exit' },
};


// The exit step text carries the realised R ("+1.80R at …" / "-1.00R at …").
const trade_was_loss = (explainer: Explainer) => (explainer.steps.find((s) => s.id === 'exit')?.text ?? '').startsWith('-');

const lineStyle = (style: string) => (style === 'dashed' ? LineStyle.Dashed : style === 'dotted' ? LineStyle.Dotted : LineStyle.Solid);

export function ExplainerChart({ explainer, focus, lang = 'en' }: { explainer: Explainer; focus: string | null; lang?: 'es' | 'en' }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = ref.current;
    if (!element || !explainer.candles.length) return;
    const colors = palette();
    const chart = createChart(element, {
      width: element.clientWidth,
      height: 420,
      layout: { background: { type: ColorType.Solid, color: colors.background }, textColor: colors.text, fontFamily: 'inherit' },
      grid: { vertLines: { color: colors.grid }, horzLines: { color: colors.grid } },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: colors.grid },
      rightPriceScale: { borderColor: colors.grid },
      crosshair: { mode: CrosshairMode.Normal },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: colors.up, downColor: colors.down, borderVisible: false, wickUpColor: colors.up, wickDownColor: colors.down,
      priceFormat: { type: 'price', precision: 5, minMove: 0.00001 },
    });
    series.setData(explainer.candles.map((c) => ({ time: c.time as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close })));
    explainer.levels.forEach((level) => {
      series.createPriceLine({ price: level.price, color: level.color, lineWidth: level.id === 'entry' || level.id === 'stop' || level.id === 'target' ? 2 : 1, lineStyle: lineStyle(level.style), axisLabelVisible: true, title: lang === 'es' && level.label_es ? level.label_es : level.label });
    });
    const markers: SeriesMarker<Time>[] = explainer.steps.map((step) => {
      const look = STEP_SHAPES[step.id] ?? { shape: 'circle' as const, color: '#8a8f98', short: step.id };
      return {
        time: step.time as UTCTimestamp,
        position: step.position,
        shape: step.id === 'entry' ? (explainer.direction === 'LONG' ? 'arrowUp' : 'arrowDown') : look.shape,
        color: step.id === 'exit' && trade_was_loss(explainer) ? '#b5443a' : look.color,
        text: focus === step.id ? `▶ ${look.short}` : look.short,
        size: focus === step.id ? 2 : 1,
      };
    });
    markers.sort((a, b) => (a.time as number) - (b.time as number));
    createSeriesMarkers(series, markers);
    chart.timeScale().fitContent();
    const observer = new ResizeObserver(() => chart.applyOptions({ width: element.clientWidth }));
    observer.observe(element);
    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [explainer, focus, lang]);
  return <div ref={ref} className="chart" aria-label="M1 candles of the setup with every rule event" />;
}

export function TradeExplainerPanel({ trade, explainer, onClose }: { trade: Trade; explainer: Explainer | undefined; onClose: () => void }) {
  const { t, lang } = useT();
  const [focus, setFocus] = useState<string | null>(null);
  const es = lang === 'es';
  const panel = useRef<HTMLElement>(null);
  useEffect(() => { panel.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, [trade.trade_id]);
  if (!explainer || explainer.error) {
    return (
      <section className="explainer" ref={panel}>
        <div className="section-head"><h2>{t('ex.title')}</h2><button type="button" className="ghost" onClick={onClose}>{t('ex.close')}</button></div>
        <p className="muted">{t('ex.none')}{explainer?.error ? `: ${explainer.error}` : t('ex.noneOld')}</p>
      </section>
    );
  }
  const r = explainer.rules;
  return (
    <section className="explainer" ref={panel}>
      <div className="section-head">
        <h2>{t('ex.title')} — {trade.symbol} {trade.direction} · {trade.date} ({formatR(trade.r_multiple)})</h2>
        <button type="button" className="ghost" onClick={onClose}>{t('ex.close')}</button>
      </div>
      <p className="muted small">
        {t('ex.intro', { start: explainer.window.start?.slice(0, 16).replace('T', ' ') ?? '—', end: explainer.window.end?.slice(0, 16).replace('T', ' ') ?? '—', n: explainer.window.bars })} {explainer.notice}
      </p>
      <ExplainerChart explainer={explainer} focus={focus} lang={lang} />
      <div className="explainer-grid">
        <ol className="steps">
          {explainer.steps.map((step, index) => (
            <li key={step.id} className={focus === step.id ? 'active' : ''} onClick={() => setFocus(focus === step.id ? null : step.id)}>
              <span className="step-index">{index + 1}</span>
              <div>
                <div className="step-title">{es && step.title_es ? step.title_es : step.title} <span className="mono muted small">{step.local} {explainer.timezone.split('/')[1]}</span></div>
                <div className="small">{es && step.text_es ? step.text_es : step.text}</div>
              </div>
            </li>
          ))}
        </ol>
        <div className="legend">
          <div className="tile-label">{t('ex.levels')}</div>
          {explainer.levels.map((level) => (
            <div key={level.id} className="legend-row"><span className="swatch" style={{ borderTop: `2px ${level.style} ${level.color}` }} /><span>{es && level.label_es ? level.label_es : level.label}</span><span className="mono">{level.price.toFixed(5)}</span></div>
          ))}
          <div className="tile-label" style={{ marginTop: 10 }}>{t('ex.rules')}</div>
          <div className="small">{t('ex.stopRef')}: <span className="mono">{r.stop_reference}</span></div>
          <div className="small">{t('ex.stopDist')}: <span className="mono">{r.stop_distance_atr?.toFixed(2) ?? '—'} ATR</span> ({t('ex.atr')} {r.atr_at_setup?.toFixed(5) ?? '—'})</div>
          <div className="small">{t('ex.window')} #{r.observation_window ?? '—'}{r.scheduled_observation_time ? ` · ${r.scheduled_observation_time}` : ''}</div>
          <div className="small">{t('ex.costs')}: spread {trade.spread_pips} pips ({trade.spread_source ?? 'n/a'}), slippage {trade.slippage_pips} pips, commission {trade.commission}</div>
          <div className="small">{t('ex.excursion')}: MFE {formatR(trade.mfe)} · MAE {formatR(trade.mae)}</div>
        </div>
      </div>
    </section>
  );
}
