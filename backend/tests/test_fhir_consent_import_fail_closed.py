from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.main import app
from app.models.consent import Consent
from app.models.user import User


client = TestClient(app)
PURPOSE_SYSTEM = "https://medflowguardian.example/fhir/purpose"
ACTION_SYSTEM = "http://terminology.hl7.org/CodeSystem/consentaction"


def _patient(db_session, email: str) -> User:
    patient = User(email=email, hashed_password="hash", role="patient", full_name="FHIR Patient")
    db_session.add(patient)
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: patient
    return patient


def _payload(patient_id: int):
    return {
        "resourceType": "Consent",
        "status": "active",
        "patient": {"reference": f"Patient/{patient_id}"},
        "provision": {
            "type": "permit",
            "purpose": [{"system": PURPOSE_SYSTEM, "code": "TREATMENT"}],
            "action": [
                {
                    "coding": [
                        {"system": ACTION_SYSTEM, "code": "access"}
                    ]
                }
            ],
        },
    }


def test_deny_provision_is_rejected_instead_of_inverted(db_session):
    patient = _patient(db_session, "fhir-deny-provision@example.com")
    payload = _payload(patient.id)
    payload["provision"]["type"] = "deny"

    response = client.post("/api/interoperability/consents/import", json=payload)

    assert response.status_code == 422
    assert "deny provisions" in response.json()["detail"]
    assert db_session.query(Consent).filter(Consent.patient_id == patient.id).count() == 0


def test_time_period_is_rejected_until_right_time_mapping_exists(db_session):
    patient = _patient(db_session, "fhir-period@example.com")
    payload = _payload(patient.id)
    payload["provision"]["period"] = {
        "start": "2026-09-01T00:00:00Z",
        "end": "2026-09-30T23:59:59Z",
    }

    response = client.post("/api/interoperability/consents/import", json=payload)

    assert response.status_code == 422
    assert "cannot yet map losslessly" in response.json()["detail"]
    assert "period" in response.json()["detail"]
    assert db_session.query(Consent).filter(Consent.patient_id == patient.id).count() == 0


def test_nested_provision_is_rejected_instead_of_silently_ignored(db_session):
    patient = _patient(db_session, "fhir-nested@example.com")
    payload = _payload(patient.id)
    payload["provision"]["provision"] = [
        {
            "type": "deny",
            "purpose": [{"system": PURPOSE_SYSTEM, "code": "RESEARCH"}],
        }
    ]

    response = client.post("/api/interoperability/consents/import", json=payload)

    assert response.status_code == 422
    assert "provision" in response.json()["detail"]
    assert db_session.query(Consent).filter(Consent.patient_id == patient.id).count() == 0


def test_data_scope_is_rejected_until_lossless_mapping_exists(db_session):
    patient = _patient(db_session, "fhir-data-scope@example.com")
    payload = _payload(patient.id)
    payload["provision"]["data"] = [
        {"meaning": "instance", "reference": {"reference": "DocumentReference/42"}}
    ]

    response = client.post("/api/interoperability/consents/import", json=payload)

    assert response.status_code == 422
    assert "data" in response.json()["detail"]
    assert db_session.query(Consent).filter(Consent.patient_id == patient.id).count() == 0
