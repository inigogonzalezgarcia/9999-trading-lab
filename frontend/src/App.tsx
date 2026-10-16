import { useCallback, useEffect, useRef, useState } from 'react';
import { api, formatR, shortTime, type RunOptions } from './api';
import type { BacktestResult, Job, Notice, ResearchReport, RunRow } from './types';
import { BacktestView } from './components/Results';
import { ResearchView } from './components/Research';

type Mode = 'backtest' | 'research';
type Loaded = { kind: 'backtest'; data: BacktestResult; title: string } | { kind: 'research'; data: ResearchReport; title: string };

const FALLBACK_NOTICE: Notice = {
  title: 'Educational research tool',
  lines: ['Simulated historical research only. Not investment advice, no live execution, no signals. Historical performance does not guarantee future results.'],
};

export default function App() {
  const [notice, setNotice] = useState<Notice>(FALLBACK_NOTICE);
  const [health, setHealth] = useState<{ version: string; max_upload_mb: number } | null>(null);
  const [offline, setOffline] = useState(false);
  const [mode, setMode] = useState<Mode>('backtest');
  const [file, setFile] = useState<File | null>(null);
  const [options, setOptions] = useState<RunOptions>({ symbol: 'EURUSD', dailyContexts: 'lookback:30', sourceTimezone: '', fixedSpreadPips: null, label: '' });
  const [research, setResearch] = useState({ train_days: 120, test_days: 30, anchored: false, mc_simulations: 1000, benchmark_simulations: 200, sensitivity: true, walk_forward: true });
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [view, setView] = useState<'result' | 'history'>('result');
  const poll = useRef<number | null>(null);

  const refreshRuns = useCallback(() => api.runs().then(setRuns).catch(() => setRuns([])), []);

  useEffect(() => {
    api.health().then((h) => { setHealth(h); setOffline(false); }).catch(() => setOffline(true));
    api.notice().then(setNotice).catch(() => undefined);
    refreshRuns();
    return () => { if (poll.current) window.clearInterval(poll.current); };
  }, [refreshRuns]);

  const openRun = useCallback(async (id: string) => {
    setError('');
    try {
      const { meta, result } = await api.run(id);
      const title = `${meta.kind} · ${meta.symbol ?? ''} · ${meta.dataset_name ?? ''} · ${shortTime(meta.created_at)}`;
      setLoaded(meta.kind === 'research' ? { kind: 'research', data: result as ResearchReport, title } : { kind: 'backtest', data: { ...(result as BacktestResult), run_id: id }, title });
      setView('result');
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const watch = useCallback((submitted: Job) => {
    setJob(submitted);
    if (poll.current) window.clearInterval(poll.current);
    poll.current = window.setInterval(async () => {
      try {
        const current = await api.job(submitted.job_id);
        setJob(current);
        if (current.status === 'done' || current.status === 'failed') {
          if (poll.current) window.clearInterval(poll.current);
          poll.current = null;
          setBusy(false);
          if (current.status === 'failed') setError(current.error ?? 'Job failed');
          else if (current.result) { await refreshRuns(); await openRun(current.result.run_id); }
        }
      } catch (e) {
        setError((e as Error).message);
      }
    }, 1200);
  }, [openRun, refreshRuns]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError('');
    setJob(null);
    try {
      const smallFile = file.size < 12 * 1024 * 1024;
      if (mode === 'backtest' && smallFile) {
        const result = await api.backtest(file, options);
        setLoaded({ kind: 'backtest', data: result, title: `backtest · ${options.symbol} · ${file.name}` });
        setView('result');
        setBusy(false);
        refreshRuns();
      } else {
        const jobOptions = mode === 'backtest'
          ? { daily_contexts: options.dailyContexts, fixed_spread_pips: options.fixedSpreadPips }
          : { fixed_spread_pips: options.fixedSpreadPips, ...research };
        watch(await api.submitJob(mode, file, options, jobOptions));
      }
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    if (!window.confirm('Delete this run from the history?')) return;
    await api.deleteRun(id);
    if (loaded && 'run_id' in loaded.data && (loaded.data as BacktestResult).run_id === id) setLoaded(null);
    refreshRuns();
  };

  return (
    <div className="app">
      <header className="masthead">
        <div>
          <small>RESEARCH / BACKTESTING · V1 BASELINE</small>
          <h1>FX Research Lab</h1>
        </div>
        <div className="masthead-right">
          <span className="badge">No live execution</span>
          <span className="badge soft">Educational</span>
          {health && <span className="muted small">v{health.version}</span>}
        </div>
      </header>

      <aside className="notice" role="note">
        <strong>{notice.title}.</strong> {notice.lines.join(' ')}
      </aside>

      {offline && <p className="error">The API is not reachable. Start it with <code>uvicorn backend.app.main:app --reload --port 8000</code> or <code>docker compose up</code>.</p>}

      <main className="layout">
        <form className="panel" onSubmit={submit}>
          <div className="segmented wide">
            <button type="button" className={mode === 'backtest' ? 'active' : ''} onClick={() => setMode('backtest')}>Backtest</button>
            <button type="button" className={mode === 'research' ? 'active' : ''} onClick={() => setMode('research')}>Research protocol</button>
          </div>
          <label>
            Historical M1 CSV / Parquet
            <input type="file" accept=".csv,.parquet,.pq" required onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            {health && <small className="muted">up to {health.max_upload_mb} MB · larger files run in the background or via the CLI</small>}
          </label>
          <label>
            Symbol
            <select value={options.symbol} onChange={(e) => setOptions({ ...options, symbol: e.target.value })}>
              <option>EURUSD</option><option>GBPUSD</option><option value="PORTFOLIO">PORTFOLIO (file with symbol column)</option>
            </select>
          </label>
          <label>
            Source timezone <small className="muted">(only for naive timestamps, e.g. UTC)</small>
            <input value={options.sourceTimezone} placeholder="UTC" onChange={(e) => setOptions({ ...options, sourceTimezone: e.target.value })} />
          </label>
          <label>
            Fixed spread fallback (pips) <small className="muted">used only when the file has no spread_pips</small>
            <input type="number" step="0.1" min="0" value={options.fixedSpreadPips ?? ''} placeholder="none" onChange={(e) => setOptions({ ...options, fixedSpreadPips: e.target.value === '' ? null : Number(e.target.value) })} />
          </label>
          {mode === 'backtest' ? (
            <label>
              Daily 01:50 contexts
              <select value={options.dailyContexts} onChange={(e) => setOptions({ ...options, dailyContexts: e.target.value })}>
                <option value="lookback:30">lookback 30 days (recommended)</option>
                <option value="lookback:90">lookback 90 days</option>
                <option value="full">full history (exact, slow on long datasets)</option>
                <option value="none">none (fastest)</option>
              </select>
            </label>
          ) : (
            <fieldset className="grid2">
              <label>Train days<input type="number" min="10" value={research.train_days} onChange={(e) => setResearch({ ...research, train_days: Number(e.target.value) })} /></label>
              <label>Test days<input type="number" min="5" value={research.test_days} onChange={(e) => setResearch({ ...research, test_days: Number(e.target.value) })} /></label>
              <label>Monte Carlo paths<input type="number" min="100" step="100" value={research.mc_simulations} onChange={(e) => setResearch({ ...research, mc_simulations: Number(e.target.value) })} /></label>
              <label>Random benchmark sims<input type="number" min="20" step="20" value={research.benchmark_simulations} onChange={(e) => setResearch({ ...research, benchmark_simulations: Number(e.target.value) })} /></label>
              <label className="check"><input type="checkbox" checked={research.anchored} onChange={(e) => setResearch({ ...research, anchored: e.target.checked })} /> anchored walk-forward</label>
              <label className="check"><input type="checkbox" checked={research.sensitivity} onChange={(e) => setResearch({ ...research, sensitivity: e.target.checked })} /> parameter sensitivity</label>
            </fieldset>
          )}
          <label>
            Label <small className="muted">(optional, shown in history)</small>
            <input value={options.label} onChange={(e) => setOptions({ ...options, label: e.target.value })} />
          </label>
          <button disabled={busy || !file}>{busy ? 'Running…' : mode === 'backtest' ? 'Run research backtest' : 'Run research protocol'}</button>
          {job && (
            <div className="progress">
              <div className="progress-bar"><span style={{ width: `${Math.round(job.progress * 100)}%` }} /></div>
              <small className="mono">{job.status} · {job.stage} · {Math.round(job.progress * 100)}%</small>
            </div>
          )}
          {error && <p className="error">{error}</p>}
        </form>

        <section className="content">
          <div className="tabs">
            <button type="button" className={view === 'result' ? 'active' : ''} onClick={() => setView('result')}>Result</button>
            <button type="button" className={view === 'history' ? 'active' : ''} onClick={() => { setView('history'); refreshRuns(); }}>History ({runs.length})</button>
            {loaded && view === 'result' && (
              <span className="tab-actions">
                <button type="button" className="ghost" onClick={() => window.print()}>Print / PDF</button>
                {'run_id' in loaded.data && (loaded.data as BacktestResult).run_id && <a className="ghost button" href={api.resultJsonUrl((loaded.data as BacktestResult).run_id!)}>JSON</a>}
              </span>
            )}
          </div>
          {view === 'result' && !loaded && (
            <div className="empty">
              <h2>Test the hypothesis. Keep the evidence.</h2>
              <p>Upload historical M1 bars to run the fully specified V1 baseline with causal fills and recorded costs, or run the research protocol (independent periods, rolling out-of-sample, Monte Carlo, sensitivity, cost-matched random benchmark).</p>
              <p className="muted small">Need data? <code>python -m backend.cli fetch dukascopy --symbol EURUSD --start 2024-01-01 --end 2024-07-01 --out data/raw/EURUSD.csv</code> or convert a HistData download with <code>python -m backend.cli convert histdata …</code>.</p>
            </div>
          )}
          {view === 'result' && loaded && (
            <>
              <p className="muted small result-title">{loaded.title}</p>
              {loaded.kind === 'backtest' ? <BacktestView result={loaded.data} /> : <ResearchView report={loaded.data} />}
            </>
          )}
          {view === 'history' && (
            <div className="table-wrap">
              {runs.length === 0 && <p className="muted">No persisted runs yet.</p>}
              {runs.length > 0 && (
                <table>
                  <thead><tr><th>When</th><th>Kind</th><th>Label</th><th>Symbol</th><th>Dataset</th><th>Trades</th><th>Expectancy</th><th>Total</th><th /></tr></thead>
                  <tbody>
                    {runs.map((r) => (
                      <tr key={r.id}>
                        <td className="mono small">{shortTime(r.created_at)}</td>
                        <td>{r.kind}</td>
                        <td>{r.label ?? ''}</td>
                        <td>{r.symbol}</td>
                        <td className="small">{r.dataset_name} <small className="mono muted">{(r.dataset_hash ?? '').slice(0, 8)}</small></td>
                        <td className="mono">{String(r.summary.trades ?? '—')}</td>
                        <td className="mono">{formatR(r.summary.expectancy_r as number)}</td>
                        <td className="mono">{formatR(r.summary.total_r as number)}</td>
                        <td className="row-actions">
                          <button type="button" className="ghost" onClick={() => openRun(r.id)}>Open</button>
                          <a className="ghost button" href={api.tradesCsvUrl(r.id)}>CSV</a>
                          <button type="button" className="ghost danger" onClick={() => remove(r.id)}>Delete</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </section>
      </main>
      <footer className="muted small">
        {notice.lines[notice.lines.length - 1]} · Source hash and configuration are recorded with every run.
      </footer>
    </div>
  );
}
