"""
FastAPI Routes for Clinical Safety Agent.

Sample Request:
POST /ai/safety-check
Headers:
  Content-Type: application/json
Body:
  {
    "patientId": "P002",
    "allergies": ["Penicillin"],
    "currentMedications": ["Warfarin", "Ibuprofen"],
    "newPrescription": ["Aspirin", "Amoxicillin"]
  }

Sample Response:
  {
    "alerts": [
      {
        "type": "Allergy Conflict",
        "severity": "High",
        "message": "Patient allergic to Penicillin. Prescribed drug Amoxicillin presents cross-sensitivity risk.",
        "relatedItems": ["Penicillin", "Amoxicillin"]
      },
      {
        "type": "Drug Interaction",
        "severity": "High",
        "message": "Warfarin and Aspirin together increase bleeding risk.",
        "relatedItems": ["Aspirin", "Warfarin"]
      }
    ],
    "safetyScore": 40,
    "risk": "Medium"
  }
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List
from ai.schemas.alert_schema import AlertSchema
from ai.schemas.prescription_schema import SafetyCheckRequest
from ai.services.safety_service import run_safety_checks

router = APIRouter(tags=["Clinical Safety"])

class SafetyCheckResponse(BaseModel):
    alerts: List[AlertSchema] = Field(..., description="List of detected safety warnings")
    safety_score: int = Field(..., alias="safetyScore", description="Calculated safety score (0-100)")
    risk: str = Field(..., description="Calculated risk level (Low, Medium, High)")

    class Config:
        populate_by_name = True

@router.post("/safety-check", response_model=SafetyCheckResponse, status_code=status.HTTP_200_OK)
async def check_clinical_safety(request: SafetyCheckRequest):
    """
    Evaluates prescription data for duplicate medications, allergy conflicts, and 
    severe drug-drug interactions. Returns a list of clinical alerts and a safety score.
    """
    try:
        results = run_safety_checks(request)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while evaluating clinical safety: {str(e)}"
        )
