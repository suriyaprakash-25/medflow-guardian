from app.models.user import User
from app.models.clinical import Prescription, Medication, LabResult, ClinicalNote
from app.models.document import MedicalDocument
from app.services.interoperability.fhir_serializers import (
    to_fhir_patient,
    to_fhir_practitioner,
    to_fhir_medication_request,
    to_fhir_observation,
    to_fhir_document_reference_note,
    to_fhir_document_reference_file,
    to_fhir_bundle
)
import datetime

def test_to_fhir_patient():
    u = User(id=1, email="test@example.com", full_name="John Doe", role="patient", is_active=True)
    res = to_fhir_patient(u)
    assert res["resourceType"] == "Patient"
    assert res["id"] == "1"
    assert res["name"][0]["text"] == "John Doe"

def test_to_fhir_medication_request():
    m = Medication(id=1, name="Aspirin")
    p = Prescription(id=10, patient_id=1, doctor_id=2, medication=m, is_active=True, dosage="100mg", frequency="Daily")
    res = to_fhir_medication_request(p)
    assert res["resourceType"] == "MedicationRequest"
    assert res["status"] == "active"
    assert res["medicationReference"]["display"] == "Aspirin"
    assert res["subject"]["reference"] == "Patient/1"

def test_to_fhir_observation():
    lab = LabResult(id=5, patient_id=1, doctor_id=2, test_name="Blood Pressure", result_value="120/80", unit="mmHg", reference_range="<120")
    res = to_fhir_observation(lab)
    assert res["resourceType"] == "Observation"
    assert res["code"]["text"] == "Blood Pressure"
    assert res["valueString"] == "120/80 mmHg"
    assert res["referenceRange"][0]["text"] == "<120"

def test_to_fhir_bundle():
    u = User(id=1, email="test@example.com", full_name="John Doe", role="patient", is_active=True)
    p = to_fhir_patient(u)
    bundle = to_fhir_bundle([p])
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "searchset"
    assert bundle["total"] == 1
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"
