import httpx
import asyncio

async def test_phase5_flow():
    print("--- Testing Phase 5 Full Workflows ---")
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        # 1. Login Admin
        print("1. Admin Login")
        admin_resp = await client.post("/api/auth/login", data={"username": "admin@demo.com", "password": "password"})
        admin_token = admin_resp.json()["access_token"]
        
        admin_dash = await client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
        assert admin_dash.status_code == 200, "Admin dashboard failed"
        print(f"Admin dashboard OK. Hospital ID: {admin_dash.json()['hospital_id']}")

        # 2. Login Doctor 1 (City General) & Doctor 2 (Westside)
        d1_resp = await client.post("/api/auth/login", data={"username": "doctor@demo.com", "password": "password"})
        doctor1_token = d1_resp.json()["access_token"]
        d2_resp = await client.post("/api/auth/login", data={"username": "doctor2@demo.com", "password": "password"})
        doctor2_token = d2_resp.json()["access_token"]

        # 3. Doctor 1 uploads a document for Patient
        print("2. Doctor 1 (Hospital A) uploads document")
        # Get doctor 1 visits
        d1_visits = await client.get("/api/visits/doctor", headers={"Authorization": f"Bearer {doctor1_token}"})
        visit1 = d1_visits.json()[0]

        files = {'file': ('report.pdf', b'fake pdf content', 'application/pdf')}
        data = {
            'patient_id': str(visit1['patient_id']),
            'hospital_id': str(visit1['hospital_id']),
            'visit_id': str(visit1['id']),
            'document_type': 'lab report',
            'title': 'Test Report Phase 5'
        }
        upload_resp = await client.post("/api/documents", headers={"Authorization": f"Bearer {doctor1_token}"}, files=files, data=data)
        doc = upload_resp.json()
        print(f"Uploaded document ID: {doc['id']}")

        # 4. Patient Login & See Document
        print("3. Patient sees document")
        p1_resp = await client.post("/api/auth/login", data={"username": "patient@demo.com", "password": "password"})
        patient_token = p1_resp.json()["access_token"]
        
        p1_docs = await client.get("/api/documents/patient", headers={"Authorization": f"Bearer {patient_token}"})
        found_docs = p1_docs.json()
        assert len(found_docs) > 0, "Patient cannot see docs"

        # 5. Doctor 2 (Hospital B) Requests Access
        print("4. Doctor 2 requests access")
        # Get Doctor 2 hospital ID
        d2_hospitals = await client.get("/api/hospitals", headers={"Authorization": f"Bearer {doctor2_token}"})
        d2_hospital_id = 2 # Hardcoded Westside for test speed
        
        req_resp = await client.post("/api/access-requests", json={
            "patient_id": visit1['patient_id'],
            "hospital_id": d2_hospital_id,
            "document_ids": [doc['id']],
            "reason": "Consultation"
        }, headers={"Authorization": f"Bearer {doctor2_token}"})
        req = req_resp.json()
        
        print("5. Patient approves access")
        appr_resp = await client.post(f"/api/access-requests/{req['id']}/approve", json={
            "document_ids": [doc['id']],
            "duration_hours": 1
        }, headers={"Authorization": f"Bearer {patient_token}"})
        print("Approve response:", appr_resp.status_code, appr_resp.text)

        # 7. Doctor 2 reads document
        print("6. Doctor 2 reads document")
        read_resp = await client.get(f"/api/documents/{doc['id']}/download", headers={"Authorization": f"Bearer {doctor2_token}"})
        assert read_resp.status_code == 200, "Doctor 2 could not read document"
        print("SUCCESS! Full multi-hospital flow verified.")

if __name__ == "__main__":
    asyncio.run(test_phase5_flow())
