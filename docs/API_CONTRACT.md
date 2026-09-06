# API Contract

## Authentication
**Base Path:** `/api/auth`
### `POST /login`
Accepts `OAuth2PasswordRequestForm` (form fields `username` and `password`).
Returns `{ "access_token": "...", "token_type": "bearer", "role": "doctor|patient" }`.

## Triage
**Base Path:** `/api/triage`

### `POST /` (Patient Only)
Submit new symptoms for AI triage.
- **Request Body**:
```json
{
  "symptoms": "I have a severe headache and blurred vision."
}
```
- **Response** (200 OK):
```json
{
  "id": 1,
  "patient_id": 2,
  "symptoms": "I have a severe headache and blurred vision.",
  "status": "pending",
  "priority": "high",
  "ai_reasoning": "Keyword match for severe symptoms.",
  "created_at": "2026-09-06T12:00:00Z",
  "updated_at": null
}
```

### `GET /` (Doctor Only)
Retrieve all triage requests, optionally filtered by status.
- **Response** (200 OK):
```json
[
  {
    "id": 1,
    "patient_id": 2,
    "symptoms": "...",
    "status": "pending",
    "priority": "high",
    "ai_reasoning": "...",
    "created_at": "2026-09-06T12:00:00Z",
    "updated_at": null
  }
]
```
