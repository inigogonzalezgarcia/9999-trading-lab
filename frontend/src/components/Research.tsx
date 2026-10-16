import { formatNumber, formatPercent, formatR } from '../api';
import type { PeriodSummary, ResearchReport } from '../types';
import { Tile } from './Results';

function PeriodRow({ name, summary }: { name: string; summary: PeriodSummary }) {
  return (
    <tr>
      <td>{name}</td>
      <td className="mono small">{summary.period ? `${summary.period.start.slice(0, 10)} → ${summary.period.end.slice(0, 10)}` : '—'}</td>
      <td className="mono">{summary.trades}</td>
      <td className={`mono strong ${summary.expectancy_r > 0 ? 'good' : summary.expectancy_r < 0 ? 'bad' : ''}`}>{formatR(summary.expectancy_r)}</td>
      <td className="mono">{formatR(summary.total_r)}</td>
      <td className="mono">{formatPercent(summary.win_rate)}</td>
      <td className="mono">{formatNumber(summary.profit_factor)}</td>
      <td className="mono">{formatR(summary.max_drawdown_r)}</td>
      <td className="mono">{formatNumber(summary.annualized_sharpe)}</td>
    </tr>
  );
}

function PeriodTable({ rows }: { rows: [string, PeriodSummary][] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Period</th><th>Range</th><th>Trades</th><th>Expectancy</th><th>Total</th><th>Win rate</th><th>PF</th><th>Max DD</th><th>Sharpe (ann.)</th></tr></thead>
        <tbody>{rows.map(([name, summary]) => <PeriodRow key={name} name={name} summary={summary} />)}</tbody>
      </table>
    </div>
  );
}

function Percentiles({ title, values, unit = 'R' }: { title: string; values: Record<string, number>; unit?: string }) {
  const keys = Object.keys(values);
  if (!keys.length) return null;
  return (
    <div className="percentiles">
      <div className="tile-label">{title}</div>
      <div className="pct-row">
        {keys.map((k) => (
          <div key={k} className="pct"><span className="pct-k">p{k}</span><span className="mono">{unit === 'R' ? formatR(values[k]) : formatNumber(values[k])}</span></div>
        ))}
      </div>
    </div>
  );
}

export function ResearchView({ report }: { report: ResearchReport }) {
  const wf = report.walk_forward;
  const mc = report.monte_carlo;
  const bench = report.benchmark;
  return (
    <div className="stack">
      <section>
        <h2>Baseline ({report.symbol})</h2>
        <div className="tiles">
          <Tile label="Trades" value={String(report.baseline.trades)} hint={`${report.baseline.candidates ?? '—'} candidates`} />
          <Tile label="Expectancy" value={formatR(report.baseline.expectancy_r)} tone={report.baseline.expectancy_r > 0 ? 'good' : 'bad'} />
          <Tile label="Total" value={formatR(report.baseline.total_r)} tone={report.baseline.total_r > 0 ? 'good' : 'bad'} />
          <Tile label="Max drawdown" value={formatR(report.baseline.max_drawdown_r)} tone="bad" />
          {bench?.baseline_percentile_vs_random != null && (
            <Tile label="vs random (cost-matched)" value={`p${(bench.baseline_percentile_vs_random * 100).toFixed(0)}`} hint={`one-sided p ≈ ${formatNumber(bench.empirical_p_value_one_sided)}`} tone={bench.baseline_percentile_vs_random >= 0.95 ? 'good' : 'neutral'} />
          )}
          {wf?.out_of_sample_concatenated.consistency != null && (
            <Tile label="OOS fold consistency" value={formatPercent(wf.out_of_sample_concatenated.consistency)} hint={`${wf.out_of_sample_concatenated.folds_positive}/${wf.out_of_sample_concatenated.folds_with_trades} folds positive`} />
          )}
        </div>
      </section>
      {report.splits && (
        <section>
          <h2>Independent chronological periods</h2>
          <PeriodTable rows={Object.entries(report.splits.results)} />
          <p className="muted small">{report.splits.note}</p>
        </section>
      )}
      {wf && (
        <section>
          <h2>Rolling out-of-sample (walk-forward)</h2>
          <p className="muted small">{wf.fold_count} folds · train {String(wf.parameters.train_days)} days, test {String(wf.parameters.test_days)} days{wf.parameters.anchored ? ', anchored' : ''}. Concatenated OOS: {wf.out_of_sample_concatenated.trades} trades, {formatR(wf.out_of_sample_concatenated.total_r)} total, {formatR(wf.out_of_sample_concatenated.expectancy_r)} expectancy.</p>
          <PeriodTable rows={wf.folds.flatMap((f) => [[`Fold ${f.fold} · in-sample`, f.in_sample], [`Fold ${f.fold} · out-of-sample`, f.out_of_sample]] as [string, PeriodSummary][])} />
        </section>
      )}
      {mc && mc.trades_per_path > 0 && (
        <section>
          <h2>Monte Carlo (trade-sequence bootstrap)</h2>
          <p className="muted small">{mc.simulations} resampled paths of {mc.trades_per_path} trades · probability of a losing path {formatPercent(mc.probability_losing)} · observed {formatR(mc.observed?.final_r)} with {formatR(mc.observed?.max_drawdown_r)} max drawdown.</p>
          <div className="two-col">
            <Percentiles title="Final R" values={mc.final_r_percentiles} />
            <Percentiles title="Max drawdown R" values={mc.max_drawdown_r_percentiles} />
          </div>
        </section>
      )}
      {bench && bench.random_expectancy_percentiles && (
        <section>
          <h2>Cost-matched random benchmark</h2>
          <p className="muted small">{bench.note} {bench.simulations} simulations.</p>
          <Percentiles title="Random expectancy (R per trade)" values={bench.random_expectancy_percentiles} />
          <p className="small">Baseline expectancy {formatR(bench.baseline_expectancy_r)} sits at percentile {formatNumber((bench.baseline_percentile_vs_random ?? 0) * 100, 0)} of the random distribution.</p>
        </section>
      )}
      {report.sensitivity && (
        <section>
          <h2>Parameter sensitivity (one at a time)</h2>
          <p className="muted small">{report.sensitivity.note}</p>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Parameter</th><th>Value</th><th>Trades</th><th>Expectancy</th><th>Total</th><th>Max DD</th><th>Note</th></tr></thead>
              <tbody>
                <tr className="baseline-row"><td>baseline</td><td>—</td><td className="mono">{report.sensitivity.baseline.trades}</td><td className="mono strong">{formatR(report.sensitivity.baseline.expectancy_r)}</td><td className="mono">{formatR(report.sensitivity.baseline.total_r)}</td><td className="mono">{formatR(report.sensitivity.baseline.max_drawdown_r)}</td><td /></tr>
                {report.sensitivity.variants.map((v, i) => (
                  <tr key={i}>
                    <td className="mono small">{v.scope}:{v.parameter}</td>
                    <td className="mono">{String(v.value)}</td>
                    <td className="mono">{v.trades ?? '—'}</td>
                    <td className={`mono strong ${(v.expectancy_r ?? 0) > 0 ? 'good' : (v.expectancy_r ?? 0) < 0 ? 'bad' : ''}`}>{formatR(v.expectancy_r)}</td>
                    <td className="mono">{formatR(v.total_r)}</td>
                    <td className="mono">{formatR(v.max_drawdown_r)}</td>
                    <td className="small warn-text">{v.error ?? ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      <section>
        <h2>Limitations</h2>
        <ul className="small">{report.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
      </section>
    </div>
  );
}
