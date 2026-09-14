import { lazy, Suspense, useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { ensureSession } from './lib/api';

const Login = lazy(() => import('./pages/Login'));
const Layout = lazy(() => import('./components/Layout'));
const DashboardView = lazy(() => import('./pages/DashboardView'));
const Appointments = lazy(() => import('./pages/Appointments'));
const Documents = lazy(() => import('./pages/Documents'));
const AccessRequests = lazy(() => import('./pages/AccessRequests'));
const AccessHistory = lazy(() => import('./pages/AccessHistory'));
const Notifications = lazy(() => import('./pages/Notifications'));
const Profile = lazy(() => import('./pages/Profile'));
const ClinicalHistory = lazy(() => import('./pages/ClinicalHistory'));
const Consents = lazy(() => import('./pages/Consents'));

function LoadingState({ message }: { message: string }) {
  return (
    <main className="grid min-h-screen place-items-center p-6">
      <div className="w-full max-w-md">
        <FeedbackState tone="loading" title="Loading MedFlow" message={message} />
      </div>
    </main>
  );
}

function ProtectedRoute() {
  const [authorized, setAuthorized] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    ensureSession().then((ok) => { if (active) setAuthorized(ok); });
    return () => { active = false; };
  }, []);

  if (authorized === null) {
    return <LoadingState message="Checking your authenticated patient session." />;
  }
  if (!authorized) return <Navigate to="/login" replace />;
  return <Layout />;
}

function App() {
  return (
    <Router>
      <Toaster position="top-right" toastOptions={{ duration: 4500 }} />
      <Suspense fallback={<LoadingState message="Loading the requested patient workspace." />}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<DashboardView />} />
            <Route path="/appointments" element={<Appointments />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/clinical-history" element={<ClinicalHistory />} />
            <Route path="/access-requests" element={<AccessRequests />} />
            <Route path="/access-history" element={<AccessHistory />} />
            <Route path="/consents" element={<Consents />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/profile" element={<Profile />} />
          </Route>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </Router>
  );
}

export default App;
