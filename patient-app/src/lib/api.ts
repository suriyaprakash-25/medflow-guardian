import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const TOKEN_BRIDGE_KEY = '__medflowPatientAccessTokenBridge';

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

  // Remove any bearer token left by an older deployment before installing the
  // compatibility bridge. Legacy call sites may still read/write the `token`
  // key, but those operations are redirected to memory and never persisted.
  state.originalRemoveItem.call(window.localStorage, 'token');

  Storage.prototype.getItem = function (key: string): string | null {
    if (this === window.localStorage && key === 'token') {
      return state.accessToken;
    }
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
  headers: { 'Content-Type': 'application/json' },
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

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

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
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }

    if (error.response) {
      const { status, data } = error.response;
      return Promise.reject({
        status,
        message: data?.detail || 'An unexpected error occurred.',
        originalError: error,
      });
    }
    if (error.request) {
      return Promise.reject({
        status: 0,
        message: 'Network error. Please check your connection.',
        originalError: error,
      });
    }
    return Promise.reject({
      status: 500,
      message: error.message || 'An unexpected error occurred.',
      originalError: error,
    });
  },
);

// Install the compatibility bridge immediately so no legacy component can
// persist a bearer token before the first API request is made.
tokenBridge();
