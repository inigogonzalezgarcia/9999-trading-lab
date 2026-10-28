import { useEffect, useRef } from 'react';
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  LineSeries,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type IChartApi,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts';
import type { Candle, EquityPoint, Trade } from '../types';

export function cssVar(name: string, fallback: string): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

export function palette() {
  const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  return {
    background: cssVar('--panel', dark ? '#142331' : '#f9f6f0'),
    text: cssVar('--muted', dark ? '#9aa6b0' : '#5c6670'),
    grid: cssVar('--line', dark ? '#24364a' : '#e1dacd'),
    up: cssVar('--good', '#2f7d6b'),
    down: cssVar('--bad', '#b5443a'),
    line: cssVar('--accent', '#c4672b'),
    drawdown: cssVar('--warn', '#9a6a1f'),
  };
}

function useChart(container: React.RefObject<HTMLDivElement>, height: number, build: (chart: IChartApi) => void, deps: unknown[]) {
  useEffect(() => {
    const element = container.current;
    if (!element) return;
    const colors = palette();
    const chart = createChart(element, {
      width: element.clientWidth,
      height,
      layout: { background: { type: ColorType.Solid, color: colors.background }, textColor: colors.text, fontFamily: 'inherit' },
      grid: { vertLines: { color: colors.grid }, horzLines: { color: colors.grid } },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: colors.grid },
      rightPriceScale: { borderColor: colors.grid },
      crosshair: { mode: CrosshairMode.Normal },
    });
    build(chart);
    chart.timeScale().fitContent();
    const observer = new ResizeObserver(() => chart.applyOptions({ width: element.clientWidth }));
    observer.observe(element);
    return () => {
      observer.disconnect();
      chart.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

const toTime = (seconds: number) => seconds as UTCTimestamp;
const isoToTime = (iso: string) => Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;

export function CandleChart({ candles, trades, symbol, timeframe }: { candles: Candle[]; trades: Trade[]; symbol: string; timeframe: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useChart(
    ref,
    380,
    (chart) => {
      const colors = palette();
      const series = chart.addSeries(CandlestickSeries, {
        upColor: colors.up,
        downColor: colors.down,
        borderVisible: false,
        wickUpColor: colors.up,
        wickDownColor: colors.down,
        priceFormat: { type: 'price', precision: 5, minMove: 0.00001 },
      });
      series.setData(candles.map((c) => ({ time: toTime(c.time), open: c.open, high: c.high, low: c.low, close: c.close })));
      const markers: SeriesMarker<Time>[] = [];
      trades
        .filter((t) => t.symbol === symbol)
        .forEach((t) => {
          markers.push({
            time: isoToTime(t.entry_timestamp),
            position: t.direction === 'LONG' ? 'belowBar' : 'aboveBar',
            color: t.direction === 'LONG' ? colors.up : colors.down,
            shape: t.direction === 'LONG' ? 'arrowUp' : 'arrowDown',
            text: `${t.direction} entry`,
          });
          markers.push({
            time: isoToTime(t.exit_timestamp),
            position: t.r_multiple >= 0 ? 'aboveBar' : 'belowBar',
            color: t.r_multiple >= 0 ? colors.up : colors.down,
            shape: 'circle',
            text: `${t.exit_reason} ${t.r_multiple >= 0 ? '+' : ''}${t.r_multiple.toFixed(2)}R`,
          });
        });
      markers.sort((a, b) => (a.time as number) - (b.time as number));
      createSeriesMarkers(series, markers);
      if (trades.length) {
        const last = trades[trades.length - 1];
        const center = isoToTime(last.entry_timestamp) as number;
        const span = timeframe === 'H1' ? 3600 * 48 : 900 * 64;
        chart.timeScale().setVisibleRange({ from: toTime(center - span), to: toTime(center + span) });
      }
    },
    [candles, trades, symbol],
  );
  return <div ref={ref} className="chart" aria-label={`${symbol} ${timeframe} candles with trade markers`} />;
}

export function EquityChart({ points }: { points: EquityPoint[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useChart(
    ref,
    240,
    (chart) => {
      const colors = palette();
      const equity = chart.addSeries(LineSeries, { color: colors.line, lineWidth: 2, priceFormat: { type: 'price', precision: 2, minMove: 0.01 } });
      const drawdown = chart.addSeries(LineSeries, { color: colors.drawdown, lineWidth: 1, lineStyle: LineStyle.Dashed, priceFormat: { type: 'price', precision: 2, minMove: 0.01 } });
      // Several trades may close in the same second; keep the last value per timestamp.
      const dedupe = (rows: { time: UTCTimestamp; value: number }[]) => {
        const map = new Map<number, number>();
        rows.forEach((row) => map.set(row.time as number, row.value));
        return [...map.entries()].sort((a, b) => a[0] - b[0]).map(([time, value]) => ({ time: toTime(time), value }));
      };
      equity.setData(dedupe(points.map((p) => ({ time: isoToTime(p.timestamp), value: p.cumulative_r }))));
      drawdown.setData(dedupe(points.map((p) => ({ time: isoToTime(p.timestamp), value: -p.drawdown_r }))));
    },
    [points],
  );
  return <div ref={ref} className="chart" aria-label="Cumulative R and drawdown" />;
}
