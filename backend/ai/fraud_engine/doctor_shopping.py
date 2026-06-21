from datetime import timedelta
from typing import List
from ai.schemas.alert_schema import AlertSchema
from ai.schemas.prescription_schema import PrescriptionSchema

# Mapping medications to their general therapeutic classes
THERAPEUTIC_CLASSES = {
    "Metoprolol": "Cardiovascular/Beta-Blocker",
    "Lisinopril": "Cardiovascular/ACE-Inhibitor",
    "Atorvastatin": "Cardiovascular/Statin",
    "Ibuprofen": "NSAID/Pain-Relief",
    "Aspirin": "NSAID/Pain-Relief",
    "Codeine": "Opioid/Analgesic",
    "Oxycodone": "Opioid/Analgesic",
    "Paracetamol": "Analgesic",
    "Amoxicillin": "Antibiotic",
    "Penicillin": "Antibiotic"
}

def get_medication_class(med_name: str) -> str:
    """Gets the therapeutic class for a medication name (normalized)."""
    return THERAPEUTIC_CLASSES.get(med_name.strip().title(), "Other")

def check_doctor_shopping(history: List[PrescriptionSchema]) -> List[AlertSchema]:
    """
    Detects the same medicine (or therapeutic class) prescribed by 3 or more 
    distinct doctors within a 30-day rolling window in the patient's history.
    """
    alerts = []
    if not history:
        return alerts

    # Group prescriptions by medication name and therapeutic class
    records_by_group = {}
    
    for pr in history:
        for med in pr.medications:
            med_normalized = med.strip().title()
            med_class = get_medication_class(med_normalized)
            
            # Group by both specific name and class
            for group_key in set([med_normalized, med_class]):
                if group_key not in records_by_group:
                    records_by_group[group_key] = []
                records_by_group[group_key].append({
                    "date": pr.prescribed_date,
                    "doctor_id": pr.doctor_id,
                    "doctor_name": pr.doctor_name,
                    "medication": med_normalized
                })
                
    # Evaluate 30-day rolling window for each group
    for group_key, entries in records_by_group.items():
        sorted_entries = sorted(entries, key=lambda x: x["date"])
        n = len(sorted_entries)
        
        for i in range(n):
            window_start = sorted_entries[i]["date"]
            window_end = window_start + timedelta(days=30)
            
            # Find all entries falling within the window
            window_entries = []
            for j in range(i, n):
                if sorted_entries[j]["date"] <= window_end:
                    window_entries.append(sorted_entries[j])
                else:
                    break
                    
            # Count distinct doctors
            unique_doctors = {e["doctor_name"] for e in window_entries}
            if len(unique_doctors) >= 3:
                meds_involved = sorted(list({e["medication"] for e in window_entries}))
                alerts.append(AlertSchema(
                    type="Doctor Shopping",
                    severity="High",
                    message=f"{group_key} prescribed by {len(unique_doctors)} different doctors within 30 days.",
                    relatedItems=meds_involved
                ))
                break  # Alert raised for this class/drug, move to next group
                
    return alerts
