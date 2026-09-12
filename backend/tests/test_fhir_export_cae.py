"""P0 certification tests for direct CAE enforcement on FHIR export."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.audit import AuditLog
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState, ConsentStatus
from app.models.hospital import Hospital, HospitalStaff, Visit
from app.models.user import User
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    DenialReason,
    Operation,
    ResourceType,
)


def make_database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Hospital.__table__,
            HospitalStaff.__table__,
            Visit.__table__,
            Consent.__table__,
            ConsentPolicyVersion.__table__,
            ConsentState.__table__,
            AuditLog.__table__,
        ],
    )
    return engine, sessionmaker(bind=engine)()


def seed_authorized_export(db):
    patient = User(
        id=101,
        email="patient-export@example.test",
        hashed_password="unused",
        role="patient",
        is_active=True,
    )
    doctor = User(
        id=202,
        email="doctor-export@example.test",
        hashed_password="unused",
        role="doctor",
        is_active=True,
    )
    hospital = Hospital(id=303, name="Export Hospital", is_active=True)
    db.add_all([patient, doctor, hospital])
    db.flush()
    db.add(HospitalStaff(user_id=doctor.id, hospital_id=hospital.id, is_active=True))
    db.add(Visit(patient_id=patient.id, doctor_id=doctor.id, hospital_id=hospital.id))
    consent = Consent(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
        status=ConsentStatus.ACTIVE.value,
    )
    db.add(consent)
    db.flush()
    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": ["read"],
        },
        status="active",
    )
    db.add(policy)
    db.flush()
    db.add(ConsentState(
        consent_id=consent.id,
        policy_version_id=policy.id,
        status=ConsentStatus.ACTIVE.value,
    ))
    db.flush()
    return patient, doctor, hospital, consent, policy


def export_context(db, doctor, patient, hospital, consent, **overrides):
    values = {
        "actor": doctor,
        "operation": Operation.READ,
        "resource_type": ResourceType.FHIR_EXPORT,
        "db": db,
        "patient_id": patient.id,
        "hospital_id": hospital.id,
        "relationship_context": consent,
        "purpose": "TREATMENT",
        "consent_id": consent.id,
    }
    values.update(overrides)
    return AuthorizationContext(**values)


def test_doctor_fhir_export_requires_every_control():
    engine, db = make_database()
    try:
        patient, doctor, hospital, consent, _ = seed_authorized_export(db)
        decision = AuthorizationService(db).authorize(
            export_context(db, doctor, patient, hospital, consent)
        )
        assert decision.allowed is True
    finally:
        db.close()
        engine.dispose()


def test_doctor_fhir_export_denies_missing_explicit_consent():
    engine, db = make_database()
    try:
        patient, doctor, hospital, consent, _ = seed_authorized_export(db)
        decision = AuthorizationService(db).authorize(export_context(
            db,
            doctor,
            patient,
            hospital,
            consent,
            consent_id=None,
            relationship_context=None,
        ))
        assert decision.allowed is False
        assert decision.reason == DenialReason.CONSENT_REQUIRED
    finally:
        db.close()
        engine.dispose()


def test_doctor_fhir_export_denies_consent_for_other_patient():
    engine, db = make_database()
    try:
        patient, doctor, hospital, consent, _ = seed_authorized_export(db)
        other_patient = User(
            id=404,
            email="other-patient@example.test",
            hashed_password="unused",
            role="patient",
            is_active=True,
        )
        db.add(other_patient)
        db.flush()
        decision = AuthorizationService(db).authorize(export_context(
            db, doctor, other_patient, hospital, consent, patient_id=other_patient.id
        ))
        assert decision.allowed is False
        assert decision.reason == DenialReason.RESOURCE_NOT_OWNED
    finally:
        db.close()
        engine.dispose()


def test_doctor_fhir_export_denies_wrong_purpose_and_revoked_state():
    engine, db = make_database()
    try:
        patient, doctor, hospital, consent, policy = seed_authorized_export(db)
        service = AuthorizationService(db)

        purpose_denial = service.authorize(export_context(
            db, doctor, patient, hospital, consent, purpose="RESEARCH"
        ))
        assert purpose_denial.allowed is False
        assert "PURPOSE_NOT_ALLOWED" in purpose_denial.detail

        db.add(ConsentState(
            consent_id=consent.id,
            policy_version_id=policy.id,
            status=ConsentStatus.REVOKED.value,
        ))
        db.flush()
        revoked_denial = service.authorize(
            export_context(db, doctor, patient, hospital, consent)
        )
        assert revoked_denial.allowed is False
        assert "revoked" in revoked_denial.detail
    finally:
        db.close()
        engine.dispose()


def test_doctor_fhir_export_denies_missing_relationship_or_membership():
    engine, db = make_database()
    try:
        patient, doctor, hospital, consent, _ = seed_authorized_export(db)
        db.query(Visit).delete()
        relationship_denial = AuthorizationService(db).authorize(
            export_context(db, doctor, patient, hospital, consent)
        )
        assert relationship_denial.allowed is False
        assert relationship_denial.reason == DenialReason.RELATIONSHIP_REQUIRED

        other_hospital = Hospital(id=304, name="Other Hospital", is_active=True)
        db.add(other_hospital)
        db.add(Visit(patient_id=patient.id, doctor_id=doctor.id, hospital_id=other_hospital.id))
        db.flush()
        cross_hospital_denial = AuthorizationService(db).authorize(
            export_context(db, doctor, patient, hospital, consent)
        )
        assert cross_hospital_denial.allowed is False
        assert cross_hospital_denial.reason == DenialReason.RELATIONSHIP_REQUIRED

        db.add(Visit(patient_id=patient.id, doctor_id=doctor.id, hospital_id=hospital.id))
        membership = db.query(HospitalStaff).filter(
            HospitalStaff.user_id == doctor.id,
            HospitalStaff.hospital_id == hospital.id,
        ).one()
        membership.is_active = False
        db.flush()
        membership_denial = AuthorizationService(db).authorize(
            export_context(db, doctor, patient, hospital, consent)
        )
        assert membership_denial.allowed is False
        assert membership_denial.reason == DenialReason.MEMBERSHIP_REQUIRED
    finally:
        db.close()
        engine.dispose()


def test_doctor_fhir_export_denies_wrong_practitioner_organization_and_operation():
    engine, db = make_database()
    try:
        patient, doctor, hospital, consent, policy = seed_authorized_export(db)
        other_doctor = User(
            id=505,
            email="other-doctor@example.test",
            hashed_password="unused",
            role="doctor",
            is_active=True,
        )
        db.add(other_doctor)
        db.flush()

        consent.doctor_id = other_doctor.id
        practitioner_denial = AuthorizationService(db).authorize(
            export_context(db, doctor, patient, hospital, consent)
        )
        assert practitioner_denial.allowed is False
        assert practitioner_denial.reason == DenialReason.RELATIONSHIP_REQUIRED

        consent.doctor_id = doctor.id
        organization_denial = AuthorizationService(db).authorize(export_context(
            db, doctor, patient, hospital, consent, hospital_id=999
        ))
        assert organization_denial.allowed is False
        assert organization_denial.reason == DenialReason.ORGANIZATION_MISMATCH

        operation_denial = AuthorizationService(db).authorize(export_context(
            db, doctor, patient, hospital, consent, operation=Operation.DOWNLOAD
        ))
        assert operation_denial.allowed is False
        assert operation_denial.reason == DenialReason.OPERATION_NOT_ALLOWED

        policy.policy_payload = {
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": ["download"],
        }
        db.flush()
        policy_denial = AuthorizationService(db).authorize(
            export_context(db, doctor, patient, hospital, consent)
        )
        assert policy_denial.allowed is False
        assert "OPERATION_NOT_ALLOWED" in policy_denial.detail
    finally:
        db.close()
        engine.dispose()
