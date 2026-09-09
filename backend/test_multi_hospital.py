import httpx
import asyncio

async def test_multi_hospital():
    print("--- Testing Multi-Hospital Foundation ---")
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        # 1. Login as different roles
        p_resp = await client.post("/api/auth/login", data={"username": "patient@demo.com", "password": "password"})
        patient_token = p_resp.json()["access_token"]
        
        d1_resp = await client.post("/api/auth/login", data={"username": "doctor@demo.com", "password": "password"})
        doctor1_token = d1_resp.json()["access_token"]
        
        d2_resp = await client.post("/api/auth/login", data={"username": "doctor2@demo.com", "password": "password"})
        doctor2_token = d2_resp.json()["access_token"]

        # 2. Test Invalid/Missing JWT
        print("\n[Auth Validation]")
        r_no_auth = await client.get("/api/hospitals")
        print(f"Missing JWT status: {r_no_auth.status_code}") # Expected 401
        
        r_bad_auth = await client.get("/api/hospitals", headers={"Authorization": "Bearer BAD"})
        print(f"Invalid JWT status: {r_bad_auth.status_code}") # Expected 401

        # 3. List Hospitals
        print("\n[Hospital Listing]")
        h_resp = await client.get("/api/hospitals", headers={"Authorization": f"Bearer {patient_token}"})
        hospitals = h_resp.json()
        print(f"Hospitals found: {len(hospitals)}")
        for h in hospitals:
            print(f"- {h['name']} (ID: {h['id']})")
        
        if len(hospitals) < 2:
            print("FAILED: Expected at least 2 hospitals")
            return
            
        h1_id = hospitals[0]["id"]
        h2_id = hospitals[1]["id"]

        # 4. Patient Visits
        print("\n[Patient Visits]")
        pv_resp = await client.get("/api/visits/patient", headers={"Authorization": f"Bearer {patient_token}"})
        p_visits = pv_resp.json()
        print(f"Patient visits found: {len(p_visits)}")
        hospitals_visited = set(v["hospital_id"] for v in p_visits)
        print(f"Hospitals visited by patient: {len(hospitals_visited)}")
        if len(hospitals_visited) < 2:
            print("FAILED: Patient should have visits in multiple hospitals")

        # 5. Doctor 1 Visits (Should only see their hospital's visits)
        print("\n[Doctor 1 Affiliated Visits]")
        d1v_resp = await client.get("/api/visits/doctor", headers={"Authorization": f"Bearer {doctor1_token}"})
        d1_visits = d1v_resp.json()
        print(f"Doctor 1 affiliated visits found: {len(d1_visits)}")
        d1_hospitals = set(v["hospital_id"] for v in d1_visits)
        print(f"Doctor 1 sees visits for hospitals: {d1_hospitals}")
        if h2_id in d1_hospitals:
            print("FAILED: Doctor 1 should not see Hospital 2's visits")

        # 6. Doctor 2 Visits (Should only see their hospital's visits)
        print("\n[Doctor 2 Affiliated Visits]")
        d2v_resp = await client.get("/api/visits/doctor", headers={"Authorization": f"Bearer {doctor2_token}"})
        d2_visits = d2v_resp.json()
        print(f"Doctor 2 affiliated visits found: {len(d2_visits)}")
        d2_hospitals = set(v["hospital_id"] for v in d2_visits)
        print(f"Doctor 2 sees visits for hospitals: {d2_hospitals}")
        if h1_id in d2_hospitals:
            print("FAILED: Doctor 2 should not see Hospital 1's visits")

        # 7. Unauthorized Cross-Role Access
        print("\n[RBAC Verification]")
        cross_resp1 = await client.get("/api/visits/doctor", headers={"Authorization": f"Bearer {patient_token}"})
        print(f"Patient accessing doctor visits route: {cross_resp1.status_code}") # Expected 403
        
        cross_resp2 = await client.get("/api/visits/patient", headers={"Authorization": f"Bearer {doctor1_token}"})
        print(f"Doctor accessing patient visits route: {cross_resp2.status_code}") # Expected 403

        print("\n--- Phase 1 Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(test_multi_hospital())
