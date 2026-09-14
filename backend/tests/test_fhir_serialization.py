import base64
from datetime import date, datetime, timezone

import pytest

from app.models.clinical import ClinicalNote, LabResult, Medication, Prescription
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState, ConsentStatus
from app.models.document import MedicalDocument
from app.models.user import PractitionerProfile, User
from app.services.interoperability.fhir_consent import FHIRConsentValidationError
from app.services.interoperability.fhir_serializers import (
    to_fhir_bundle,
    to_fhir_consent,
    to_fhir_document_reference_file,
    to_fhir_document_reference_note,
    to_fhir_medication_request,
    to_fhir_observation,
    to_fhir_patient,
    to_fhir_practitioner,
)


def test_to_fhir_patient():
    user = User(id=1, email="patient@example.com", full_name="Pat Example")
    profile = type(
        "Profile",
        (),
        {
            "id": 1,
            "user": user,
            "date_of_birth": date(1990, 1, 2),
            "gender": "female",
            "address": "123 Main St",
        },
    )()
    resource = to_fhir_patient(profile)
    assert resource["resourceType"] == "Patient"
    assert resource["id"] == "1"
    assert resource["name"][0]["text"] == "Pat Example"
    assert resource["birthDate"] == "1990-01-02"


def test_to_fhir_practitioner():
    user = User(id=2, email="doctor@example.com", full_name="Doc Example")
    profile = PractitionerProfile(
        id=2,
        user_id=2,
        medical_license_number="LIC-123",
        specialty="cardiology",
    )
    profile.user = user
    resource = to_fhir_practitioner(profile)
    assert resource["resourceType"] == "Practitioner"
    assert resource["id"] == "2"
    assert resource["identifier"][0]["value"] == "LIC-123"


def test_to_fhir_medication_request_uses_codeable_concept():
    prescription = Prescription(
        id=9,
        patient_id=1,
        doctor_id=2,
        medication_id=3,
        dosage="10 mg",
        frequency="daily",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 7),
        is_active=True,
    )
    prescription.medication = Medication(id=3, name="Example Drug")
    resource = to_fhir_medication_request(prescription)
    assert resource["resourceType"] == "MedicationRequest"
    assert resource["medicationCodeableConcept"]["text"] == "Example Drug"
    assert "medicationReference" not in resource


def test_to_fhir_observation_maps_internal_status_to_r4_status():
    lab = LabResult(
        id=7,
        patient_id=1,
        doctor_id=2,
        test_name="CBC",
        result_value="Normal",
        status="completed",
    )
    resource = to_fhir_observation(lab)
    assert resource["resourceType"] == "Observation"
    assert resource["status"] == "final"


def test_clinical_note_attachment_data_is_base64_binary():
    note = ClinicalNote(
        id=8,
        patient_id=1,
        doctor_id=2,
        title="Progress note",
        content="Sensitive clinical text",
        note_type="progress",
    )
    resource = to_fhir_document_reference_note(note)
    attachment = resource["content"][0]["attachment"]
    decoded = base64.b64decode(attachment["data"]).decode("utf-8")
    assert decoded == note.content
    assert attachment["contentType"].startswith("text/plain")
    assert attachment["data"] != note.content


def test_protected_document_reference_does_not_expose_storage_key():
    document = MedicalDocument(
        id=42,
        patient_id=1,
        hospital_id=3,
        uploaded_by_doctor_id=2,
        document_type="lab report",
        title="CBC",
        description="CBC result",
        original_filename="cbc.pdf",
        stored_filename="private/tenant-3/secret-object-key.pdf",
        mime_type="application/pdf",
        file_size=1234,
        status="active",
    )
    resource = to_fhir_document_reference_file(document)
    attachment = resource["content"][0]["attachment"]
    assert resource["id"] == "medical-document-42"
    assert "url" not in attachment
    assert "extension" not in attachment
    assert document.stored_filename not in str(resource)


def test_medflow_consent_round_trips_through_one_canonical_profile():
    consent = Consent(
        id=11,
        patient_id=101,
        doctor_id=202,
        hospital_id=303,
        status=ConsentStatus.ACTIVE.value,
    )
    policy = ConsentPolicyVersion(
        id=21,
        consent_id=11,
        version_number=4,
        policy_payload={
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": ["read", "download"],
        },
        status="active",
        valid_from=datetime(2026, 9, 1, tzinfo=timezone.utc),
        valid_until=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    state = ConsentState(
        id=31,
        consent_id=11,
        policy_version_id=21,
        status=ConsentStatus.ACTIVE.value,
    )
    resource = to_fhir_consent(consent, policy, state)
    assert resource["resourceType"] == "Consent"
    assert resource["status"] == "active"
    assert resource["patient"]["reference"] == "Patient/101"
    assert resource["provision"]["type"] == "permit"
    assert {item["coding"][0]["code"] for item in resource["provision"]["action"]} == {
        "access",
    }
    assert resource["provision"]["period"] == {
        "start": "2026-09-01T00:00:00+00:00",
        "end": "2026-10-01T00:00:00+00:00",
    }


def test_consent_export_fails_if_fhir_action_would_broaden_authority():
    consent = Consent(
        id=12,
        patient_id=101,
        doctor_id=202,
        hospital_id=303,
        status=ConsentStatus.ACTIVE.value,
    )
    policy = ConsentPolicyVersion(
        id=22,
        consent_id=12,
        version_number=1,
        policy_payload={
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": ["delete"],
        },
        status="active",
    )
    state = ConsentState(
        id=32,
        consent_id=12,
        policy_version_id=22,
        status=ConsentStatus.ACTIVE.value,
    )
    with pytest.raises(FHIRConsentValidationError):
        to_fhir_consent(consent, policy, state)


def test_revoked_internal_consent_exports_non_authorizing_fhir_status():
    consent = Consent(
        id=13,
        patient_id=101,
        doctor_id=202,
        hospital_id=303,
        status=ConsentStatus.REVOKED.value,
    )
    policy = ConsentPolicyVersion(
        id=23,
        consent_id=13,
        version_number=1,
        policy_payload={
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": ["read"],
        },
        status="active",
    )
    state = ConsentState(
        id=33,
        consent_id=13,
        policy_version_id=23,
        status=ConsentStatus.REVOKED.value,
    )
    resource = to_fhir_consent(consent, policy, state)
    assert resource["status"] == "inactive"


def test_to_fhir_bundle_uses_collection_semantics():
    resources = [{"resourceType": "Patient", "id": "1"}]
    bundle = to_fhir_bundle(resources)
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert bundle["entry"][0]["resource"] == resources[0]
