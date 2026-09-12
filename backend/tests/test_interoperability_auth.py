import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.main import app
from app.models.user import User


@pytest.fixture
def client():
    return TestClient(app)


def test_patient_can_export_own_fhir(client, db_session):
    patient = User(
        id=100,
        email="p100@example.com",
        hashed_password="hash",
        role="patient",
        full_name="Patient",
        is_active=True,
    )
    db_session.add(patient)
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: patient
    try:
        response = client.get(
            f"/api/interoperability/patients/{patient.id}/export?purpose=PATIENT_REQUEST"
        )
        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "collection"
        assert len(bundle["entry"]) >= 1
        assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"
    finally:
        app.dependency_overrides.clear()


def test_fhir_export_requires_explicit_purpose(client):
    patient = User(id=100, role="patient", is_active=True)
    app.dependency_overrides[get_current_user] = lambda: patient
    try:
        response = client.get("/api/interoperability/patients/100/export")
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
