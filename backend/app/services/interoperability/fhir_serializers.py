from __future__ import annotations

import base64
from typing import Any, Dict, List

from app.models.user import User
from app.models.hospital import Hospital
from app.models.clinical import Prescription, LabResult, ClinicalNote
from app.models.document import MedicalDocument
from app.models.consent import Consent, ConsentState, ConsentPolicyVersion
from app.services.interoperability.fhir_consent import (
    FHIR_ACTION_SYSTEM,
    FHIR_CATEGORY_CODE,
    FHIR_CATEGORY_SYSTEM,
    FHIR_PURPOSE_SYSTEM,
    FHIR_SCOPE_CODE,
    FHIR_SCOPE_SYSTEM,
    MEDFLOW_ACTOR_ROLE_SYSTEM,
    MEDFLOW_POLICY_URI,
    medflow_operations_to_fhir_actions,
    medflow_purposes_to_fhir_codes,
    medflow_status_to_fhir_status,
)


def to_fhir_patient(user: User) -> Dict[str, Any]:
    """Serialize a User (Patient) to the supported FHIR R4 Patient subset."""
    resource: Dict[str, Any] = {
        "resourceType": "Patient",
        "id": str(user.id),
        "active": bool(user.is_active),
        "name": [{"text": user.full_name or user.email}],
        "telecom": [{"system": "email", "value": user.email}],
    }
    if user.phone_number:
        resource["telecom"].append({"system": "phone", "value": user.phone_number})
    return resource


def to_fhir_practitioner(user: User) -> Dict[str, Any]:
    """Serialize a User (Doctor) to the supported FHIR R4 Practitioner subset."""
    return {
        "resourceType": "Practitioner",
        "id": str(user.id),
        "active": bool(user.is_active),
        "name": [{"text": f"Dr. {user.full_name or user.email}"}],
        "telecom": [{"system": "email", "value": user.email}],
    }


def to_fhir_organization(hospital: Hospital) -> Dict[str, Any]:
    """Serialize a Hospital to the supported FHIR R4 Organization subset."""
    resource: Dict[str, Any] = {
        "resourceType": "Organization",
        "id": str(hospital.id),
        "active": bool(hospital.is_active),
        "name": hospital.name,
    }
    if hospital.address:
        resource["address"] = [{"text": hospital.address}]
    if hospital.contact_info:
        resource["telecom"] = [{"system": "other", "value": hospital.contact_info}]
    return resource


def _actor(role_code: str, resource_type: str, resource_id: int) -> Dict[str, Any]:
    return {
        "role": {
            "coding": [
                {
                    "system": MEDFLOW_ACTOR_ROLE_SYSTEM,
                    "code": role_code,
                }
            ],
            "text": role_code,
        },
        "reference": {"reference": f"{resource_type}/{resource_id}"},
    }


def to_fhir_consent(
    consent: Consent,
    state: ConsentState,
    policy: ConsentPolicyVersion,
) -> Dict[str, Any]:
    """Serialize authoritative MedFlow consent as the canonical FHIR R4 subset.

    Export is fail-closed: purposes/operations that cannot be represented without
    broadening authority raise ``FHIRConsentError`` in the shared semantic mapper.
    """
    payload = policy.policy_payload or {}
    allowed_purposes = payload.get("allowed_purposes", [])
    allowed_operations = payload.get("allowed_operations", [])
    purpose_codes = medflow_purposes_to_fhir_codes(allowed_purposes)
    action_codes = medflow_operations_to_fhir_actions(allowed_operations)

    provision: Dict[str, Any] = {
        "type": "permit",
        "purpose": [
            {"system": FHIR_PURPOSE_SYSTEM, "code": code}
            for code in purpose_codes
        ],
        "action": [
            {
                "coding": [
                    {"system": FHIR_ACTION_SYSTEM, "code": action}
                ]
            }
            for action in action_codes
        ],
    }

    actors: List[Dict[str, Any]] = []
    if consent.doctor_id is not None:
        actors.append(_actor("recipient", "Practitioner", consent.doctor_id))
    if consent.hospital_id is not None:
        actors.append(_actor("custodian", "Organization", consent.hospital_id))
    if actors:
        provision["actor"] = actors

    return {
        "resourceType": "Consent",
        "id": str(consent.id),
        "status": medflow_status_to_fhir_status(state.status),
        "scope": {
            "coding": [
                {"system": FHIR_SCOPE_SYSTEM, "code": FHIR_SCOPE_CODE}
            ]
        },
        "category": [
            {
                "coding": [
                    {"system": FHIR_CATEGORY_SYSTEM, "code": FHIR_CATEGORY_CODE}
                ]
            }
        ],
        "patient": {"reference": f"Patient/{consent.patient_id}"},
        "policy": [{"uri": MEDFLOW_POLICY_URI}],
        "provision": provision,
        "extension": [
            {
                "url": "https://medflowguardian.example/fhir/StructureDefinition/consent-policy-version",
                "valueInteger": policy.version_number,
            },
            {
                "url": "https://medflowguardian.example/fhir/StructureDefinition/consent-state-id",
                "valueInteger": state.id,
            },
            {
                "url": "https://medflowguardian.example/fhir/StructureDefinition/medflow-consent-status",
                "valueCode": state.status,
            },
        ],
    }


def to_fhir_medication_request(prescription: Prescription) -> Dict[str, Any]:
    """Serialize a Prescription to the supported FHIR R4 MedicationRequest subset."""
    med_display = prescription.medication.name if prescription.medication else "Unknown Medication"
    resource: Dict[str, Any] = {
        "resourceType": "MedicationRequest",
        "id": str(prescription.id),
        "status": "active" if prescription.is_active else "completed",
        "intent": "order",
        "medicationCodeableConcept": {"text": med_display},
        "subject": {"reference": f"Patient/{prescription.patient_id}"},
        "requester": {"reference": f"Practitioner/{prescription.doctor_id}"},
        "dosageInstruction": [
            {"text": f"{prescription.dosage} {prescription.frequency}"}
        ],
    }
    if prescription.created_at:
        resource["authoredOn"] = prescription.created_at.isoformat()
    if prescription.start_date:
        validity = {"start": prescription.start_date.isoformat()}
        if prescription.end_date:
            validity["end"] = prescription.end_date.isoformat()
        resource["dispenseRequest"] = {"validityPeriod": validity}
    return resource


def to_fhir_observation(lab: LabResult) -> Dict[str, Any]:
    """Serialize a LabResult to the supported FHIR R4 Observation subset."""
    status_map = {
        "pending": "preliminary",
        "completed": "final",
        "cancelled": "cancelled",
    }
    resource: Dict[str, Any] = {
        "resourceType": "Observation",
        "id": str(lab.id),
        "status": status_map.get(lab.status, "unknown"),
        "code": {"text": lab.test_name},
        "subject": {"reference": f"Patient/{lab.patient_id}"},
        "performer": [{"reference": f"Practitioner/{lab.doctor_id}"}],
        "valueString": f"{lab.result_value}{(' ' + lab.unit) if lab.unit else ''}",
    }
    if lab.reference_range:
        resource["referenceRange"] = [{"text": lab.reference_range}]
    if lab.test_date:
        resource["effectiveDateTime"] = lab.test_date.isoformat()
    return resource


def to_fhir_document_reference_note(note: ClinicalNote) -> Dict[str, Any]:
    """Serialize a ClinicalNote as a FHIR R4 DocumentReference.

    Attachment.data is base64Binary in FHIR. Raw clinical text must never be
    placed directly in that field.
    """
    encoded_content = base64.b64encode(note.content.encode("utf-8")).decode("ascii")
    resource: Dict[str, Any] = {
        "resourceType": "DocumentReference",
        "id": f"clinical-note-{note.id}",
        "status": "current",
        "type": {"text": note.note_type or note.title},
        "description": note.title,
        "subject": {"reference": f"Patient/{note.patient_id}"},
        "author": [{"reference": f"Practitioner/{note.doctor_id}"}],
        "content": [
            {
                "attachment": {
                    "contentType": "text/plain; charset=utf-8",
                    "title": note.title,
                    "data": encoded_content,
                }
            }
        ],
    }
    if note.created_at:
        resource["date"] = note.created_at.isoformat()
    return resource


def to_fhir_document_reference_file(doc: MedicalDocument) -> Dict[str, Any]:
    """Serialize protected document metadata without exposing storage internals.

    The private Supabase object key is intentionally not exported as an
    Attachment.url. Binary release must continue through MedFlow's authorized
    download path rather than bypassing the PDP/PEP boundary.
    """
    attachment: Dict[str, Any] = {
        "contentType": doc.mime_type,
        "title": doc.original_filename,
        "size": doc.file_size,
        "extension": [
            {
                "url": "https://medflowguardian.example/fhir/StructureDefinition/protected-document-id",
                "valueInteger": doc.id,
            }
        ],
    }
    resource: Dict[str, Any] = {
        "resourceType": "DocumentReference",
        "id": f"medical-document-{doc.id}",
        "status": "current" if doc.status == "active" else "superseded",
        "type": {"text": doc.document_type},
        "subject": {"reference": f"Patient/{doc.patient_id}"},
        "author": [
            {"reference": f"Practitioner/{doc.uploaded_by_doctor_id}"}
        ],
        "content": [{"attachment": attachment}],
    }
    if doc.title:
        resource["description"] = doc.description or doc.title
    if doc.created_at:
        resource["date"] = doc.created_at.isoformat()
    return resource


def to_fhir_bundle(resources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Wrap exported resources in a FHIR R4 collection Bundle."""
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "total": len(resources),
        "entry": [{"resource": resource} for resource in resources],
    }
