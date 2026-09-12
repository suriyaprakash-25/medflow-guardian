"""Regression coverage for R5 multi-grant document authorization."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.access import DocumentAccessGrant, DocumentAccessRequest
from app.models.document import MedicalDocument
from app.models.hospital import Hospital, Visit
from app.models.user import User
from app.services.authorization import AuthorizationService


def test_active_grant_resolution_checks_every_candidate(db_session: Session):
    hospital = Hospital(name="R5 Multi Grant Hospital", is_active=True)
    db_session.add(hospital)
    db_session.flush()

    patient = User(
        email="r5-multigrant-patient@test.com",
        hashed_password=get_password_hash("pass"),
        role="patient",
        full_name="R5 Multi Grant Patient",
        is_active=True,
    )
    doctor = User(
        email="r5-multigrant-doctor@test.com",
        hashed_password=get_password_hash("pass"),
        role="doctor",
        full_name="R5 Multi Grant Doctor",
        is_active=True,
    )
    db_session.add_all([patient, doctor])
    db_session.flush()

    visit = Visit(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
        status="active",
        reason="R5 multi-grant regression",
    )
    db_session.add(visit)
    db_session.flush()

    unrelated_doc = MedicalDocument(
        patient_id=patient.id,
        hospital_id=hospital.id,
        uploaded_by_doctor_id=doctor.id,
        visit_id=visit.id,
        document_type="lab report",
        title="Unrelated grant document",
        original_filename="unrelated.pdf",
        stored_filename="r5/multigrant/unrelated.pdf",
        mime_type="application/pdf",
        file_size=100,
        scan_status="clean",
        status="active",
    )
    target_doc = MedicalDocument(
        patient_id=patient.id,
        hospital_id=hospital.id,
        uploaded_by_doctor_id=doctor.id,
        visit_id=visit.id,
        document_type="lab report",
        title="Target grant document",
        original_filename="target.pdf",
        stored_filename="r5/multigrant/target.pdf",
        mime_type="application/pdf",
        file_size=100,
        scan_status="clean",
        status="active",
    )
    db_session.add_all([unrelated_doc, target_doc])
    db_session.flush()

    unrelated_request = DocumentAccessRequest(
        patient_id=patient.id,
        requesting_doctor_id=doctor.id,
        requesting_hospital_id=hospital.id,
        reason="Unrelated grant",
        status="approved",
    )
    target_request = DocumentAccessRequest(
        patient_id=patient.id,
        requesting_doctor_id=doctor.id,
        requesting_hospital_id=hospital.id,
        reason="Target grant",
        status="approved",
    )
    db_session.add_all([unrelated_request, target_request])
    db_session.flush()

    now = datetime.now(timezone.utc)
    unrelated_grant = DocumentAccessGrant(
        access_request_id=unrelated_request.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
        status="active",
        granted_at=now,
        expires_at=now + timedelta(hours=2),
    )
    unrelated_grant.granted_documents.append(unrelated_doc)

    target_grant = DocumentAccessGrant(
        access_request_id=target_request.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
        status="active",
        granted_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(hours=2),
    )
    target_grant.granted_documents.append(target_doc)

    db_session.add_all([unrelated_grant, target_grant])
    db_session.flush()

    resolved = AuthorizationService(db_session)._get_active_grant(
        doctor.id,
        target_doc.id,
    )

    assert resolved is not None
    assert resolved.id == target_grant.id
