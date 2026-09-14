# P1 Validation Plan

The P1 branch must not merge until the repository's existing backend/security/frontend checks and the new authenticated HTTP FHIR integration workflow are green.

Validation includes:

1. backend authorization/consent/storage/malware/full integration suite;
2. patient, clinician and admin lint/test/build;
3. official HL7 validator over generated fixtures;
4. authenticated HTTP login -> identity -> FHIR export -> official HL7 validator;
5. source-level regression tests preventing client consent-ID authority;
6. production smoke/recovery protocol readiness.

Live Render/Supabase account verification is a separate operational evidence gate and is not implied by repository CI.
