import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
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
import './App.css';

import { Toaster } from 'react-hot-toast';

function ProtectedRoute() {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <Layout />;
}

function App() {
  const token = localStorage.getItem('token');
  
  return (
    <Router>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<Login />} />
        {/* Protected Layout Route */}
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
        <Route path="/" element={<Navigate to={token ? "/dashboard" : "/login"} />} />
      </Routes>
    </Router>
  );
}

export default App;
