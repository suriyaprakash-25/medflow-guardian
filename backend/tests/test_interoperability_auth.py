from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.main import app
from app.models.clinical import LabResult
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState, ConsentStatus
from app.models.hospital import Hospital, HospitalStaff, Visit
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


def test_practitioner_export_releases_only_authorized_hospital_records(client, db_session):
    patient = User(
        id=1101,
        email="scope-patient@example.com",
        hashed_password="hash",
        role="patient",
        full_name="Scoped Patient",
        is_active=True,
    )
    doctor = User(
        id=1202,
        email="scope-doctor@example.com",
        hashed_password="hash",
        role="doctor",
        full_name="Scoped Doctor",
        is_active=True,
    )
    hospital_a = Hospital(id=1303, name="Authorized Hospital", is_active=True)
    hospital_b = Hospital(id=1304, name="Other Hospital", is_active=True)
    db_session.add_all([patient, doctor, hospital_a, hospital_b])
    db_session.flush()
    db_session.add_all(
        [
            HospitalStaff(
                user_id=doctor.id,
                hospital_id=hospital_a.id,
                role="doctor",
                is_active=True,
            ),
            Visit(
                patient_id=patient.id,
                doctor_id=doctor.id,
                hospital_id=hospital_a.id,
            ),
        ]
    )

    consent = Consent(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital_a.id,
        status=ConsentStatus.ACTIVE.value,
    )
    db_session.add(consent)
    db_session.flush()
    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": ["read"],
        },
        status="active",
    )
    db_session.add(policy)
    db_session.flush()
    db_session.add(
        ConsentState(
            consent_id=consent.id,
            policy_version_id=policy.id,
            status=ConsentStatus.ACTIVE.value,
        )
    )

    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            LabResult(
                id=1401,
                patient_id=patient.id,
                doctor_id=doctor.id,
                hospital_id=hospital_a.id,
                test_name="Authorized Lab",
                result_value="1",
                status="completed",
                test_date=now,
            ),
            LabResult(
                id=1402,
                patient_id=patient.id,
                doctor_id=doctor.id,
                hospital_id=hospital_b.id,
                test_name="Other Hospital Lab",
                result_value="2",
                status="completed",
                test_date=now,
            ),
        ]
    )
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: doctor
    try:
        response = client.get(
            f"/api/interoperability/patients/{patient.id}/export",
            params={"purpose": "TREATMENT", "consent_id": consent.id},
        )
        assert response.status_code == 200
        resources = [entry["resource"] for entry in response.json()["entry"]]
        observations = [
            resource for resource in resources if resource["resourceType"] == "Observation"
        ]
        assert [observation["id"] for observation in observations] == ["1401"]
        assert "Other Hospital Lab" not in str(response.json())
    finally:
        app.dependency_overrides.clear()
