import { Shell } from './components/Shell';
import { MethodPage } from './components/Method';
import { LangProvider } from './i18n';
import { HomePage } from './pages/Home';
import { LabPage } from './pages/Lab';
import { LegalPage } from './pages/Legal';
import { LessonPage, LessonsIndex } from './pages/Lessons';
import { RouterProvider, matchRoute, useRoute } from './router';
import { useSeo } from './seo';
import { useT } from './i18n';
import { STATIC_MODE } from './site';

function Routes() {
  const { path } = useRoute();
  const { lang } = useT();
  useSeo(path, lang);
  const lab = matchRoute('/lab/:runId', path);
  const lesson = matchRoute('/lessons/:slug', path);
  const legal = matchRoute('/legal/:slug', path);
  // The local research tool opens on the lab; the public site opens on the landing page.
  if (path === '/' && !STATIC_MODE) return <LabPage />;
  if (path === '/') return <HomePage />;
  if (path === '/lab') return <LabPage />;
  if (lab) return <LabPage runId={lab.runId} />;
  if (path === '/lessons') return <LessonsIndex />;
  if (lesson) return <LessonPage slug={lesson.slug} />;
  if (path === '/method') return <main className="prose"><MethodPage /></main>;
  if (legal) return <LegalPage slug={legal.slug} />;
  return <NotFound />;
}

function NotFound() {
  const { lang } = useT();
  const es = lang === 'es';
  return (
    <main className="prose">
      <p className="kicker">404</p>
      <h1 className="page-title">{es ? 'Esta página no existe' : 'This page does not exist'}</h1>
      <p className="muted">{es ? 'Puede que el enlace sea antiguo. Esto es lo que hay:' : 'The link may be old. Here is what exists:'}</p>
      <ul>
        <li><a href="/">{es ? 'Inicio' : 'Home'}</a></li>
        <li><a href="/lab">{es ? 'Laboratorio (24 ejecuciones reales 2019–2025)' : 'Lab (24 real runs 2019–2025)'}</a></li>
        <li><a href="/lessons">{es ? 'Lecciones gratis' : 'Free lessons'}</a></li>
        <li><a href="/method">{es ? 'Método y aviso' : 'Method and notice'}</a></li>
      </ul>
    </main>
  );
}

export default function App() {
  return (
    <LangProvider>
      <RouterProvider>
        <Shell>
          <Routes />
        </Shell>
      </RouterProvider>
    </LangProvider>
  );
}
