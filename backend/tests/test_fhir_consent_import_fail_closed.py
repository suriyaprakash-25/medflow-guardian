from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.main import app
from app.models.consent import Consent
from app.models.user import User


client = TestClient(app)
SOURCE_SYSTEM = "https://external-fhir.example.test"
PURPOSE_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-ActReason"
ACTION_SYSTEM = "http://terminology.hl7.org/CodeSystem/consentaction"


def _patient(db_session, email: str) -> User:
    patient = User(
        email=email,
        hashed_password="hash",
        role="patient",
        full_name="FHIR Patient",
        is_active=True,
    )
    db_session.add(patient)
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: patient
    return patient


def _payload(patient_id: int):
    return {
        "resourceType": "Consent",
        "id": "canonical-import-test",
        "status": "active",
        "scope": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/consentscope",
                    "code": "patient-privacy",
                }
            ]
        },
        "category": [
            {
                "coding": [
                    {"system": "http://loinc.org", "code": "59284-0"}
                ]
            }
        ],
        "patient": {"reference": f"Patient/{patient_id}"},
        "policy": [{"uri": "https://external-fhir.example.test/policy/privacy"}],
        "provision": {
            "type": "permit",
            "purpose": [{"system": PURPOSE_SYSTEM, "code": "TREAT"}],
            "action": [
                {
                    "coding": [
                        {"system": ACTION_SYSTEM, "code": "access"}
                    ]
                }
            ],
        },
    }


def _post(path: str, payload: dict):
    return client.post(
        path,
        params={"source_system": SOURCE_SYSTEM},
        json=payload,
    )


def test_deprecated_alias_uses_same_canonical_fail_closed_mapper(db_session):
    patient = _patient(db_session, "fhir-alias-deny@example.com")
    payload = _payload(patient.id)
    payload["provision"]["type"] = "deny"

    response = _post("/api/interoperability/consents/import", payload)

    assert response.status_code == 422
    assert "Deny provisions" in response.json()["detail"]
    assert db_session.query(Consent).filter(Consent.patient_id == patient.id).count() == 0


def test_time_period_is_rejected_until_right_time_mapping_exists(db_session):
    patient = _patient(db_session, "fhir-period@example.com")
    payload = _payload(patient.id)
    payload["provision"]["period"] = {
        "start": "2026-09-01T00:00:00Z",
        "end": "2026-09-30T23:59:59Z",
    }

    response = _post("/api/interoperability/fhir/consents/import", payload)

    assert response.status_code == 422
    assert "cannot enforce losslessly" in response.json()["detail"]
    assert "period" in response.json()["detail"]
    assert db_session.query(Consent).filter(Consent.patient_id == patient.id).count() == 0


def test_nested_provision_is_rejected_instead_of_silently_ignored(db_session):
    patient = _patient(db_session, "fhir-nested@example.com")
    payload = _payload(patient.id)
    payload["provision"]["provision"] = [
        {
            "type": "deny",
            "purpose": [{"system": PURPOSE_SYSTEM, "code": "RESCH"}],
        }
    ]

    response = _post("/api/interoperability/fhir/consents/import", payload)

    assert response.status_code == 422
    assert "Nested provisions" in response.json()["detail"]
    assert db_session.query(Consent).filter(Consent.patient_id == patient.id).count() == 0


def test_data_scope_is_rejected_until_lossless_mapping_exists(db_session):
    patient = _patient(db_session, "fhir-data-scope@example.com")
    payload = _payload(patient.id)
    payload["provision"]["data"] = [
        {
            "meaning": "instance",
            "reference": {"reference": "DocumentReference/42"},
        }
    ]

    response = _post("/api/interoperability/fhir/consents/import", payload)

    assert response.status_code == 422
    assert "data" in response.json()["detail"]
    assert db_session.query(Consent).filter(Consent.patient_id == patient.id).count() == 0


def test_old_vendor_purpose_dialect_no_longer_selects_a_second_mapper(db_session):
    patient = _patient(db_session, "fhir-old-purpose@example.com")
    payload = _payload(patient.id)
    payload["provision"]["purpose"][0]["system"] = (
        "https://medflowguardian.example/fhir/purpose"
    )
    payload["provision"]["purpose"][0]["code"] = "TREATMENT"

    response = _post("/api/interoperability/fhir/consents/import", payload)

    assert response.status_code == 422
    assert "must include a coding" in response.json()["detail"]
    assert db_session.query(Consent).filter(Consent.patient_id == patient.id).count() == 0
