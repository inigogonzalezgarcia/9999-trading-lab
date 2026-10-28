import { useEffect, useState } from 'react';
import { LessonWidget } from '../components/LessonWidgets';
import { LabNote, Quiz } from '../components/Quiz';
import { Subscribe } from '../components/Subscribe';
import { LESSONS, UPCOMING } from '../content/lessons';
import { useT } from '../i18n';
import { readProgress, writeProgress, type LessonProgress } from '../progress';
import { Link, useRoute } from '../router';

export function LessonsIndex() {
  const { t, pick } = useT();
  const [progress, setProgress] = useState<Record<string, LessonProgress>>({});
  useEffect(() => setProgress(readProgress()), []);
  return (
    <main className="prose">
      <h1 className="page-title">{t('lessons.title')}</h1>
      <p className="lead">{t('lessons.lead')}</p>
      <ol className="lesson-cards">
        {LESSONS.map((lesson) => {
          const p = progress[lesson.slug];
          return (
            <li key={lesson.slug} className="lesson-card">
              <div className="lesson-meta"><span className="badge soft">{t('lessons.free')}</span><span className="muted small">{t('lessons.minutes', { n: lesson.minutes })}</span>{p?.completed && <span className="good small">✓ {t('lessons.done')}</span>}</div>
              <h2>{lesson.order}. {pick(lesson.title)}</h2>
              <p className="muted">{pick(lesson.summary)}</p>
              <Link to={`/lessons/${lesson.slug}`} className="button">{p?.completed ? t('lessons.review') : t('lessons.start')}</Link>
            </li>
          );
        })}
        {UPCOMING.map((item, index) => (
          <li key={index} className="lesson-card upcoming">
            <div className="lesson-meta"><span className="badge soft">{t('lessons.soon')}</span></div>
            <h2>{LESSONS.length + index + 1}. {pick(item.title)}</h2>
            <p className="muted">{pick(item.summary)}</p>
          </li>
        ))}
      </ol>
      <Subscribe />
    </main>
  );
}

export function LessonPage({ slug }: { slug: string }) {
  const { t, pick, lang } = useT();
  const { navigate } = useRoute();
  const lesson = LESSONS.find((item) => item.slug === slug);
  const [progress, setProgress] = useState<LessonProgress>({});
  useEffect(() => { setProgress(readProgress()[slug] ?? {}); }, [slug]);
  if (!lesson) {
    return <main className="prose"><p className="muted">404</p><Link to="/lessons">{t('lessons.back')}</Link></main>;
  }
  const next = LESSONS.find((item) => item.order === lesson.order + 1);
  return (
    <main className="prose lesson">
      <p className="small"><Link to="/lessons">← {t('lessons.back')}</Link></p>
      <div className="lesson-meta"><span className="badge soft">{t('lessons.free')}</span><span className="muted small">{t('lessons.minutes', { n: lesson.minutes })}</span></div>
      <h1 className="page-title">{lesson.order}. {pick(lesson.title)}</h1>
      <p className="lead">{pick(lesson.summary)}</p>
      {lesson.sections.map((section, index) => (
        <section key={index} className="lesson-section">
          <h2>{pick(section.heading)}</h2>
          {(pick(section.paragraphs) ?? []).map((paragraph, i) => <p key={i}>{paragraph}</p>)}
          {section.widget && <LessonWidget widget={section.widget} />}
          {section.callout && <aside className="notice">{pick(section.callout)}</aside>}
        </section>
      ))}
      <Quiz questions={lesson.quiz} onScore={(ok, total) => setProgress(writeProgress(slug, { quizScore: { ok, total, at: new Date().toISOString() } })[slug])} />
      <LabNote
        prompt={pick(lesson.labNote.prompt) ?? ''}
        rubric={lesson.labNote.rubric}
        example={lesson.labNote.example[lang]}
        initial={progress.noteText}
        onScore={(text, ok, total) => setProgress(writeProgress(slug, { noteText: text, noteScore: { ok, total, at: new Date().toISOString() } })[slug])}
      />
      <div className="row-actions lesson-nav">
        {progress.completed && <span className="good">✓ {t('lessons.done')}</span>}
        {next ? <button type="button" onClick={() => navigate(`/lessons/${next.slug}`)}>{t('lessons.next')}: {pick(next.title)} →</button> : <Link to="/lessons" className="button">{t('lessons.back')}</Link>}
      </div>
      {!next && <Subscribe />}
    </main>
  );
}
