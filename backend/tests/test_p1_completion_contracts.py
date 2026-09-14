from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_shared_frontend_contracts_exist_and_all_portals_consume_them():
    contracts = ROOT / "frontend-shared" / "api" / "contracts.ts"
    assert contracts.exists()
    source = contracts.read_text()
    assert "LoginResponseContract" in source
    assert "FhirExportContextContract" in source

    assert "@shared/api/contracts" in (
        ROOT / "patient-app" / "src" / "lib" / "patientContext.ts"
    ).read_text()
    assert "@shared/api/contracts" in (
        ROOT / "doctor-portal" / "src" / "lib" / "doctorContext.ts"
    ).read_text()
    assert "@shared/api/contracts" in (
        ROOT / "admin-portal" / "src" / "pages" / "Login.tsx"
    ).read_text()


def test_clinician_fhir_export_has_no_client_consent_authority():
    portal = (ROOT / "doctor-portal" / "src" / "pages" / "PatientDetails.tsx").read_text()
    endpoint = (ROOT / "backend" / "app" / "api" / "interoperability.py").read_text()

    assert "window.prompt" not in portal
    assert "consent_id" not in portal
    assert "hospital_id" in portal
    assert "resolve_active_scoped_consent" in endpoint
    assert "consent.id if consent else None" in endpoint


def test_current_architecture_reference_replaces_superseded_audit():
    assert (ROOT / "docs" / "ARCHITECTURE_CURRENT.md").exists()
    assert not (ROOT / "docs" / "audit" / "MEDFLOW_COMPLETE_FEATURE_IMPLEMENTATION_AUDIT.md").exists()
    assert (ROOT / "docs" / "adr" / "ADR-001-OIDC-FEDERATION.md").exists()


def test_live_release_evidence_protocol_covers_storage_clamav_and_recovery():
    report = (ROOT / "docs" / "release" / "P1_LIVE_DEPLOYMENT_RECOVERY.md").read_text()
    for phrase in ("public=false", "PING/PONG", "pending scan", "restart/redeploy", "/ready"):
        assert phrase in report
