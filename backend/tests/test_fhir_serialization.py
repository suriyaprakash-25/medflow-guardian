import base64

import pytest

from app.models.clinical import ClinicalNote, LabResult, Medication, Prescription
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState, ConsentStatus
from app.models.document import MedicalDocument
from app.models.user import User
from app.services.interoperability.fhir_consent import FHIRConsentError, map_fhir_consent
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
    user = User(
        id=1,
        email="test@example.com",
        full_name="John Doe",
        role="patient",
        is_active=True,
    )
    resource = to_fhir_patient(user)
    assert resource["resourceType"] == "Patient"
    assert resource["id"] == "1"
    assert resource["name"][0]["text"] == "John Doe"


def test_to_fhir_practitioner():
    user = User(
        id=2,
        email="doctor@example.com",
        full_name="Jane Doe",
        role="doctor",
        is_active=True,
    )
    resource = to_fhir_practitioner(user)
    assert resource["resourceType"] == "Practitioner"
    assert resource["id"] == "2"


def test_to_fhir_medication_request_uses_codeable_concept():
    medication = Medication(id=1, name="Aspirin")
    prescription = Prescription(
        id=10,
        patient_id=1,
        doctor_id=2,
        medication=medication,
        is_active=True,
        dosage="100mg",
        frequency="Daily",
    )
    resource = to_fhir_medication_request(prescription)
    assert resource["resourceType"] == "MedicationRequest"
    assert resource["status"] == "active"
    assert resource["medicationCodeableConcept"]["text"] == "Aspirin"
    assert "medicationReference" not in resource
    assert resource["subject"]["reference"] == "Patient/1"


def test_to_fhir_observation_maps_internal_status_to_r4_status():
    lab = LabResult(
        id=5,
        patient_id=1,
        doctor_id=2,
        test_name="Blood Pressure",
        result_value="120/80",
        unit="mmHg",
        reference_range="<120",
        status="pending",
    )
    resource = to_fhir_observation(lab)
    assert resource["resourceType"] == "Observation"
    assert resource["status"] == "preliminary"
    assert resource["code"]["text"] == "Blood Pressure"
    assert resource["valueString"] == "120/80 mmHg"
    assert resource["referenceRange"][0]["text"] == "<120"


def test_clinical_note_attachment_data_is_base64_binary():
    note = ClinicalNote(
        id=8,
        patient_id=1,
        doctor_id=2,
        hospital_id=3,
        title="Progress Note",
        note_type="progress",
        content="Patient improving ✓",
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
    assert "url" not in attachment
    assert document.stored_filename not in str(resource)
    assert attachment["extension"][0]["valueInteger"] == 42


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
    )
    state = ConsentState(
        id=31,
        consent_id=11,
        policy_version_id=21,
        status=ConsentStatus.ACTIVE.value,
    )

    resource = to_fhir_consent(consent, state, policy)
    assert resource["status"] == "active"
    assert resource["scope"]["coding"][0]["code"] == "patient-privacy"
    assert resource["category"][0]["coding"][0]["code"] == "59284-0"
    assert resource["provision"]["action"][0]["coding"][0]["code"] == "disclose"
    assert resource["provision"]["purpose"][0]["code"] == "TREAT"
    assert {a["reference"]["reference"] for a in resource["provision"]["actor"]} == {
        "Practitioner/202",
        "Organization/303",
    }

    mapped = map_fhir_consent(resource, "https://medflow.example.test/fhir")
    assert mapped.patient_id == consent.patient_id
    assert mapped.doctor_id == consent.doctor_id
    assert mapped.hospital_id == consent.hospital_id
    assert mapped.status == ConsentStatus.ACTIVE.value
    assert mapped.policy_payload["allowed_purposes"] == ["TREATMENT"]
    assert mapped.policy_payload["allowed_operations"] == ["download", "read"]


def test_consent_export_fails_if_fhir_action_would_broaden_authority():
    consent = Consent(id=11, patient_id=101, status=ConsentStatus.ACTIVE.value)
    policy = ConsentPolicyVersion(
        id=21,
        consent_id=11,
        version_number=1,
        policy_payload={
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": ["download"],
        },
        status="active",
    )
    state = ConsentState(
        id=31,
        consent_id=11,
        policy_version_id=21,
        status=ConsentStatus.ACTIVE.value,
    )

    with pytest.raises(FHIRConsentError, match="cannot be represented losslessly"):
        to_fhir_consent(consent, state, policy)


def test_revoked_internal_consent_exports_non_authorizing_fhir_status():
    consent = Consent(id=11, patient_id=101, status=ConsentStatus.REVOKED.value)
    policy = ConsentPolicyVersion(
        id=21,
        consent_id=11,
        version_number=1,
        policy_payload={
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": ["read"],
        },
        status="active",
    )
    state = ConsentState(
        id=31,
        consent_id=11,
        policy_version_id=21,
        status=ConsentStatus.REVOKED.value,
    )
    resource = to_fhir_consent(consent, state, policy)
    assert resource["status"] == "inactive"


def test_to_fhir_bundle_uses_collection_semantics():
    user = User(
        id=1,
        email="test@example.com",
        full_name="John Doe",
        role="patient",
        is_active=True,
    )
    patient = to_fhir_patient(user)
    bundle = to_fhir_bundle([patient])
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert bundle["total"] == 1
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"
