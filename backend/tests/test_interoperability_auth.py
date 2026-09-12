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

def make_consent(db_session, patient_id, doctor_id=None):
    consent = Consent(patient_id=patient_id, doctor_id=doctor_id, status=ConsentStatus.ACTIVE.value)
    db_session.add(consent)
    db_session.flush()
    policy = ConsentPolicyVersion(consent_id=consent.id, version_number=1, policy_payload={"allowed_purposes": ["TREATMENT"], "allowed_operations": ["read"]}, status="active")
    db_session.add(policy)
    db_session.flush()
    db_session.add(ConsentState(consent_id=consent.id, policy_version_id=policy.id, status=ConsentStatus.ACTIVE.value))
    db_session.commit()
    return consent

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

    visit = Visit(patient_id=patient.id, doctor_id=doctor.id, hospital_id=1)
    db_session.add(visit)
    db_session.commit()

    decision = AuthorizationService(db_session).authorize(
        AuthorizationContext(
            actor=doctor,
            operation=Operation.READ,
            resource_type=ResourceType.FHIR_EXPORT,
            db=db_session,
            patient_id=patient.id,
            purpose="TREATMENT",
        )
    )

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
        assert response.json()["resourceType"] == "Bundle"
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
