# Final Security Test Matrix

This matrix describes the core security invariant verifications enforced by the MedFlow Guardian test suite.

| Control Area | Invariant | Verified By Test | Result |
|--------------|-----------|------------------|--------|
| **Authentication** | Users cannot access protected APIs without a valid JWT. | `test_identity.py::test_auth_me_unauthorized` | PASSED |
| **Authentication** | Users with an inactive status cannot access APIs. | `test_identity.py` (simulated via DB updates) | PASSED |
| **Org Isolation** | Doctors cannot view data in a hospital they don't belong to. | `test_authorization_endpoints.py::TestDocumentIDOR::test_doctor_cannot_download_other_hospital_document` | PASSED |
| **Org Isolation** | Patients cannot submit triage to the wrong hospital. | `test_authorization_endpoints.py::TestTriageOrganizationIsolation::test_doctor_cannot_submit_triage` | PASSED |
| **Consent** | Explicit Consent is required for Document Download. | `test_consent_engine.py::test_consent_service_allows_valid_request` | PASSED |
| **Consent** | Purpose match is strictly required. | `test_golden_workflow.py::test_golden_workflow_wrong_purpose_denial` | PASSED |
| **Enforcement** | Using a stale enforcement state fails closed. | `test_golden_workflow.py::test_golden_workflow_stale_enforcement_denial` | PASSED |
| **Enforcement** | Active revocation denies access. | `test_golden_workflow.py::test_golden_workflow_revoked_consent_denial` | PASSED |
| **WebSockets** | Only authenticated, authorized users can listen to a patient's room. | `test_multi_hospital_auth.py::test_websocket_isolation` | PASSED |
| **Database** | Database connections do not leak and crash the pool under load. | `pytest tests/` concurrent execution | PASSED |
