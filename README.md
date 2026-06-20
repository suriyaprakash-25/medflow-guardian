# MedFlow Guardian

> **A modern healthcare platform for real-time patient monitoring, AI-powered triage, and seamless doctor–patient communication.**

Built for the 2026 Healthcare Hackathon.

---

## 🏗️ Architecture Overview

MedFlow Guardian follows a **monorepo** layout with three independent applications that communicate through a shared backend API.

```
medflow/
├── patient-app/       # React Native (Expo) — mobile app for patients
├── doctor-portal/     # React + Vite — web dashboard for doctors
├── backend/           # FastAPI (Python) — REST API, AI services, data layer
│   └── app/
│       ├── api/       # Route definitions & request handlers
│       ├── models/    # Pydantic schemas & database models
│       ├── services/  # Business logic & integrations
│       ├── ai/        # AI/ML inference modules
│       └── main.py    # FastAPI application entry point
└── docs/              # Documentation, ADRs, diagrams
```

### Data Flow

```
┌──────────────┐        HTTPS / WSS        ┌───────────────┐
│  Patient App │  ◄──────────────────────►  │   FastAPI      │
│  (Expo/RN)   │                            │   Backend      │
└──────────────┘                            │                │
                                            │  ┌──────────┐  │
┌──────────────┐        HTTPS / WSS        │  │ AI / ML  │  │
│ Doctor Portal│  ◄──────────────────────►  │  │ Engine   │  │
│  (React+Vite)│                            │  └──────────┘  │
└──────────────┘                            │                │
                                            │  ┌──────────┐  │
                                            │  │ Database │  │
                                            │  └──────────┘  │
                                            └───────────────┘
```

---

## 📦 Tech Stack

| Layer          | Technology                          |
| -------------- | ----------------------------------- |
| Patient App    | React Native, Expo, TypeScript      |
| Doctor Portal  | React, Vite, TypeScript             |
| Backend API    | Python, FastAPI, Pydantic           |
| AI / ML        | (TBD — pluggable module in `app/ai`)  |
| Database       | (TBD — Postgres / Supabase / Firebase) |
| Auth           | (TBD)                               |

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** ≥ 18
- **Python** ≥ 3.10
- **npm** (ships with Node)

### 1. Patient App (React Native / Expo)

```bash
cd patient-app
npm install
npx expo start        # launches the Expo dev server
```

### 2. Doctor Portal (React + Vite)

```bash
cd doctor-portal
npm install
npm run dev            # http://localhost:5173
```

### 3. Backend (FastAPI)

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000
```

API docs are auto-generated at [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI).

---

## 🗂️ Project Structure Details

### `patient-app/`
Expo-managed React Native app bootstrapped with the **blank-typescript** template. Targets iOS, Android, and web.

### `doctor-portal/`
Vite-powered React SPA using the **react-ts** template. Intended as a desktop-first dashboard for clinicians.

### `backend/`
FastAPI server exposing a REST + WebSocket API.

| Sub-package | Purpose |
|-------------|---------|
| `app/api/`      | Route modules (one file per resource/domain) |
| `app/models/`   | Pydantic request/response schemas & ORM models |
| `app/services/` | Business logic, third-party integrations |
| `app/ai/`       | AI/ML inference wrappers (triage, NLP, etc.) |

### `docs/`
Architecture Decision Records, API specs, and design documents.

---

## 📝 License

TBD — to be decided by the team.
