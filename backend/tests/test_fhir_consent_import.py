from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState, ConsentStatus
from app.models.hospital import Hospital, HospitalStaff
from app.models.user import User
from app.services.authorization import AuthorizationContext, AuthorizationService, Operation, ResourceType
from app.services.interoperability.fhir_consent import (
    FHIRConsentError,
    FHIRConsentImporter,
    map_fhir_consent,
)


def fhir_consent() -> dict:
    return {
        "resourceType": "Consent",
        "id": "external-consent-1",
        "meta": {"versionId": "7", "lastUpdated": "2026-09-12T08:30:00Z"},
        "status": "active",
        "scope": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/consentscope", "code": "patient-privacy"}]
        },
        "category": [{
            "coding": [{"system": "http://loinc.org", "code": "59284-0"}]
        }],
        "patient": {"reference": "Patient/101"},
        "policy": [{"uri": "https://example.test/policies/privacy"}],
        "provision": {
            "type": "permit",
            "actor": [
                {"role": {"text": "recipient"}, "reference": {"reference": "Practitioner/202"}},
                {"role": {"text": "custodian"}, "reference": {"reference": "Organization/303"}},
            ],
            "action": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/consentaction",
                    "code": "disclose",
                }]
            }],
            "purpose": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActReason",
                "code": "TREAT",
            }],
        },
    }


def test_maps_supported_active_consent_deterministically():
    mapped = map_fhir_consent(fhir_consent(), "https://fhir.example.test/")

    assert mapped.source_resource_id == "external-consent-1"
    assert mapped.patient_id == 101
    assert mapped.doctor_id == 202
    assert mapped.hospital_id == 303
    assert mapped.status == ConsentStatus.ACTIVE.value
    assert mapped.policy_payload["allowed_purposes"] == ["TREATMENT"]
    assert mapped.policy_payload["allowed_operations"] == ["download", "read"]
    assert mapped.policy_payload["fhir"]["source_system"] == "https://fhir.example.test"
    assert mapped.policy_payload["fhir"]["version_id"] == "7"


@pytest.mark.parametrize(
    ("fhir_status", "expected"),
    [
        ("draft", ConsentStatus.DRAFT.value),
        ("proposed", ConsentStatus.DRAFT.value),
        ("active", ConsentStatus.ACTIVE.value),
        ("rejected", ConsentStatus.CANCELLED.value),
        ("inactive", ConsentStatus.REVOKED.value),
        ("entered-in-error", ConsentStatus.CANCELLED.value),
    ],
)
def test_maps_every_fhir_r4_status(fhir_status, expected):
    resource = fhir_consent()
    resource["status"] = fhir_status
    assert map_fhir_consent(resource, "https://fhir.example.test").status == expected


def test_expired_active_period_maps_to_expired():
    resource = fhir_consent()
    resource["provision"]["period"] = {
        "end": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    }
    assert map_fhir_consent(resource, "https://fhir.example.test").status == ConsentStatus.EXPIRED.value


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda r: r.update(resourceType="Patient"), "resourceType must be Consent"),
        (lambda r: r["provision"].update(type="deny"), "Deny provisions are not supported"),
        (lambda r: r["provision"].update(provision=[{"type": "permit"}]), "Nested provisions are not supported"),
        (lambda r: r["provision"]["action"][0]["coding"][0].update(code="execute"), "Unsupported consent action"),
        (lambda r: r["provision"]["purpose"][0].update(code="UNKNOWN"), "Unsupported purpose"),
        (lambda r: r["patient"].update(reference="Patient/external-id"), "numeric Patient"),
    ],
)
def test_rejects_unsupported_or_ambiguous_policy(mutation, message):
    resource = deepcopy(fhir_consent())
    mutation(resource)
    with pytest.raises(FHIRConsentError, match=message):
        map_fhir_consent(resource, "https://fhir.example.test")


def test_rejects_unsafe_source_url():
    with pytest.raises(FHIRConsentError, match="without credentials"):
        map_fhir_consent(fhir_consent(), "https://user:secret@fhir.example.test")


def test_import_is_idempotent_and_changed_resource_creates_new_version():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Hospital.__table__,
            HospitalStaff.__table__,
            Consent.__table__,
            ConsentPolicyVersion.__table__,
            ConsentState.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    try:
        patient = User(
            id=101,
            email="patient101@example.test",
            hashed_password="unused",
            full_name="Patient 101",
            role="patient",
            is_active=True,
        )
        doctor = User(
            id=202,
            email="doctor202@example.test",
            hashed_password="unused",
            full_name="Doctor 202",
            role="doctor",
            is_active=True,
        )
        hospital = Hospital(id=303, name="Test Hospital", is_active=True)
        session.add_all([patient, doctor, hospital])
        session.flush()
        session.add(HospitalStaff(user_id=202, hospital_id=303, is_active=True))
        session.flush()

        importer = FHIRConsentImporter(session)
        first = importer.import_consent(fhir_consent(), "https://fhir.example.test", patient)
        assert first.created is True
        assert first.policy.version_number == 1
        assert first.state.status == ConsentStatus.ACTIVE.value

        identical = importer.import_consent(fhir_consent(), "https://fhir.example.test", patient)
        assert identical.created is False
        assert identical.policy.id == first.policy.id
        assert session.query(ConsentPolicyVersion).count() == 1
        assert session.query(ConsentState).count() == 1

        changed = fhir_consent()
        changed["meta"]["versionId"] = "8"
        changed["status"] = "inactive"
        updated = importer.import_consent(changed, "https://fhir.example.test", patient)
        assert updated.created is False
        assert updated.policy.version_number == 2
        assert updated.state.status == ConsentStatus.REVOKED.value
        assert first.policy.status == "superseded"
        assert session.query(Consent).count() == 1
        assert session.query(ConsentPolicyVersion).count() == 2
        assert session.query(ConsentState).count() == 2
    finally:
        session.close()
        engine.dispose()


def test_consent_authorization_is_patient_owned_and_default_deny():
    service = AuthorizationService(db=None)
    patient = User(id=101, role="patient", is_active=True)
    doctor = User(id=202, role="doctor", is_active=True)

    own = service._authorize_consent(AuthorizationContext(
        actor=patient,
        operation=Operation.CREATE,
        resource_type=ResourceType.CONSENT,
        db=None,
        patient_id=101,
    ))
    other_patient = service._authorize_consent(AuthorizationContext(
        actor=patient,
        operation=Operation.CREATE,
        resource_type=ResourceType.CONSENT,
        db=None,
        patient_id=999,
    ))
    doctor_write = service._authorize_consent(AuthorizationContext(
        actor=doctor,
        operation=Operation.CREATE,
        resource_type=ResourceType.CONSENT,
        db=None,
        patient_id=101,
    ))
    patient_delete = service._authorize_consent(AuthorizationContext(
        actor=patient,
        operation=Operation.DELETE,
        resource_type=ResourceType.CONSENT,
        db=None,
        patient_id=101,
    ))

    assert own.allowed is True
    assert other_patient.allowed is False
    assert doctor_write.allowed is False
    assert patient_delete.allowed is False
