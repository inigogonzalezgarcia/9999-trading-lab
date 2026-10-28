import { useEffect, useState } from 'react';
import { api, formatNumber, formatPercent, formatR } from '../api';
import type { Widget } from '../content/lessons';
import { useT } from '../i18n';
import { Link } from '../router';
import type { BacktestResult, ResearchReport, Trade } from '../types';
import { PerformanceBreakdowns } from './Breakdowns';
import { EquityChart } from './Charts';
import { HourHistogram, KpiTiles, Rejections, Tile } from './Results';
import { TradeExplainerPanel } from './TradeExplainer';

type Loaded = { kind: 'backtest'; data: BacktestResult } | { kind: 'research'; data: ResearchReport };

const cache = new Map<string, Promise<Loaded>>();

export function useRun(id: string): { run: Loaded | null; error: string } {
  const [run, setRun] = useState<Loaded | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    if (!cache.has(id)) {
      cache.set(id, api.run(id).then(({ meta, result }) => (meta.kind === 'research' ? { kind: 'research', data: result as ResearchReport } : { kind: 'backtest', data: result as BacktestResult })));
      cache.get(id)!.catch(() => cache.delete(id));
    }
    cache.get(id)!.then((loaded) => { if (alive) setRun(loaded); }).catch((e: Error) => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [id]);
  return { run, error };
}

function pickTrade(trades: Trade[], which: 'best' | 'worst' | number): Trade | undefined {
  if (!trades.length) return undefined;
  if (typeof which === 'number') return trades[which];
  const sorted = [...trades].sort((a, b) => b.r_multiple - a.r_multiple);
  return which === 'best' ? sorted[0] : sorted[sorted.length - 1];
}

function inWindows(windows?: { start: string; end: string }[]): (hour: number) => boolean {
  const ranges = (windows ?? []).map((w) => [Number(w.start.slice(0, 2)), Number(w.end.slice(0, 2)) + (w.end.slice(3) === '00' ? -1 : 0)]);
  return (hour) => ranges.some(([a, b]) => hour >= a && hour <= b);
}

function Pct({ title, values }: { title: string; values: Record<string, number> }) {
  return (
    <div className="percentiles">
      <div className="tile-label">{title}</div>
      <div className="pct-row">{Object.keys(values).map((k) => <div key={k} className="pct"><span className="pct-k">p{k}</span><span className="mono">{formatR(values[k])}</span></div>)}</div>
    </div>
  );
}

export function LessonWidget({ widget }: { widget: Widget }) {
  const { t, lang } = useT();
  const { run, error } = useRun(widget.run);
  const [explainerTrade, setExplainerTrade] = useState<Trade | null>(null);
  useEffect(() => {
    if (run?.kind === 'backtest' && widget.type === 'explainer') setExplainerTrade(pickTrade(run.data.trades, widget.trade) ?? null);
  }, [run, widget]);

  if (error) return <div className="widget muted small">{t('lessons.unavailable')} <span className="mono">({widget.run})</span></div>;
  if (!run) return <div className="widget muted small">{t('lessons.loading')}</div>;

  const footer = <p className="small"><Link to={`/lab/${widget.run}`}>{t('lessons.openLab')} →</Link></p>;

  if (run.kind === 'backtest') {
    const r = run.data;
    switch (widget.type) {
      case 'kpis':
        return <div className="widget">{r.metrics && <KpiTiles metrics={r.metrics} />}<p className="muted small">{r.candidate_count} {lang === 'es' ? 'candidatos seguidos' : 'candidates tracked'} · {r.symbol} · {r.reproducibility?.strategy_version ? `v${String(r.reproducibility.strategy_version)}` : ''}</p>{footer}</div>;
      case 'equity':
        return <div className="widget">{r.equity_curve && <EquityChart points={r.equity_curve} />}{r.metrics && <PerformanceBreakdowns metrics={r.metrics} timezone={r.report?.timing?.timezone} />}{footer}</div>;
      case 'rejections':
        return <div className="widget">{r.report && <Rejections rejections={r.report.rejections} total={Math.max(1, r.candidate_count ?? 1)} />}{footer}</div>;
      case 'timing':
        return <div className="widget">{r.report?.timing && <HourHistogram title={t('res.setupsByHour')} counts={r.report.timing.complete_setups_by_hour} highlight={inWindows(r.report.timing.windows)} />}{footer}</div>;
      case 'breakdowns':
        return <div className="widget">{r.metrics && <PerformanceBreakdowns metrics={r.metrics} timezone={r.report?.timing?.timezone} />}{footer}</div>;
      case 'explainer':
        return explainerTrade ? <div className="widget"><TradeExplainerPanel trade={explainerTrade} explainer={r.trade_explainers?.[explainerTrade.trade_id]} onClose={() => undefined} />{footer}</div> : <div className="widget muted small">{t('res.noTrades')}</div>;
      default:
        return null;
    }
  }

  const report = run.data;
  if (widget.type !== 'research') return null;
  const bench = report.benchmark;
  const mc = report.monte_carlo;
  const wf = report.walk_forward;
  return (
    <div className="widget stack">
      {widget.parts.includes('benchmark') && bench && (
        <div>
          <div className="tiles">
            <Tile label={lang === 'es' ? 'Esperanza real' : 'Real expectancy'} value={formatR(bench.baseline_expectancy_r)} />
            <Tile label={lang === 'es' ? 'Percentil frente al azar' : 'Percentile vs random'} value={bench.baseline_percentile_vs_random != null ? `p${(bench.baseline_percentile_vs_random * 100).toFixed(0)}` : '—'} hint={`p ≈ ${formatNumber(bench.empirical_p_value_one_sided)}`} tone={(bench.baseline_percentile_vs_random ?? 0) >= 0.95 ? 'good' : 'neutral'} />
            <Tile label={lang === 'es' ? 'Simulaciones' : 'Simulations'} value={String(bench.simulations)} />
          </div>
          {bench.random_expectancy_percentiles && <Pct title={lang === 'es' ? 'Esperanza de las estrategias aleatorias (R/operación)' : 'Random strategies expectancy (R/trade)'} values={bench.random_expectancy_percentiles} />}
        </div>
      )}
      {widget.parts.includes('montecarlo') && mc && mc.trades_per_path > 0 && (
        <div>
          <div className="tiles">
            <Tile label={lang === 'es' ? 'Caminos' : 'Paths'} value={String(mc.simulations)} hint={`${mc.trades_per_path} ${lang === 'es' ? 'operaciones por camino' : 'trades per path'}`} />
            <Tile label={lang === 'es' ? 'Prob. de camino perdedor' : 'Prob. of losing path'} value={formatPercent(mc.probability_losing)} />
            <Tile label={lang === 'es' ? 'Observado' : 'Observed'} value={formatR(mc.observed?.final_r)} hint={`DD ${formatR(mc.observed?.max_drawdown_r)}`} />
          </div>
          <div className="two-col">
            <Pct title={lang === 'es' ? 'R final' : 'Final R'} values={mc.final_r_percentiles} />
            <Pct title={lang === 'es' ? 'Drawdown máximo' : 'Max drawdown'} values={mc.max_drawdown_r_percentiles} />
          </div>
        </div>
      )}
      {widget.parts.includes('sensitivity') && report.sensitivity && (
        <div className="table-wrap">
          <table className="compact">
            <thead><tr><th>{lang === 'es' ? 'Parámetro' : 'Parameter'}</th><th>{lang === 'es' ? 'Valor' : 'Value'}</th><th>{t('kpi.trades')}</th><th>{t('kpi.expectancy')}</th><th>{t('kpi.total')}</th></tr></thead>
            <tbody>
              <tr className="baseline-row"><td>baseline</td><td>—</td><td className="mono">{report.sensitivity.baseline.trades}</td><td className="mono strong">{formatR(report.sensitivity.baseline.expectancy_r)}</td><td className="mono">{formatR(report.sensitivity.baseline.total_r)}</td></tr>
              {report.sensitivity.variants.filter((v) => !v.error).map((v, i) => (
                <tr key={i} className={(v.total_r ?? 0) >= 0 ? 'win' : 'loss'}><td className="mono small">{v.scope}:{v.parameter}</td><td className="mono">{String(v.value)}</td><td className="mono">{v.trades ?? '—'}</td><td className="mono">{formatR(v.expectancy_r)}</td><td className="mono strong">{formatR(v.total_r)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {widget.parts.includes('walkforward') && wf && (
        <p className="small muted">{lang === 'es' ? 'Walk-forward' : 'Walk-forward'}: {wf.fold_count} {lang === 'es' ? 'tramos' : 'folds'} · OOS {wf.out_of_sample_concatenated.trades} {t('home.trades')}, {formatR(wf.out_of_sample_concatenated.total_r)} · {wf.out_of_sample_concatenated.folds_positive}/{wf.out_of_sample_concatenated.folds_with_trades} {lang === 'es' ? 'tramos positivos' : 'folds positive'}.</p>
      )}
      {footer}
    </div>
  );
}
