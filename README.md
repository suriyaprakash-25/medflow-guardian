# MedFlow Guardian

> **A modern healthcare platform for real-time patient monitoring, AI-powered triage, and seamless doctor–patient communication.**

Built for the 2026 Healthcare Hackathon.

---

## 🏗️ Architecture Overview

MedFlow Guardian follows a **monorepo** layout with two independent frontend web applications that communicate through a shared backend API and WebSocket hub.

```
medflow/
├── patient-app/       # React + Vite — web dashboard for patients
├── doctor-portal/     # React + Vite — web dashboard for doctors
├── backend/           # FastAPI (Python) — REST API, WebSockets, AI, data layer
│   └── app/
│       ├── api/       # Route definitions & request handlers
│       ├── models/    # SQLAlchemy ORM models
│       ├── schemas/   # Pydantic schemas
│       ├── core/      # Config, security, DB connections
│       ├── ai/        # AI/ML triage engine
│       └── main.py    # FastAPI application entry point
└── docs/              # Documentation, ADRs, diagrams, demo guides
```

### Data Flow

```
┌──────────────┐        HTTPS / WSS        ┌───────────────┐
│  Patient App │  ◄──────────────────────►  │   FastAPI      │
│ (React+Vite) │                            │   Backend      │
└──────────────┘                            │                │
                                            │  ┌──────────┐  │
┌──────────────┐        HTTPS / WSS        │  │ AI Triage│  │
│ Doctor Portal│  ◄──────────────────────►  │  │ Engine   │  │
│ (React+Vite) │                            │  └──────────┘  │
└──────────────┘                            │                │
                                            │  ┌──────────┐  │
                                            │  │  SQLite  │  │
                                            │  └──────────┘  │
                                            └───────────────┘
```

---

## 📦 Tech Stack

| Layer          | Technology                          |
| -------------- | ----------------------------------- |
| Patient App    | React, Vite, TypeScript, Axios      |
| Doctor Portal  | React, Vite, TypeScript, Axios      |
| Backend API    | Python, FastAPI, Pydantic, WebSockets|
| AI / ML        | Keyword-based Mock (Hackathon MVP)  |
| Database       | SQLite (via SQLAlchemy & Alembic)   |
| Auth           | JWT (JSON Web Tokens)               |

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** ≥ 18
- **Python** ≥ 3.10

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```
API runs on `http://localhost:8080`.

### 2. Patient App (React + Vite)

```bash
cd patient-app
npm install
npm run dev -- --port 5174
```
Runs on `http://localhost:5174`.

### 3. Doctor Portal (React + Vite)

```bash
cd doctor-portal
npm install
npm run dev -- --port 5175
```
Runs on `http://localhost:5175`.

---

## 📖 Further Reading
- [End-to-End Demo Guide](docs/DEMO_GUIDE.md)
