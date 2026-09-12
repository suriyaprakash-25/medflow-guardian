import pytest
from fastapi.testclient import TestClient
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
        full_name="Pat ient",
    )
    db_session.add(patient)
    db_session.commit()

    from app.api.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: patient

    response = client.get(
        f"/api/interoperability/patients/{patient.id}/export",
        params={"purpose": "SELF_ACCESS"},
    )
    assert response.status_code == 200
    bundle = response.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "searchset"
    assert len(bundle["entry"]) >= 1
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"

    app.dependency_overrides.clear()


def test_provider_fhir_export_requires_consent_context(client, db_session):
    doctor = User(
        id=101,
        email="d101@example.com",
        hashed_password="hash",
        role="doctor",
        full_name="Doctor",
    )
    patient = User(
        id=102,
        email="p102@example.com",
        hashed_password="hash",
        role="patient",
        full_name="Patient",
    )
    db_session.add_all([doctor, patient])
    db_session.commit()

    from app.api.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: doctor

    response = client.get(
        f"/api/interoperability/patients/{patient.id}/export",
        params={"purpose": "TREATMENT"},
    )
    assert response.status_code == 403

    app.dependency_overrides.clear()
