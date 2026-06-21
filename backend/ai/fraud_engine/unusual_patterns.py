from typing import List
from ai.schemas.alert_schema import AlertSchema
from ai.schemas.prescription_schema import PrescriptionSchema

# Medication to class mapping for pattern shifts
MEDICATION_CLASSES = {
    "Metoprolol": "Cardiovascular",
    "Lisinopril": "Cardiovascular",
    "Atorvastatin": "Cardiovascular",
    "Ibuprofen": "NSAID",
    "Aspirin": "NSAID",
    "Codeine": "Opioid",
    "Oxycodone": "Opioid",
    "Paracetamol": "Analgesic",
    "Amoxicillin": "Antibiotic",
    "Penicillin": "Antibiotic"
}

def get_medication_class(med_name: str) -> str:
    """Retrieves the therapeutic class grouping for a medication."""
    return MEDICATION_CLASSES.get(med_name.strip().title(), "Other")

def check_unusual_patterns(history: List[PrescriptionSchema]) -> List[AlertSchema]:
    """
    Scans the patient's prescription history chronologically.
    Detects abrupt, unexplained shifts in drug class (e.g. from stable cardiovascular therapy directly to opioids)
    at the exact historical points where they occur.
    """
    alerts = []
    if len(history) < 2:
        return alerts

    # Sort history chronologically
    sorted_history = sorted(history, key=lambda x: x.prescribed_date)
    
    seen_classes = set()
    
    for pr in sorted_history:
        current_classes = {get_medication_class(med) for med in pr.medications}
        
        # Only check for shifts if we have accumulated prior history
        if seen_classes:
            for c_class in current_classes:
                if c_class == "Opioid" and "Cardiovascular" in seen_classes and "Opioid" not in seen_classes:
                    alerts.append(AlertSchema(
                        type="Unusual Medication Pattern",
                        severity="High",
                        message="Abrupt shift in medication pattern: transitioning from stable Cardiovascular therapy to Opioids.",
                        relatedItems=pr.medications
                    ))
                    # Mark Opioid as seen to prevent duplicate alerts for subsequent opioid prescriptions
                    seen_classes.update(current_classes)
                    return alerts
                elif c_class not in seen_classes:
                    alerts.append(AlertSchema(
                        type="Unusual Medication Pattern",
                        severity="High",
                        message=f"Abrupt shift in medication pattern: new class '{c_class}' prescribed with no overlapping history.",
                        relatedItems=pr.medications
                    ))
                    seen_classes.update(current_classes)
                    return alerts
                    
        seen_classes.update(current_classes)
        
    return alerts
