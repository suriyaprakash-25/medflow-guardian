import sys
from pathlib import Path

# Set up system paths
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from ai.main import app
from app.api.dependencies import get_current_active_user

# The standalone AI routes intentionally require a MedFlow-authenticated user.
# This smoke script isolates AI engine behavior by overriding only that identity
# dependency; authentication enforcement itself is covered in backend/tests.
app.dependency_overrides[get_current_active_user] = lambda: object()
client = TestClient(app)


def run_tests():
    print("==================================================")
    print("RUNNING AUTOMATED TESTS FOR AI INTELLIGENCE LAYER")
    print("==================================================")

    # ----------------------------------------------------
    # TEST 1: Clinical Safety - Clean Baseline (P001)
    # ----------------------------------------------------
    print("\n[Test 1] POST /ai/safety-check (Clean Baseline)...")
    payload_clean = {
        "patientId": "P001",
        "allergies": [],
        "currentMedications": ["Atorvastatin"],
        "newPrescription": ["Metoprolol"],
    }
    response = client.post("/ai/safety-check", json=payload_clean)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    print("Response:", data)
    assert len(data["alerts"]) == 0, "Expected 0 alerts for clean baseline"
    assert data["safetyScore"] == 100, f"Expected score 100, got {data['safetyScore']}"
    assert data["risk"] == "Low", f"Expected risk Low, got {data['risk']}"
    print("Result: PASS")

    # ----------------------------------------------------
    # TEST 2: Clinical Safety - Multiple Alerts (P002)
    # ----------------------------------------------------
    print("\n[Test 2] POST /ai/safety-check (Allergy, Duplicate, & Interaction)...")
    payload_conflict = {
        "patientId": "P002",
        "allergies": ["Penicillin"],
        "currentMedications": ["Warfarin"],
        "newPrescription": ["Warfarin", "Aspirin", "Amoxicillin"],
    }
    response = client.post("/ai/safety-check", json=payload_conflict)
    assert response.status_code == 200
    data = response.json()
    print("Response:")
    import json

    print(json.dumps(data, indent=2))

    alert_types = [alert["type"] for alert in data["alerts"]]
    assert "Duplicate Medication" in alert_types, "Duplicate alert missing"
    assert "Allergy Conflict" in alert_types, "Allergy conflict alert missing"
    assert "Drug Interaction" in alert_types, "Drug interaction alert missing"

    assert data["safetyScore"] == 25, f"Expected safetyScore 25, got {data['safetyScore']}"
    assert data["risk"] == "High", f"Expected risk High, got {data['risk']}"
    print("Result: PASS")

    # ----------------------------------------------------
    # TEST 3: Fraud Engine - Clean History (P001)
    # ----------------------------------------------------
    print("\n[Test 3] POST /ai/fraud-check (Clean Patient History)...")
    response = client.post("/ai/fraud-check", json={"patientId": "P001"})
    assert response.status_code == 200
    data = response.json()
    print("Response:", data)
    assert len(data["alerts"]) == 0, f"Expected 0 alerts, got {len(data['alerts'])}"
    assert data["overallRisk"] == "Low", f"Expected overallRisk Low, got {data['overallRisk']}"
    print("Result: PASS")

    # ----------------------------------------------------
    # TEST 4: Fraud Engine - Multi-Alert Fraud (P003)
    # ----------------------------------------------------
    print("\n[Test 4] POST /ai/fraud-check (Doctor Shopping, Repeated, Claim Anomaly, Unusual Pattern)...")
    response = client.post("/ai/fraud-check", json={"patientId": "P003"})
    assert response.status_code == 200
    data = response.json()
    print("Response:")
    print(json.dumps(data, indent=2))

    fraud_types = [alert["type"] for alert in data["alerts"]]
    assert "Doctor Shopping" in fraud_types, "Doctor shopping alert missing"
    assert "Repeated Requests" in fraud_types, "Repeated requests alert missing"
    assert "Insurance Anomaly" in fraud_types, "Insurance anomaly alert missing"
    assert "Unusual Medication Pattern" in fraud_types, "Unusual pattern alert missing"
    assert data["overallRisk"] == "High", f"Expected overallRisk High, got {data['overallRisk']}"
    print("Result: PASS")

    print("\n==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    try:
        run_tests()
    finally:
        app.dependency_overrides.clear()
