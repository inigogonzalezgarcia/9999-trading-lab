/** Per-viewer lesson progress kept in the browser (no account, no server). */
const KEY = 'fxlab.progress';

export interface LessonProgress {
  quizScore?: { ok: number; total: number; at: string };
  noteScore?: { ok: number; total: number; at: string };
  noteText?: string;
  completed?: boolean;
}

export function readProgress(): Record<string, LessonProgress> {
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Record<string, LessonProgress>) : {};
  } catch {
    return {};
  }
}

export function writeProgress(slug: string, patch: Partial<LessonProgress>): Record<string, LessonProgress> {
  const all = readProgress();
  const current = { ...(all[slug] ?? {}), ...patch };
  current.completed = Boolean(current.quizScore && current.noteScore);
  all[slug] = current;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(all));
  } catch {
    /* storage unavailable: progress lives only in memory for this page */
  }
  return all;
}

/* ---------- Simulator levels (per viewer, in the browser until accounts arrive) ---------- */
const SIM_KEY = 'fxlab.sim';

export interface LevelProgress {
  score?: { ok: number; total: number; at: string };
  note?: string;
  completed?: boolean;
}

export function readSim(): Record<string, LevelProgress> {
  try {
    const raw = window.localStorage.getItem(SIM_KEY);
    return raw ? (JSON.parse(raw) as Record<string, LevelProgress>) : {};
  } catch {
    return {};
  }
}

export function writeSim(level: number, patch: Partial<LevelProgress>): Record<string, LevelProgress> {
  const all = readSim();
  const current = { ...(all[String(level)] ?? {}), ...patch };
  current.completed = Boolean(current.score && current.score.ok >= Math.ceil(current.score.total * 0.6));
  all[String(level)] = current;
  try {
    window.localStorage.setItem(SIM_KEY, JSON.stringify(all));
  } catch {
    /* storage unavailable */
  }
  return all;
}
