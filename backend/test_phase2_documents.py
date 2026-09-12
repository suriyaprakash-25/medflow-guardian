import httpx
import asyncio
import os

async def test_documents():
    print("--- Testing Phase 2 Documents ---")
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # 1. Login
        p_resp = await client.post("/api/auth/login", data={"username": "patient@demo.com", "password": "password"})
        patient_token = p_resp.json()["access_token"]
        
        d1_resp = await client.post("/api/auth/login", data={"username": "doctor@demo.com", "password": "password"})
        doctor1_token = d1_resp.json()["access_token"]
        
        d2_resp = await client.post("/api/auth/login", data={"username": "doctor2@demo.com", "password": "password"})
        doctor2_token = d2_resp.json()["access_token"]

        # Wait to get visit ID for doctor 1
        d1v_resp = await client.get("/api/visits/doctor", headers={"Authorization": f"Bearer {doctor1_token}"})
        d1_visits = d1v_resp.json()
        if not d1_visits:
            print("FAILED: No visits found for Doctor 1")
            return
        visit_1_id = d1_visits[0]["id"]
        
        d2v_resp = await client.get("/api/visits/doctor", headers={"Authorization": f"Bearer {doctor2_token}"})
        d2_visits = d2v_resp.json()
        visit_2_id = d2_visits[0]["id"]

        # 2. Test Invalid/Missing JWT on upload
        print("\n[Auth Validation]")
        r_no_auth = await client.post("/api/documents")
        print(f"Missing JWT status: {r_no_auth.status_code}") # Expected 401

        # 3. Test File Validation (Invalid type, Oversized)
        print("\n[File Validation]")
        dummy_txt = b"Hello world"
        # Invalid mime type
        files_invalid = {'file': ('test.exe', dummy_txt, 'application/x-msdownload')}
        data = {"visit_id": str(visit_1_id), "document_type": "prescription", "title": "Test"}
        r_invalid_type = await client.post("/api/documents", data=data, files=files_invalid, headers={"Authorization": f"Bearer {doctor1_token}"})
        print(f"Invalid file type status: {r_invalid_type.status_code}") # Expected 400

        # Oversized file
        large_txt = b"0" * (11 * 1024 * 1024) # 11 MB
        files_large = {'file': ('large.txt', large_txt, 'text/plain')}
        r_large = await client.post("/api/documents", data=data, files=files_large, headers={"Authorization": f"Bearer {doctor1_token}"})
        print(f"Oversized file status: {r_large.status_code}") # Expected 400

        # 4. Valid Upload
        print("\n[Valid Upload]")
        files_valid = {'file': ('valid.pdf', b"PDF content mock", 'application/pdf')}
        r_upload = await client.post("/api/documents", data=data, files=files_valid, headers={"Authorization": f"Bearer {doctor1_token}"})
        print(f"Valid upload status: {r_upload.status_code}")
        doc_id = r_upload.json()["id"]

        # 5. Doctor 2 attempts to upload to Doctor 1's visit (Hospital 1)
        print("\n[Upload RBAC]")
        files_valid2 = {'file': ('valid2.txt', b"TXT content", 'text/plain')}
        r_upload2 = await client.post("/api/documents", data={"visit_id": str(visit_1_id), "document_type": "lab report", "title": "Sneaky"}, files=files_valid2, headers={"Authorization": f"Bearer {doctor2_token}"})
        print(f"Doctor 2 uploading to Hospital 1 visit: {r_upload2.status_code}") # Expected 403

        # 6. Patient List Documents & Metadata Persistence
        print("\n[Patient Documents API]")
        p_docs_resp = await client.get("/api/documents/patient", headers={"Authorization": f"Bearer {patient_token}"})
        p_docs = p_docs_resp.json()
        print(f"Documents found: {len(p_docs)}")
        doc = p_docs[0]
        print(f"Metadata - Title: {doc['title']}, Type: {doc['document_type']}, Filename: {doc['original_filename']}")

        # 7. Document Download Authorization
        print("\n[Download Authorization]")
        # Doctor 1 (Uploader / Hospital 1)
        r_d1_down = await client.get(f"/api/documents/{doc_id}/download", headers={"Authorization": f"Bearer {doctor1_token}"})
        print(f"Doctor 1 download status: {r_d1_down.status_code}") # Expected 200

        # Doctor 2 (Different Hospital)
        r_d2_down = await client.get(f"/api/documents/{doc_id}/download", headers={"Authorization": f"Bearer {doctor2_token}"})
        print(f"Doctor 2 download status: {r_d2_down.status_code}") # Expected 403

        # Patient (Owner)
        r_p_down = await client.get(f"/api/documents/{doc_id}/download", headers={"Authorization": f"Bearer {patient_token}"})
        print(f"Patient download status: {r_p_down.status_code}") # Expected 200

        # Another patient? We only have one patient demoed, but patient accessing another is protected since they only see theirs.
        
        print("\n--- Phase 2 Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(test_documents())
