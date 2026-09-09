import httpx
import asyncio

async def test_audit_notifications():
    print("--- Testing Phase 4 Audit and Notifications ---")
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        # Login
        p1_resp = await client.post("/api/auth/login", data={"username": "patient@demo.com", "password": "password"})
        patient1_token = p1_resp.json()["access_token"]
        
        d1_resp = await client.post("/api/auth/login", data={"username": "doctor@demo.com", "password": "password"})
        doctor1_token = d1_resp.json()["access_token"]
        
        # 1. Check patient notifications
        p1_notif_resp = await client.get("/api/notifications", headers={"Authorization": f"Bearer {patient1_token}"})
        notifs = p1_notif_resp.json()
        print(f"Patient notifications found: {len(notifs)}")
        
        # 2. Check patient audit logs
        p1_audit_resp = await client.get("/api/audit/patient", headers={"Authorization": f"Bearer {patient1_token}"})
        audits = p1_audit_resp.json()
        print(f"Patient audit logs found: {len(audits)}")
        
        # 3. Check doctor audit logs
        d1_audit_resp = await client.get("/api/audit/doctor", headers={"Authorization": f"Bearer {doctor1_token}"})
        d_audits = d1_audit_resp.json()
        print(f"Doctor audit logs found: {len(d_audits)}")
        
        # 4. Try unauthorized access to audit logs
        d1_unauth_resp = await client.get("/api/audit/patient", headers={"Authorization": f"Bearer {doctor1_token}"})
        print(f"Doctor accessing patient audit endpoint status: {d1_unauth_resp.status_code}") # Expected 403
        
        p1_unauth_resp = await client.get("/api/audit/doctor", headers={"Authorization": f"Bearer {patient1_token}"})
        print(f"Patient accessing doctor audit endpoint status: {p1_unauth_resp.status_code}") # Expected 403

        # 5. Mark notification as read
        if len(notifs) > 0:
            n_id = notifs[0]['id']
            r_read = await client.post(f"/api/notifications/{n_id}/read", headers={"Authorization": f"Bearer {patient1_token}"})
            print(f"Mark read status: {r_read.status_code}")
            
            r_all_read = await client.post(f"/api/notifications/read-all", headers={"Authorization": f"Bearer {patient1_token}"})
            print(f"Mark all read status: {r_all_read.status_code}")

    print("--- Phase 4 Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(test_audit_notifications())
