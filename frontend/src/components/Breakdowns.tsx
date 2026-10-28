import { useState } from 'react';
import { formatPercent, formatR } from '../api';
import type { Bucket, Metrics } from '../types';
import { useT } from '../i18n';

type Measure = 'total_r' | 'expectancy_r';

const WEEKDAY_ORDER = new Map(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, index) => [day, index]));

/** "2024-02" → "24-02"; other labels unchanged (lower-cased exit reasons read better). */
function shortLabel(key: string): string {
  if (/^\d{4}-\d{2}$/.test(key)) return key.slice(2);
  return key.replace(/_/g, ' ').toLowerCase();
}

/** Signed bar chart of R per bucket (hour, weekday, month, …). Bars above the axis are positive R. */
export function SignedBars({ title, buckets, measure, caption }: { title: string; buckets: Record<string, Bucket>; measure: Measure; caption?: string }) {
  const entries = Object.entries(buckets).sort(([a], [b]) => (WEEKDAY_ORDER.has(a) && WEEKDAY_ORDER.has(b) ? WEEKDAY_ORDER.get(a)! - WEEKDAY_ORDER.get(b)! : a.localeCompare(b)));
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
              <span className="signed-label" title={key}>{shortLabel(key)}</span>
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
  const { t } = useT();
  const [measure, setMeasure] = useState<Measure>('total_r');
  const [table, setTable] = useState(false);
  const groups: { key: string; title: string; data?: Record<string, Bucket> }[] = [
    { key: 'hour', title: t('bd.hour', { tz: timezone ?? 'local' }), data: metrics.by_hour },
    { key: 'weekday', title: t('bd.weekday'), data: metrics.by_weekday },
    { key: 'month', title: t('bd.month'), data: metrics.by_month },
    { key: 'direction', title: t('bd.direction'), data: metrics.by_direction },
    { key: 'exit', title: t('bd.exit'), data: metrics.by_exit_reason },
  ];
  const available = groups.filter((g) => g.data && Object.keys(g.data).length);
  if (!available.length) return <p className="muted">{t('bd.old')}</p>;
  return (
    <>
      <div className="row-actions">
        <div className="segmented">
          <button type="button" className={measure === 'total_r' ? 'active' : ''} onClick={() => setMeasure('total_r')}>{t('bd.totalR')}</button>
          <button type="button" className={measure === 'expectancy_r' ? 'active' : ''} onClick={() => setMeasure('expectancy_r')}>{t('bd.expectancy')}</button>
        </div>
        <button type="button" className="ghost" onClick={() => setTable(!table)}>{table ? t('bd.showCharts') : t('bd.showTables')}</button>
        <span className="muted small">{t('bd.note')}</span>
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
