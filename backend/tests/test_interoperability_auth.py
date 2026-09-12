import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState, ConsentStatus
from app.models.hospital import Visit
from app.services.authorization import AuthorizationService, AuthorizationContext, Operation, ResourceType


@pytest.fixture
def client():
    return TestClient(app)


def override_user(user):
    from app.api.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user


def clear_overrides():
    app.dependency_overrides.clear()


def make_consent(db_session, patient_id, doctor_id=None, purposes=None, operations=None):
    consent = Consent(patient_id=patient_id, doctor_id=doctor_id, status=ConsentStatus.ACTIVE.value)
    db_session.add(consent)
    db_session.flush()
    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={
            "allowed_purposes": purposes or ["TREATMENT"],
            "allowed_operations": operations or ["read"],
        },
        status="active",
    )
    db_session.add(policy)
    db_session.flush()
    db_session.add(ConsentState(consent_id=consent.id, policy_version_id=policy.id, status=ConsentStatus.ACTIVE.value))
    db_session.commit()
    return consent


def authorize_provider(db_session, doctor, patient_id, consent_id, purpose="TREATMENT"):
    return AuthorizationService(db_session).authorize(
        AuthorizationContext(
            actor=doctor,
            operation=Operation.READ,
            resource_type=ResourceType.FHIR_EXPORT,
            db=db_session,
            patient_id=patient_id,
            relationship_context=consent_id,
            purpose=purpose,
        )
    )


def test_patient_can_export_own_fhir(client, db_session):
    patient = User(id=100, email="p100@example.com", hashed_password="hash", role="patient", full_name="Patient")
    db_session.add(patient)
    db_session.commit()
    override_user(patient)
    try:
        response = client.get(f"/api/interoperability/patients/{patient.id}/export", params={"purpose": "SELF_ACCESS"})
        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "searchset"
        assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"
    finally:
        clear_overrides()


def test_provider_fhir_export_requires_consent_context(client, db_session):
    doctor = User(id=101, email="d101@example.com", hashed_password="hash", role="doctor", full_name="Doctor")
    patient = User(id=102, email="p102@example.com", hashed_password="hash", role="patient", full_name="Patient")
    db_session.add_all([doctor, patient])
    db_session.commit()
    override_user(doctor)
    try:
        response = client.get(f"/api/interoperability/patients/{patient.id}/export", params={"purpose": "TREATMENT"})
        assert response.status_code == 403
    finally:
        clear_overrides()


def test_provider_fhir_export_denies_visit_only_access_at_cae(db_session):
    doctor = User(id=111, email="d111@example.com", hashed_password="hash", role="doctor", full_name="Doctor")
    patient = User(id=112, email="p112@example.com", hashed_password="hash", role="patient", full_name="Patient")
    db_session.add_all([doctor, patient])
    db_session.commit()
    db_session.add(Visit(patient_id=patient.id, doctor_id=doctor.id, hospital_id=1))
    db_session.commit()
    decision = authorize_provider(db_session, doctor, patient.id, None)
    assert decision.allowed is False
    assert decision.reason.value == "consent_required"


def test_provider_fhir_export_accepts_matching_active_consent(client, db_session):
    doctor = User(id=103, email="d103@example.com", hashed_password="hash", role="doctor", full_name="Doctor")
    patient = User(id=104, email="p104@example.com", hashed_password="hash", role="patient", full_name="Patient")
    db_session.add_all([doctor, patient])
    db_session.commit()
    consent = make_consent(db_session, patient.id, doctor.id)
    override_user(doctor)
    try:
        response = client.get(f"/api/interoperability/patients/{patient.id}/export", params={"purpose": "TREATMENT", "consent_id": consent.id})
        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"
        consent_resources = [entry["resource"] for entry in bundle["entry"] if entry["resource"]["resourceType"] == "Consent"]
        assert len(consent_resources) == 1
        exported_consent = consent_resources[0]
        assert exported_consent["id"] == str(consent.id)
        assert exported_consent["status"] == "active"
        assert exported_consent["patient"]["reference"] == f"Patient/{patient.id}"
        assert any(ext["valueInteger"] == 1 for ext in exported_consent["extension"] if "valueInteger" in ext)
    finally:
        clear_overrides()


def test_provider_fhir_export_denies_mismatched_consent(client, db_session):
    doctor = User(id=105, email="d105@example.com", hashed_password="hash", role="doctor", full_name="Doctor")
    other_doctor = User(id=106, email="d106@example.com", hashed_password="hash", role="doctor", full_name="Other Doctor")
    patient = User(id=107, email="p107@example.com", hashed_password="hash", role="patient", full_name="Patient")
    db_session.add_all([doctor, other_doctor, patient])
    db_session.commit()
    consent = make_consent(db_session, patient.id, other_doctor.id)
    override_user(doctor)
    try:
        response = client.get(f"/api/interoperability/patients/{patient.id}/export", params={"purpose": "TREATMENT", "consent_id": consent.id})
        assert response.status_code == 403
    finally:
        clear_overrides()


def test_provider_fhir_export_denies_wrong_patient(client, db_session):
    doctor = User(id=108, email="d108@example.com", hashed_password="hash", role="doctor", full_name="Doctor")
    consent_patient = User(id=109, email="p109@example.com", hashed_password="hash", role="patient", full_name="Consent Patient")
    requested_patient = User(id=110, email="p110@example.com", hashed_password="hash", role="patient", full_name="Requested Patient")
    db_session.add_all([doctor, consent_patient, requested_patient])
    db_session.commit()
    consent = make_consent(db_session, consent_patient.id, doctor.id)
    override_user(doctor)
    try:
        response = client.get(f"/api/interoperability/patients/{requested_patient.id}/export", params={"purpose": "TREATMENT", "consent_id": consent.id})
        assert response.status_code == 403
    finally:
        clear_overrides()


def test_provider_fhir_export_denies_disallowed_purpose(db_session):
    doctor = User(id=113, email="d113@example.com", hashed_password="hash", role="doctor", full_name="Doctor")
    patient = User(id=114, email="p114@example.com", hashed_password="hash", role="patient", full_name="Patient")
    db_session.add_all([doctor, patient])
    db_session.commit()
    consent = make_consent(db_session, patient.id, doctor.id, purposes=["TREATMENT"])
    decision = authorize_provider(db_session, doctor, patient.id, consent.id, purpose="RESEARCH")
    assert decision.allowed is False
    assert "PURPOSE_NOT_ALLOWED" in decision.detail


def test_provider_fhir_export_denies_disallowed_operation(db_session):
    doctor = User(id=115, email="d115@example.com", hashed_password="hash", role="doctor", full_name="Doctor")
    patient = User(id=116, email="p116@example.com", hashed_password="hash", role="patient", full_name="Patient")
    db_session.add_all([doctor, patient])
    db_session.commit()
    consent = make_consent(db_session, patient.id, doctor.id, operations=["download"])
    decision = authorize_provider(db_session, doctor, patient.id, consent.id)
    assert decision.allowed is False
    assert "OPERATION_NOT_ALLOWED" in decision.detail


def test_provider_fhir_export_denies_revoked_consent(db_session):
    doctor = User(id=117, email="d117@example.com", hashed_password="hash", role="doctor", full_name="Doctor")
    patient = User(id=118, email="p118@example.com", hashed_password="hash", role="patient", full_name="Patient")
    db_session.add_all([doctor, patient])
    db_session.commit()
    consent = make_consent(db_session, patient.id, doctor.id)
    state = db_session.query(ConsentState).filter(ConsentState.consent_id == consent.id).one()
    state.status = ConsentStatus.REVOKED.value
    consent.status = ConsentStatus.REVOKED.value
    db_session.commit()
    decision = authorize_provider(db_session, doctor, patient.id, consent.id)
    assert decision.allowed is False
    assert "currently revoked" in decision.detail


def test_provider_fhir_export_denies_suspended_consent(db_session):
    doctor = User(id=119, email="d119@example.com", hashed_password="hash", role="doctor", full_name="Doctor")
    patient = User(id=120, email="p120@example.com", hashed_password="hash", role="patient", full_name="Patient")
    db_session.add_all([doctor, patient])
    db_session.commit()
    consent = make_consent(db_session, patient.id, doctor.id)
    state = db_session.query(ConsentState).filter(ConsentState.consent_id == consent.id).one()
    state.status = ConsentStatus.SUSPENDED.value
    consent.status = ConsentStatus.SUSPENDED.value
    db_session.commit()
    decision = authorize_provider(db_session, doctor, patient.id, consent.id)
    assert decision.allowed is False
    assert "currently suspended" in decision.detail
