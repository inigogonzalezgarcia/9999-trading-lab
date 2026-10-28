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
