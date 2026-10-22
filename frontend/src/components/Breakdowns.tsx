import { useState } from 'react';
import { formatPercent, formatR } from '../api';
import type { Bucket, Metrics } from '../types';

type Measure = 'total_r' | 'expectancy_r';

/** Signed bar chart of R per bucket (hour, weekday, month, …). Bars above the axis are positive R. */
export function SignedBars({ title, buckets, measure, caption }: { title: string; buckets: Record<string, Bucket>; measure: Measure; caption?: string }) {
  const entries = Object.entries(buckets);
  if (!entries.length) return null;
  const max = Math.max(0.01, ...entries.map(([, b]) => Math.abs(b[measure])));
  return (
    <div className="signed">
      <div className="tile-label">{title}</div>
      <div className="signed-row" role="img" aria-label={`${title}: ${entries.map(([k, b]) => `${k} ${formatR(b[measure])}`).join(', ')}`}>
        {entries.map(([key, bucket]) => {
          const value = bucket[measure];
          const height = (Math.abs(value) / max) * 50;
          return (
            <div key={key} className="signed-col" title={`${key} · ${bucket.trades} trades · total ${formatR(bucket.total_r)} · expectancy ${formatR(bucket.expectancy_r)} · win rate ${formatPercent(bucket.win_rate)}`}>
              <div className="signed-half top">{value > 0 && <span className="signed-bar good" style={{ height: `${height}%` }} />}</div>
              <div className="signed-half bottom">{value < 0 && <span className="signed-bar bad" style={{ height: `${height}%` }} />}</div>
              <span className="signed-label">{key.length > 4 ? key.slice(2) : key}</span>
              <span className="signed-n mono">{bucket.trades}</span>
            </div>
          );
        })}
      </div>
      {caption && <p className="muted small">{caption}</p>}
    </div>
  );
}

function BucketTable({ buckets }: { buckets: Record<string, Bucket> }) {
  return (
    <div className="table-wrap">
      <table className="compact">
        <thead><tr><th>Bucket</th><th>Trades</th><th>Total R</th><th>Expectancy</th><th>Win rate</th></tr></thead>
        <tbody>
          {Object.entries(buckets).map(([key, b]) => (
            <tr key={key} className={b.total_r >= 0 ? 'win' : 'loss'}><td>{key}</td><td className="mono">{b.trades}</td><td className="mono strong">{formatR(b.total_r)}</td><td className="mono">{formatR(b.expectancy_r)}</td><td className="mono">{formatPercent(b.win_rate)}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PerformanceBreakdowns({ metrics, timezone }: { metrics: Metrics; timezone?: string }) {
  const [measure, setMeasure] = useState<Measure>('total_r');
  const [table, setTable] = useState(false);
  const groups: { key: string; title: string; data?: Record<string, Bucket> }[] = [
    { key: 'hour', title: `By entry hour (${timezone ?? 'local'})`, data: metrics.by_hour },
    { key: 'weekday', title: 'By weekday', data: metrics.by_weekday },
    { key: 'month', title: 'By month', data: metrics.by_month },
    { key: 'direction', title: 'By direction', data: metrics.by_direction },
    { key: 'exit', title: 'By exit reason', data: metrics.by_exit_reason },
  ];
  const available = groups.filter((g) => g.data && Object.keys(g.data).length);
  if (!available.length) return <p className="muted">This run predates v0.4 and has no time breakdowns; re-run the backtest to get them.</p>;
  return (
    <>
      <div className="row-actions">
        <div className="segmented">
          <button type="button" className={measure === 'total_r' ? 'active' : ''} onClick={() => setMeasure('total_r')}>Total R</button>
          <button type="button" className={measure === 'expectancy_r' ? 'active' : ''} onClick={() => setMeasure('expectancy_r')}>Expectancy (R/trade)</button>
        </div>
        <button type="button" className="ghost" onClick={() => setTable(!table)}>{table ? 'Show charts' : 'Show tables'}</button>
        <span className="muted small">The number under each bar is the trade count. Buckets with one or two trades say nothing reliable.</span>
      </div>
      <div className="breakdown-grid">
        {available.map((g) => (
          <div key={g.key} className="breakdown">
            {table ? <><div className="tile-label">{g.title}</div><BucketTable buckets={g.data!} /></> : <SignedBars title={g.title} buckets={g.data!} measure={measure} />}
          </div>
        ))}
      </div>
    </>
  );
}
