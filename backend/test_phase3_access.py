import httpx
import asyncio
from datetime import datetime, timedelta

async def test_access_requests():
    print("--- Testing Phase 3 Access Requests ---")
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        # Login
        p1_resp = await client.post("/api/auth/login", data={"username": "patient@demo.com", "password": "password"})
        patient1_token = p1_resp.json()["access_token"]
        
        d1_resp = await client.post("/api/auth/login", data={"username": "doctor@demo.com", "password": "password"})
        doctor1_token = d1_resp.json()["access_token"]
        
        d2_resp = await client.post("/api/auth/login", data={"username": "doctor2@demo.com", "password": "password"})
        doctor2_token = d2_resp.json()["access_token"]

        # Setup: Doctor 1 uploads a document for Patient 1
        d1v_resp = await client.get("/api/visits/doctor", headers={"Authorization": f"Bearer {doctor1_token}"})
        d1_visits = d1v_resp.json()
        visit_1_id = d1_visits[0]["id"]
        
        files_valid = {'file': ('doc1.txt', b"Secret content", 'text/plain')}
        r_upload1 = await client.post("/api/documents", data={"visit_id": str(visit_1_id), "document_type": "lab report", "title": "Doc 1"}, files=files_valid, headers={"Authorization": f"Bearer {doctor1_token}"})
        doc1_id = r_upload1.json()["id"]
        
        files_valid2 = {'file': ('doc2.txt', b"Secret content 2", 'text/plain')}
        r_upload2 = await client.post("/api/documents", data={"visit_id": str(visit_1_id), "document_type": "scan report", "title": "Doc 2"}, files=files_valid2, headers={"Authorization": f"Bearer {doctor1_token}"})
        doc2_id = r_upload2.json()["id"]

        print(f"\n[Cross-hospital access requires approval]")
        r_d2_down = await client.get(f"/api/documents/{doc1_id}/download", headers={"Authorization": f"Bearer {doctor2_token}"})
        print(f"Doctor 2 downloading Doc 1 before grant: {r_d2_down.status_code}") # 403

        print(f"\n[Doctor requests access]")
        # Doctor 2 requests access to doc1
        req_data = {
            "patient_id": 1,
            "hospital_id": 2, # Doctor 2 is at hospital 2
            "document_ids": [doc1_id],
            "reason": "Consultation review"
        }
        r_req = await client.post("/api/access-requests", json=req_data, headers={"Authorization": f"Bearer {doctor2_token}"})
        print(f"Request access status: {r_req.status_code}")
        req_id = r_req.json()["id"]

        print(f"\n[Doctor cannot approve own request]")
        r_approve_doc = await client.post(f"/api/access-requests/{req_id}/approve", json={"duration_hours": 1, "document_ids": [doc1_id]}, headers={"Authorization": f"Bearer {doctor2_token}"})
        print(f"Doctor approving own request: {r_approve_doc.status_code}") # 403

        print(f"\n[Patient rejects request]")
        r_reject = await client.post(f"/api/access-requests/{req_id}/reject", json={"rejection_reason": "Not now"}, headers={"Authorization": f"Bearer {patient1_token}"})
        print(f"Patient rejection status: {r_reject.status_code}") # 200

        print(f"\n[Doctor requests access again]")
        r_req2 = await client.post("/api/access-requests", json=req_data, headers={"Authorization": f"Bearer {doctor2_token}"})
        req2_id = r_req2.json()["id"]

        print(f"\n[Invalid expiry rejected]")
        r_approve_inv = await client.post(f"/api/access-requests/{req2_id}/approve", json={"duration_hours": 2, "document_ids": [doc1_id]}, headers={"Authorization": f"Bearer {patient1_token}"})
        print(f"Patient approves with invalid duration (2h): {r_approve_inv.status_code}") # 400

        print(f"\n[Patient approves request]")
        r_approve = await client.post(f"/api/access-requests/{req2_id}/approve", json={"duration_hours": 1, "document_ids": [doc1_id]}, headers={"Authorization": f"Bearer {patient1_token}"})
        print(f"Patient approval status: {r_approve.status_code}") # 200
        grant_id = r_approve.json()["id"]

        print(f"\n[Access works before expiry]")
        r_d2_down_ok = await client.get(f"/api/documents/{doc1_id}/download", headers={"Authorization": f"Bearer {doctor2_token}"})
        print(f"Doctor 2 downloading Doc 1 after grant: {r_d2_down_ok.status_code}") # 200

        print(f"\n[Doctor cannot access unselected documents]")
        r_d2_down_fail = await client.get(f"/api/documents/{doc2_id}/download", headers={"Authorization": f"Bearer {doctor2_token}"})
        print(f"Doctor 2 downloading Doc 2 (unselected): {r_d2_down_fail.status_code}") # 403

        print(f"\n[Patient revokes access]")
        r_revoke = await client.post(f"/api/access-grants/{grant_id}/revoke", headers={"Authorization": f"Bearer {patient1_token}"})
        print(f"Patient revocation status: {r_revoke.status_code}") # 200

        print(f"\n[Access fails after revocation]")
        r_d2_down_revoked = await client.get(f"/api/documents/{doc1_id}/download", headers={"Authorization": f"Bearer {doctor2_token}"})
        print(f"Doctor 2 downloading Doc 1 after revocation: {r_d2_down_revoked.status_code}") # 403

        print("\n--- Phase 3 Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(test_access_requests())
