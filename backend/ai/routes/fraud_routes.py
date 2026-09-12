"""
FastAPI Routes for AI Fraud & Prescription Pattern Detection.

Sample Request:
POST /ai/fraud-check
Headers:
  Content-Type: application/json
Body:
  {
    "patientId": "P003"
  }

Sample Response:
  {
    "alerts": [
      {
        "type": "Doctor Shopping",
        "severity": "High",
        "message": "Ibuprofen prescribed by 3 different doctors within 30 days.",
        "relatedItems": ["Ibuprofen"]
      },
      {
        "type": "Repeated Requests",
        "severity": "Medium",
        "message": "Same medicine requested 3 times within 10 days.",
        "relatedItems": ["Codeine"]
      },
      {
        "type": "Insurance Anomaly",
        "severity": "High",
        "message": "Claim amount ($250.00) significantly exceeds historical average ($50.00).",
        "relatedItems": ["RX310"]
      },
      {
        "type": "Unusual Medication Pattern",
        "severity": "High",
        "message": "Abrupt shift in medication pattern: transitioning from stable Cardiovascular therapy to Opioids.",
        "relatedItems": ["Oxycodone"]
      }
    ],
    "overallRisk": "High"
  }
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ai.schemas.alert_schema import AlertSchema
from ai.services.fraud_service import run_fraud_checks

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Fraud Detection"])


class FraudCheckRequest(BaseModel):
    patient_id: str = Field(..., alias="patientId", description="Unique identifier for the patient to check")

    class Config:
        populate_by_name = True


class FraudCheckResponse(BaseModel):
    alerts: List[AlertSchema] = Field(..., description="List of detected anomalies or policy violations")
    overall_risk: str = Field(..., alias="overallRisk", description="Aggregated risk status (Low, Medium, High)")

    class Config:
        populate_by_name = True


@router.post("/fraud-check", response_model=FraudCheckResponse, status_code=status.HTTP_200_OK)
async def check_fraud_anomalies(request: FraudCheckRequest):
    """
    Scans a patient's historical prescription profile to detect anomalies such as doctor shopping,
    excessive fill frequencies, unusual billing totals, and sharp therapeutic class shifts.
    """
    try:
        return run_fraud_checks(request.patient_id)
    except Exception:
        logger.exception("Fraud indicator evaluation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fraud indicator evaluation failed",
        ) from None
