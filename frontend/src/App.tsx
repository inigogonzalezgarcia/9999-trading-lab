import { Shell } from './components/Shell';
import { MethodPage } from './components/Method';
import { LangProvider } from './i18n';
import { HomePage } from './pages/Home';
import { LabPage } from './pages/Lab';
import { LegalPage } from './pages/Legal';
import { LessonPage, LessonsIndex } from './pages/Lessons';
import { RouterProvider, matchRoute, useRoute } from './router';
import { STATIC_MODE } from './site';

function Routes() {
  const { path } = useRoute();
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
  return <main className="prose"><h1 className="page-title">404</h1></main>;
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
