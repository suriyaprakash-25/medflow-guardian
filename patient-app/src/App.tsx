import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Layout from './components/Layout';
import DashboardView from './pages/DashboardView';
import Documents from './pages/Documents';
import AccessRequests from './pages/AccessRequests';
import AccessHistory from './pages/AccessHistory';
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
          <Route path="/documents" element={<Documents />} />
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
