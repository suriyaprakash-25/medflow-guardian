import axios from 'axios';
import { toast } from 'react-hot-toast';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000'
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
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    } else if (error.response?.status === 403) {
      toast.error('Access denied. You do not have permission for this action.');
    }
    return Promise.reject(error);
  }
);
