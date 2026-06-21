"""
All alerts produced by this module are advisory signals intended for review by
a licensed clinician, pharmacist, or fraud analyst. This module does not make
autonomous medical, legal, or financial decisions, and does not replace
professional judgment.
"""

from typing import Dict, Any
from ai.schemas.prescription_schema import SafetyCheckRequest
from ai.safety_agent.duplicate_medications import check_duplicate_medications
from ai.safety_agent.allergy_checker import check_allergies
from ai.safety_agent.drug_interactions import check_drug_interactions
from ai.safety_agent.safety_score import calculate_safety_score

def run_safety_checks(request: SafetyCheckRequest) -> Dict[str, Any]:
    """
    Orchestrates duplicate, allergy, and drug interaction clinical safety checks.
    Calculates safety score and risk status.
    """
    dup_alerts = check_duplicate_medications(request.current_medications, request.new_prescription)
    allergy_alerts = check_allergies(request.allergies, request.new_prescription)
    interaction_alerts = check_drug_interactions(request.current_medications, request.new_prescription)
    
    # Combine alerts
    raw_alerts = dup_alerts + allergy_alerts + interaction_alerts
    
    # Deduplicate alerts (e.g. if the same drug interaction is triggered multiple times)
    seen = set()
    all_alerts = []
    for alert in raw_alerts:
        related_key = tuple(sorted(alert.related_items))
        unique_key = (alert.type, alert.severity, alert.message, related_key)
        if unique_key not in seen:
            seen.add(unique_key)
            all_alerts.append(alert)
    
    # Calculate safety score and corresponding risk label
    score, risk = calculate_safety_score(all_alerts)
    
    return {
        "alerts": all_alerts,
        "safetyScore": score,
        "risk": risk
    }
