import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App() {
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  async function submit(e: any) {
    e.preventDefault(); setBusy(true); setErr('');
    const form = new FormData(e.currentTarget);
    try {
      const response = await fetch('http://localhost:8000/api/backtest', { method: 'POST', body: form });
      const body = await response.json();
      if (!response.ok) throw Error(body.detail || 'Validation failed');
      setResult(body);
    } catch (error: any) { setErr(error.message); } finally { setBusy(false); }
  }
  return <main>
    <header><div><small>RESEARCH / BACKTESTING</small><h1>FX Research Lab</h1></div><span className="badge">No live execution</span></header>
    <section className="intro"><h2>Test the hypothesis. Keep the evidence.</h2><p>Import historical bars and inspect data quality against the versioned strategy specification.</p></section>
    <form onSubmit={submit}>
      <label>Historical CSV / Parquet<input name="file" type="file" accept=".csv,.parquet,.pq" required /></label>
      <label>Symbol<select name="symbol"><option>EURUSD</option><option>GBPUSD</option></select></label>
      <label>Timeframe<select name="timeframe"><option>M1</option><option>M5</option><option>M15</option><option>H1</option></select></label>
      <label>Source timezone (for naive timestamps)<input name="source_timezone" placeholder="e.g. UTC" /></label>
      <button disabled={busy}>{busy ? 'Validating…' : 'Validate dataset'}</button>
    </form>
    {err && <p className="error">{err}</p>}
    {result && <>
      <div className="notice"><strong>Strategy status: {result.strategy_status}</strong><p>{result.blocked_reason || (result.backtest_blocked ? 'No strategy results were generated.' : 'Research backtest completed. Historical results are not evidence of a profitable edge.')}</p></div>
      <h2>Data quality</h2><pre>{JSON.stringify(result.quality, null, 2)}</pre>
      <h2>Configured schedule</h2><p>Preparation is reference only. Observation points are exact Europe/Madrid timestamps.</p>
      <div className="table"><table><thead><tr><th>Type</th><th>Europe/Madrid</th><th>UTC</th><th>America/New_York</th></tr></thead><tbody>{result.scheduled_observations.map((item: any) => <tr key={item.madrid}><td>{item.kind}</td><td>{item.madrid}</td><td>{item.utc}</td><td>{item.new_york}</td></tr>)}</tbody></table></div>
      <h2>V1 backtest status</h2><p>{result.backtest_blocked ? <>The deterministic strategy rules are recorded in <code>config/strategy_v1.yaml</code>. The backtest stays blocked until the implementation gate passes. Uploads remain available for data-quality review.</> : 'The configured strategy ran in historical research mode. Historical performance does not establish a profitable edge.'}</p>
      {!result.backtest_blocked && <><h2>Backtest metrics</h2><pre>{JSON.stringify(result.metrics, null, 2)}</pre><h2>Candidate and trade events</h2><pre>{JSON.stringify({ events: result.events, trades: result.trades, reproducibility: result.reproducibility }, null, 2)}</pre></>}
    </>}
  </main>;
}
createRoot(document.getElementById('root')!).render(<App />);
