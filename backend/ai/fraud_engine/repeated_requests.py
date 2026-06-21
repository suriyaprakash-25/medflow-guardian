from datetime import timedelta
from typing import List
from ai.schemas.alert_schema import AlertSchema
from ai.schemas.prescription_schema import PrescriptionSchema

def check_repeated_requests(history: List[PrescriptionSchema]) -> List[AlertSchema]:
    """
    Detects the same medication requested multiple times (3 or more times) 
    within a short 10-day rolling window in the patient's history.
    """
    alerts = []
    if not history:
        return alerts

    # Group prescription dates by medication
    records_by_med = {}
    for pr in history:
        for med in pr.medications:
            med_normalized = med.strip().title()
            if med_normalized not in records_by_med:
                records_by_med[med_normalized] = []
            records_by_med[med_normalized].append(pr.prescribed_date)
            
    # Check each medication's request timeline
    for med, dates in records_by_med.items():
        sorted_dates = sorted(dates)
        n = len(sorted_dates)
        
        for i in range(n):
            window_start = sorted_dates[i]
            window_end = window_start + timedelta(days=10)
            
            # Count how many prescriptions fall in the 10-day window
            count = 0
            for j in range(i, n):
                if sorted_dates[j] <= window_end:
                    count += 1
                else:
                    break
                    
            if count >= 3:
                alerts.append(AlertSchema(
                    type="Repeated Requests",
                    severity="Medium",
                    message=f"Same medicine requested {count} times within 10 days.",
                    relatedItems=[med]
                ))
                break  # Alert raised for this drug, move to next drug
                
    return alerts
