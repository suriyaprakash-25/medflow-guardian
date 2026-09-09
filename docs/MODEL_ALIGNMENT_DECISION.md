# Model Alignment Decision

## Background
The gap analysis suggested renaming `HospitalStaff` to `PractitionerProfile`. We needed to review `HospitalStaff`'s current capabilities to determine if it should be renamed, and if `PractitionerProfile` was genuinely missing.

## Analysis of `HospitalStaff`
`HospitalStaff` acts as a many-to-many junction table linking doctors to hospitals.
It currently supports:
- Multiple hospitals per doctor
- Roles (e.g., admin, doctor)
- Active/inactive membership (`is_active` flag)

While it lacks a detailed string status for invitations/onboarding and granular hospital-specific permissions, it successfully serves its primary purpose: providing hospital-level authorization and isolation for doctors.

## Decision: Retain `HospitalStaff`
Because `HospitalStaff` acts as a multi-tenant authorization mapping rather than a 1-to-1 global profile, renaming it to `PractitionerProfile` would be architecturally incorrect. A profile represents a single doctor's global attributes, not their many relationships to various hospitals. Furthermore, renaming a functioning, highly-relied-upon junction table introduces unnecessary regression risks. We will not rename `HospitalStaff`.

## Decision: Introduce `PractitionerProfile`
`PractitionerProfile` is genuinely missing from the domain model. Patients currently have a `PatientProfile` table that extends their 1-to-1 `User` record, but doctors have no such table to store their global professional information (e.g., medical license number, specialty, bio).

We will implement `PractitionerProfile` as a new table with a 1-to-1 relationship to the `User` table (where `role == 'doctor'`).

### PractitionerProfile Model
- `user_id` (ForeignKey, Unique)
- `specialty` (String)
- `license_number` (String)
- `bio` (Text)
- `is_verified` (Boolean)
