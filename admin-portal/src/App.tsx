import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Staff from './pages/Staff';
import Audit from './pages/Audit';

function ProtectedRoute() {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/staff" element={<Staff />} />
            <Route path="/audit" element={<Audit />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
