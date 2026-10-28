import { useState } from 'react';
import type { Question, RubricItem } from '../content/lessons';
import { useT } from '../i18n';

export function Quiz({ questions, onScore }: { questions: Question[]; onScore: (ok: number, total: number) => void }) {
  const { t, pick } = useT();
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [checked, setChecked] = useState(false);
  const ok = questions.filter((q) => answers[q.id] === q.answer).length;
  const check = () => { setChecked(true); onScore(ok, questions.length); };
  return (
    <section className="quiz">
      <h2>{t('quiz.title')}</h2>
      <ol className="quiz-list">
        {questions.map((q) => {
          const options = pick(q.options) ?? [];
          const chosen = answers[q.id];
          return (
            <li key={q.id} className={checked ? (chosen === q.answer ? 'correct' : 'wrong') : ''}>
              <div className="quiz-prompt">{pick(q.prompt)}</div>
              <div className="quiz-options">
                {options.map((option, index) => (
                  <label key={index} className="check">
                    <input type="radio" name={q.id} checked={chosen === index} disabled={checked} onChange={() => setAnswers({ ...answers, [q.id]: index })} /> {option}
                  </label>
                ))}
              </div>
              {checked && <div className="small quiz-explain">{chosen === q.answer ? '✓ ' : '✗ '}{pick(q.explanation)}</div>}
            </li>
          );
        })}
      </ol>
      {!checked ? (
        <button type="button" disabled={Object.keys(answers).length < questions.length} onClick={check}>{t('quiz.check')}</button>
      ) : (
        <div className="row-actions">
          <strong>{t('quiz.score', { ok, n: questions.length })}</strong>
          <button type="button" className="ghost" onClick={() => { setChecked(false); setAnswers({}); }}>{t('quiz.retry')}</button>
        </div>
      )}
    </section>
  );
}

export function gradeNote(text: string, rubric: RubricItem[], lang: 'es' | 'en'): { id: string; found: boolean }[] {
  const haystack = text.toLowerCase();
  return rubric.map((item) => ({ id: item.id, found: item.keywords[lang].some((kw) => haystack.includes(kw.toLowerCase())) || item.keywords[lang === 'es' ? 'en' : 'es'].some((kw) => haystack.includes(kw.toLowerCase())) }));
}

export function LabNote({ prompt, rubric, example, initial, onScore }: { prompt: string; rubric: RubricItem[]; example: string; initial?: string; onScore: (text: string, ok: number, total: number) => void }) {
  const { t, pick, lang } = useT();
  const [text, setText] = useState(initial ?? '');
  const [result, setResult] = useState<{ id: string; found: boolean }[] | null>(null);
  const [showExample, setShowExample] = useState(false);
  const grade = () => {
    const graded = gradeNote(text, rubric, lang);
    setResult(graded);
    onScore(text, graded.filter((g) => g.found).length, rubric.length);
  };
  return (
    <section className="labnote">
      <h2>{t('note.title')}</h2>
      <p className="muted small">{t('note.lead')}</p>
      <p>{prompt}</p>
      <textarea rows={8} value={text} placeholder={t('note.placeholder')} onChange={(e) => { setText(e.target.value); setResult(null); }} />
      <div className="row-actions">
        <button type="button" disabled={text.trim().length < 40} onClick={grade}>{t('note.grade')}</button>
        <button type="button" className="ghost" onClick={() => setShowExample(!showExample)}>{t('note.example')}</button>
        {result && <strong>{t('note.result', { ok: result.filter((r) => r.found).length, n: rubric.length })}</strong>}
      </div>
      {result && (
        <ul className="rubric">
          {rubric.map((item) => {
            const found = result.find((r) => r.id === item.id)?.found;
            return <li key={item.id} className={found ? 'found' : 'missing'}>{found ? '✓' : '○'} {pick(item.label)} <span className="muted small">— {found ? t('note.found') : t('note.missing')}</span></li>;
          })}
        </ul>
      )}
      {showExample && <blockquote className="example">{example}</blockquote>}
    </section>
  );
}
