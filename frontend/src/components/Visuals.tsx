/** Original inline SVG visuals: a setup diagram for the hero, sparklines, step icons. No external assets. */
import { useT } from '../i18n';

export function Sparkline({ values, width = 160, height = 44, className }: { values: number[]; width?: number; height?: number; className?: string }) {
  if (!values || values.length < 2) return null;
  const min = Math.min(0, ...values);
  const max = Math.max(0, ...values);
  const span = max - min || 1;
  const x = (i: number) => (i / (values.length - 1)) * (width - 2) + 1;
  const y = (v: number) => height - 1 - ((v - min) / span) * (height - 2);
  const points = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const last = values[values.length - 1];
  const tone = last > 0 ? 'var(--good)' : last < 0 ? 'var(--bad)' : 'var(--muted)';
  return (
    <svg className={`sparkline ${className ?? ''}`} viewBox={`0 0 ${width} ${height}`} width={width} height={height} aria-hidden="true">
      <line x1="0" x2={width} y1={y(0)} y2={y(0)} stroke="var(--line)" strokeWidth="1" />
      <polyline points={points} fill="none" stroke={tone} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={x(values.length - 1)} cy={y(last)} r="2.5" fill={tone} />
    </svg>
  );
}

/** The hypothesis in one picture: sweep → zone → displacement → retracement → BOS → entry/stop/target. */
export function SetupIllustration() {
  const { lang } = useT();
  const L = (es: string, en: string) => (lang === 'es' ? es : en);
  // Candles: [x, open, high, low, close] in a 520×300 box, y grows downwards (price inverted).
  const candles: [number, number, number, number, number][] = [
    [40, 150, 140, 168, 160], [62, 160, 152, 176, 170], [84, 170, 158, 182, 164], [106, 164, 150, 172, 156],
    [128, 156, 146, 198, 190], [150, 190, 176, 210, 206], [172, 206, 196, 236, 232], [194, 232, 214, 242, 220],
    [216, 220, 180, 226, 188], [238, 188, 150, 194, 156], [260, 156, 128, 164, 134], [282, 134, 122, 150, 146],
    [304, 146, 136, 172, 168], [326, 168, 150, 178, 154], [348, 154, 118, 160, 124], [370, 124, 104, 132, 110],
    [392, 110, 98, 120, 104], [414, 104, 92, 112, 98], [436, 98, 76, 106, 84], [458, 84, 70, 92, 78],
  ];
  const liquidity = 236;
  const zoneTop = 190;
  const zoneBottom = 210;
  const bos = 128;
  const entry = 122;
  const stop = 212;
  const target = 32;
  return (
    <svg className="setup-art" viewBox="0 0 520 300" role="img" aria-label={L('Diagrama de la hipótesis: barrido, zona, impulso, retroceso, ruptura, entrada, stop y objetivo', 'Hypothesis diagram: sweep, zone, displacement, retracement, break, entry, stop and target')}>
      <defs>
        <pattern id="grid" width="26" height="26" patternUnits="userSpaceOnUse"><path d="M26 0H0V26" fill="none" stroke="var(--line)" strokeWidth="0.6" /></pattern>
      </defs>
      <rect width="520" height="300" fill="url(#grid)" rx="14" />
      <rect x="150" y={zoneTop} width="370" height={zoneBottom - zoneTop} fill="var(--warn)" opacity="0.14" />
      <text x="156" y={zoneTop - 4} className="art-label">{L('zona de demanda', 'demand zone')}</text>
      <line x1="20" x2="200" y1={liquidity} y2={liquidity} stroke="var(--muted)" strokeDasharray="5 4" strokeWidth="1.2" />
      <text x="22" y={liquidity + 14} className="art-label">{L('liquidez (mínimo previo)', 'liquidity (prior low)')}</text>
      <line x1="236" x2="520" y1={bos} y2={bos} stroke="var(--muted)" strokeDasharray="5 4" strokeWidth="1.2" />
      <text x="240" y={bos - 5} className="art-label">BOS</text>
      {candles.map(([x, o, h, l, c], i) => {
        const up = c < o;
        const color = up ? 'var(--good)' : 'var(--bad)';
        const top = Math.min(o, c);
        const bottom = Math.max(o, c);
        return (
          <g key={i} className="art-candle" style={{ animationDelay: `${i * 40}ms` }}>
            <line x1={x} x2={x} y1={h} y2={l} stroke={color} strokeWidth="1.4" />
            <rect x={x - 6} y={top} width="12" height={Math.max(2, bottom - top)} fill={color} rx="1.5" />
          </g>
        );
      })}
      <g className="art-marker" style={{ animationDelay: '900ms' }}>
        <circle cx="172" cy="240" r="9" fill="var(--panel)" stroke="var(--ink)" strokeWidth="1.5" /><text x="172" y="244" textAnchor="middle" className="art-num">1</text>
        <text x="186" y="262" className="art-label">{L('barrido', 'sweep')}</text>
      </g>
      <g className="art-marker" style={{ animationDelay: '1050ms' }}>
        <circle cx="260" cy="118" r="9" fill="var(--panel)" stroke="var(--ink)" strokeWidth="1.5" /><text x="260" y="122" textAnchor="middle" className="art-num">2</text>
        <text x="274" y="112" className="art-label">{L('impulso', 'displacement')}</text>
      </g>
      <g className="art-marker" style={{ animationDelay: '1200ms' }}>
        <circle cx="304" cy="184" r="9" fill="var(--panel)" stroke="var(--ink)" strokeWidth="1.5" /><text x="304" y="188" textAnchor="middle" className="art-num">3</text>
        <text x="318" y="198" className="art-label">{L('retroceso', 'retracement')}</text>
      </g>
      <g className="art-marker" style={{ animationDelay: '1350ms' }}>
        <circle cx="370" cy="96" r="9" fill="var(--accent)" stroke="var(--accent)" /><text x="370" y="100" textAnchor="middle" className="art-num inv">4</text>
        <text x="384" y="90" className="art-label">{L('ruptura de estructura', 'break of structure')}</text>
      </g>
      <g className="art-marker" style={{ animationDelay: '1500ms' }}>
        <line x1="392" x2="520" y1={entry} y2={entry} stroke="var(--accent)" strokeWidth="2" />
        <text x="470" y={entry - 5} className="art-label strong">{L('entrada', 'entry')}</text>
        <line x1="392" x2="520" y1={stop} y2={stop} stroke="var(--bad)" strokeWidth="1.6" />
        <text x="478" y={stop + 14} className="art-label">stop</text>
        <line x1="392" x2="520" y1={target} y2={target} stroke="var(--good)" strokeWidth="1.6" />
        <text x="462" y={target - 5} className="art-label">{L('objetivo', 'target')}</text>
        <rect x="392" y={target} width="128" height={entry - target} fill="var(--good)" opacity="0.08" />
        <rect x="392" y={entry} width="128" height={stop - entry} fill="var(--bad)" opacity="0.08" />
      </g>
    </svg>
  );
}

export function StepIcon({ kind }: { kind: 'write' | 'run' | 'protocol' | 'log' }) {
  const common = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  switch (kind) {
    case 'write':
      return <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><path {...common} d="M5 4h9l5 5v11H5z" /><path {...common} d="M14 4v5h5M8 13h8M8 17h5" /></svg>;
    case 'run':
      return <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><path {...common} d="M4 18l5-6 4 4 7-9" /><path {...common} d="M4 21h16" /></svg>;
    case 'protocol':
      return <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><path {...common} d="M12 3v18M5 7l7-4 7 4" /><path {...common} d="M3 14l2-7 2 7a2 2 0 0 1-4 0zM17 14l2-7 2 7a2 2 0 0 1-4 0z" /></svg>;
    default:
      return <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><path {...common} d="M6 3h12v18H6z" /><path {...common} d="M9 8h6M9 12h6M9 16h4" /></svg>;
  }
}
