import axios from 'axios';
import { toast } from 'react-hot-toast';

// Keep all three frontends on one deployment contract. Render injects this
// build-time value for production; local development still defaults to :8000.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  response => response,
  error => {
    // Suppress repeated network errors or handle them gracefully
    if (!error.response) {
      if (error.code === 'ERR_NETWORK') {
        toast.error('Network Error: Cannot connect to the server. Check your backend status.', { id: 'network-error' });
      }
      return Promise.reject(error);
    }
    
    if (error.response.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    } else if (error.response.status === 403) {
      toast.error('Access denied. You do not have permission for this action.', { id: 'auth-error' });
    } else if (error.response.status >= 500) {
      toast.error('Server error occurred while processing your request.', { id: 'server-error' });
    }
    return Promise.reject(error);
  }
);
