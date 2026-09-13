DISCLAIMER = (
    "Automated triage support only — not a diagnosis or treatment recommendation. "
    "Priority is generated from deterministic symptom-keyword rules and may be incomplete. "
    "A qualified clinician must review the report. If symptoms may be life-threatening, "
    "seek emergency care immediately."
)


def analyze_symptoms(symptoms: str) -> dict:
    """Return deterministic triage-support priority from configured keyword rules.

    This function is intentionally not described as diagnostic AI. The output is a
    screening aid for clinician review and must not be used to rule out urgency.
    """
    symptoms_lower = symptoms.lower()

    critical_keywords = [
        "chest pain",
        "heart",
        "stroke",
        "bleeding profusely",
        "can't breathe",
        "unconscious",
    ]
    if any(keyword in symptoms_lower for keyword in critical_keywords):
        return {
            "priority": "critical",
            "ai_reasoning": (
                "Configured keyword rules matched terms associated with potentially "
                "urgent symptoms; prompt clinician review is required."
            ),
            "disclaimer": DISCLAIMER,
        }

    high_keywords = [
        "severe headache",
        "blurred vision",
        "high fever",
        "broken bone",
        "vomiting blood",
    ]
    if any(keyword in symptoms_lower for keyword in high_keywords):
        return {
            "priority": "high",
            "ai_reasoning": (
                "Configured keyword rules matched terms assigned to the high-priority "
                "review queue; a clinician must determine actual urgency."
            ),
            "disclaimer": DISCLAIMER,
        }

    medium_keywords = ["fever", "pain", "sprain", "dizzy", "nausea"]
    if any(keyword in symptoms_lower for keyword in medium_keywords):
        return {
            "priority": "medium",
            "ai_reasoning": (
                "Configured keyword rules matched terms assigned to the medium-priority "
                "review queue; this is not a clinical assessment."
            ),
            "disclaimer": DISCLAIMER,
        }

    return {
        "priority": "low",
        "ai_reasoning": (
            "No configured higher-priority keywords were matched. This does not mean "
            "the symptoms are safe, mild, or non-urgent."
        ),
        "disclaimer": DISCLAIMER,
    }
