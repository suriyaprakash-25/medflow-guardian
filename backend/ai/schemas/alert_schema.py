from pydantic import BaseModel, Field

class AlertSchema(BaseModel):
    type: str = Field(..., description="Type of alert (e.g., Duplicate Medication, Allergy Conflict)")
    severity: str = Field(..., description="Severity level: Low, Medium, High")
    message: str = Field(..., description="User-friendly alert message detailing the conflict/anomaly")
    related_items: list[str] = Field(..., alias="relatedItems", description="The specific items (medications, doctors, claims) causing this alert")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "type": "Allergy Conflict",
                "severity": "High",
                "message": "Patient allergic to Penicillin.",
                "relatedItems": ["Penicillin"]
            }
        }
