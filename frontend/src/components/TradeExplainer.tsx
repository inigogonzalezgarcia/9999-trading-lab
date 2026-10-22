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
import type { Trade, TradeExplainer as Explainer } from '../types';

const STEP_SHAPES: Record<string, { shape: 'circle' | 'square' | 'arrowUp' | 'arrowDown'; color: string; short: string }> = {
  sweep: { shape: 'circle', color: '#8a8f98', short: 'sweep' },
  sweep_confirmed: { shape: 'square', color: '#8a8f98', short: 'confirmed' },
  zone: { shape: 'square', color: '#e0a458', short: 'zone' },
  displacement_start: { shape: 'circle', color: '#8ab4f8', short: 'leg 1' },
  displacement_end: { shape: 'square', color: '#8ab4f8', short: 'displacement' },
  retracement: { shape: 'circle', color: '#b26d12', short: 'retrace' },
  leg2: { shape: 'circle', color: '#8ab4f8', short: 'leg 2' },
  bos: { shape: 'square', color: '#2457c5', short: 'BOS' },
  entry: { shape: 'arrowUp', color: '#2457c5', short: 'entry' },
  exit: { shape: 'circle', color: '#2a9d8f', short: 'exit' },
};

function palette() {
  const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  return { background: dark ? '#14161b' : '#ffffff', text: dark ? '#c9ced6' : '#333a45', grid: dark ? '#23262e' : '#eef0f3', up: '#2a9d8f', down: '#c2544b' };
}

// The exit step text carries the realised R ("+1.80R at …" / "-1.00R at …").
const trade_was_loss = (explainer: Explainer) => (explainer.steps.find((s) => s.id === 'exit')?.text ?? '').startsWith('-');

const lineStyle = (style: string) => (style === 'dashed' ? LineStyle.Dashed : style === 'dotted' ? LineStyle.Dotted : LineStyle.Solid);

export function ExplainerChart({ explainer, focus }: { explainer: Explainer; focus: string | null }) {
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
      series.createPriceLine({ price: level.price, color: level.color, lineWidth: level.id === 'entry' || level.id === 'stop' || level.id === 'target' ? 2 : 1, lineStyle: lineStyle(level.style), axisLabelVisible: true, title: level.label });
    });
    const markers: SeriesMarker<Time>[] = explainer.steps.map((step) => {
      const look = STEP_SHAPES[step.id] ?? { shape: 'circle' as const, color: '#8a8f98', short: step.id };
      return {
        time: step.time as UTCTimestamp,
        position: step.position,
        shape: step.id === 'entry' ? (explainer.direction === 'LONG' ? 'arrowUp' : 'arrowDown') : look.shape,
        color: step.id === 'exit' && trade_was_loss(explainer) ? '#c2544b' : look.color,
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
  }, [explainer, focus]);
  return <div ref={ref} className="chart" aria-label="M1 candles of the setup with every rule event" />;
}

export function TradeExplainerPanel({ trade, explainer, onClose }: { trade: Trade; explainer: Explainer | undefined; onClose: () => void }) {
  const [focus, setFocus] = useState<string | null>(null);
  const panel = useRef<HTMLElement>(null);
  useEffect(() => { panel.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, [trade.trade_id]);
  if (!explainer || explainer.error) {
    return (
      <section className="explainer" ref={panel}>
        <div className="section-head"><h2>Trade explainer</h2><button type="button" className="ghost" onClick={onClose}>Close</button></div>
        <p className="muted">No explainer is available for this trade{explainer?.error ? `: ${explainer.error}` : ' (runs made before v0.4 do not carry them; re-run the backtest).'}</p>
      </section>
    );
  }
  const r = explainer.rules;
  return (
    <section className="explainer" ref={panel}>
      <div className="section-head">
        <h2>How this trade happened — {trade.symbol} {trade.direction} on {trade.date} ({formatR(trade.r_multiple)})</h2>
        <button type="button" className="ghost" onClick={onClose}>Close</button>
      </div>
      <p className="muted small">
        M1 candles from {explainer.window.start?.slice(0, 16).replace('T', ' ')} to {explainer.window.end?.slice(0, 16).replace('T', ' ')} UTC ({explainer.window.bars} bars).
        Horizontal lines are the rule levels; markers are the moments each rule fired. Click a step to highlight it. {explainer.notice}
      </p>
      <ExplainerChart explainer={explainer} focus={focus} />
      <div className="explainer-grid">
        <ol className="steps">
          {explainer.steps.map((step, index) => (
            <li key={step.id} className={focus === step.id ? 'active' : ''} onClick={() => setFocus(focus === step.id ? null : step.id)}>
              <span className="step-index">{index + 1}</span>
              <div>
                <div className="step-title">{step.title} <span className="mono muted small">{step.local} {explainer.timezone.split('/')[1]}</span></div>
                <div className="small">{step.text}</div>
              </div>
            </li>
          ))}
        </ol>
        <div className="legend">
          <div className="tile-label">Levels</div>
          {explainer.levels.map((level) => (
            <div key={level.id} className="legend-row"><span className="swatch" style={{ borderTop: `2px ${level.style} ${level.color}` }} /><span>{level.label}</span><span className="mono">{level.price.toFixed(5)}</span></div>
          ))}
          <div className="tile-label" style={{ marginTop: 10 }}>Rules applied</div>
          <div className="small">Stop reference: <span className="mono">{r.stop_reference}</span></div>
          <div className="small">Stop distance: <span className="mono">{r.stop_distance_atr?.toFixed(2) ?? '—'} ATR</span> (ATR at setup {r.atr_at_setup?.toFixed(5) ?? '—'})</div>
          <div className="small">Observation window #{r.observation_window ?? '—'}{r.scheduled_observation_time ? ` · scheduled ${r.scheduled_observation_time}` : ''}</div>
          <div className="small">Costs: spread {trade.spread_pips} pips ({trade.spread_source ?? 'n/a'}), slippage {trade.slippage_pips} pips, commission {trade.commission}</div>
          <div className="small">Excursion: MFE {formatR(trade.mfe)} · MAE {formatR(trade.mae)}</div>
        </div>
      </div>
    </section>
  );
}
