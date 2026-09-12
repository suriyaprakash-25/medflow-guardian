from pathlib import Path

import pytest
import yaml

from app.core.config import _parse_cors_origins


ROOT = Path(__file__).resolve().parents[2]


def _services_by_name():
    blueprint = yaml.safe_load((ROOT / "render.yaml").read_text())
    return {service["name"]: service for service in blueprint["services"]}


def _env_by_key(service):
    return {
        entry["key"]: entry
        for entry in service.get("envVars", [])
        if "key" in entry
    }


def test_production_blueprint_gates_deploys_and_runs_migrations_predeploy():
    services = _services_by_name()
    backend = services["medflow-backend-prod"]

    assert backend["runtime"] == "python"
    assert backend["autoDeployTrigger"] == "checksPass"
    assert "alembic upgrade head" not in backend["buildCommand"]
    assert backend["preDeployCommand"] == "cd backend && alembic upgrade head"
    assert backend["healthCheckPath"] == "/ready"

    env = _env_by_key(backend)
    for key in {
        "DATABASE_URL",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "ENCRYPTION_KEY",
        "TRUSTED_PROXY_CIDRS",
        "FRONTEND_CORS_ORIGINS",
    }:
        assert env[key]["sync"] is False
    assert env["SECRET_KEY"]["generateValue"] is True


def test_static_frontends_use_backend_url_and_spa_rewrite():
    services = _services_by_name()
    for name in {
        "medflow-patient-app-prod",
        "medflow-doctor-portal-prod",
        "medflow-admin-portal-prod",
    }:
        service = services[name]
        assert service["runtime"] == "static"
        assert service["autoDeployTrigger"] == "checksPass"
        assert service["routes"] == [
            {"type": "rewrite", "source": "/*", "destination": "/index.html"}
        ]

        api_url = _env_by_key(service)["VITE_API_BASE_URL"]["fromService"]
        assert api_url == {
            "type": "web",
            "name": "medflow-backend-prod",
            "envVarKey": "RENDER_EXTERNAL_URL",
        }


def test_backend_cors_origins_are_wired_from_all_frontends():
    backend = _services_by_name()["medflow-backend-prod"]
    env = _env_by_key(backend)
    expected = {
        "PATIENT_APP_ORIGIN": "medflow-patient-app-prod",
        "DOCTOR_PORTAL_ORIGIN": "medflow-doctor-portal-prod",
        "ADMIN_PORTAL_ORIGIN": "medflow-admin-portal-prod",
    }
    for key, service_name in expected.items():
        assert env[key]["fromService"] == {
            "type": "web",
            "name": service_name,
            "envVarKey": "RENDER_EXTERNAL_URL",
        }


def test_cors_parser_rejects_wildcards_and_non_origin_urls():
    assert _parse_cors_origins([
        "https://patient.example.com, https://doctor.example.com/",
        "https://patient.example.com",
    ]) == [
        "https://patient.example.com",
        "https://doctor.example.com",
    ]

    with pytest.raises(ValueError, match="Wildcard"):
        _parse_cors_origins(["*"])

    with pytest.raises(ValueError, match="path/query/fragment"):
        _parse_cors_origins(["https://patient.example.com/dashboard"])

    with pytest.raises(ValueError, match="Invalid CORS origin"):
        _parse_cors_origins(["patient.example.com"])
