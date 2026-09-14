# P1 Change Log

- Added shared TypeScript API transport contracts under `frontend-shared/api` and migrated core patient, clinician and admin auth/context consumers.
- Removed clinician-entered consent IDs from FHIR export.
- Changed practitioner FHIR export to accept purpose + hospital scope and resolve exact active consent server-side before CAE/ConsentService evaluation.
- Added server-resolved consent regression coverage.
- Added authenticated HTTP FHIR integration exporter and official HL7-validator CI workflow.
- Extended production smoke validation with FHIR CapabilityStatement checks.
- Added explicit live Render/Supabase/ClamAV recovery evidence protocol.
- Recorded external OIDC federation as not currently required.
- Added current architecture reference and removed an obsolete feature audit that contradicted runtime reality.
