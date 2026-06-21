# SWAP POINT: replace the JSON file reads in these two functions with real
# database/API calls later (e.g. PostgreSQL query or consent-verified vault API
# call). No other file in this codebase should need to change as a result.

import json
from pathlib import Path
from typing import List, Optional
from ai.schemas.patient_schema import PatientSchema
from ai.schemas.prescription_schema import PrescriptionSchema

DATA_DIR = Path(__file__).parent

def get_patient_data(patient_id: str) -> Optional[PatientSchema]:
    """
    Fetches details of a specific patient by ID.
    Returns PatientSchema if found, or None.
    """
    file_path = DATA_DIR / "mock_patients.json"
    with open(file_path, "r", encoding="utf-8") as f:
        patients_raw = json.load(f)
        
    for p in patients_raw:
        if p.get("patientId") == patient_id:
            return PatientSchema(**p)
            
    return None

def get_prescription_history(patient_id: str) -> List[PrescriptionSchema]:
    """
    Fetches the historical list of prescriptions for a specific patient.
    Returns a list of PrescriptionSchema.
    """
    file_path = DATA_DIR / "mock_prescriptions.json"
    with open(file_path, "r", encoding="utf-8") as f:
        prescriptions_raw = json.load(f)
        
    history = []
    for pr in prescriptions_raw:
        if pr.get("patientId") == patient_id:
            history.append(PrescriptionSchema(**pr))
            
    return history
