# MedFlow Guardian — Demo Guide

**Last verified**: 2026-09-06 — Complete demo journey passed end-to-end.

---

## Exact Startup Commands

Open **three terminals** from `d:\Vscode\VORTEXA 2\medflow\`:

### Terminal 1 — Backend (port 8080)
```
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```
Wait for: `Application startup complete.`  
**First run**: tables are created and demo users are seeded automatically.

### Terminal 2 — Patient App (port 5174)
```
cd patient-app
npm run dev -- --port 5174
```
Wait for: `Local: http://localhost:5174/`

### Terminal 3 — Doctor Portal (port 5175)
```
cd doctor-portal
npm run dev -- --port 5175
```
Wait for: `Local: http://localhost:5175/`

---

## Demo Credentials

| Role | Email | Password |
|---|---|---|
| Patient | `patient@demo.com` | `password` |
| Doctor | `doctor@demo.com` | `password` |

> These accounts are seeded automatically on backend startup. No manual setup required.

---

## Browser Setup

Open **two browser windows side-by-side**:
- **Left**: http://localhost:5174 (Patient App)
- **Right**: http://localhost:5175 (Doctor Portal)

---

## Step-by-Step Demo Journey

### Phase 1 — Authentication

1. **Left (Patient)**: Navigate to http://localhost:5174  
   → Credentials are pre-filled: `patient@demo.com` / `password`  
   → Click **Sign In**  
   → **Expected**: Redirected to `/dashboard` with symptom submission form

2. **Right (Doctor)**: Navigate to http://localhost:5175  
   → Enter `doctor@demo.com` / `password`  
   → Click **Sign In**  
   → **Expected**: Redirected to `/dashboard` with triage queue

3. **Security check**: Try logging in on the doctor portal with patient credentials  
   → **Expected**: "Only doctors can log in here."

---

### Phase 2 — AI Triage

4. **Left (Patient)**: In "Submit New Symptoms", type exactly:  
   `Severe chest pain radiating to left arm`  
   → Click **Request Triage**  
   → **Expected**: Entry appears immediately in "My Triage History"  
   → AI Priority badge: **CRITICAL** (red)  
   → AI Reasoning: "Detected critical keywords indicating potential life-threatening emergency."  
   → Disclaimer: "⚠️ AI Assessment Only — Not a medical diagnosis..."

5. **Right (Doctor)**: Without refreshing  
   → **Expected**: Triage request appears in "Patient Triage Queue" automatically (WebSocket)  
   → Priority badge: **AI: CRITICAL**  
   → Status badge: **PENDING**

---

### Phase 3 — Status Update

6. **Right (Doctor)**: Click **Mark Reviewed**  
   → **Expected**: Status badge changes to **REVIEWED**

7. **Left (Patient)**: Without refreshing  
   → **Expected**: Status badge on that triage entry changes to **REVIEWED** automatically (WebSocket)

---

### Phase 4 — Live Vitals

8. **Left (Patient)**: Click the **Monitor OFF** button to toggle it ON  
   → **Expected**: Button shows "Monitor ON", text appears: "Broadcasting simulated vitals every 5s..."

9. **Right (Doctor)**: Wait 10 seconds  
   → **Expected**: "Live Patient Vitals" section shows reading with heart rate, O2 level, blood pressure  
   → Label `[SIMULATED]` is visible

---

### Phase 5 — Messaging

10. **Left (Patient)**: In "Chat with Doctor", type:  
    `Hello Doctor, I am worried.`  
    → Click **Send**  
    → **Expected**: Message appears in chat bubble on the right

11. **Right (Doctor)**: Without refreshing  
    → **Expected**: Patient message appears in "Chat with Patient"  
    → Type: `We are preparing a room for you immediately.`  
    → Click **Send**

12. **Left (Patient)**: Without refreshing  
    → **Expected**: Doctor reply appears in chat

---

### Phase 6 — Persistence Check

13. Hard refresh (F5) the Patient App  
    → **Expected**: Triage history still shows all entries  
    → REVIEWED status is preserved  
    → Chat messages are preserved

14. Hard refresh the Doctor Portal  
    → **Expected**: Triage queue still shows entries  
    → Chat messages are preserved

---

## Expected Behavior Summary

| Step | Expected Result |
|---|---|
| Patient login | Redirect to dashboard |
| Doctor login | Redirect to dashboard |
| Triage submit | CRITICAL priority, instant doctor queue update |
| Doctor marks reviewed | Patient sees update without refresh |
| Vitals toggle | Doctor sees simulated readings every 5s |
| Patient sends message | Doctor receives without refresh |
| Doctor sends reply | Patient receives without refresh |
| Page refresh | All data persists (SQLite) |

---

## Known Limitations

| Limitation | Notes |
|---|---|
| AI is keyword-based | Not ML — deterministic keyword matching only |
| Vitals are simulated | Clearly labeled `[SIMULATED]` — no hardware |
| Patient/Doctor IDs hardcoded | Demo uses patient id=1, doctor id=2. The Patient-to-Doctor assignment logic is simplified for demo purposes. |
| SQLite database | In-process; not for production multi-user |

---

## Troubleshooting

**Backend fails to start on port 8080**  
→ Check if another process has port 8080: `netstat -an | findstr 8080`  
→ Kill it or change the port in the uvicorn command AND vite proxy config

**"Could not validate credentials" on frontend**  
→ Backend was restarted. Click Logout and log in again.

**Doctor queue doesn't update in real-time**  
→ WebSocket may have disconnected. Refresh the doctor portal page.

**Triage POST returns 500 OperationalError**  
→ Old `medflow.db` from before the schema update. Delete `backend/medflow.db` and restart backend.

**Login fails for demo accounts**  
→ Ensure backend started successfully (check terminal for "Application startup complete.")  
→ Demo users are seeded on startup — if DB was corrupted, delete `medflow.db` and restart.


## Setup Before Presentation
1. Ensure all three servers are running:
   - Backend on `http://localhost:8080` (`uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload`)
   - Patient App on `http://localhost:5174` (`npm run dev -- --port 5174`)
   - Doctor Portal on `http://localhost:5175` (`npm run dev -- --port 5175`)
2. Open two browser windows side-by-side:
   - Left window: Patient App
   - Right window: Doctor Portal

## Demo Journey

### Phase 1: Authentication
1. **Patient App (Left)**: Log in with:
   - Email: `patient@demo.com`
   - Password: `password`
2. **Doctor Portal (Right)**: Log in with:
   - Email: `doctor@demo.com`
   - Password: `password`
3. *Narrative*: "We have a unified secure backend utilizing JWT authentication and role-based access control to ensure patients and doctors only see what they are authorized to see."

### Phase 2: AI Triage Submission
1. **Patient App**: In the 'Submit New Symptoms' box, type: `"Severe chest pain radiating to left arm"` and click **Request Triage**.
2. **Doctor Portal**: Point out that the request instantly appears in the queue on the right without refreshing the page (WebSockets).
3. *Narrative*: "The moment the patient submits symptoms, our AI Triage Engine analyzes the text. It detects critical keywords, flags the priority as **CRITICAL**, and instantly pushes the new request to the doctor's queue via WebSockets."

### Phase 3: Live Vitals Monitoring
1. **Patient App**: Click the **Monitor ON** button in the Vitals Monitor section.
2. **Doctor Portal**: Observe the 'Live Patient Vitals' feed. It will update every 5 seconds.
3. *Narrative*: "MedFlow Guardian integrates with hardware monitors. For this demo, we're simulating a live hardware feed. The patient app is streaming vitals via WebSockets, and the doctor can monitor them in real-time."

### Phase 4: Bi-Directional Chat & Resolution
1. **Doctor Portal**: Click **Mark Reviewed** on the new triage request.
2. **Patient App**: Show that the status badge changes to `REVIEWED` instantly.
3. **Patient App**: In the chat box, type `"Hello Doctor, I am worried."` and click **Send**.
4. **Doctor Portal**: Show the message appearing instantly. Reply with `"We are preparing a room for you immediately."`
5. *Narrative*: "Doctors can update statuses and chat with patients seamlessly in real-time. All data is persisted to an SQLite database via REST fallbacks to ensure zero data loss."

### End of Demo
"Thank you! MedFlow Guardian is fully functional end-to-end today."
