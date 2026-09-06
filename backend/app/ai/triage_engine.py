DISCLAIMER = (
    "⚠️ AI Assessment Only — Not a medical diagnosis. "
    "This is a keyword-based prototype triage tool. "
    "Always consult a qualified healthcare professional."
)


def analyze_symptoms(symptoms: str) -> dict:
    """
    Mock AI Triage Engine for Hackathon Prototype.
    Returns deterministic priority and reasoning based on keyword matches.
    """
    symptoms_lower = symptoms.lower()
    
    # Critical keywords
    critical_keywords = ["chest pain", "heart", "stroke", "bleeding profusely", "can't breathe", "unconscious"]
    if any(keyword in symptoms_lower for keyword in critical_keywords):
        return {
            "priority": "critical",
            "ai_reasoning": "Detected critical keywords indicating potential life-threatening emergency.",
            "disclaimer": DISCLAIMER,
        }
        
    # High keywords
    high_keywords = ["severe headache", "blurred vision", "high fever", "broken bone", "vomiting blood"]
    if any(keyword in symptoms_lower for keyword in high_keywords):
        return {
            "priority": "high",
            "ai_reasoning": "Detected high priority keywords requiring urgent attention.",
            "disclaimer": DISCLAIMER,
        }
        
    # Medium keywords
    medium_keywords = ["fever", "pain", "sprain", "dizzy", "nausea"]
    if any(keyword in symptoms_lower for keyword in medium_keywords):
        return {
            "priority": "medium",
            "ai_reasoning": "Detected moderate symptoms requiring evaluation.",
            "disclaimer": DISCLAIMER,
        }
        
    # Default to low
    return {
        "priority": "low",
        "ai_reasoning": "Symptoms appear mild based on initial keyword analysis.",
        "disclaimer": DISCLAIMER,
    }
