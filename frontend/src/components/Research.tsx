import { formatNumber, formatPercent, formatR } from '../api';
import type { PeriodSummary, ResearchReport } from '../types';
import { Tile } from './Results';
import { useT } from '../i18n';

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
  const { t } = useT();
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>{t('rs.period')}</th><th>{t('rs.range')}</th><th>{t('kpi.trades')}</th><th>{t('kpi.expectancy')}</th><th>{t('kpi.total')}</th><th>{t('kpi.winRate')}</th><th>PF</th><th>{t('rs.maxDdShort')}</th><th>{t('rs.sharpeAnn')}</th></tr></thead>
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
  const { t } = useT();
  const wf = report.walk_forward;
  const mc = report.monte_carlo;
  const bench = report.benchmark;
  return (
    <div className="stack">
      <section>
        <h2>{t('rs.baseline')} ({report.symbol})</h2>
        <div className="tiles">
          <Tile label={t('kpi.trades')} value={String(report.baseline.trades)} hint={`${report.baseline.candidates ?? '—'} ${t('rs.candidates')}`} />
          <Tile label={t('kpi.expectancy')} value={formatR(report.baseline.expectancy_r)} tone={report.baseline.expectancy_r > 0 ? 'good' : 'bad'} />
          <Tile label={t('kpi.total')} value={formatR(report.baseline.total_r)} tone={report.baseline.total_r > 0 ? 'good' : 'bad'} />
          <Tile label={t('kpi.dd')} value={formatR(report.baseline.max_drawdown_r)} tone="bad" />
          {bench?.baseline_percentile_vs_random != null && (
            <Tile label={t('rs.vsRandom')} value={`p${(bench.baseline_percentile_vs_random * 100).toFixed(0)}`} hint={`p ≈ ${formatNumber(bench.empirical_p_value_one_sided)}`} tone={bench.baseline_percentile_vs_random >= 0.95 ? 'good' : 'neutral'} />
          )}
          {wf?.out_of_sample_concatenated.consistency != null && (
            <Tile label={t('rs.oos')} value={formatPercent(wf.out_of_sample_concatenated.consistency)} hint={t('rs.foldsPositive', { a: wf.out_of_sample_concatenated.folds_positive, b: wf.out_of_sample_concatenated.folds_with_trades })} />
          )}
        </div>
      </section>
      {report.splits && (
        <section>
          <h2>{t('rs.splits')}</h2>
          <PeriodTable rows={Object.entries(report.splits.results)} />
          <p className="muted small">{report.splits.note}</p>
        </section>
      )}
      {wf && (
        <section>
          <h2>{t('rs.wf')}</h2>
          <p className="muted small">{t('rs.wfNote', { n: wf.fold_count, train: String(wf.parameters.train_days), test: String(wf.parameters.test_days), anchored: wf.parameters.anchored ? t('rs.anchored') : '', trades: wf.out_of_sample_concatenated.trades, total: formatR(wf.out_of_sample_concatenated.total_r), exp: formatR(wf.out_of_sample_concatenated.expectancy_r) })}</p>
          <PeriodTable rows={wf.folds.flatMap((f) => [[`${t('rs.fold')} ${f.fold} · ${t('rs.inSample')}`, f.in_sample], [`${t('rs.fold')} ${f.fold} · ${t('rs.outSample')}`, f.out_of_sample]] as [string, PeriodSummary][])} />
        </section>
      )}
      {mc && mc.trades_per_path > 0 && (
        <section>
          <h2>{t('rs.mc')}</h2>
          <p className="muted small">{t('rs.mcNote', { sims: mc.simulations, n: mc.trades_per_path, p: formatPercent(mc.probability_losing), final: formatR(mc.observed?.final_r), dd: formatR(mc.observed?.max_drawdown_r) })}</p>
          <div className="two-col">
            <Percentiles title={t('rs.finalR')} values={mc.final_r_percentiles} />
            <Percentiles title={t('rs.maxDd')} values={mc.max_drawdown_r_percentiles} />
          </div>
        </section>
      )}
      {bench && bench.random_expectancy_percentiles && (
        <section>
          <h2>{t('rs.bench')}</h2>
          <p className="muted small">{bench.note} {t('rs.benchSims', { n: bench.simulations })}</p>
          <Percentiles title={t('rs.benchPct')} values={bench.random_expectancy_percentiles} />
          <p className="small">{t('rs.benchNote', { exp: formatR(bench.baseline_expectancy_r), pct: formatNumber((bench.baseline_percentile_vs_random ?? 0) * 100, 0) })}</p>
        </section>
      )}
      {report.sensitivity && (
        <section>
          <h2>{t('rs.sens')}</h2>
          <p className="muted small">{report.sensitivity.note}</p>
          <div className="table-wrap">
            <table>
              <thead><tr><th>{t('rs.param')}</th><th>{t('rs.value')}</th><th>{t('kpi.trades')}</th><th>{t('kpi.expectancy')}</th><th>{t('kpi.total')}</th><th>{t('rs.maxDdShort')}</th><th>{t('rs.note')}</th></tr></thead>
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
        <h2>{t('rs.limits')}</h2>
        <ul className="small">{report.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
      </section>
    </div>
  );
}
