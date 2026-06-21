from pydantic import BaseModel, Field
from datetime import date

class PrescriptionSchema(BaseModel):
    prescription_id: str = Field(..., alias="prescriptionId", description="Unique identifier for the prescription record")
    patient_id: str = Field(..., alias="patientId", description="Unique identifier for the patient")
    doctor_id: str = Field(..., alias="doctorId", description="Unique identifier for the prescribing physician")
    doctor_name: str = Field(..., alias="doctorName", description="Name of the prescribing physician")
    medications: list[str] = Field(..., description="List of medications prescribed in this record")
    claim_amount: float = Field(..., alias="claimAmount", description="Insurance claim amount for the prescription")
    prescribed_date: date = Field(..., alias="prescribedDate", description="Date when the prescription was issued")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "prescriptionId": "RX001",
                "patientId": "P001",
                "doctorId": "DOC001",
                "doctorName": "Dr. Sarah Smith",
                "medications": ["Ibuprofen"],
                "claimAmount": 45.0,
                "prescribedDate": "2026-06-01"
            }
        }

class SafetyCheckRequest(BaseModel):
    patient_id: str = Field(..., alias="patientId", description="Unique identifier for the patient")
    allergies: list[str] = Field(default_factory=list, description="List of patient allergies")
    current_medications: list[str] = Field(default_factory=list, alias="currentMedications", description="List of medications currently being taken")
    new_prescription: list[str] = Field(..., alias="newPrescription", description="List of new medications to be prescribed")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "patientId": "P001",
                "allergies": ["Penicillin"],
                "currentMedications": ["Paracetamol", "Ibuprofen"],
                "newPrescription": ["Ibuprofen", "Amoxicillin"]
            }
        }
