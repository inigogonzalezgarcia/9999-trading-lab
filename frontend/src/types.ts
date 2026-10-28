export interface Notice {
  title: string;
  lines: string[];
}

export interface Trade {
  trade_id: string;
  symbol: string;
  date: string;
  direction: 'LONG' | 'SHORT';
  observation_window: string;
  entry_timestamp: string;
  exit_timestamp: string;
  entry_price: number;
  stop_price: number;
  target_price: number;
  exit_price: number;
  exit_reason: string;
  spread_pips: number;
  spread_source: string | null;
  slippage_pips: number;
  commission: number;
  r_multiple: number;
  pnl: number;
  mfe: number;
  mae: number;
}

export interface CandidateEvent {
  candidate_id: string;
  symbol: string;
  direction: string;
  candidate_status: string;
  rejection_reason: string | null;
  trading_date: string;
  sweep_confirmation_timestamp: string;
  actual_signal_time?: string;
  current_state: string;
}

export interface DailyMetrics {
  trading_days: number;
  days_with_trades: number;
  mean_daily_r: number;
  std_daily_r: number;
  annualized_sharpe: number | null;
  annualized_sortino: number | null;
  annualized_r: number | null;
}

export interface Metrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  expectancy_r: number;
  total_r: number;
  profit_factor: number | null;
  payoff_ratio: number | null;
  max_drawdown_r: number;
  max_consecutive_losses: number;
  sharpe_per_trade: number;
  average_win_r: number;
  average_loss_r: number;
  average_mfe_r: number;
  average_mae_r: number;
  exit_reasons: Record<string, number>;
  by_symbol: Record<string, { trades: number; total_r: number; expectancy_r: number; win_rate: number }>;
  by_window: Record<string, { trades: number; total_r: number; expectancy_r: number; win_rate: number }>;
  by_hour?: Record<string, Bucket>;
  by_weekday?: Record<string, Bucket>;
  by_month?: Record<string, Bucket>;
  by_direction?: Record<string, Bucket>;
  by_exit_reason?: Record<string, Bucket>;
  daily: DailyMetrics;
  methodology: Record<string, string>;
}

export interface Bucket {
  trades: number;
  total_r: number;
  expectancy_r: number;
  win_rate: number;
}

export interface ExplainerLevel {
  id: string;
  price: number;
  label: string;
  label_es?: string;
  style: 'solid' | 'dashed' | 'dotted';
  color: string;
}

export interface ExplainerStep {
  id: string;
  time: number;
  timestamp: string;
  local: string;
  title: string;
  text: string;
  title_es?: string;
  text_es?: string;
  position: 'aboveBar' | 'belowBar';
}

export interface TradeExplainer {
  trade_id: string;
  candidate_id: string;
  symbol: string;
  direction: 'LONG' | 'SHORT';
  timezone: string;
  timeframe: string;
  candles: Candle[];
  levels: ExplainerLevel[];
  steps: ExplainerStep[];
  window: { start: string | null; end: string | null; bars: number };
  rules: { stop_reference: string; atr_at_setup: number | null; stop_distance_atr: number | null; observation_window: string | null; scheduled_observation_time: string | null };
  notice: string;
  error?: string;
}

export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface EquityPoint {
  timestamp: string;
  trade_id: string;
  symbol: string;
  r_multiple: number;
  cumulative_r: number;
  drawdown_r: number;
}

export interface BacktestResult {
  run_id?: string;
  strategy_version: string;
  strategy_status: string;
  backtest_blocked: boolean;
  blocked_reason?: string;
  symbol?: string;
  symbols?: string[];
  candidate_count?: number;
  signal_count?: number | null;
  trades: Trade[];
  events?: CandidateEvent[];
  metrics: Metrics | null;
  equity_curve?: EquityPoint[];
  trade_explainers?: Record<string, TradeExplainer>;
  chart?: { timeframe: string; series: Record<string, Candle[]> };
  quality: Record<string, unknown> & { warnings?: string[]; errors?: string[] };
  dataset_version: string;
  scheduled_observations: { kind: string; status: string; madrid: string | null; utc: string | null; new_york: string | null }[];
  reproducibility: Record<string, unknown> & { dataset_hash: string; config_hash: string; software_revision: string; dataset_date_range_utc: { start: string; end: string } };
  report?: {
    rejections: Record<string, number>;
    spread_sources: string[];
    daily_contexts: string;
    timing?: { timezone: string; windows?: { start: string; end: string }[]; sweep_confirmations_by_hour: Record<string, number>; complete_setups_by_hour: Record<string, number>; complete_setups: number; complete_setups_outside_windows: number };
  } & Record<string, unknown>;
  notice: Notice;
}

export interface PeriodSummary {
  period: { start: string; end: string; warmup_days: number } | null;
  trades: number;
  candidates?: number;
  expectancy_r: number;
  total_r: number;
  win_rate: number;
  profit_factor: number | null;
  max_drawdown_r: number;
  annualized_sharpe: number | null;
  trading_days: number;
}

export interface ResearchReport {
  run_id?: string;
  symbol: string;
  baseline: PeriodSummary;
  splits?: { splits: Record<string, { start: string; end: string }>; results: Record<string, PeriodSummary>; note: string };
  walk_forward?: {
    parameters: Record<string, unknown>;
    fold_count: number;
    folds: { fold: number; in_sample: PeriodSummary; out_of_sample: PeriodSummary }[];
    out_of_sample_concatenated: { trades: number; total_r: number; expectancy_r: number; folds_with_trades: number; folds_positive: number; consistency: number | null };
  };
  monte_carlo?: {
    simulations: number;
    trades_per_path: number;
    final_r_percentiles: Record<string, number>;
    max_drawdown_r_percentiles: Record<string, number>;
    probability_losing: number | null;
    observed?: { final_r: number; max_drawdown_r: number };
  };
  sensitivity?: { baseline: PeriodSummary; variants: (Partial<PeriodSummary> & { scope: string; parameter: string; value: unknown; error: string | null })[]; note: string };
  benchmark?: {
    simulations: number;
    baseline_expectancy_r?: number;
    random_expectancy_percentiles?: Record<string, number>;
    baseline_percentile_vs_random?: number;
    empirical_p_value_one_sided?: number;
    note: string;
  };
  limitations: string[];
  reproducibility: Record<string, unknown>;
  notice: Notice;
}

export interface Job {
  job_id: string;
  kind: 'backtest' | 'research';
  status: 'queued' | 'running' | 'done' | 'failed';
  stage: string;
  progress: number;
  created_at: string;
  finished_at: string | null;
  error: string | null;
  result: { run_id: string; summary: Record<string, unknown> } | null;
  symbol?: string;
  dataset_name?: string;
  label?: string | null;
}

export interface RunRow {
  id: string;
  created_at: string;
  kind: 'backtest' | 'research';
  label: string | null;
  symbol: string | null;
  dataset_name: string | null;
  dataset_hash: string | null;
  strategy_version: string | null;
  size: number;
  summary: Record<string, number | string | boolean | null>;
  /** Static site only: localized label/description, strategy file, PDF path. */
  labels?: { es: string; en: string };
  description?: { es: string; en: string };
  strategy?: string;
  pdf?: string | null;
  order?: number;
  sparkline?: number[];
}

export interface SiteIndex {
  generated_at: string;
  software_version: string;
  software_revision: string;
  notice: Notice;
  strategies: string[];
  runs: SiteRun[];
}

export interface SiteRun {
  id: string;
  kind: 'backtest' | 'research';
  symbol: string;
  strategy: string;
  dataset_name: string;
  dataset_hash: string | null;
  label: { es: string; en: string };
  description: { es: string; en: string };
  order: number;
  created_at: string;
  summary: Record<string, number | string | boolean | null>;
  software_version: string;
  pdf: string | null;
  size_bytes: number;
  sparkline?: number[];
}
