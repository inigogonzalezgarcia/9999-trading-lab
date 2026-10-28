import type { BacktestResult, Job, Notice, ResearchReport, RunRow, SiteIndex } from './types';
import { DATA_BASE, STATIC_MODE } from './site';

// Empty base means same origin (production image); dev defaults to the local API port.
export const API_BASE: string = (import.meta.env.VITE_API_BASE as string | undefined) ?? (import.meta.env.DEV ? 'http://localhost:8000' : '');

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  const text = await response.text();
  let body: unknown = text;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    /* non-JSON error body */
  }
  if (!response.ok) {
    const detail = (body as { detail?: unknown })?.detail;
    const message = typeof detail === 'string' ? detail : detail && typeof detail === 'object' && 'detail' in (detail as object) ? String((detail as { detail: string }).detail) : `HTTP ${response.status}`;
    throw new Error(message);
  }
  return body as T;
}

export interface RunOptions {
  symbol: string;
  strategy: string;
  sourceTimezone?: string;
  dailyContexts: string;
  fixedSpreadPips?: number | null;
  label?: string;
}

function form(file: File, options: RunOptions, extra: Record<string, string> = {}): FormData {
  const data = new FormData();
  data.append('file', file);
  data.append('symbol', options.symbol);
  data.append('timeframe', 'M1');
  data.append('strategy', options.strategy);
  if (options.sourceTimezone) data.append('source_timezone', options.sourceTimezone);
  if (options.label) data.append('label', options.label);
  Object.entries(extra).forEach(([key, value]) => data.append(key, value));
  return data;
}

const serverApi = {
  health: () => request<{ status: string; version: string; max_upload_mb: number }>('/api/health'),
  config: () => request<{ strategies: string[]; default_strategy: string; instruments: Record<string, string[]>; instrument_specs: Record<string, { pip: number; description?: string }> }>('/api/config'),
  notice: () => request<Notice>('/api/notice'),
  backtest: (file: File, options: RunOptions) => {
    const data = form(file, options, { daily_contexts: options.dailyContexts });
    if (options.fixedSpreadPips != null) data.append('fixed_spread_pips', String(options.fixedSpreadPips));
    return request<BacktestResult>('/api/backtest', { method: 'POST', body: data });
  },
  submitJob: (kind: 'backtest' | 'research', file: File, options: RunOptions, jobOptions: Record<string, unknown>) =>
    request<Job>(`/api/jobs/${kind}`, { method: 'POST', body: form(file, options, { options: JSON.stringify({ ...jobOptions, strategy: options.strategy }) }) }),
  job: (id: string) => request<Job>(`/api/jobs/${id}`),
  jobs: () => request<Job[]>('/api/jobs'),
  runs: (kind?: string) => request<RunRow[]>(`/api/runs${kind ? `?kind=${kind}` : ''}`),
  run: (id: string) => request<{ meta: RunRow; result: BacktestResult | ResearchReport }>(`/api/runs/${id}`),
  deleteRun: (id: string) => request<{ deleted: boolean }>(`/api/runs/${id}`, { method: 'DELETE' }),
  tradesCsvUrl: (id: string) => `${API_BASE}/api/runs/${id}/trades.csv`,
  resultJsonUrl: (id: string) => `${API_BASE}/api/runs/${id}/result.json`,
  reportPdfUrl: (id: string) => `${API_BASE}/api/runs/${id}/report.pdf`,
};

export type Api = typeof serverApi;

/* ---------- Static site (Cloudflare Pages): precomputed JSON, no backend ---------- */

let indexPromise: Promise<SiteIndex> | null = null;
function siteIndex(): Promise<SiteIndex> {
  if (!indexPromise) {
    indexPromise = fetch(`${DATA_BASE}runs.json`).then(async (response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return (await response.json()) as SiteIndex;
    });
    indexPromise.catch(() => { indexPromise = null; });
  }
  return indexPromise;
}

function notAvailable(): never {
  throw new Error('This installation is read-only: run the engine locally to compute new results.');
}

const staticApi: Api = {
  health: async () => ({ status: 'static', version: (await siteIndex()).software_version, max_upload_mb: 0 }),
  config: async () => {
    const index = await siteIndex();
    return { strategies: index.strategies, default_strategy: index.strategies[0] ?? 'strategy_v1.yaml', instruments: {}, instrument_specs: {} };
  },
  notice: async () => (await siteIndex()).notice,
  backtest: async () => notAvailable(),
  submitJob: async () => notAvailable(),
  job: async () => notAvailable(),
  jobs: async () => [],
  runs: async (kind?: string) => {
    const index = await siteIndex();
    return index.runs
      .filter((run) => !kind || run.kind === kind)
      .map<RunRow>((run) => ({
        id: run.id, created_at: run.created_at, kind: run.kind, label: run.label?.en ?? run.id, labels: run.label, description: run.description,
        symbol: run.symbol, dataset_name: run.dataset_name, dataset_hash: run.dataset_hash, strategy_version: null, strategy: run.strategy,
        size: run.size_bytes, summary: run.summary, pdf: run.pdf, order: run.order, sparkline: run.sparkline,
      }));
  },
  run: async (id: string) => {
    const rows = await staticApi.runs();
    const meta = rows.find((row) => row.id === id);
    if (!meta) throw new Error(`Unknown run ${id}`);
    const response = await fetch(`${DATA_BASE}runs/${encodeURIComponent(id)}.json`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result = (await response.json()) as BacktestResult | ResearchReport;
    return { meta, result };
  },
  deleteRun: async () => ({ deleted: false }),
  tradesCsvUrl: () => '',
  resultJsonUrl: (id: string) => `${DATA_BASE}runs/${encodeURIComponent(id)}.json`,
  reportPdfUrl: (id: string) => `${DATA_BASE}runs/${encodeURIComponent(id)}.pdf`,
};

export const api: Api = STATIC_MODE ? staticApi : serverApi;

export function formatR(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return '—';
  return `${value > 0 ? '+' : ''}${value.toFixed(digits)}R`;
}

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return '—';
  return value.toFixed(digits);
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(0)}%`;
}

export function shortTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  return iso.replace('T', ' ').replace('+00:00', 'Z').slice(0, 17);
}
