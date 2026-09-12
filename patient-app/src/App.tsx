import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Login from './pages/Login';
import Layout from './components/Layout';
import DashboardView from './pages/DashboardView';
import Appointments from './pages/Appointments';
import Documents from './pages/Documents';
import AccessRequests from './pages/AccessRequests';
import AccessHistory from './pages/AccessHistory';
import Notifications from './pages/Notifications';
import Profile from './pages/Profile';
import ClinicalHistory from './pages/ClinicalHistory';
import { ensureSession } from './lib/api';
import './App.css';

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
  return <Layout />;
}

function App() {
  return (
    <Router>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardView />} />
          <Route path="/appointments" element={<Appointments />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/clinical-history" element={<ClinicalHistory />} />
          <Route path="/access-requests" element={<AccessRequests />} />
          <Route path="/access-history" element={<AccessHistory />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
