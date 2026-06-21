from typing import List
from ai.schemas.alert_schema import AlertSchema
from ai.schemas.prescription_schema import PrescriptionSchema

def check_insurance_anomaly(history: List[PrescriptionSchema]) -> List[AlertSchema]:
    """
    Detects abnormal claim amounts in the patient's history.
    Compares each prescription's claim amount to the average of all other claims.
    If any claim is more than 2x the average of other claims, it triggers an alert.
    """
    alerts = []
    if len(history) < 2:
        return alerts

    for i, pr in enumerate(history):
        other_claims = [x.claim_amount for j, x in enumerate(history) if j != i]
        if not other_claims:
            continue
            
        avg_other = sum(other_claims) / len(other_claims)
        
        # Check if the claim exceeds 2x the average of other claims
        if pr.claim_amount > 2 * avg_other:
            alerts.append(AlertSchema(
                type="Insurance Anomaly",
                severity="High",
                message=f"Claim amount (${pr.claim_amount:.2f}) significantly exceeds average of other historical claims (${avg_other:.2f}).",
                relatedItems=[pr.prescription_id]
            ))
            
    return alerts
