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


def test_canonical_and_deprecated_routes_share_idempotent_persistence(db_session):
    patient = _patient(db_session, "fhir-route-unification@example.com")
    payload = _payload(patient.id)

    canonical = _post("/api/interoperability/fhir/consents/import", payload)
    compatibility = _post("/api/interoperability/consents/import", payload)

    assert canonical.status_code == 200
    assert compatibility.status_code == 200
    first = canonical.json()
    second = compatibility.json()
    assert first["created"] is True
    assert second["created"] is False
    assert second["consent_id"] == first["consent_id"]
    assert second["policy_version_id"] == first["policy_version_id"]
    assert second["state_id"] == first["state_id"]
    assert db_session.query(Consent).filter(Consent.patient_id == patient.id).count() == 1


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


def test_client_supplied_enforcement_state_cannot_authorize_other_patient_import(db_session):
    subject = User(
        email="fhir-other-subject@example.com",
        hashed_password="hash",
        role="patient",
        full_name="Other Subject",
        is_active=True,
    )
    db_session.add(subject)
    db_session.commit()

    actor = _patient(db_session, "fhir-attacker-patient@example.com")
    payload = _payload(subject.id)
    # Model A does not accept client authority snapshots. This field is deliberately
    # irrelevant to the authorization context and must never change the decision.
    payload["enforcement_state_id"] = 999999

    response = _post("/api/interoperability/fhir/consents/import", payload)

    assert response.status_code == 403
    assert actor.id != subject.id
    assert db_session.query(Consent).filter(Consent.patient_id == subject.id).count() == 0


def test_practitioner_cannot_import_patient_consent_even_with_spoofed_authority_fields(db_session):
    subject = User(
        email="fhir-doctor-target@example.com",
        hashed_password="hash",
        role="patient",
        full_name="Target Patient",
        is_active=True,
    )
    doctor = User(
        email="fhir-import-doctor@example.com",
        hashed_password="hash",
        role="doctor",
        full_name="Import Doctor",
        is_active=True,
    )
    db_session.add_all([subject, doctor])
    db_session.commit()
    app.dependency_overrides[get_current_user] = lambda: doctor

    payload = _payload(subject.id)
    payload["enforcement_state_id"] = 1
    payload["organization"] = [{"reference": "Organization/1"}]

    try:
        response = _post("/api/interoperability/fhir/consents/import", payload)
        assert response.status_code == 403
        assert db_session.query(Consent).filter(Consent.patient_id == subject.id).count() == 0
    finally:
        app.dependency_overrides.clear()
