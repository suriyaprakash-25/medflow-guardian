import { lazy, Suspense, useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { ensureSession } from './lib/api';

const Layout = lazy(() => import('./components/Layout'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Login = lazy(() => import('./pages/Login'));
const Staff = lazy(() => import('./pages/Staff'));
const Audit = lazy(() => import('./pages/Audit'));
const Settings = lazy(() => import('./pages/Settings'));
const Organizations = lazy(() => import('./pages/Organizations'));

function ProtectedRoute() {
  const [authorized, setAuthorized] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    ensureSession().then((ok) => {
      if (active) setAuthorized(ok);
    });
    return () => {
      active = false;
    };
  }, []);

  if (authorized === null) return null;
  if (!authorized) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function RouteLoading() {
  return (
    <main className="grid min-h-screen place-items-center p-6" aria-live="polite">
      <div role="status" className="text-sm text-slate-600">Loading MedFlow administration…</div>
    </main>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Suspense fallback={<RouteLoading />}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/organizations" element={<Organizations />} />
              <Route path="/staff" element={<Staff />} />
              <Route path="/audit" element={<Audit />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
