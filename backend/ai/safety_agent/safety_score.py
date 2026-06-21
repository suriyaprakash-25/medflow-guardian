from typing import List, Tuple
from ai.schemas.alert_schema import AlertSchema

def calculate_risk_label(score: int) -> str:
    """
    Maps a numerical score to a standardized risk label (Low, Medium, High).
    This mapping function is shared conceptually across safety and fraud domains.
    """
    if score >= 70:
        return "Low"
    elif score >= 40:
        return "Medium"
    else:
        return "High"

# Use this exact scoring formula, and document it as a comment directly above the
# function that implements it:
#   - Start at 100
#   - Subtract 30 for each High severity alert
#   - Subtract 15 for each Medium severity alert
#   - Subtract 5 for each Low severity alert
#   - Floor the result at 0 (never negative)
def calculate_safety_score(alerts: List[AlertSchema]) -> Tuple[int, str]:
    """
    Calculates a safety score out of 100 based on active safety alerts,
    along with a descriptive risk label.
    """
    score = 100
    for alert in alerts:
        sev = alert.severity.strip().title()
        if sev == "High":
            score -= 30
        elif sev == "Medium":
            score -= 15
        elif sev == "Low":
            score -= 5
            
    score = max(0, score)
    risk_label = calculate_risk_label(score)
    return score, risk_label
