import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Layout from './components/Layout';
import DashboardView from './pages/DashboardView';
import Patients from './pages/Patients';
import PatientDetails from './pages/PatientDetails';
import UploadReport from './pages/UploadReport';
import AccessControl from './pages/AccessControl';
import Notifications from './pages/Notifications';
import Profile from './pages/Profile';
import './App.css';

function App() {
  const token = localStorage.getItem('token');
  
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        {/* Layout Route */}
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<DashboardView />} />
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
