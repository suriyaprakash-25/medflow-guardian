from typing import List, Tuple, Dict
from ai.schemas.alert_schema import AlertSchema

# Internal interaction database
# Keys are sorted tuples of normalized drug names: (Drug A, Drug B)
# Values are tuples of (Severity, Message)
INTERACTION_DATABASE: Dict[Tuple[str, str], Tuple[str, str]] = {
    ("Aspirin", "Warfarin"): (
        "High",
        "Warfarin and Aspirin together increase bleeding risk."
    ),
    ("Ibuprofen", "Warfarin"): (
        "High",
        "NSAIDs like Ibuprofen combined with Warfarin significantly increase the risk of gastrointestinal bleeding."
    ),
    ("Aspirin", "Ibuprofen"): (
        "Medium",
        "Ibuprofen may decrease the cardioprotective effect of low-dose Aspirin."
    ),
    ("Clopidogrel", "Omeprazole"): (
        "Medium",
        "Omeprazole reduces the antiplatelet effectiveness of Clopidogrel."
    ),
    ("Nitroglycerin", "Sildenafil"): (
        "High",
        "Co-administration of Nitroglycerin and Sildenafil can cause a severe, life-threatening drop in blood pressure."
    )
}

def normalize_drug_pair(drug1: str, drug2: str) -> Tuple[str, str]:
    """
    Normalizes a pair of drug names by trimming whitespace,
    converting to title case, and sorting alphabetically.
    """
    n1 = drug1.strip().title()
    n2 = drug2.strip().title()
    return tuple(sorted([n1, n2]))

def check_drug_interactions(current_medications: List[str], new_prescription: List[str]) -> List[AlertSchema]:
    """
    Checks for drug-drug interactions between current medications and the new prescription,
    as well as interactions internal to the new prescription itself.
    """
    alerts = []
    
    # 1. Check interactions between current medications and new prescription
    for current in current_medications:
        for new in new_prescription:
            pair = normalize_drug_pair(current, new)
            if pair in INTERACTION_DATABASE:
                severity, msg = INTERACTION_DATABASE[pair]
                alerts.append(AlertSchema(
                    type="Drug Interaction",
                    severity=severity,
                    message=msg,
                    relatedItems=list(pair)
                ))
                
    # 2. Check interactions within the new prescription itself
    n = len(new_prescription)
    for i in range(n):
        for j in range(i + 1, n):
            pair = normalize_drug_pair(new_prescription[i], new_prescription[j])
            if pair in INTERACTION_DATABASE:
                severity, msg = INTERACTION_DATABASE[pair]
                alerts.append(AlertSchema(
                    type="Drug Interaction",
                    severity=severity,
                    message=msg,
                    relatedItems=list(pair)
                ))
                
    return alerts
