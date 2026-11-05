import { useMemo, useState } from 'react';
import type { Candle } from '../../types';

/** Pure-SVG strip of real M1 candles with hover/click inspection and an optional "now" cutoff.
 *  Candles after `revealUntil` are hidden; the candle containing `revealUntil` is drawn as the engine
 *  would see it before close: only its open (a tick), to make look-ahead visible. */
export function CandleStrip({ candles, revealUntil, selected, onSelect, height = 240, markers = [] }:
  { candles: Candle[]; revealUntil?: number; selected?: number | null; onSelect?: (index: number) => void; height?: number;
    markers?: { time: number; label: string; color?: string }[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const width = Math.max(320, candles.length * 14 + 40);
  const { min, max } = useMemo(() => {
    const visible = revealUntil == null ? candles : candles.filter((c) => c.time <= revealUntil);
    const lows = visible.map((c) => c.low); const highs = visible.map((c) => c.high);
    const lo = Math.min(...lows); const hi = Math.max(...highs);
    const pad = (hi - lo || 0.0005) * 0.12;
    return { min: lo - pad, max: hi + pad };
  }, [candles, revealUntil]);
  const y = (p: number) => 12 + ((max - p) / (max - min || 1)) * (height - 36);
  const x = (i: number) => 30 + i * 14;
  const active = hover ?? selected ?? null;
  return (
    <div className="strip-wrap">
      <svg className="strip" viewBox={`0 0 ${width} ${height}`} width="100%" role="img" aria-label="M1 candles">
        {[0.25, 0.5, 0.75].map((f) => <line key={f} x1="24" x2={width - 6} y1={12 + f * (height - 36)} y2={12 + f * (height - 36)} stroke="var(--line)" strokeWidth="0.6" />)}
        {candles.map((c, i) => {
          if (revealUntil != null && c.time > revealUntil) return null;
          const partial = revealUntil != null && c.time + 60 > revealUntil && c.time <= revealUntil && c.time === revealUntil;
          const up = c.close >= c.open;
          const color = up ? 'var(--good)' : 'var(--bad)';
          const top = y(Math.max(c.open, c.close)); const bottom = y(Math.min(c.open, c.close));
          const isActive = active === i;
          if (partial) {
            return <g key={c.time}><line x1={x(i) - 5} x2={x(i) + 5} y1={y(c.open)} y2={y(c.open)} stroke="var(--warn)" strokeWidth="2" /><rect x={x(i) - 6} y={12} width="12" height={height - 36} fill="var(--warn)" opacity="0.08" /></g>;
          }
          return (
            <g key={c.time} className={`strip-candle ${isActive ? 'active' : ''}`} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} onClick={() => onSelect?.(i)} style={{ cursor: onSelect ? 'pointer' : 'default' }}>
              <rect x={x(i) - 7} y={10} width="14" height={height - 32} fill="transparent" />
              <line x1={x(i)} x2={x(i)} y1={y(c.high)} y2={y(c.low)} stroke={color} strokeWidth={isActive ? 2 : 1} />
              <rect x={x(i) - 4} y={top} width="8" height={Math.max(1.5, bottom - top)} fill={color} opacity={isActive ? 1 : 0.85} stroke={isActive ? 'var(--ink)' : 'none'} strokeWidth="1" />
            </g>
          );
        })}
        {markers.map((m) => {
          const i = candles.findIndex((c) => c.time >= m.time);
          if (i < 0 || (revealUntil != null && m.time > revealUntil)) return null;
          return <g key={m.label + m.time}><line x1={x(i)} x2={x(i)} y1={8} y2={height - 24} stroke={m.color ?? 'var(--accent)'} strokeDasharray="3 3" strokeWidth="1" /><text x={x(i) + 3} y={height - 12} fontSize="9" fill={m.color ?? 'var(--accent)'} className="mono">{m.label}</text></g>;
        })}
        {candles.filter((_, i) => i % 10 === 0).map((c, k) => <text key={c.time} x={x(k * 10)} y={height - 2} fontSize="9" textAnchor="middle" fill="var(--muted)" className="mono">{hhmm(c.time)}</text>)}
      </svg>
      {active != null && candles[active] && (
        <div className="strip-tip mono small">
          <span>{hhmm(candles[active].time)}</span>
          <span>O {candles[active].open.toFixed(5)}</span><span>H {candles[active].high.toFixed(5)}</span><span>L {candles[active].low.toFixed(5)}</span><span>C {candles[active].close.toFixed(5)}</span>
        </div>
      )}
    </div>
  );
}

export function hhmm(time: number): string {
  return new Intl.DateTimeFormat('es-ES', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Madrid' }).format(new Date(time * 1000));
}

/** Big anatomy drawing of one real candle, with labelled parts. */
export function BigCandle({ candle, lang, reveal }: { candle: Candle; lang: 'es' | 'en'; reveal: boolean }) {
  const up = candle.close >= candle.open;
  const color = up ? 'var(--good)' : 'var(--bad)';
  const span = candle.high - candle.low || 0.0001;
  const y = (p: number) => 20 + ((candle.high - p) / span) * 200;
  const top = y(Math.max(candle.open, candle.close)); const bottom = y(Math.min(candle.open, candle.close));
  const L = (es: string, en: string) => (lang === 'es' ? es : en);
  return (
    <svg viewBox="0 0 320 250" className="big-candle" role="img" aria-label={L('Anatomía de una vela', 'Anatomy of a candle')}>
      <line x1="110" x2="110" y1={y(candle.high)} y2={y(candle.low)} stroke={color} strokeWidth="3" />
      <rect x="86" y={top} width="48" height={Math.max(3, bottom - top)} fill={color} />
      {reveal && (<g className="mono" fontSize="11" fill="var(--ink)">
        <text x="150" y={y(candle.high) + 4}>{L('máximo', 'high')} {candle.high.toFixed(5)}</text>
        <text x="150" y={y(candle.low) + 4}>{L('mínimo', 'low')} {candle.low.toFixed(5)}</text>
        <text x="150" y={(up ? bottom : top) + 4}>{L('apertura', 'open')} {candle.open.toFixed(5)}</text>
        <text x="150" y={(up ? top : bottom) + 4}>{L('cierre', 'close')} {candle.close.toFixed(5)}</text>
        <text x="20" y="240" fill="var(--muted)">{hhmm(candle.time)} · {up ? L('alcista', 'bullish') : L('bajista', 'bearish')}</text>
      </g>)}
    </svg>
  );
}
