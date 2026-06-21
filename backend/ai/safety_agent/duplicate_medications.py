from typing import List
from ai.schemas.alert_schema import AlertSchema

def check_duplicate_medications(current_medications: List[str], new_prescription: List[str]) -> List[AlertSchema]:
    """
    Checks if any medication in the new prescription is already active
    in the patient's current medications.
    """
    alerts = []
    current_set = {med.strip().title() for med in current_medications}
    
    for med in new_prescription:
        med_trimmed = med.strip()
        med_normalized = med_trimmed.title()
        if med_normalized in current_set:
            alerts.append(AlertSchema(
                type="Duplicate Medication",
                severity="Medium",
                message=f"{med_trimmed} already exists in current medications.",
                relatedItems=[med_trimmed]
            ))
            
    return alerts
