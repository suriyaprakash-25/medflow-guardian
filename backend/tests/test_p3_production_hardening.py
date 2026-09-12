import json
import logging
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core.config import _parse_trusted_proxy_cidrs, settings
from app.core.logging import JSONFormatter
from app.main import app


ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
client = TestClient(app)


def _production_subprocess_env(*, role: str) -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "PATIENT_APP_ORIGIN",
        "DOCTOR_PORTAL_ORIGIN",
        "ADMIN_PORTAL_ORIGIN",
        "FRONTEND_CORS_ORIGINS",
        "SECRET_KEY",
        "ENCRYPTION_KEY",
    ):
        env.pop(key, None)

    env.update(
        {
            "ENV": "production",
            "MEDFLOW_SERVICE_ROLE": role,
            "DATABASE_URL": "postgresql://medflow:password@localhost/medflow_prod",
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "dummy-service-role-key",
            "SUPABASE_STORAGE_BUCKET": "medical-documents",
            "CLAMAV_HOST": "127.0.0.1",
            "CLAMAV_PORT": "3310",
            "TRUSTED_PROXY_CIDRS": "",
        }
    )
    return env


def test_backend_security_headers_are_non_cacheable_and_privacy_preserving(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "production")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == (
        "camera=(), microphone=(), geolocation=()"
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-xss-protection"] == "0"
    assert response.headers["x-permitted-cross-domain-policies"] == "none"
    assert "max-age=31536000" in response.headers["strict-transport-security"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_backend_cors_rejects_unneeded_methods_and_headers():
    origin = settings.FRONTEND_CORS_ORIGINS[0]

    allowed = client.options(
        "/api/auth/me",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == origin

    bad_method = client.options(
        "/api/auth/me",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "TRACE",
        },
    )
    assert bad_method.status_code == 400

    bad_header = client.options(
        "/api/auth/me",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Untrusted-Header",
        },
    )
    assert bad_header.status_code == 400


def test_production_web_disables_interactive_api_documentation():
    env = _production_subprocess_env(role="web")
    env.update(
        {
            "SECRET_KEY": "production-test-secret",
            "ENCRYPTION_KEY": Fernet.generate_key().decode(),
            "PATIENT_APP_ORIGIN": "https://patient.example.com",
        }
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.main import app; "
                "assert app.docs_url is None; "
                "assert app.redoc_url is None; "
                "assert app.openapi_url is None; "
                "print('docs-disabled')"
            ),
        ],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "docs-disabled" in completed.stdout


def test_production_worker_does_not_require_web_only_secrets_or_cors():
    env = _production_subprocess_env(role="malware_worker")

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.core.config import settings; "
                "assert settings.SERVICE_ROLE == 'malware_worker'; "
                "assert settings.FRONTEND_CORS_ORIGINS == []; "
                "assert bool(settings.SECRET_KEY); "
                "assert bool(settings.ENCRYPTION_KEY); "
                "print('worker-config-ok')"
            ),
        ],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "worker-config-ok" in completed.stdout


def test_trusted_proxy_configuration_rejects_invalid_or_catch_all_networks():
    assert _parse_trusted_proxy_cidrs(
        "10.0.0.8/8, 192.168.10.4/24, 10.0.0.0/8"
    ) == ["10.0.0.0/8", "192.168.10.0/24"]

    with pytest.raises(ValueError, match="Invalid TRUSTED_PROXY_CIDRS"):
        _parse_trusted_proxy_cidrs("not-a-network")

    with pytest.raises(ValueError, match="catch-all"):
        _parse_trusted_proxy_cidrs("0.0.0.0/0")

    with pytest.raises(ValueError, match="catch-all"):
        _parse_trusted_proxy_cidrs("::/0")


def test_structured_logging_recursively_redacts_secret_metadata():
    record = logging.LogRecord(
        name="medflow",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="security event",
        args=(),
        exc_info=None,
    )
    record.authorization = "Bearer top-secret"
    record.context = {
        "patient_id": 42,
        "refresh_token": "refresh-secret",
        "nested": {
            "password": "password-secret",
            "api-key": "api-secret",
            "safe": "retained",
        },
    }

    payload = json.loads(JSONFormatter().format(record))

    assert payload["authorization"] == "***REDACTED***"
    assert payload["context"]["refresh_token"] == "***REDACTED***"
    assert payload["context"]["nested"]["password"] == "***REDACTED***"
    assert payload["context"]["nested"]["api-key"] == "***REDACTED***"
    assert payload["context"]["nested"]["safe"] == "retained"
    serialized = json.dumps(payload)
    assert "top-secret" not in serialized
    assert "refresh-secret" not in serialized
    assert "password-secret" not in serialized
    assert "api-secret" not in serialized


def test_render_blueprint_deploys_durable_malware_worker_and_required_scanner_config():
    blueprint = yaml.safe_load((ROOT / "render.yaml").read_text())
    services = {service["name"]: service for service in blueprint["services"]}

    backend = services["medflow-backend-prod"]
    backend_env = {entry["key"]: entry for entry in backend["envVars"]}
    assert backend_env["MEDFLOW_SERVICE_ROLE"]["value"] == "web"
    assert backend_env["CLAMAV_HOST"]["sync"] is False
    assert backend_env["CLAMAV_PORT"]["value"] == "3310"
    assert "--no-server-header" in backend["startCommand"]

    worker = services["medflow-malware-worker-prod"]
    worker_env = {entry["key"]: entry for entry in worker["envVars"]}
    assert worker["type"] == "worker"
    assert worker["runtime"] == "python"
    assert worker["autoDeployTrigger"] == "checksPass"
    assert worker["startCommand"] == "cd backend && python -m app.workers.malware_worker"
    assert worker_env["MEDFLOW_SERVICE_ROLE"]["value"] == "malware_worker"
    for key in {
        "DATABASE_URL",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "CLAMAV_HOST",
    }:
        assert worker_env[key]["sync"] is False


def test_render_static_frontends_define_security_headers():
    blueprint = yaml.safe_load((ROOT / "render.yaml").read_text())
    services = {service["name"]: service for service in blueprint["services"]}

    required = {
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
        "Content-Security-Policy",
    }
    for name in {
        "medflow-patient-app-prod",
        "medflow-doctor-portal-prod",
        "medflow-admin-portal-prod",
    }:
        service = services[name]
        global_headers = {
            entry["name"]: entry["value"]
            for entry in service["headers"]
            if entry["path"] == "/*"
        }
        assert required <= global_headers.keys()
        assert global_headers["X-Frame-Options"] == "DENY"
        assert "frame-ancestors 'none'" in global_headers["Content-Security-Policy"]

        asset_cache = [
            entry
            for entry in service["headers"]
            if entry["path"] == "/assets/*" and entry["name"] == "Cache-Control"
        ]
        assert asset_cache == [
            {
                "path": "/assets/*",
                "name": "Cache-Control",
                "value": "public, max-age=31536000, immutable",
            }
        ]


def test_ci_uses_pinned_modern_actions_and_least_privilege_checkout():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

    assert "permissions:\n  contents: read" in workflow
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in workflow
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97" in workflow
    assert "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020" in workflow
    assert workflow.count("persist-credentials: false") == 2
    assert "Run P3 production hardening verification" in workflow


def test_dependabot_covers_backend_frontends_and_github_actions():
    config = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text())
    updates = config["updates"]
    configured = {
        (entry["package-ecosystem"], entry["directory"])
        for entry in updates
    }
    assert {
        ("pip", "/backend"),
        ("npm", "/patient-app"),
        ("npm", "/doctor-portal"),
        ("npm", "/admin-portal"),
        ("npm", "/frontend-shared"),
        ("github-actions", "/"),
    } <= configured
