import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

import ai.routes.fraud_routes as fraud_routes
import ai.routes.safety_routes as safety_routes
from ai.main import app as ai_app
from app.api.dependencies import get_current_active_user
from app.core.config import settings


client = TestClient(ai_app)


@pytest.fixture(autouse=True)
def _clear_ai_dependency_overrides():
    ai_app.dependency_overrides.clear()
    yield
    ai_app.dependency_overrides.clear()


def _authenticate_ai_client():
    ai_app.dependency_overrides[get_current_active_user] = lambda: object()


def test_ai_health_remains_public_but_clinical_routes_require_authentication():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    safety = client.post(
        "/ai/safety-check",
        json={
            "patientId": "P001",
            "allergies": [],
            "currentMedications": [],
            "newPrescription": [],
        },
    )
    fraud = client.post("/ai/fraud-check", json={"patientId": "P001"})

    assert safety.status_code == 401
    assert fraud.status_code == 401


def test_ai_cors_uses_explicit_medflow_allowlist():
    allowed_origin = settings.FRONTEND_CORS_ORIGINS[0]
    allowed = client.options(
        "/ai/safety-check",
        headers={
            "Origin": allowed_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers.get("access-control-allow-origin") == allowed_origin

    blocked = client.options(
        "/ai/safety-check",
        headers={
            "Origin": "https://attacker.invalid",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert blocked.headers.get("access-control-allow-origin") is None


def test_authenticated_ai_routes_still_execute_normally():
    _authenticate_ai_client()

    safety = client.post(
        "/ai/safety-check",
        json={
            "patientId": "P001",
            "allergies": [],
            "currentMedications": ["Atorvastatin"],
            "newPrescription": ["Metoprolol"],
        },
    )
    fraud = client.post("/ai/fraud-check", json={"patientId": "P001"})

    assert safety.status_code == 200
    assert safety.json()["safetyScore"] == 100
    assert fraud.status_code == 200
    assert fraud.json()["overallRisk"] == "Low"


def test_ai_internal_exceptions_are_logged_but_not_reflected_to_clients(monkeypatch):
    _authenticate_ai_client()

    def safety_failure(_request):
        raise RuntimeError("postgresql://secret-user:secret-password@internal-db/patient")

    def fraud_failure(_patient_id):
        raise RuntimeError("private fraud model path /srv/models/internal.bin")

    monkeypatch.setattr(safety_routes, "run_safety_checks", safety_failure)
    monkeypatch.setattr(fraud_routes, "run_fraud_checks", fraud_failure)

    safety = client.post(
        "/ai/safety-check",
        json={
            "patientId": "P001",
            "allergies": [],
            "currentMedications": [],
            "newPrescription": [],
        },
    )
    fraud = client.post("/ai/fraud-check", json={"patientId": "P001"})

    assert safety.status_code == 500
    assert safety.json() == {"detail": "Clinical safety evaluation failed"}
    assert "secret-password" not in safety.text

    assert fraud.status_code == 500
    assert fraud.json() == {"detail": "Fraud indicator evaluation failed"}
    assert "/srv/models" not in fraud.text


def test_development_config_generates_secret_key_when_env_key_is_absent():
    backend_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.pop("SECRET_KEY", None)
    env.update(
        {
            "ENV": "test",
            "DATABASE_URL": "postgresql://medflow:password@localhost/medflow_test",
            "SUPABASE_URL": "http://localhost:8000",
            "SUPABASE_SERVICE_ROLE_KEY": "dummy_key",
            "SUPABASE_STORAGE_BUCKET": "medflow-bucket",
        }
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.core.config import settings; print('generated=' + str(bool(settings.SECRET_KEY)))",
        ],
        cwd=backend_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "generated=True" in completed.stdout
