from copy import deepcopy

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


SOURCE_SYSTEM = "https://fhir.example.test"


def fhir_consent() -> dict:
    return {
        "resourceType": "Consent",
        "id": "external-consent-1",
        "meta": {"versionId": "7", "lastUpdated": "2026-09-12T08:30:00Z"},
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
        "patient": {"reference": "Patient/101"},
        "policy": [{"uri": "https://example.test/policies/privacy"}],
        "provision": {
            "type": "permit",
            "actor": [
                {
                    "role": {"text": "recipient"},
                    "reference": {"reference": "Practitioner/202"},
                },
                {
                    "role": {"text": "custodian"},
                    "reference": {"reference": "Organization/303"},
                },
            ],
            "action": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/consentaction",
                            "code": "disclose",
                        }
                    ]
                }
            ],
            "purpose": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActReason",
                    "code": "TREAT",
                }
            ],
        },
    }


def test_maps_supported_active_consent_deterministically():
    mapped = map_fhir_consent(fhir_consent(), SOURCE_SYSTEM + "/")

    assert mapped.source_resource_id == "external-consent-1"
    assert mapped.patient_id == 101
    assert mapped.doctor_id == 202
    assert mapped.hospital_id == 303
    assert mapped.status == ConsentStatus.ACTIVE.value
    assert mapped.policy_payload["allowed_purposes"] == ["TREATMENT"]
    assert mapped.policy_payload["allowed_operations"] == ["download", "read"]
    assert mapped.policy_payload["fhir"]["source_system"] == SOURCE_SYSTEM
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
def test_maps_every_supported_fhir_r4_status(fhir_status, expected):
    resource = fhir_consent()
    resource["status"] = fhir_status
    assert map_fhir_consent(resource, SOURCE_SYSTEM).status == expected


def test_rejects_time_period_until_right_time_is_enforced_dynamically():
    resource = fhir_consent()
    resource["provision"]["period"] = {
        "start": "2026-09-01T00:00:00Z",
        "end": "2026-09-30T23:59:59Z",
    }
    with pytest.raises(FHIRConsentError, match="cannot enforce losslessly: period"):
        map_fhir_consent(resource, SOURCE_SYSTEM)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda r: r.update(resourceType="Patient"), "resourceType must be Consent"),
        (lambda r: r["provision"].update(type="deny"), "Deny provisions are not supported"),
        (lambda r: r["provision"].pop("type"), "must explicitly be permit"),
        (
            lambda r: r["provision"].update(provision=[{"type": "permit"}]),
            "Nested provisions are not supported",
        ),
        (
            lambda r: r["provision"]["action"][0]["coding"][0].update(code="execute"),
            "Unsupported consent action",
        ),
        (
            lambda r: r["provision"]["purpose"][0].update(code="UNKNOWN"),
            "Unsupported purpose",
        ),
        (
            lambda r: r["patient"].update(reference="Patient/external-id"),
            "numeric Patient",
        ),
        (
            lambda r: r["scope"]["coding"][0].update(code="research"),
            "Unsupported Consent.scope",
        ),
        (
            lambda r: r["category"][0]["coding"][0].update(code="not-supported"),
            "Unsupported Consent.category",
        ),
        (
            lambda r: r["provision"]["purpose"][0].update(
                system="https://medflowguardian.example/fhir/purpose"
            ),
            "must include a coding",
        ),
        (
            lambda r: r.update(verification=[{"verified": False}]),
            "lifecycle semantics",
        ),
    ],
)
def test_rejects_unsupported_or_ambiguous_policy(mutation, message):
    resource = deepcopy(fhir_consent())
    mutation(resource)
    with pytest.raises(FHIRConsentError, match=message):
        map_fhir_consent(resource, SOURCE_SYSTEM)


def test_rejects_unsafe_source_url():
    with pytest.raises(FHIRConsentError, match="without credentials"):
        map_fhir_consent(
            fhir_consent(),
            "https://user:secret@fhir.example.test",
        )


def test_import_is_idempotent_conflict_aware_and_versions_real_updates():
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
        session.add(
            HospitalStaff(
                user_id=202,
                hospital_id=303,
                is_active=True,
            )
        )
        session.flush()

        importer = FHIRConsentImporter(session)
        first = importer.import_consent(fhir_consent(), SOURCE_SYSTEM, patient)
        assert first.created is True
        assert first.policy.version_number == 1
        assert first.state.status == ConsentStatus.ACTIVE.value

        identical = importer.import_consent(fhir_consent(), SOURCE_SYSTEM, patient)
        assert identical.created is False
        assert identical.policy.id == first.policy.id
        assert session.query(ConsentPolicyVersion).count() == 1
        assert session.query(ConsentState).count() == 1

        conflict = fhir_consent()
        conflict["provision"]["purpose"][0]["code"] = "HPAYMT"
        with pytest.raises(FHIRConsentError, match="Conflicting FHIR Consent content"):
            importer.import_consent(conflict, SOURCE_SYSTEM, patient)

        scope_conflict = fhir_consent()
        scope_conflict["provision"]["actor"] = [
            scope_conflict["provision"]["actor"][0]
        ]
        with pytest.raises(FHIRConsentError, match="Conflicting FHIR Consent content"):
            importer.import_consent(scope_conflict, SOURCE_SYSTEM, patient)

        assert session.query(ConsentPolicyVersion).count() == 1
        assert session.query(ConsentState).count() == 1

        changed = fhir_consent()
        changed["meta"]["versionId"] = "8"
        changed["meta"]["lastUpdated"] = "2026-09-12T09:30:00Z"
        changed["status"] = "inactive"
        updated = importer.import_consent(changed, SOURCE_SYSTEM, patient)
        assert updated.created is False
        assert updated.policy.version_number == 2
        assert updated.state.status == ConsentStatus.REVOKED.value
        assert first.policy.status == "superseded"
        assert session.query(Consent).count() == 1
        assert session.query(ConsentPolicyVersion).count() == 2
        assert session.query(ConsentState).count() == 2

        stale_replay = fhir_consent()
        stale_replay["meta"]["versionId"] = "9"
        stale_replay["meta"]["lastUpdated"] = "2026-09-12T08:45:00Z"
        with pytest.raises(FHIRConsentError, match="Stale or replayed"):
            importer.import_consent(stale_replay, SOURCE_SYSTEM, patient)
        assert session.query(ConsentPolicyVersion).count() == 2
        assert session.query(ConsentState).count() == 2
    finally:
        session.close()
        engine.dispose()


def test_consent_authorization_is_patient_owned_and_default_deny():
    service = AuthorizationService(db=None)
    patient = User(id=101, role="patient", is_active=True)
    doctor = User(id=202, role="doctor", is_active=True)

    own = service._authorize_consent(
        AuthorizationContext(
            actor=patient,
            operation=Operation.CREATE,
            resource_type=ResourceType.CONSENT,
            db=None,
            patient_id=101,
        )
    )
    other_patient = service._authorize_consent(
        AuthorizationContext(
            actor=patient,
            operation=Operation.CREATE,
            resource_type=ResourceType.CONSENT,
            db=None,
            patient_id=999,
        )
    )
    doctor_write = service._authorize_consent(
        AuthorizationContext(
            actor=doctor,
            operation=Operation.CREATE,
            resource_type=ResourceType.CONSENT,
            db=None,
            patient_id=101,
        )
    )
    patient_delete = service._authorize_consent(
        AuthorizationContext(
            actor=patient,
            operation=Operation.DELETE,
            resource_type=ResourceType.CONSENT,
            db=None,
            patient_id=101,
        )
    )

    assert own.allowed is True
    assert other_patient.allowed is False
    assert doctor_write.allowed is False
    assert patient_delete.allowed is False
