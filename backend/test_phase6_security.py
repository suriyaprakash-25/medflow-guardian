import httpx
import asyncio

async def test_phase6_security():
    print("--- Testing Phase 6 Security Fixes ---")
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        # 1. Login Admin, Doctor 1, Doctor 2, Patient 1
        d1_resp = await client.post("/api/auth/login", data={"username": "doctor@demo.com", "password": "password"})
        doctor1_token = d1_resp.json()["access_token"]
        
        d2_resp = await client.post("/api/auth/login", data={"username": "doctor2@demo.com", "password": "password"})
        doctor2_token = d2_resp.json()["access_token"]
        
        p1_resp = await client.post("/api/auth/login", data={"username": "patient@demo.com", "password": "password"})
        patient1_token = p1_resp.json()["access_token"]

        patient_id = 1 # Patient 1 id is 1

        # Register a brand new Doctor 3 who has no visits using DB
        import uuid
        from app.core.database import SessionLocal
        from app.models.user import User
        from app.core.security import get_password_hash
        
        db = SessionLocal()
        hacker_email = f"hacker_{uuid.uuid4().hex[:6]}@demo.com"
        hacker = User(email=hacker_email, hashed_password=get_password_hash("password"), role="doctor", full_name="Hacker Doc")
        db.add(hacker)
        db.commit()
        db.refresh(hacker)
        hacker_id = hacker.id
        db.close()

        d3_resp = await client.post("/api/auth/login", data={"username": hacker_email, "password": "password"})
        hacker_token = d3_resp.json()["access_token"]

        # Test IDOR 1: Hacker doc (no visit with Patient 1) tries to view readings
        print("Testing IDOR: Unauthorized Readings Access")
        r_readings = await client.get(f"/api/readings/{patient_id}", headers={"Authorization": f"Bearer {hacker_token}"})
        assert r_readings.status_code == 403, f"Expected 403 for unauthorized readings, got {r_readings.status_code}"
        print("PASS: Unauthorized reading access blocked")

        # Test IDOR 2: Hacker doc tries to view document metadata of Patient 1 (no visit)
        print("Testing IDOR: Unauthorized Metadata Access")
        r_meta = await client.get(f"/api/documents/metadata/{patient_id}", headers={"Authorization": f"Bearer {hacker_token}"})
        assert r_meta.status_code == 403, f"Expected 403 for unauthorized metadata, got {r_meta.status_code}"
        print("PASS: Unauthorized metadata access blocked")

        # Test IDOR 3: Patient tries to message Hacker doc (no relationship)
        print("Testing IDOR: Unauthorized Messaging")
        # Find hacker doc id
        r_msg = await client.post("/api/messages", json={"receiver_id": hacker_id, "content": "Hello"}, headers={"Authorization": f"Bearer {patient1_token}"})
        assert r_msg.status_code == 403, f"Expected 403 for unauthorized messaging, got {r_msg.status_code}"
        print("PASS: Unauthorized messaging blocked")
        
        # Test 4: Path traversal on file upload
        print("Testing Path Traversal extension")
        # Doctor 1 has visit, so they can upload
        d1_visits = await client.get("/api/visits/doctor", headers={"Authorization": f"Bearer {doctor1_token}"})
        visit1 = d1_visits.json()[0]

        files = {'file': ('evil.pdf/../malware.sh', b'fake pdf content', 'application/pdf')}
        data = {
            'patient_id': str(visit1['patient_id']),
            'hospital_id': str(visit1['hospital_id']),
            'visit_id': str(visit1['id']),
            'document_type': 'lab report',
            'title': 'Test Report Phase 6'
        }
        r_upload = await client.post("/api/documents", headers={"Authorization": f"Bearer {doctor1_token}"}, files=files, data=data)
        assert r_upload.status_code == 400, f"Expected 400 for bad extension, got {r_upload.status_code}"
        print("PASS: Bad file extension rejected")

        print("SUCCESS! All security tests passed.")

if __name__ == "__main__":
    asyncio.run(test_phase6_security())
