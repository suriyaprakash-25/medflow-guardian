"""
All alerts produced by this module are advisory signals intended for review by
a licensed clinician, pharmacist, or fraud analyst. This module does not make
autonomous medical, legal, or financial decisions, and does not replace
professional judgment.
"""

from typing import Dict, Any
from ai.data.data_loader import get_prescription_history
from ai.fraud_engine.doctor_shopping import check_doctor_shopping
from ai.fraud_engine.repeated_requests import check_repeated_requests
from ai.fraud_engine.insurance_anomaly import check_insurance_anomaly
from ai.fraud_engine.unusual_patterns import check_unusual_patterns
from ai.safety_agent.safety_score import calculate_safety_score

def run_fraud_checks(patient_id: str) -> Dict[str, Any]:
    """
    Orchestrates fraud pattern checks (doctor shopping, repeated requests,
    insurance claim anomalies, class pattern shifts).
    Calculates overall risk category using the shared risk scale.
    """
    # Fetch prescription history from isolated data loader (SWAP POINT)
    history = get_prescription_history(patient_id)
    
    # Run detectors
    shopping_alerts = check_doctor_shopping(history)
    repeated_alerts = check_repeated_requests(history)
    anomaly_alerts = check_insurance_anomaly(history)
    pattern_alerts = check_unusual_patterns(history)
    
    # Combine fraud engine alerts
    all_alerts = shopping_alerts + repeated_alerts + anomaly_alerts + pattern_alerts
    
    # Calculate overall risk status using standard scoring ranges
    _, overall_risk = calculate_safety_score(all_alerts)
    
    return {
        "alerts": all_alerts,
        "overallRisk": overall_risk
    }
