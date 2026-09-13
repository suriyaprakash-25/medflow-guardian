from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_admin_local_origin_is_present_in_default_backend_cors_allowlist():
    source = (ROOT / "backend" / "app" / "core" / "config.py").read_text()

    assert "http://localhost:5176" in source
    assert "http://127.0.0.1:5176" in source


def test_env_example_uses_active_cors_setting_and_includes_admin_portal():
    example = (ROOT / "backend" / ".env.example").read_text()

    assert "FRONTEND_CORS_ORIGINS=" in example
    assert "http://localhost:5176" in example
    assert "\nCORS_ORIGINS=" not in example
