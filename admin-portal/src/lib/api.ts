import axios from 'axios';
import { toast } from 'react-hot-toast';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_BRIDGE_KEY = '__medflowAdminAccessTokenBridge';

type TokenBridgeState = {
  accessToken: string | null;
  originalGetItem: Storage['getItem'];
  originalSetItem: Storage['setItem'];
  originalRemoveItem: Storage['removeItem'];
};

function tokenBridge(): TokenBridgeState {
  const root = globalThis as any;
  if (root[TOKEN_BRIDGE_KEY]) return root[TOKEN_BRIDGE_KEY] as TokenBridgeState;

  const state: TokenBridgeState = {
    accessToken: null,
    originalGetItem: Storage.prototype.getItem,
    originalSetItem: Storage.prototype.setItem,
    originalRemoveItem: Storage.prototype.removeItem,
  };
  root[TOKEN_BRIDGE_KEY] = state;

  state.originalRemoveItem.call(window.localStorage, 'token');

  Storage.prototype.getItem = function (key: string): string | null {
    if (this === window.localStorage && key === 'token') return state.accessToken;
    return state.originalGetItem.call(this, key);
  };

  Storage.prototype.setItem = function (key: string, value: string): void {
    if (this === window.localStorage && key === 'token') {
      state.accessToken = value;
      state.originalRemoveItem.call(this, 'token');
      return;
    }
    state.originalSetItem.call(this, key, value);
  };

  Storage.prototype.removeItem = function (key: string): void {
    if (this === window.localStorage && key === 'token') {
      state.accessToken = null;
      state.originalRemoveItem.call(this, 'token');
      return;
    }
    state.originalRemoveItem.call(this, key);
  };

  return state;
}

export function getAccessToken(): string | null {
  return tokenBridge().accessToken;
}

export function setAccessToken(token: string): void {
  const state = tokenBridge();
  state.accessToken = token;
  state.originalRemoveItem.call(window.localStorage, 'token');
}

export function clearAccessToken(): void {
  const state = tokenBridge();
  state.accessToken = null;
  state.originalRemoveItem.call(window.localStorage, 'token');
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

let refreshPromise: Promise<string> | null = null;

export async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = axios
    .post(`${API_BASE_URL}/api/auth/refresh`, {}, { withCredentials: true })
    .then(({ data }) => {
      if (typeof data?.access_token !== 'string' || !data.access_token) {
        throw new Error('Refresh response did not include an access token');
      }
      setAccessToken(data.access_token);
      return data.access_token as string;
    })
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

export async function ensureSession(): Promise<boolean> {
  if (getAccessToken()) return true;
  try {
    await refreshAccessToken();
    return true;
  } catch {
    clearAccessToken();
    return false;
  }
}

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      const url = String(originalRequest.url || '');
      if (
        url.includes('/auth/refresh') ||
        url.includes('/auth/login') ||
        url.includes('/auth/mfa/verify')
      ) {
        return Promise.reject(error);
      }

      originalRequest._retry = true;
      try {
        const token = await refreshAccessToken();
        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      } catch (refreshError) {
        clearAccessToken();
        localStorage.removeItem('user');
        if (window.location.pathname !== '/login') window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    if (!error.response) {
      if (error.code === 'ERR_NETWORK') {
        toast.error(
          'Network Error: Cannot connect to the server. Check your backend status.',
          { id: 'network-error' },
        );
      }
      return Promise.reject(error);
    }

    if (error.response.status === 403) {
      toast.error('Access denied. You do not have permission for this action.', {
        id: 'auth-error',
      });
    } else if (error.response.status >= 500) {
      toast.error('Server error occurred while processing your request.', {
        id: 'server-error',
      });
    }
    return Promise.reject(error);
  },
);

tokenBridge();
