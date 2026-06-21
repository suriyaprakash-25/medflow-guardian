from pydantic import BaseModel, Field

class PatientSchema(BaseModel):
    patient_id: str = Field(..., alias="patientId", description="Unique identifier for the patient")
    name: str = Field(..., description="Full name of the patient")
    allergies: list[str] = Field(default_factory=list, description="List of substances/medications the patient is allergic to")
    current_medications: list[str] = Field(default_factory=list, alias="currentMedications", description="List of medications currently being taken by the patient")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "patientId": "P001",
                "name": "John Doe",
                "allergies": ["Penicillin"],
                "currentMedications": ["Paracetamol", "Ibuprofen"]
            }
        }
