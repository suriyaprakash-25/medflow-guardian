# MedFlow Guardian Architecture

## Overview
MedFlow Guardian is a unified healthcare prototype built for the 2026 Healthcare Hackathon. The platform consists of two Vite+React single-page applications and a FastAPI Python backend, all communicating over REST (with WebSockets planned for live updates).

## Tech Stack
- **Frontend (Doctor & Patient)**: React, Vite, TypeScript, Vanilla CSS
- **Backend**: FastAPI, Pydantic, SQLAlchemy, Alembic
- **Database**: SQLite (local development)
- **Authentication**: JWT-based stateless auth
- **AI Triage**: Mock keyword-based engine (pluggable for future real LLM integration)

## Core Components
### `doctor-portal/` & `patient-app/`
Both frontends are simple SPAs. They consume the REST API to load the patient queue, submit triage requests, and manage messaging.

### `backend/`
- `app/api/`: REST API routers.
- `app/core/`: Security, config, and DB session management.
- `app/models/`: SQLAlchemy ORM models.
- `app/schemas/`: Pydantic validation schemas.
- `app/services/`: Core business logic.
- `app/ai/`: The `triage_engine.py` module responsible for parsing symptoms and returning a priority/disclaimer.

## Data Model
- **User**: Represents either a `doctor` or a `patient`.
- **PatientProfile**: Extended details for a patient, linking them to an assigned doctor.
- **TriageRequest**: A patient's submitted symptoms, the AI's triage result, and the doctor's review status.
