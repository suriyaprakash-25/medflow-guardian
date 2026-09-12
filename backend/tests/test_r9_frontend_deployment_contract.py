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
