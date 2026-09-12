from app.models.user import User
from app.models.hospital import Hospital
from app.models.clinical import Prescription, LabResult, ClinicalNote
from app.models.document import MedicalDocument
from app.models.consent import Consent, ConsentState, ConsentPolicyVersion
from typing import List, Dict, Any, Optional


def to_fhir_patient(user: User) -> Dict[str, Any]:
    """Serialize a User (Patient) to FHIR R4 Patient."""
    resource = {
        "resourceType": "Patient",
        "id": str(user.id),
        "active": user.is_active,
        "name": [{"text": user.full_name or user.email}],
        "telecom": [{"system": "email", "value": user.email}],
    }
    if user.phone_number:
        resource["telecom"].append({"system": "phone", "value": user.phone_number})
    return resource


def to_fhir_practitioner(user: User) -> Dict[str, Any]:
    """Serialize a User (Doctor) to FHIR R4 Practitioner."""
    return {
        "resourceType": "Practitioner",
        "id": str(user.id),
        "active": user.is_active,
        "name": [{"text": f"Dr. {user.full_name or user.email}"}],
        "telecom": [{"system": "email", "value": user.email}],
    }


def to_fhir_organization(hospital: Hospital) -> Dict[str, Any]:
    """Serialize a Hospital to FHIR R4 Organization."""
    resource = {
        "resourceType": "Organization",
        "id": str(hospital.id),
        "active": hospital.is_active,
        "name": hospital.name,
    }
    if hospital.address:
        resource["address"] = [{"text": hospital.address}]
    if hospital.contact_info:
        resource["telecom"] = [{"system": "other", "value": hospital.contact_info}]
    return resource


def to_fhir_consent(
    consent: Consent,
    state: ConsentState,
    policy: ConsentPolicyVersion,
) -> Dict[str, Any]:
    """Serialize the authoritative MedFlow consent state as FHIR R4 Consent.

    MedFlow policy values are retained in a vendor extension so importing systems
    can round-trip the exact purpose/operation policy without inventing FHIR codes.
    """
    allowed_purposes = policy.policy_payload.get("allowed_purposes", [])
    allowed_operations = policy.policy_payload.get("allowed_operations", [])

    provision: Dict[str, Any] = {}
    purpose_codings = [
        {"system": "https://medflowguardian.example/fhir/purpose", "code": str(value)}
        for value in allowed_purposes
    ]
    if purpose_codings:
        provision["purpose"] = purpose_codings

    action_map = {
        "READ": "access",
        "DOWNLOAD": "disclose",
        "CREATE": "access",
        "UPDATE": "access",
        "DELETE": "access",
    }
    actions = []
    for operation in allowed_operations:
        action = action_map.get(str(operation).upper())
        if action and action not in actions:
            actions.append(action)
    if actions:
        provision["action"] = [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/consentaction", "code": action}]} for action in actions]

    resource: Dict[str, Any] = {
        "resourceType": "Consent",
        "id": str(consent.id),
        "status": state.status,
        "patient": {"reference": f"Patient/{consent.patient_id}"},
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
                "url": "https://medflowguardian.example/fhir/StructureDefinition/allowed-operations",
                "valueString": ",".join(str(value) for value in allowed_operations),
            },
        ],
    }
    if consent.doctor_id:
        resource["performer"] = [{"reference": f"Practitioner/{consent.doctor_id}"}]
    if consent.hospital_id:
        resource["organization"] = [{"reference": f"Organization/{consent.hospital_id}"}]
    return resource


def to_fhir_medication_request(prescription: Prescription) -> Dict[str, Any]:
    """Serialize a Prescription to FHIR R4 MedicationRequest."""
    med_display = prescription.medication.name if prescription.medication else "Unknown Medication"
    resource = {
        "resourceType": "MedicationRequest",
        "id": str(prescription.id),
        "status": "active" if prescription.is_active else "completed",
        "intent": "order",
        "medicationReference": {"display": med_display},
        "subject": {"reference": f"Patient/{prescription.patient_id}"},
        "requester": {"reference": f"Practitioner/{prescription.doctor_id}"},
        "dosageInstruction": [{"text": f"{prescription.dosage} {prescription.frequency}"}],
        "authoredOn": prescription.created_at.isoformat() if prescription.created_at else None,
    }
    if prescription.start_date:
        resource["dispenseRequest"] = {"validityPeriod": {"start": prescription.start_date.date().isoformat()}}
        if prescription.end_date:
            resource["dispenseRequest"]["validityPeriod"]["end"] = prescription.end_date.date().isoformat()
    return resource


def to_fhir_observation(lab: LabResult) -> Dict[str, Any]:
    """Serialize a LabResult to FHIR R4 Observation."""
    resource = {
        "resourceType": "Observation",
        "id": str(lab.id),
        "status": "final" if lab.status == "completed" else lab.status,
        "code": {"text": lab.test_name},
        "subject": {"reference": f"Patient/{lab.patient_id}"},
        "performer": [{"reference": f"Practitioner/{lab.doctor_id}"}],
        "valueString": f"{lab.result_value}{(' ' + lab.unit) if lab.unit else ''}",
        "referenceRange": [{"text": lab.reference_range}] if lab.reference_range else [],
    }
    if lab.test_date:
        resource["effectiveDateTime"] = lab.test_date.isoformat()
    return resource


def to_fhir_document_reference_note(note: ClinicalNote) -> Dict[str, Any]:
    """Serialize a ClinicalNote to FHIR R4 DocumentReference."""
    return {
        "resourceType": "DocumentReference",
        "id": str(note.id),
        "status": "current",
        "type": {"text": note.note_type or note.title},
        "description": note.title,
        "subject": {"reference": f"Patient/{note.patient_id}"},
        "author": [{"reference": f"Practitioner/{note.doctor_id}"}],
        "date": note.created_at.isoformat() if note.created_at else None,
        "content": [{"attachment": {"title": note.title, "data": note.content}}],
    }


def to_fhir_document_reference_file(doc: MedicalDocument) -> Dict[str, Any]:
    """Serialize a MedicalDocument to FHIR R4 DocumentReference."""
    return {
        "resourceType": "DocumentReference",
        "id": str(doc.id),
        "status": "current" if doc.status == "active" else "superseded",
        "type": {"text": doc.document_type},
        "description": doc.description,
        "subject": {"reference": f"Patient/{doc.patient_id}"},
        "author": [{"reference": f"Practitioner/{doc.uploaded_by_doctor_id}"}],
        "date": doc.created_at.isoformat() if doc.created_at else None,
        "content": [{"attachment": {"url": doc.stored_filename, "title": doc.original_filename, "contentType": doc.mime_type}}],
    }


def to_fhir_bundle(resources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Wrap a list of FHIR resources in a FHIR R4 searchset Bundle."""
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(resources),
        "entry": [{"resource": res} for res in resources],
    }
