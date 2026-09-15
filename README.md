# MedFlow Guardian

**MedFlow Guardian** is a hospital monitoring application and patient-controlled medical record platform.

**Disclaimer:** This is a verified platform for demonstration. We do not claim real hospital integration, real medical-device integration, trained medical AI, or actual regulatory (HIPAA/GDPR) compliance. 

## Architecture
- **Backend**: FastAPI (Python 3.11), PostgreSQL (via Supabase), Uvicorn, WebSockets.
- **Storage**: Supabase Storage for secure medical document persistence.
- **Security**: Model A collocated PDP + PEP, ClamAV Malware Quarantine, FHIR Interoperability.
- **Doctor Portal**: React/Vite (Port 5175).
- **Patient App**: React/Vite (Port 5174).
- **Admin Portal**: React/Vite (Port 5176).

## Main Workflows
1. **Hospital A doctor uploads reports** for a patient.
2. **Patient sees reports** in their vault.
3. **Hospital B doctor requests access** to a specific report.
4. **Patient approves access** for a limited time duration.
5. **Hospital B doctor can view** the approved report until it naturally expires or the patient revokes access.
6. **Audit log** completely records the sequence of uploads, views, grants, and revocations.

## Startup Instructions

### 1. Backend (port 8080)
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 2. Patient App (port 5174)
```bash
cd patient-app
npm ci
npm run dev
```
Navigate to: http://localhost:5174

### 3. Doctor Portal (port 5175)
```bash
cd doctor-portal
npm ci
npm run dev
```
Navigate to: http://localhost:5175

### 4. Admin Portal (port 5176)
```bash
cd admin-portal
npm ci
npm run dev
```
Navigate to: http://localhost:5176

## Pre-configured Demo Accounts
Use password `password` for all accounts.
- **Patient**: `patient@demo.com`
- **Doctor (Hospital A)**: `doctor@demo.com`
- **Doctor (Hospital B)**: `doctor2@demo.com`
- **Admin**: `admin@demo.com`

## Known Limitations
- Triage queues are globally visible to all doctors rather than siloed per hospital.
- Hardcoded test documents are mocked via API integrations rather than actual EMR ingestion endpoints.
