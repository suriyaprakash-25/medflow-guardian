from typing import List
from ai.schemas.alert_schema import AlertSchema

# Simple cross-sensitivity mapping for medication classes.
# If a patient is allergic to a group, they should be flagged for related derivatives.
CROSS_SENSITIVITIES = {
    "Penicillin": ["Penicillin", "Amoxicillin", "Ampicillin", "Piperacillin", "Nafcillin", "Cloxacillin"],
    "Sulfa": ["Sulfamethoxazole", "Bactrim", "Sulfasalazine", "Sulfadiazine"],
    "Aspirin": ["Aspirin", "Ibuprofen", "Naproxen", "Diclofenac", "Ketorolac"]  # NSAIDs cross-sensitivity
}

def check_allergies(allergies: List[str], new_prescription: List[str]) -> List[AlertSchema]:
    """
    Checks if any prescribed medication in the new prescription conflicts with 
    the patient's documented allergies (including cross-sensitivities).
    """
    alerts = []
    normalized_allergies = [allergy.strip().title() for allergy in allergies]
    
    for med in new_prescription:
        med_trimmed = med.strip()
        med_normalized = med_trimmed.title()
        
        for allergy in normalized_allergies:
            # 1. Exact or substring match (e.g. "Penicillin" in "Penicillin V")
            if allergy in med_normalized or med_normalized in allergy:
                alerts.append(AlertSchema(
                    type="Allergy Conflict",
                    severity="High",
                    message=f"Patient allergic to {allergy}.",
                    relatedItems=[allergy]
                ))
                break
            
            # 2. Cross-sensitivity check
            if allergy in CROSS_SENSITIVITIES:
                related_meds = [m.title() for m in CROSS_SENSITIVITIES[allergy]]
                if med_normalized in related_meds:
                    alerts.append(AlertSchema(
                        type="Allergy Conflict",
                        severity="High",
                        message=f"Patient allergic to {allergy}. Prescribed drug {med_trimmed} presents cross-sensitivity risk.",
                        relatedItems=[allergy, med_trimmed]
                    ))
                    break
                    
    return alerts
