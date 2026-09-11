import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
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
          <Route path="/patients" element={<Patients />} />
          <Route path="/patient-details" element={<PatientDetails />} />
          <Route path="/upload-report" element={<UploadReport />} />
          <Route path="/access-control" element={<AccessControl />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
        <Route path="/" element={<Navigate to={token ? "/dashboard" : "/login"} />} />
      </Routes>
    </Router>
  );
}

export default App;
