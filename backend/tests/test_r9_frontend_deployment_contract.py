from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text()


def test_all_frontend_api_clients_use_shared_production_base_and_credentials():
    for app in ("patient-app", "doctor-portal", "admin-portal"):
        source = _read(f"{app}/src/lib/api.ts")
        assert "VITE_API_BASE_URL" in source
        assert "VITE_API_URL" not in source
        assert "withCredentials: true" in source


def test_realtime_clients_derive_ws_target_from_production_api_base_without_query_token():
    for app in ("patient-app", "doctor-portal"):
        source = _read(f"{app}/src/lib/websocket.ts")
        assert "VITE_API_BASE_URL" in source
        assert "target.protocol === 'https:' ? 'wss:' : 'ws:'" in source
        assert "target.pathname = '/ws'" in source
        assert "target.search = ''" in source
        assert "?token=" not in source
        assert "[WS_AUTH_PROTOCOL, token]" in source


def test_frontend_bearer_tokens_are_memory_only_and_sessions_bootstrap_from_refresh_cookie():
    for app in ("patient-app", "doctor-portal", "admin-portal"):
        api_source = _read(f"{app}/src/lib/api.ts")
        app_source = _read(f"{app}/src/App.tsx")
        login_source = _read(f"{app}/src/pages/Login.tsx")

        # Access bearer tokens live only in JS memory. The compatibility bridge
        # intercepts any remaining legacy token-key call sites and removes the
        # underlying persisted localStorage value.
        assert "accessToken: string | null" in api_source
        assert "originalRemoveItem.call(window.localStorage, 'token')" in api_source
        assert "export function setAccessToken" in api_source
        assert "export async function ensureSession" in api_source

        # A browser reload restores a short-lived access token through the
        # existing HttpOnly refresh cookie instead of persistent bearer storage.
        assert "ensureSession" in app_source
        assert "localStorage.getItem('token')" not in app_source

        # New login flows must never directly persist the bearer token.
        assert "localStorage.setItem('token'" not in login_source
        assert "setAccessToken" in login_source
