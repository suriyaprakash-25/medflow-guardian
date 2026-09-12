import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState, ConsentStatus


@pytest.fixture
def client():
    return TestClient(app)


def test_patient_can_export_own_fhir(client, db_session):
    patient = User(id=100, email="p100@example.com", hashed_password="hash", role="patient", full_name="Patient")
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
    doctor = User(id=101, email="d101@example.com", hashed_password="hash", role="doctor", full_name="Doctor")
    patient = User(id=102, email="p102@example.com", hashed_password="hash", role="patient", full_name="Patient")
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


def test_provider_fhir_export_denies_mismatched_consent(client, db_session):
    doctor = User(id=103, email="d103@example.com", hashed_password="hash", role="doctor", full_name="Doctor")
    other_doctor = User(id=104, email="d104@example.com", hashed_password="hash", role="doctor", full_name="Other Doctor")
    patient = User(id=105, email="p105@example.com", hashed_password="hash", role="patient", full_name="Patient")
    db_session.add_all([doctor, other_doctor, patient])
    db_session.commit()

    consent = Consent(patient_id=patient.id, doctor_id=other_doctor.id, status=ConsentStatus.ACTIVE.value)
    db_session.add(consent)
    db_session.flush()
    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={"allowed_purposes": ["TREATMENT"], "allowed_operations": ["read"]},
        status="active",
    )
    db_session.add(policy)
    db_session.flush()
    db_session.add(ConsentState(consent_id=consent.id, policy_version_id=policy.id, status=ConsentStatus.ACTIVE.value))
    db_session.commit()

    from app.api.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: doctor
    response = client.get(
        f"/api/interoperability/patients/{patient.id}/export",
        params={"purpose": "TREATMENT", "consent_id": consent.id},
    )
    assert response.status_code == 403
    app.dependency_overrides.clear()
