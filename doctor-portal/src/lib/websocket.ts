const WS_AUTH_PROTOCOL = 'medflow.jwt';

export function createAuthenticatedWebSocket(token: string): WebSocket {
  if (!token) {
    throw new Error('An access token is required to open the realtime connection.');
  }

  const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim();
  const target = new URL(configuredBase || window.location.origin, window.location.origin);
  target.protocol = target.protocol === 'https:' ? 'wss:' : 'ws:';
  target.pathname = '/ws';
  target.search = '';
  target.hash = '';

  // Browser WebSocket APIs cannot set an Authorization header. The backend
  // accepts the JWT as a secondary subprotocol and echoes only medflow.jwt, so
  // the bearer token is not placed in the request URL or normal access logs.
  return new WebSocket(target.toString(), [WS_AUTH_PROTOCOL, token]);
}
