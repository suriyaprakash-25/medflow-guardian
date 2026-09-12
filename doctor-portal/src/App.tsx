import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Login from './pages/Login';
import Layout from './components/Layout';
import DashboardView from './pages/DashboardView';
import Patients from './pages/Patients';
import Appointments from './pages/Appointments';
import PatientDetails from './pages/PatientDetails';
import UploadReport from './pages/UploadReport';
import AccessControl from './pages/AccessControl';
import Notifications from './pages/Notifications';
import Profile from './pages/Profile';
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
          <Route path="/patients" element={<Patients />} />
          <Route path="/patient-details" element={<PatientDetails />} />
          <Route path="/upload-report" element={<UploadReport />} />
          <Route path="/access-control" element={<AccessControl />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
