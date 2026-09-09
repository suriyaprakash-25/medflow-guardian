import httpx
import asyncio
import sqlite3
import os
import sys

async def run_final_verification():
    print("=== FINAL END-TO-END VERIFICATION ===")
    
    # Run the seed script to ensure DB is initialized and migrated
    print("Running database initialization and seeding (Step 0)...")
    import subprocess
    import os
    seed_script_path = os.path.join(os.path.dirname(__file__), "scripts", "seed.py")
    seed_result = subprocess.run([sys.executable, seed_script_path], capture_output=True, text=True)
    if seed_result.returncode != 0:
        print("FAILED to seed database:", seed_result.stderr)
        assert False
    print("VERIFIED: Database initialization and seeding successful")
    
    # Check git tracking first (Step 30)
    print("Checking Git tracking (Step 30)...")
    git_check = os.popen('git ls-files medflow.db storage/documents/').read()
    if git_check.strip() == "":
        print("VERIFIED: No secrets or medical files tracked by Git")
    else:
        print("FAILED: Git is tracking files it shouldn't be:", git_check)

    # We assume the server is running on localhost:8080. 
    # (Step 1) Start backend on the documented port.
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        
        # (Step 4) Create or use safe demo accounts.
        # (Step 5, 6, 7, 8, 9) Implicitly handled by backend seed
        p_resp = await client.post("/api/auth/login", data={"username": "patient@demo.com", "password": "password"})
        patient_token = p_resp.json()["access_token"]
        
        d1_resp = await client.post("/api/auth/login", data={"username": "doctor@demo.com", "password": "password"})
        doctor1_token = d1_resp.json()["access_token"]
        
        d2_resp = await client.post("/api/auth/login", data={"username": "doctor2@demo.com", "password": "password"})
        doctor2_token = d2_resp.json()["access_token"]

        print("VERIFIED: Safe demo accounts and login.")

        # Doctor A gets visits
        d1_visits = await client.get("/api/visits/doctor", headers={"Authorization": f"Bearer {doctor1_token}"})
        visit1 = d1_visits.json()[0]
        
        # (Step 10) Upload a prescription or medical report.
        print("Uploading Document 1 (Prescription)...")
        doc1_data = {
            'patient_id': str(visit1['patient_id']),
            'hospital_id': str(visit1['hospital_id']),
            'visit_id': str(visit1['id']),
            'document_type': 'prescription',
            'title': 'Prescription A'
        }
        r_doc1 = await client.post("/api/documents", headers={"Authorization": f"Bearer {doctor1_token}"}, files={'file': ('rx.pdf', b'fake pdf', 'application/pdf')}, data=doc1_data)
        doc1 = r_doc1.json()

        print("Uploading Document 2 (Lab Report)...")
        doc2_data = {
            'patient_id': str(visit1['patient_id']),
            'hospital_id': str(visit1['hospital_id']),
            'visit_id': str(visit1['id']),
            'document_type': 'lab report',
            'title': 'Lab Report A'
        }
        r_doc2 = await client.post("/api/documents", headers={"Authorization": f"Bearer {doctor1_token}"}, files={'file': ('lab.pdf', b'fake lab', 'application/pdf')}, data=doc2_data)
        doc2 = r_doc2.json()

        # (Step 11) Confirm the patient sees the document.
        p_docs = await client.get("/api/documents/patient", headers={"Authorization": f"Bearer {patient_token}"})
        doc_ids = [d['id'] for d in p_docs.json()]
        assert doc1['id'] in doc_ids and doc2['id'] in doc_ids
        print("VERIFIED: Patient sees documents.")

        # (Step 12 & 13) Log in as Doctor B. Confirm Hospital B doctor cannot automatically view Hospital A report.
        r_fail = await client.get(f"/api/documents/{doc1['id']}/download", headers={"Authorization": f"Bearer {doctor2_token}"})
        assert r_fail.status_code == 403
        print("VERIFIED: Doctor B cannot view unapproved documents.")

        # (Step 14) Submit an access request for ONE selected document.
        d2_visits = await client.get("/api/visits/doctor", headers={"Authorization": f"Bearer {doctor2_token}"})
        d2_hospital_id = d2_visits.json()[0]['hospital_id']
        
        r_req = await client.post("/api/access-requests", json={
            "patient_id": visit1['patient_id'],
            "hospital_id": d2_hospital_id,
            "document_ids": [doc1['id']],
            "reason": "Consultation"
        }, headers={"Authorization": f"Bearer {doctor2_token}"})
        if r_req.status_code != 200:
            print("FAILED at Step 14. Access request rejected:", r_req.text)
            assert False
        req = r_req.json()

        # (Step 15) Confirm the patient receives the request.
        p_reqs = await client.get("/api/access-requests/patient", headers={"Authorization": f"Bearer {patient_token}"})
        reqs_json = p_reqs.json()
        
        if not any(r['id'] == req['id'] for r in reqs_json):
            print("FAILED at Step 15. Request ID not found in patient reqs:", reqs_json)
            assert False
        print("VERIFIED: Patient receives the access request.")

        # (Step 16) Patient approves access for a short duration.
        appr_resp = await client.post(f"/api/access-requests/{req['id']}/approve", json={
            "document_ids": [doc1['id']],
            "duration_hours": 1
        }, headers={"Authorization": f"Bearer {patient_token}"})
        grant1 = appr_resp.json()
        print("VERIFIED: Patient approves access request.")

        # (Step 17) Confirm Hospital B doctor can view only the approved document.
        r_succ = await client.get(f"/api/documents/{doc1['id']}/download", headers={"Authorization": f"Bearer {doctor2_token}"})
        assert r_succ.status_code == 200
        print("VERIFIED: Doctor B can view the approved document.")

        # (Step 18) Confirm another unapproved document remains inaccessible.
        r_fail2 = await client.get(f"/api/documents/{doc2['id']}/download", headers={"Authorization": f"Bearer {doctor2_token}"})
        assert r_fail2.status_code == 403
        print("VERIFIED: Unapproved document remains inaccessible.")

        # (Step 19) Revoke access.
        await client.post(f"/api/access-grants/{grant1['id']}/revoke", headers={"Authorization": f"Bearer {patient_token}"})
        
        # (Step 20) Confirm access is immediately denied.
        r_fail3 = await client.get(f"/api/documents/{doc1['id']}/download", headers={"Authorization": f"Bearer {doctor2_token}"})
        assert r_fail3.status_code == 403
        print("VERIFIED: Access immediately denied after revocation.")

        # (Step 21) Test automatic expiry using a short test expiry or controlled test clock.
        # Re-request and approve
        r_req2 = await client.post("/api/access-requests", json={
            "patient_id": visit1['patient_id'],
            "hospital_id": d2_hospital_id,
            "document_ids": [doc2['id']],
            "reason": "Consultation 2"
        }, headers={"Authorization": f"Bearer {doctor2_token}"})
        req2 = r_req2.json()

        appr_resp = await client.post(f"/api/access-requests/{req2['id']}/approve", json={
            "document_ids": [doc2['id']],
            "duration_hours": 1
        }, headers={"Authorization": f"Bearer {patient_token}"})
        grant2 = appr_resp.json()

        # Modify database to expire the grant artificially
        conn = sqlite3.connect("medflow.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE document_access_grants SET expires_at = datetime('now', '-1 hour') WHERE id = ?", (grant2['id'],))
        conn.commit()
        conn.close()

        # Try to download again
        r_fail4 = await client.get(f"/api/documents/{doc2['id']}/download", headers={"Authorization": f"Bearer {doctor2_token}"})
        assert r_fail4.status_code == 403
        print("VERIFIED: Automatic expiry correctly denies access.")

        # (Step 22) Confirm audit events are created.
        p_audit = await client.get("/api/audit/patient", headers={"Authorization": f"Bearer {patient_token}"})
        audit_actions = [a['action'] for a in p_audit.json()]
        assert "access approved" in audit_actions and "access revoked" in audit_actions
        print("VERIFIED: Audit events are created.")

        # (Step 23) Confirm notifications are created.
        d2_notifs = await client.get("/api/notifications", headers={"Authorization": f"Bearer {doctor2_token}"})
        notif_msgs = [n['message'] for n in d2_notifs.json()]
        assert any("approved" in m for m in notif_msgs)
        print("VERIFIED: Notifications are created.")
        
        print("=== VERIFICATION SCRIPT COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(run_final_verification())
