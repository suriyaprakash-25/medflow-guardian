import httpx
import asyncio

async def test_security():
    print("--- Testing API Security ---")
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        # 1. Invalid JWT
        r1 = await client.get("/api/triage/", headers={"Authorization": "Bearer invalid_token"})
        print(f"Invalid JWT status: {r1.status_code}") # Expected 401

        # 2. Missing JWT
        r2 = await client.get("/api/triage/")
        print(f"Missing JWT status: {r2.status_code}") # Expected 401
        
        # 3. Patient accessing doctor-only routes
        # Login as patient
        p_resp = await client.post("/api/auth/login", data={"username": "patient@demo.com", "password": "password"})
        patient_token = p_resp.json()["access_token"]
        
        r3 = await client.get("/api/triage/", headers={"Authorization": f"Bearer {patient_token}"})
        print(f"Patient accessing doctor triage queue status: {r3.status_code}") # Expected 403 or 401

        # 4. Doctor accessing unrelated patient data
        d_resp = await client.post("/api/auth/login", data={"username": "doctor@demo.com", "password": "password"})
        doctor_token = d_resp.json()["access_token"]

        # This depends on if our /api/triage/patient route restricts doctors, wait, the doctor route is /api/triage/ to get all. The patient history route is /api/triage/patient (patient only).
        r4 = await client.get("/api/triage/patient", headers={"Authorization": f"Bearer {doctor_token}"})
        print(f"Doctor accessing patient history route status: {r4.status_code}") # Expected 403 or 401

        # 5. Unauthorized status updates
        # Patient trying to update status
        r5 = await client.patch("/api/triage/1/status", json={"status": "resolved"}, headers={"Authorization": f"Bearer {patient_token}"})
        print(f"Patient updating status: {r5.status_code}") # Expected 403 or 401

if __name__ == "__main__":
    asyncio.run(test_security())
