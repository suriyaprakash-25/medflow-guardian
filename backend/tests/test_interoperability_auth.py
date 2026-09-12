import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.services.authorization import AuthorizationDecision, DenialReason

@pytest.fixture
def client():
    return TestClient(app)

def test_patient_can_export_own_fhir(client, db_session):
    # Create patient
    patient = User(id=100, email="p100@example.com", hashed_password="hash", role="patient", full_name="Pat ient")
    db_session.add(patient)
    db_session.commit()

    # We mock dependency get_current_user to return patient
    app.dependency_overrides[User] = lambda: patient
    from app.api.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: patient

    response = client.get(
        f"/api/interoperability/patients/{patient.id}/export?purpose=PATIENT_REQUEST"
    )
    assert response.status_code == 200
    bundle = response.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "searchset"
    assert len(bundle["entry"]) >= 1
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"

    app.dependency_overrides.clear()


def test_fhir_export_requires_explicit_purpose(client):
    from app.api.dependencies import get_current_user

    patient = User(id=100, role="patient", is_active=True)
    app.dependency_overrides[get_current_user] = lambda: patient
    try:
        response = client.get("/api/interoperability/patients/100/export")
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
