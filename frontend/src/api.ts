import type { BacktestResult, Job, Notice, ResearchReport, RunRow } from './types';

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

export const api = {
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
