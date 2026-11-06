import { useEffect, type ReactNode } from 'react';
import { AuthProvider, useAuth } from './auth';
import { Shell } from './components/Shell';
import { MethodPage } from './components/Method';
import { LangProvider } from './i18n';
import { AccountPage } from './pages/Account';
import { DashboardPage } from './pages/Dashboard';
import { HomePage } from './pages/Home';
import { PlansPage } from './pages/Plans';
import { SimPage } from './pages/Sim';
import { TourPage } from './pages/Tour';
import { LabPage } from './pages/Lab';
import { LegalPage } from './pages/Legal';
import { LoginPage } from './pages/Login';
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
  const sim = matchRoute('/app/sim/:n', path);
  // The local research tool opens on the lab; the public site opens on the landing page.
  if (path === '/' && !STATIC_MODE) return <LabPage />;
  if (path === '/') return <HomePage />;
  if (path === '/lab') return <LabPage />;
  if (lab) return <LabPage runId={lab.runId} />;
  if (path === '/lessons') return <LessonsIndex />;
  if (lesson) return <LessonPage slug={lesson.slug} />;
  if (path === '/tour') return <TourPage />;
  if (path === '/planes' || path === '/plans') return <PlansPage />;
  if (path === '/entrar' || path === '/login') return <LoginPage />;
  if (path === '/app') return <RequireAccount path={path}><DashboardPage /></RequireAccount>;
  if (path === '/app/cuenta' || path === '/app/account') return <RequireAccount path={path}><AccountPage /></RequireAccount>;
  if (sim) return <RequireAccount path={path}><SimPage n={sim.n} /></RequireAccount>;
  if (path === '/method') return <main className="prose"><MethodPage /></main>;
  if (legal) return <LegalPage slug={legal.slug} />;
  return <NotFound />;
}

/** The protected area: with an account backend configured, a session is required; without one (local dev) it opens. */
function RequireAccount({ path, children }: { path: string; children: ReactNode }) {
  const { ready, configured, user } = useAuth();
  const { navigate } = useRoute();
  const { lang } = useT();
  const mustLogin = ready && configured && !user;
  useEffect(() => { if (mustLogin) navigate(`/entrar?next=${encodeURIComponent(path)}`); }, [mustLogin, path, navigate]);
  if (!ready) return <main className="prose"><p className="muted">{lang === 'es' ? 'Comprobando tu sesión…' : 'Checking your session…'}</p></main>;
  if (mustLogin) return null;
  return <>{children}</>;
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
        <li><a href="/lab">{es ? 'Laboratorio (27 ejecuciones reales 2019–2026)' : 'Lab (27 real runs 2019–2026)'}</a></li>
        <li><a href="/app">{es ? 'Simulador (niveles 0–2 gratis)' : 'Simulator (levels 0–2 free)'}</a></li>
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
        <AuthProvider>
          <Shell>
            <Routes />
          </Shell>
        </AuthProvider>
      </RouterProvider>
    </LangProvider>
  );
}
