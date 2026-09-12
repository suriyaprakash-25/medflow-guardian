from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.main import app
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState
from app.models.hospital import Hospital, HospitalStaff
from app.models.user import User
from app.services.authorization import AuthorizationContext, AuthorizationService, Operation, ResourceType


client = TestClient(app)

PURPOSE_SYSTEM = "https://medflowguardian.example/fhir/purpose"
ACTION_SYSTEM = "http://terminology.hl7.org/CodeSystem/consentaction"


def make_user(db_session, email: str, role: str) -> User:
    user = User(email=email, hashed_password="hash", role=role, full_name=email.split("@")[0])
    db_session.add(user)
    db_session.flush()
    return user


def make_payload(
    patient_id: int,
    *,
    doctor_id: int | None = None,
    hospital_id: int | None = None,
    status: str = "active",
    purpose: str = "TREATMENT",
    action: str = "access",
    source_id: str = "external-consent-1",
):
    resource = {
        "resourceType": "Consent",
        "id": source_id,
        "status": status,
        "patient": {"reference": f"Patient/{patient_id}"},
        "provision": {
            "purpose": [{"system": PURPOSE_SYSTEM, "code": purpose}],
            "action": [
                {
                    "coding": [
                        {"system": ACTION_SYSTEM, "code": action}
                    ]
                }
            ],
        },
    }
    if doctor_id is not None:
        resource["performer"] = [{"reference": f"Practitioner/{doctor_id}"}]
    if hospital_id is not None:
        resource["organization"] = [{"reference": f"Organization/{hospital_id}"}]
    return resource


def override_user(user: User):
    app.dependency_overrides[get_current_user] = lambda: user


def test_patient_import_creates_consent_policy_and_state(db_session):
    patient = make_user(db_session, "fhir-import-patient@example.com", "patient")
    db_session.commit()
    override_user(patient)

    response = client.post(
        "/api/interoperability/consents/import",
        json=make_payload(patient.id),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "active"
    assert body["source_resource_id"] == "external-consent-1"
    assert body["allowed_purposes"] == ["TREATMENT"]
    assert body["allowed_operations"] == ["read"]

    consent = db_session.query(Consent).filter(Consent.id == body["consent_id"]).one()
    policy = db_session.query(ConsentPolicyVersion).filter(
        ConsentPolicyVersion.id == body["policy_version_id"]
    ).one()
    state = db_session.query(ConsentState).filter(ConsentState.id == body["state_id"]).one()

    assert consent.patient_id == patient.id
    assert policy.consent_id == consent.id
    assert policy.version_number == 1
    assert policy.policy_payload["provenance"] == {
        "source": "FHIR_R4_CONSENT_IMPORT",
        "source_resource_id": "external-consent-1",
    }
    assert state.consent_id == consent.id
    assert state.policy_version_id == policy.id
    assert state.status == "active"


def test_import_is_denied_for_another_patient(db_session):
    patient = make_user(db_session, "fhir-owner@example.com", "patient")
    other_patient = make_user(db_session, "fhir-other@example.com", "patient")
    db_session.commit()
    override_user(patient)

    response = client.post(
        "/api/interoperability/consents/import",
        json=make_payload(other_patient.id),
    )

    assert response.status_code == 403
    assert db_session.query(Consent).filter(Consent.patient_id == other_patient.id).count() == 0


def test_provider_cannot_import_patient_consent(db_session):
    patient = make_user(db_session, "fhir-provider-target@example.com", "patient")
    doctor = make_user(db_session, "fhir-provider@example.com", "doctor")
    db_session.commit()
    override_user(doctor)

    response = client.post(
        "/api/interoperability/consents/import",
        json=make_payload(patient.id),
    )

    assert response.status_code == 403
    assert db_session.query(Consent).filter(Consent.patient_id == patient.id).count() == 0


def test_import_rejects_unsupported_purpose_system(db_session):
    patient = make_user(db_session, "fhir-purpose@example.com", "patient")
    db_session.commit()
    override_user(patient)

    payload = make_payload(patient.id)
    payload["provision"]["purpose"][0]["system"] = "http://example.invalid/purpose"

    response = client.post("/api/interoperability/consents/import", json=payload)

    assert response.status_code == 422
    assert "Unsupported purpose coding system" in response.json()["detail"]


def test_import_rejects_unsupported_action(db_session):
    patient = make_user(db_session, "fhir-action@example.com", "patient")
    db_session.commit()
    override_user(patient)

    response = client.post(
        "/api/interoperability/consents/import",
        json=make_payload(patient.id, action="collect"),
    )

    assert response.status_code == 422
    assert "Unsupported FHIR consent action code" in response.json()["detail"]


def test_inactive_maps_to_revoked(db_session):
    patient = make_user(db_session, "fhir-inactive@example.com", "patient")
    db_session.commit()
    override_user(patient)

    response = client.post(
        "/api/interoperability/consents/import",
        json=make_payload(patient.id, status="inactive"),
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "revoked"


def test_import_validates_practitioner_organization_membership(db_session):
    patient = make_user(db_session, "fhir-membership-patient@example.com", "patient")
    doctor = make_user(db_session, "fhir-membership-doctor@example.com", "doctor")
    hospital = Hospital(name="FHIR Import Hospital")
    db_session.add(hospital)
    db_session.commit()
    override_user(patient)

    payload = make_payload(
        patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
    )

    denied = client.post("/api/interoperability/consents/import", json=payload)
    assert denied.status_code == 422
    assert "active member" in denied.json()["detail"]

    db_session.add(
        HospitalStaff(
            user_id=doctor.id,
            hospital_id=hospital.id,
            role="doctor",
            is_active=True,
        )
    )
    db_session.commit()

    allowed = client.post("/api/interoperability/consents/import", json=payload)
    assert allowed.status_code == 201, allowed.text


def test_imported_active_consent_is_consumed_by_existing_cae(db_session):
    patient = make_user(db_session, "fhir-cae-patient@example.com", "patient")
    doctor = make_user(db_session, "fhir-cae-doctor@example.com", "doctor")
    hospital = Hospital(name="FHIR CAE Hospital")
    db_session.add(hospital)
    db_session.flush()
    db_session.add(
        HospitalStaff(
            user_id=doctor.id,
            hospital_id=hospital.id,
            role="doctor",
            is_active=True,
        )
    )
    db_session.commit()
    override_user(patient)

    response = client.post(
        "/api/interoperability/consents/import",
        json=make_payload(
            patient.id,
            doctor_id=doctor.id,
            hospital_id=hospital.id,
            purpose="TREATMENT",
            action="access",
        ),
    )
    assert response.status_code == 201, response.text

    consent_id = response.json()["consent_id"]
    decision = AuthorizationService(db_session).authorize(
        AuthorizationContext(
            actor=doctor,
            operation=Operation.READ,
            resource_type=ResourceType.FHIR_EXPORT,
            db=db_session,
            patient_id=patient.id,
            hospital_id=hospital.id,
            relationship_context=consent_id,
            purpose="TREATMENT",
        )
    )

    assert decision.allowed is True


def test_imported_policy_still_denies_wrong_purpose(db_session):
    patient = make_user(db_session, "fhir-deny-patient@example.com", "patient")
    doctor = make_user(db_session, "fhir-deny-doctor@example.com", "doctor")
    db_session.commit()
    override_user(patient)

    response = client.post(
        "/api/interoperability/consents/import",
        json=make_payload(patient.id, doctor_id=doctor.id, purpose="TREATMENT"),
    )
    assert response.status_code == 201, response.text

    decision = AuthorizationService(db_session).authorize(
        AuthorizationContext(
            actor=doctor,
            operation=Operation.READ,
            resource_type=ResourceType.FHIR_EXPORT,
            db=db_session,
            patient_id=patient.id,
            relationship_context=response.json()["consent_id"],
            purpose="RESEARCH",
        )
    )

    assert decision.allowed is False
    assert "PURPOSE_NOT_ALLOWED" in decision.detail
