from app.models.user import User
from app.models.hospital import Hospital
from app.models.clinical import Prescription, LabResult, ClinicalNote
from app.models.document import MedicalDocument
from typing import List, Dict, Any

def to_fhir_patient(user: User) -> Dict[str, Any]:
    """Serialize a User (Patient) to FHIR R4 Patient."""
    return {
        "resourceType": "Patient",
        "id": str(user.id),
        "active": user.is_active,
        "name": [{"text": user.full_name}],
        "telecom": [{"system": "email", "value": user.email}]
    }

def to_fhir_practitioner(user: User) -> Dict[str, Any]:
    """Serialize a User (Doctor) to FHIR R4 Practitioner."""
    return {
        "resourceType": "Practitioner",
        "id": str(user.id),
        "active": user.is_active,
        "name": [{"text": f"Dr. {user.full_name}"}],
        "telecom": [{"system": "email", "value": user.email}]
    }

def to_fhir_organization(hospital: Hospital) -> Dict[str, Any]:
    """Serialize a Hospital to FHIR R4 Organization."""
    return {
        "resourceType": "Organization",
        "id": str(hospital.id),
        "name": hospital.name,
        "address": [{"text": hospital.address}] if hospital.address else []
    }

def to_fhir_medication_request(prescription: Prescription) -> Dict[str, Any]:
    """Serialize a Prescription to FHIR R4 MedicationRequest."""
    med_display = "Unknown Medication"
    if prescription.medication:
        med_display = prescription.medication.name
        
    return {
        "resourceType": "MedicationRequest",
        "id": str(prescription.id),
        "status": "active" if prescription.is_active else "completed",
        "intent": "order",
        "medicationReference": {
            "display": med_display
        },
        "subject": {"reference": f"Patient/{prescription.patient_id}"},
        "requester": {"reference": f"Practitioner/{prescription.doctor_id}"},
        "dosageInstruction": [{"text": f"{prescription.dosage} {prescription.frequency}"}]
    }

def to_fhir_observation(lab: LabResult) -> Dict[str, Any]:
    """Serialize a LabResult to FHIR R4 Observation."""
    val = f"{lab.result_value}"
    if lab.unit:
        val += f" {lab.unit}"
        
    return {
        "resourceType": "Observation",
        "id": str(lab.id),
        "status": "final",
        "code": {"text": lab.test_name},
        "subject": {"reference": f"Patient/{lab.patient_id}"},
        "performer": [{"reference": f"Practitioner/{lab.doctor_id}"}],
        "valueString": val,
        "referenceRange": [{"text": lab.reference_range}] if lab.reference_range else []
    }

def to_fhir_document_reference_note(note: ClinicalNote) -> Dict[str, Any]:
    """Serialize a ClinicalNote to FHIR R4 DocumentReference."""
    return {
        "resourceType": "DocumentReference",
        "id": str(note.id),
        "status": "current",
        "type": {"text": note.title},
        "subject": {"reference": f"Patient/{note.patient_id}"},
        "author": [{"reference": f"Practitioner/{note.doctor_id}"}],
        "content": [{"attachment": {"title": note.title, "data": note.content}}]
    }

def to_fhir_document_reference_file(doc: MedicalDocument) -> Dict[str, Any]:
    """Serialize a MedicalDocument to FHIR R4 DocumentReference."""
    return {
        "resourceType": "DocumentReference",
        "id": str(doc.id),
        "status": "current",
        "type": {"text": doc.document_type},
        "subject": {"reference": f"Patient/{doc.patient_id}"},
        "author": [{"reference": f"Practitioner/{doc.uploaded_by}"}],
        "content": [{"attachment": {"url": doc.file_path, "title": doc.filename}}]
    }

def to_fhir_bundle(resources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Wrap a list of FHIR resources in a SearchSet Bundle."""
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(resources),
        "entry": [{"resource": res} for res in resources]
    }
