# MedFlow Guardian

**MedFlow Guardian** is a prototype hospital monitoring application and patient-controlled medical record platform.

**Disclaimer:** This is a verified prototype for demonstration. We do not claim real hospital integration, real medical-device integration, trained medical AI, or actual regulatory (HIPAA/GDPR) compliance. 

## Architecture
- **Backend**: FastAPI (Python 3.11), SQLite, Uvicorn, WebSockets.
- **Doctor Portal**: React/Vite (Port 5175).
- **Patient App**: React/Vite (Port 5174).

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
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```
*(A clean `medflow.db` database will automatically initialize and seed with demo accounts on startup).*

### 2. Patient App (port 5174)
```bash
cd patient-app
npm install
npm run dev -- --port 5174
```
Navigate to: http://localhost:5174

### 3. Doctor Portal (port 5175)
```bash
cd doctor-portal
npm install
npm run dev -- --port 5175
```
Navigate to: http://localhost:5175

## Pre-configured Demo Accounts
Use password `password` for all accounts.
- **Patient**: `patient@demo.com`
- **Doctor (Hospital A)**: `doctor@demo.com`
- **Doctor (Hospital B)**: `doctor2@demo.com`
- **Admin**: `admin@demo.com`

## Reset Instructions
To completely reset the entire state of the application to a fresh install:
1. Stop the backend server.
2. Delete the `backend/medflow.db` SQLite file.
3. Restart the backend server. The database will safely reseed.

## Known Limitations
- The system uses SQLite without at-rest encryption.
- Triage queues are globally visible to all doctors rather than siloed per hospital.
- Hardcoded test documents are mocked via API integrations rather than actual EMR ingestion endpoints.
