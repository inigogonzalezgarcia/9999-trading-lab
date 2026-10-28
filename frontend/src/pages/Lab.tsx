import { useCallback, useEffect, useRef, useState } from 'react';
import { api, formatR, shortTime, type RunOptions } from '../api';
import { useT } from '../i18n';
import { Link, useRoute } from '../router';
import { REPO_URL, STATIC_MODE } from '../site';
import type { BacktestResult, Job, ResearchReport, RunRow } from '../types';
import { BacktestView } from '../components/Results';
import { ResearchView } from '../components/Research';

type Mode = 'backtest' | 'research';
type Loaded = { kind: 'backtest'; data: BacktestResult; title: string } | { kind: 'research'; data: ResearchReport; title: string };

export function LabPage({ runId }: { runId?: string }) {
  const { t, pick, lang } = useT();
  const { navigate } = useRoute();
  const [health, setHealth] = useState<{ version: string; max_upload_mb: number } | null>(null);
  const [offline, setOffline] = useState(false);
  const [mode, setMode] = useState<Mode>('backtest');
  const [file, setFile] = useState<File | null>(null);
  const [options, setOptions] = useState<RunOptions>({ symbol: 'EURUSD', strategy: 'strategy_v1.yaml', dailyContexts: 'lookback:30', sourceTimezone: '', fixedSpreadPips: null, label: '' });
  const [strategies, setStrategies] = useState<string[]>(['strategy_v1.yaml']);
  const [instruments, setInstruments] = useState<Record<string, string[]>>({ 'strategy_v1.yaml': ['EURUSD', 'GBPUSD'] });
  const [specs, setSpecs] = useState<Record<string, { pip: number; description?: string }>>({});
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
    api.config().then((c) => { setStrategies(c.strategies); setInstruments(c.instruments ?? {}); setSpecs(c.instrument_specs ?? {}); setOptions((o) => ({ ...o, strategy: c.default_strategy })); }).catch(() => undefined);
    refreshRuns();
    return () => { if (poll.current) window.clearInterval(poll.current); };
  }, [refreshRuns]);

  const openRun = useCallback(async (id: string) => {
    setError('');
    try {
      const { meta, result } = await api.run(id);
      const label = meta.labels ? (lang === 'es' ? meta.labels.es : meta.labels.en) : `${meta.kind} · ${meta.symbol ?? ''} · ${meta.dataset_name ?? ''} · ${shortTime(meta.created_at)}`;
      setLoaded(meta.kind === 'research' ? { kind: 'research', data: { ...(result as ResearchReport), run_id: id }, title: label } : { kind: 'backtest', data: { ...(result as BacktestResult), run_id: id }, title: label });
      setView('result');
    } catch (e) {
      setError((e as Error).message);
    }
  }, [lang]);

  // Static site: the run id lives in the URL (/lab/<id>) so lessons and the home page can deep-link.
  useEffect(() => {
    if (runId && (!loaded || ('run_id' in loaded.data && loaded.data.run_id !== runId))) openRun(runId);
  }, [runId, loaded, openRun]);

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
    if (!window.confirm(t('lab.deleteConfirm'))) return;
    await api.deleteRun(id);
    if (loaded && 'run_id' in loaded.data && loaded.data.run_id === id) setLoaded(null);
    refreshRuns();
  };

  const currentId = loaded && 'run_id' in loaded.data ? loaded.data.run_id : undefined;

  const catalogue = (
    <aside className="panel catalogue">
      <div>
        <h2>{t('lab.catalogue')}</h2>
        <p className="muted small">{t('lab.catalogueLead')}</p>
      </div>
      <ul className="run-list">
        {runs.map((r) => (
          <li key={r.id} className={r.id === currentId ? 'active' : ''}>
            <Link to={`/lab/${r.id}`}>
              <span className="run-kind">{r.kind === 'research' ? t('lab.research') : t('lab.backtest')}</span>
              <strong>{r.labels ? pick(r.labels) : r.label}</strong>
              <span className="small muted">{r.description ? pick(r.description) : ''}</span>
              <span className="mono small">
                {r.summary.trades != null ? `${String(r.summary.trades)} ${t('home.trades')} · ` : ''}{formatR(r.summary.total_r as number)}
              </span>
            </Link>
          </li>
        ))}
        {!runs.length && <li className="muted small">{error || '…'}</li>}
      </ul>
      <div className="run-yourself">
        <h2>{t('lab.runYourself')}</h2>
        <p className="muted small">{t('lab.runYourselfText')}</p>
        <code className="block">git clone {REPO_URL}.git{'\n'}pip install -r backend/requirements.txt{'\n'}python -m backend.cli fetch dukascopy --symbol EURUSD --start 2024-01-01 --end 2025-01-01 --out data/raw/EURUSD_2024.csv{'\n'}python -m backend.cli backtest data/raw/EURUSD_2024.csv --symbol EURUSD</code>
      </div>
    </aside>
  );

  const form = (
    <form className="panel" onSubmit={submit}>
      <div className="segmented wide">
        <button type="button" className={mode === 'backtest' ? 'active' : ''} onClick={() => setMode('backtest')}>{t('lab.backtest')}</button>
        <button type="button" className={mode === 'research' ? 'active' : ''} onClick={() => setMode('research')}>{t('lab.research')}</button>
      </div>
      <label>
        {t('lab.file')}
        <input type="file" accept=".csv,.parquet,.pq" required onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        {health && <small className="muted">{t('lab.fileHint', { mb: health.max_upload_mb })}</small>}
      </label>
      <label>
        {t('lab.strategy')}
        <select value={options.strategy} onChange={(e) => { const strategy = e.target.value; const allowed = instruments[strategy] ?? []; setOptions({ ...options, strategy, symbol: options.symbol === 'PORTFOLIO' || allowed.includes(options.symbol) ? options.symbol : allowed[0] ?? options.symbol }); }}>
          {strategies.map((name) => <option key={name} value={name}>{name.replace('strategy_', '').replace('.yaml', '').replace('_', '.')} {name === 'strategy_v1.yaml' ? t('lab.baseline') : t('lab.experiment')}</option>)}
        </select>
      </label>
      <label>
        {t('lab.symbol')}
        <select value={options.symbol} onChange={(e) => setOptions({ ...options, symbol: e.target.value })}>
          {(instruments[options.strategy] ?? ['EURUSD', 'GBPUSD']).map((s) => <option key={s} value={s}>{s}{specs[s] ? ` · pip ${specs[s].pip}` : ''}</option>)}
          <option value="PORTFOLIO">{t('lab.portfolio')}</option>
        </select>
      </label>
      <label>
        {t('lab.sourceTz')} <small className="muted">{t('lab.sourceTzHint')}</small>
        <input value={options.sourceTimezone} placeholder="UTC" onChange={(e) => setOptions({ ...options, sourceTimezone: e.target.value })} />
      </label>
      <label>
        {t('lab.spread')} <small className="muted">{t('lab.spreadHint')}</small>
        <input type="number" step="0.1" min="0" value={options.fixedSpreadPips ?? ''} placeholder="—" onChange={(e) => setOptions({ ...options, fixedSpreadPips: e.target.value === '' ? null : Number(e.target.value) })} />
      </label>
      {mode === 'backtest' ? (
        <label>
          {t('lab.contexts')}
          <select value={options.dailyContexts} onChange={(e) => setOptions({ ...options, dailyContexts: e.target.value })}>
            <option value="lookback:30">{t('lab.ctxLookback30')}</option>
            <option value="lookback:90">{t('lab.ctxLookback90')}</option>
            <option value="full">{t('lab.ctxFull')}</option>
            <option value="none">{t('lab.ctxNone')}</option>
          </select>
        </label>
      ) : (
        <fieldset className="grid2">
          <label>{t('lab.trainDays')}<input type="number" min="10" value={research.train_days} onChange={(e) => setResearch({ ...research, train_days: Number(e.target.value) })} /></label>
          <label>{t('lab.testDays')}<input type="number" min="5" value={research.test_days} onChange={(e) => setResearch({ ...research, test_days: Number(e.target.value) })} /></label>
          <label>{t('lab.mcPaths')}<input type="number" min="100" step="100" value={research.mc_simulations} onChange={(e) => setResearch({ ...research, mc_simulations: Number(e.target.value) })} /></label>
          <label>{t('lab.benchSims')}<input type="number" min="20" step="20" value={research.benchmark_simulations} onChange={(e) => setResearch({ ...research, benchmark_simulations: Number(e.target.value) })} /></label>
          <label className="check"><input type="checkbox" checked={research.anchored} onChange={(e) => setResearch({ ...research, anchored: e.target.checked })} /> {t('lab.anchored')}</label>
          <label className="check"><input type="checkbox" checked={research.sensitivity} onChange={(e) => setResearch({ ...research, sensitivity: e.target.checked })} /> {t('lab.sensitivity')}</label>
        </fieldset>
      )}
      <label>
        {t('lab.label')} <small className="muted">{t('lab.labelHint')}</small>
        <input value={options.label} onChange={(e) => setOptions({ ...options, label: e.target.value })} />
      </label>
      <button disabled={busy || !file}>{busy ? t('lab.running') : mode === 'backtest' ? t('lab.run') : t('lab.runResearch')}</button>
      {job && (
        <div className="progress">
          <div className="progress-bar"><span style={{ width: `${Math.round(job.progress * 100)}%` }} /></div>
          <small className="mono">{job.status} · {job.stage} · {Math.round(job.progress * 100)}%</small>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </form>
  );

  return (
    <>
      {offline && !STATIC_MODE && <p className="error">{t('lab.offline')} <code>uvicorn backend.app.main:app --reload --port 8000</code> / <code>docker compose up</code>.</p>}
      <main className="layout">
        {STATIC_MODE ? catalogue : form}
        <section className="content">
          <div className="tabs">
            <button type="button" className={view === 'result' ? 'active' : ''} onClick={() => setView('result')}>{t('lab.tabResult')}</button>
            {!STATIC_MODE && <button type="button" className={view === 'history' ? 'active' : ''} onClick={() => { setView('history'); refreshRuns(); }}>{t('lab.tabHistory')} ({runs.length})</button>}
            {loaded && view === 'result' && (
              <span className="tab-actions">
                <button type="button" className="ghost" onClick={() => window.print()}>{t('lab.print')}</button>
                {currentId && <a className="ghost button" href={api.resultJsonUrl(currentId)}>JSON</a>}
                {currentId && (!STATIC_MODE || runs.find((r) => r.id === currentId)?.pdf) && <a className="ghost button" href={api.reportPdfUrl(currentId)} target="_blank" rel="noreferrer">{t('lab.pdf')}</a>}
              </span>
            )}
          </div>
          {view === 'result' && !loaded && (
            <div className="empty">
              <h2>{t('lab.emptyTitle')}</h2>
              <p>{STATIC_MODE ? t('lab.emptyStatic') : t('lab.emptyText')}</p>
              {STATIC_MODE && runs.length > 0 && <p><button type="button" onClick={() => navigate(`/lab/${runs[0].id}`)}>{pick(runs[0].labels) ?? runs[0].id}</button></p>}
              {error && <p className="error">{error}</p>}
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
              {runs.length === 0 && <p className="muted">{t('lab.noRuns')}</p>}
              {runs.length > 0 && (
                <table>
                  <thead><tr><th>{t('lab.when')}</th><th>{t('lab.kind')}</th><th>{t('lab.label')}</th><th>{t('lab.symbol')}</th><th>{t('lab.dataset')}</th><th>{t('kpi.trades')}</th><th>{t('lab.expectancy')}</th><th>{t('lab.total')}</th><th /></tr></thead>
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
                          <button type="button" className="ghost" onClick={() => openRun(r.id)}>{t('lab.open')}</button>
                          <a className="ghost button" href={api.tradesCsvUrl(r.id)}>CSV</a>
                          <a className="ghost button" href={api.reportPdfUrl(r.id)} target="_blank" rel="noreferrer">PDF</a>
                          <button type="button" className="ghost danger" onClick={() => remove(r.id)}>{t('lab.delete')}</button>
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
    </>
  );
}
