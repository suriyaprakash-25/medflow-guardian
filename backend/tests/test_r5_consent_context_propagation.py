"""R5 end-to-end regression tests for trusted consent-context propagation."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.access import DocumentAccessGrant, DocumentAccessRequest
from app.models.clinical import ClinicalNote, LabResult, Medication, Prescription
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState
from app.models.document import MedicalDocument
from app.models.hospital import Hospital, HospitalStaff, Visit
from app.models.user import User


client = TestClient(app)


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(
        subject=user.email,
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


def _seed_r5(db: Session):
    hospital_a = Hospital(name="R5 Hospital A", is_active=True)
    hospital_b = Hospital(name="R5 Hospital B", is_active=True)
    db.add_all([hospital_a, hospital_b])
    db.flush()

    patient = User(
        email="r5-patient@test.com",
        hashed_password=get_password_hash("pass"),
        role="patient",
        full_name="R5 Patient",
        is_active=True,
    )
    doctor = User(
        email="r5-doctor@test.com",
        hashed_password=get_password_hash("pass"),
        role="doctor",
        full_name="R5 Doctor",
        is_active=True,
    )
    other_doctor = User(
        email="r5-other-doctor@test.com",
        hashed_password=get_password_hash("pass"),
        role="doctor",
        full_name="R5 Other Doctor",
        is_active=True,
    )
    db.add_all([patient, doctor, other_doctor])
    db.flush()

    db.add_all(
        [
            HospitalStaff(
                user_id=doctor.id,
                hospital_id=hospital_a.id,
                role="doctor",
                is_active=True,
            ),
            HospitalStaff(
                user_id=other_doctor.id,
                hospital_id=hospital_a.id,
                role="doctor",
                is_active=True,
            ),
        ]
    )
    db.flush()

    visit_a = Visit(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital_a.id,
        status="active",
        reason="R5 treatment",
    )
    visit_b = Visit(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital_b.id,
        status="completed",
        reason="Other organization",
    )
    db.add_all([visit_a, visit_b])
    db.flush()

    doc_a = MedicalDocument(
        patient_id=patient.id,
        hospital_id=hospital_a.id,
        uploaded_by_doctor_id=doctor.id,
        visit_id=visit_a.id,
        document_type="lab report",
        title="R5 A document",
        original_filename="r5-a.pdf",
        stored_filename="r5/a.pdf",
        mime_type="application/pdf",
        file_size=100,
        scan_status="clean",
        status="active",
    )
    doc_b = MedicalDocument(
        patient_id=patient.id,
        hospital_id=hospital_b.id,
        uploaded_by_doctor_id=doctor.id,
        visit_id=visit_b.id,
        document_type="lab report",
        title="R5 B document",
        original_filename="r5-b.pdf",
        stored_filename="r5/b.pdf",
        mime_type="application/pdf",
        file_size=100,
        scan_status="clean",
        status="active",
    )
    db.add_all([doc_a, doc_b])
    db.flush()

    consent = Consent(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital_a.id,
        status="active",
    )
    db.add(consent)
    db.flush()

    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": ["list", "create", "download"],
        },
        status="active",
    )
    db.add(policy)
    db.flush()

    state = ConsentState(
        consent_id=consent.id,
        policy_version_id=policy.id,
        status="active",
    )
    db.add(state)
    db.flush()

    request = DocumentAccessRequest(
        patient_id=patient.id,
        requesting_doctor_id=doctor.id,
        requesting_hospital_id=hospital_a.id,
        reason="R5 download",
        status="approved",
    )
    db.add(request)
    db.flush()

    grant = DocumentAccessGrant(
        access_request_id=request.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital_a.id,
        consent_id=consent.id,
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=4),
    )
    grant.granted_documents.append(doc_a)
    db.add(grant)

    medication = Medication(name="R5 Medication", description="R5")
    db.add(medication)
    db.flush()

    prescription_a = Prescription(
        patient_id=patient.id,
        doctor_id=doctor.id,
        medication_id=medication.id,
        hospital_id=hospital_a.id,
        dosage="5 mg",
        frequency="daily",
        start_date=datetime.now(timezone.utc),
    )
    prescription_b = Prescription(
        patient_id=patient.id,
        doctor_id=doctor.id,
        medication_id=medication.id,
        hospital_id=hospital_b.id,
        dosage="10 mg",
        frequency="daily",
        start_date=datetime.now(timezone.utc),
    )
    lab_a = LabResult(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital_a.id,
        test_name="R5 CBC",
        result_value="normal",
        test_date=datetime.now(timezone.utc),
    )
    note_a = ClinicalNote(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital_a.id,
        title="R5 note",
        content="Existing treatment note",
        note_type="progress",
    )
    db.add_all([prescription_a, prescription_b, lab_a, note_a])
    db.commit()

    return {
        "hospital_a": hospital_a,
        "hospital_b": hospital_b,
        "patient": patient,
        "doctor": doctor,
        "other_doctor": other_doctor,
        "doc_a": doc_a,
        "doc_b": doc_b,
        "consent": consent,
        "grant": grant,
    }


@patch("app.services.storage.StorageService.download_document")
def test_document_download_uses_server_resolved_grant_consent(mock_storage, db_session: Session):
    data = _seed_r5(db_session)
    mock_storage.return_value = b"r5 file"

    response = client.get(
        f"/api/documents/{data['doc_a'].id}/download?purpose=TREATMENT",
        headers=_headers(data["doctor"]),
    )

    assert response.status_code == 200, response.text
    assert response.content == b"r5 file"
    mock_storage.assert_called_once()


@patch("app.services.storage.StorageService.download_document")
def test_document_download_missing_purpose_fails_before_storage(mock_storage, db_session: Session):
    data = _seed_r5(db_session)

    response = client.get(
        f"/api/documents/{data['doc_a'].id}/download",
        headers=_headers(data["doctor"]),
    )

    assert response.status_code == 403
    assert "PURPOSE_REQUIRED" in response.json()["detail"]
    mock_storage.assert_not_called()


def test_document_metadata_is_hospital_scoped_and_cae_gated(db_session: Session):
    data = _seed_r5(db_session)

    own_scope = client.get(
        f"/api/documents/metadata/{data['patient'].id}",
        params={"hospital_id": data["hospital_a"].id},
        headers=_headers(data["doctor"]),
    )
    assert own_scope.status_code == 200, own_scope.text
    returned_ids = {item["id"] for item in own_scope.json()}
    assert data["doc_a"].id in returned_ids
    assert data["doc_b"].id not in returned_ids

    other_scope = client.get(
        f"/api/documents/metadata/{data['patient'].id}",
        params={"hospital_id": data["hospital_b"].id},
        headers=_headers(data["doctor"]),
    )
    assert other_scope.status_code == 403

    missing_scope = client.get(
        f"/api/documents/metadata/{data['patient'].id}",
        headers=_headers(data["doctor"]),
    )
    assert missing_scope.status_code == 422


def test_doctor_clinical_list_requires_server_resolved_scoped_consent(db_session: Session):
    data = _seed_r5(db_session)

    response = client.get(
        f"/api/clinical/prescriptions/patient/{data['patient'].id}",
        params={"purpose": "TREATMENT", "hospital_id": data["hospital_a"].id},
        headers=_headers(data["doctor"]),
    )
    assert response.status_code == 200, response.text
    assert len(response.json()) == 1
    assert response.json()[0]["hospital_id"] == data["hospital_a"].id

    missing_purpose = client.get(
        f"/api/clinical/prescriptions/patient/{data['patient'].id}",
        params={"hospital_id": data["hospital_a"].id},
        headers=_headers(data["doctor"]),
    )
    assert missing_purpose.status_code == 403
    assert "PURPOSE_REQUIRED" in missing_purpose.json()["detail"]

    missing_hospital = client.get(
        f"/api/clinical/prescriptions/patient/{data['patient'].id}",
        params={"purpose": "TREATMENT"},
        headers=_headers(data["doctor"]),
    )
    assert missing_hospital.status_code == 400

    wrong_purpose = client.get(
        f"/api/clinical/prescriptions/patient/{data['patient'].id}",
        params={"purpose": "BILLING", "hospital_id": data["hospital_a"].id},
        headers=_headers(data["doctor"]),
    )
    assert wrong_purpose.status_code == 403
    assert "PURPOSE_NOT_ALLOWED" in wrong_purpose.json()["detail"]


def test_doctor_without_scoped_consent_cannot_read_clinical_records(db_session: Session):
    data = _seed_r5(db_session)

    response = client.get(
        f"/api/clinical/prescriptions/patient/{data['patient'].id}",
        params={"purpose": "TREATMENT", "hospital_id": data["hospital_a"].id},
        headers=_headers(data["other_doctor"]),
    )

    assert response.status_code == 403
    assert "consent" in response.json()["detail"].lower()


def test_patient_self_clinical_read_remains_consent_independent(db_session: Session):
    data = _seed_r5(db_session)

    response = client.get(
        f"/api/clinical/prescriptions/patient/{data['patient'].id}",
        headers=_headers(data["patient"]),
    )

    assert response.status_code == 200, response.text
    assert len(response.json()) == 2


def test_clinical_create_uses_scoped_consent_and_explicit_purpose(db_session: Session):
    data = _seed_r5(db_session)

    response = client.post(
        "/api/clinical/notes",
        params={"purpose": "TREATMENT"},
        json={
            "patient_id": data["patient"].id,
            "hospital_id": data["hospital_a"].id,
            "title": "R5 authorized note",
            "content": "Created through consent-bound clinical workflow",
            "note_type": "progress",
        },
        headers=_headers(data["doctor"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["hospital_id"] == data["hospital_a"].id

    denied = client.post(
        "/api/clinical/notes",
        params={"purpose": "TREATMENT"},
        json={
            "patient_id": data["patient"].id,
            "hospital_id": data["hospital_a"].id,
            "title": "R5 unauthorized note",
            "content": "Must not be created",
            "note_type": "progress",
        },
        headers=_headers(data["other_doctor"]),
    )
    assert denied.status_code == 403

    assert (
        db_session.query(ClinicalNote)
        .filter(ClinicalNote.title == "R5 unauthorized note")
        .count()
        == 0
    )
