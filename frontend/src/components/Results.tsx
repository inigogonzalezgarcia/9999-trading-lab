import { useMemo, useState } from 'react';
import { api, formatNumber, formatPercent, formatR, shortTime } from '../api';
import type { BacktestResult, Metrics, Trade } from '../types';
import { CandleChart, EquityChart } from './Charts';
import { useT } from '../i18n';
import { STATIC_MODE } from '../site';
import { PerformanceBreakdowns } from './Breakdowns';
import { TradeExplainerPanel } from './TradeExplainer';

export function Tile({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: 'good' | 'bad' | 'neutral' }) {
  return (
    <div className={`tile ${tone ?? ''}`}>
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
      {hint && <div className="tile-hint">{hint}</div>}
    </div>
  );
}

export function KpiTiles({ metrics }: { metrics: Metrics }) {
  const { t } = useT();
  const tone = (v: number | null | undefined) => (v == null ? 'neutral' : v > 0 ? 'good' : v < 0 ? 'bad' : 'neutral');
  return (
    <div className="tiles">
      <Tile label={t('kpi.trades')} value={String(metrics.total_trades)} hint={`${metrics.winning_trades} ${t('kpi.won')} · ${metrics.losing_trades} ${t('kpi.lost')}`} />
      <Tile label={t('kpi.expectancy')} value={formatR(metrics.expectancy_r)} hint={t('kpi.expectancyHint')} tone={tone(metrics.expectancy_r)} />
      <Tile label={t('kpi.total')} value={formatR(metrics.total_r)} tone={tone(metrics.total_r)} />
      <Tile label={t('kpi.winRate')} value={formatPercent(metrics.win_rate)} hint={`${t('kpi.payoff')} ${formatNumber(metrics.payoff_ratio)}`} />
      <Tile label={t('kpi.pf')} value={formatNumber(metrics.profit_factor)} />
      <Tile label={t('kpi.dd')} value={formatR(metrics.max_drawdown_r)} hint={t('kpi.ddHint', { n: metrics.max_consecutive_losses })} tone={metrics.max_drawdown_r > 0 ? 'bad' : 'neutral'} />
      <Tile label={t('kpi.sharpeAnn')} value={formatNumber(metrics.daily.annualized_sharpe)} hint={t('kpi.sharpeAnnHint', { n: metrics.daily.trading_days })} />
      <Tile label={t('kpi.sharpeTrade')} value={formatNumber(metrics.sharpe_per_trade)} hint={t('kpi.notAnnualised')} />
    </div>
  );
}

export function TradesTable({ trades, runId, onSelect, selected }: { trades: Trade[]; runId?: string; onSelect?: (trade: Trade) => void; selected?: string }) {
  const { t } = useT();
  const [sortKey, setSortKey] = useState<keyof Trade>('entry_timestamp');
  const [descending, setDescending] = useState(false);
  const sorted = useMemo(() => {
    const rows = [...trades].sort((a, b) => {
      const x = a[sortKey];
      const y = b[sortKey];
      if (typeof x === 'number' && typeof y === 'number') return x - y;
      return String(x ?? '').localeCompare(String(y ?? ''));
    });
    return descending ? rows.reverse() : rows;
  }, [trades, sortKey, descending]);
  const header = (key: keyof Trade, label: string) => (
    <th
      onClick={() => {
        if (sortKey === key) setDescending(!descending);
        else {
          setSortKey(key);
          setDescending(false);
        }
      }}
      className={sortKey === key ? 'sorted' : ''}
    >
      {label} {sortKey === key ? (descending ? '↓' : '↑') : ''}
    </th>
  );
  const download = () => {
    const columns: (keyof Trade)[] = ['trade_id', 'symbol', 'date', 'direction', 'observation_window', 'entry_timestamp', 'entry_price', 'stop_price', 'target_price', 'exit_timestamp', 'exit_price', 'exit_reason', 'spread_pips', 'spread_source', 'slippage_pips', 'commission', 'r_multiple', 'pnl', 'mfe', 'mae'];
    const lines = ['# Educational research tool. Simulated historical results; not investment advice.', columns.join(',')];
    trades.forEach((t) => lines.push(columns.map((c) => JSON.stringify(t[c] ?? '')).join(',')));
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement('a'), { href: url, download: 'trades.csv' });
    a.click();
    URL.revokeObjectURL(url);
  };
  if (!trades.length) return <p className="muted">{t('res.noTrades')}</p>;
  return (
    <>
      <div className="row-actions">
        <button type="button" className="ghost" onClick={download}>{t('res.exportCsv')}</button>
        {runId && !STATIC_MODE && <a className="ghost button" href={api.tradesCsvUrl(runId)}>{t('res.serverCsv')}</a>}
        <span className="muted">{t('res.tradesHint', { n: trades.length })}{onSelect ? t('res.tradesClick') : ''}</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {header('date', t('th.date'))}
              {header('symbol', t('th.symbol'))}
              {header('direction', t('th.side'))}
              {header('observation_window', t('th.window'))}
              {header('entry_timestamp', t('th.entryTime'))}
              {header('entry_price', t('th.entry'))}
              {header('stop_price', t('th.stop'))}
              {header('target_price', t('th.target'))}
              {header('exit_timestamp', t('th.exitTime'))}
              {header('exit_reason', t('th.exitReason'))}
              {header('spread_pips', t('th.spread'))}
              {header('r_multiple', 'R')}
              {header('mfe', 'MFE')}
              {header('mae', 'MAE')}
            </tr>
          </thead>
          <tbody>
            {sorted.map((t) => (
              <tr key={t.trade_id} className={`${t.r_multiple >= 0 ? 'win' : 'loss'}${onSelect ? ' clickable' : ''}${selected === t.trade_id ? ' selected' : ''}`} onClick={onSelect ? () => onSelect(t) : undefined}>
                <td>{t.date}</td>
                <td>{t.symbol}</td>
                <td>{t.direction}</td>
                <td>{t.observation_window}</td>
                <td className="mono">{shortTime(t.entry_timestamp)}</td>
                <td className="mono">{t.entry_price.toFixed(5)}</td>
                <td className="mono">{t.stop_price.toFixed(5)}</td>
                <td className="mono">{t.target_price.toFixed(5)}</td>
                <td className="mono">{shortTime(t.exit_timestamp)}</td>
                <td>{t.exit_reason}</td>
                <td className="mono">{formatNumber(t.spread_pips, 1)} <small>{t.spread_source ?? ''}</small></td>
                <td className="mono strong">{formatR(t.r_multiple)}</td>
                <td className="mono">{formatNumber(t.mfe)}</td>
                <td className="mono">{formatNumber(t.mae)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function Rejections({ rejections, total }: { rejections: Record<string, number>; total: number }) {
  const entries = Object.entries(rejections);
  if (!entries.length) return null;
  const max = Math.max(...entries.map(([, n]) => n));
  return (
    <div className="bars">
      {entries.map(([reason, count]) => (
        <div key={reason} className="bar-row">
          <span className="bar-label">{reason}</span>
          <span className="bar-track">
            <span className={`bar-fill ${reason === 'EXECUTED' ? 'good' : ''}`} style={{ width: `${(count / max) * 100}%` }} />
          </span>
          <span className="bar-value mono">{count} <small>({((count / total) * 100).toFixed(0)}%)</small></span>
        </div>
      ))}
    </div>
  );
}

function inWindows(windows?: { start: string; end: string }[]): (hour: number) => boolean {
  const ranges = (windows ?? [{ start: '02:15', end: '04:15' }]).map((w) => [Number(w.start.slice(0, 2)), Number(w.end.slice(0, 2)) + (w.end.slice(3) === '00' ? -1 : 0)]);
  return (hour) => ranges.some(([a, b]) => hour >= a && hour <= b);
}

export function HourHistogram({ title, counts, highlight }: { title: string; counts: Record<string, number>; highlight: (hour: number) => boolean }) {
  const max = Math.max(1, ...Object.values(counts));
  return (
    <div className="hours">
      <div className="tile-label">{title}</div>
      <div className="hours-row">
        {Object.entries(counts).map(([hour, count]) => (
          <div key={hour} className={`hour ${highlight(Number(hour)) ? 'window' : ''}`} title={`${hour}:00 · ${count}`}>
            <span className="hour-bar" style={{ height: `${(count / max) * 100}%` }} />
            <span className="hour-label">{hour}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function QualityPanel({ result }: { result: BacktestResult }) {
  const q = result.quality;
  const items: [string, unknown][] = [
    ['Rows', q.rows], ['Gaps', q.gap_count], ['Duplicates', q.duplicate_timestamps], ['Invalid rows', q.invalid_rows], ['Weekend rows', q.weekend_rows],
    ['Spread column', q.spread_available ? 'yes' : 'no'], ['Source timezone', q.source_timezone], ['Start (UTC)', shortTime(String(q.start_utc))], ['End (UTC)', shortTime(String(q.end_utc))],
  ];
  return (
    <>
      <dl className="facts">
        {items.map(([k, v]) => (
          <div key={k}><dt>{k}</dt><dd className="mono">{String(v ?? '—')}</dd></div>
        ))}
      </dl>
      {(q.warnings ?? []).map((w) => <p key={w} className="warn">⚠ {w}</p>)}
    </>
  );
}

export function Reproducibility({ result }: { result: BacktestResult }) {
  const r = result.reproducibility;
  const items: [string, unknown][] = [
    ['Dataset SHA-256', r.dataset_hash], ['Config hash', r.config_hash], ['Software', `${String(r.software_version)} · ${String(r.software_revision)}`],
    ['Strategy', `v${String(r.strategy_version)} (${result.strategy_status})`], ['Timezone DB', JSON.stringify(r.timezone_database_version)],
    ['Spread sources', JSON.stringify(r.spread_source)], ['Daily contexts', result.report?.daily_contexts ?? '—'],
  ];
  return (
    <dl className="facts">
      {items.map(([k, v]) => (
        <div key={k}><dt>{k}</dt><dd className="mono small">{String(v ?? '—')}</dd></div>
      ))}
    </dl>
  );
}

export function BacktestView({ result }: { result: BacktestResult }) {
  const { t } = useT();
  const symbols = result.chart ? Object.keys(result.chart.series) : [];
  const [symbol, setSymbol] = useState(symbols[0] ?? '');
  const [selected, setSelected] = useState<Trade | null>(null);
  const metrics = result.metrics;
  const explainers = result.trade_explainers ?? {};
  if (result.backtest_blocked) {
    return <div className="notice-box"><strong>{t('res.blocked')}: {result.strategy_status}</strong><p>{result.blocked_reason}</p><QualityPanel result={result} /></div>;
  }
  return (
    <div className="stack">
      <section>
        <h2>{t('res.summary')}</h2>
        {metrics && <KpiTiles metrics={metrics} />}
        <p className="muted small">{t('res.summaryNote')}</p>
      </section>
      {result.equity_curve && result.equity_curve.length > 0 && (
        <section>
          <h2>{t('res.equity')}</h2>
          <EquityChart points={result.equity_curve} />
        </section>
      )}
      {result.chart && symbol && (
        <section>
          <div className="section-head">
            <h2>{t('res.candles', { tf: result.chart.timeframe })}</h2>
            {symbols.length > 1 && (
              <div className="segmented">
                {symbols.map((s) => <button key={s} type="button" className={s === symbol ? 'active' : ''} onClick={() => setSymbol(s)}>{s}</button>)}
              </div>
            )}
          </div>
          <CandleChart candles={result.chart.series[symbol]} trades={result.trades} symbol={symbol} timeframe={result.chart.timeframe} />
          <p className="muted small">{t('res.candlesNote')}</p>
        </section>
      )}
      <section>
        <h2>{t('res.rejections')}</h2>
        <p className="muted small">{t('res.rejectionsNote', { n: result.candidate_count ?? 0 })}</p>
        {result.report && <Rejections rejections={result.report.rejections} total={Math.max(1, result.candidate_count ?? 1)} />}
      </section>
      {result.report?.timing && (
        <section>
          <h2>{t('res.timing', { tz: result.report.timing.timezone })}</h2>
          <p className="muted small">{t('res.timingNote', { n: result.report.timing.complete_setups, out: result.report.timing.complete_setups_outside_windows })}</p>
          <HourHistogram title={t('res.setupsByHour')} counts={result.report.timing.complete_setups_by_hour} highlight={inWindows(result.report.timing.windows)} />
          <HourHistogram title={t('res.sweepsByHour')} counts={result.report.timing.sweep_confirmations_by_hour} highlight={inWindows(result.report.timing.windows)} />
        </section>
      )}
      {metrics && metrics.total_trades > 0 && (
        <section>
          <h2>{t('res.breakdowns')}</h2>
          <PerformanceBreakdowns metrics={metrics} timezone={result.report?.timing?.timezone} />
        </section>
      )}
      <section>
        <h2>{t('res.trades')}</h2>
        <TradesTable trades={result.trades} runId={result.run_id} selected={selected?.trade_id} onSelect={(t) => setSelected(selected?.trade_id === t.trade_id ? null : t)} />
      </section>
      {selected && <TradeExplainerPanel trade={selected} explainer={explainers[selected.trade_id]} onClose={() => setSelected(null)} />}
      <section className="two-col">
        <div><h2>{t('res.quality')}</h2><QualityPanel result={result} /></div>
        <div><h2>{t('res.repro')}</h2><Reproducibility result={result} /></div>
      </section>
    </div>
  );
}
