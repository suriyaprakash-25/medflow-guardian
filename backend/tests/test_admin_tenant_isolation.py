from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.main import app
from app.models.audit import AuditLog
from app.models.consent import Consent
from app.models.hospital import Hospital, HospitalStaff, Visit
from app.models.user import User


client = TestClient(app)


def _token(user: User) -> str:
    return create_access_token(subject=user.email, expires_delta=timedelta(minutes=15))


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user)}"}


def _seed_two_tenants(db: Session):
    h1 = Hospital(name="Tenant Isolation Hospital A")
    h2 = Hospital(name="Tenant Isolation Hospital B")
    db.add_all([h1, h2])
    db.flush()

    admin_a = User(
        email="tenant-admin-a@test.com",
        hashed_password="hashed",
        role="doctor",
        full_name="Tenant Admin A",
        is_active=True,
    )
    doctor_a = User(
        email="tenant-doctor-a@test.com",
        hashed_password="hashed",
        role="doctor",
        full_name="Tenant Doctor A",
        is_active=True,
    )
    patient_a = User(
        email="tenant-patient-a@test.com",
        hashed_password="hashed",
        role="patient",
        full_name="Tenant Patient A",
        is_active=True,
    )
    patient_b = User(
        email="tenant-patient-b@test.com",
        hashed_password="hashed",
        role="patient",
        full_name="Tenant Patient B",
        is_active=True,
    )
    db.add_all([admin_a, doctor_a, patient_a, patient_b])
    db.flush()

    db.add_all(
        [
            HospitalStaff(user_id=admin_a.id, hospital_id=h1.id, role="admin", is_active=True),
            HospitalStaff(user_id=doctor_a.id, hospital_id=h1.id, role="doctor", is_active=True),
            Visit(patient_id=patient_a.id, doctor_id=doctor_a.id, hospital_id=h1.id),
            # Duplicate visit must not inflate the distinct-patient metric.
            Visit(patient_id=patient_a.id, doctor_id=doctor_a.id, hospital_id=h1.id),
            Visit(patient_id=patient_b.id, doctor_id=None, hospital_id=h2.id),
            Consent(patient_id=patient_a.id, hospital_id=h1.id, status="active"),
            Consent(patient_id=patient_b.id, hospital_id=h2.id, status="active"),
            # Historical/non-active consent must not count as currently active.
            Consent(patient_id=patient_a.id, hospital_id=h1.id, status="revoked"),
        ]
    )
    db.flush()

    audit_a = AuditLog(
        actor_id=doctor_a.id,
        actor_role="doctor",
        organization_id=h1.id,
        patient_id=patient_a.id,
        operation="read",
        resource_type="document",
        resource_id="TENANT-A-AUDIT",
        decision="ALLOW",
    )
    audit_b = AuditLog(
        actor_id=doctor_a.id,
        actor_role="doctor",
        organization_id=h2.id,
        patient_id=patient_b.id,
        operation="read",
        resource_type="document",
        resource_id="TENANT-B-AUDIT",
        decision="ALLOW",
    )
    db.add_all([audit_a, audit_b])
    db.commit()

    return h1, h2, admin_a, doctor_a, patient_a, patient_b


def test_org_admin_dashboard_is_strictly_tenant_scoped(db_session: Session):
    h1, h2, admin_a, _, _, _ = _seed_two_tenants(db_session)

    response = client.get(
        f"/api/admin/dashboard?hospital_id={h1.id}",
        headers=_headers(admin_a),
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["metrics"]["total_staff"] == 2
    assert payload["metrics"]["active_consents"] == 1
    assert payload["metrics"]["total_patients"] == 1

    recent = payload["recent_activity"]
    assert recent
    assert all(item["organization_id"] == h1.id for item in recent)
    assert all(item.get("resource_id") != "TENANT-B-AUDIT" for item in recent)

    other = client.get(
        f"/api/admin/dashboard?hospital_id={h2.id}",
        headers=_headers(admin_a),
    )
    assert other.status_code == 403


def test_org_admin_audit_endpoint_cannot_cross_tenant_boundary(db_session: Session):
    h1, h2, admin_a, _, _, _ = _seed_two_tenants(db_session)

    own = client.get(
        f"/api/admin/audit?hospital_id={h1.id}&limit=200",
        headers=_headers(admin_a),
    )
    assert own.status_code == 200, own.text
    own_items = own.json()["items"]
    assert any(item.get("resource_id") == "TENANT-A-AUDIT" for item in own_items)
    assert all(item["organization_id"] == h1.id for item in own_items)
    assert all(item.get("resource_id") != "TENANT-B-AUDIT" for item in own_items)

    cross = client.get(
        f"/api/admin/audit?hospital_id={h2.id}&limit=200",
        headers=_headers(admin_a),
    )
    assert cross.status_code == 403


def test_non_admin_doctor_cannot_use_admin_audit_surface(db_session: Session):
    h1, _, _, doctor_a, _, _ = _seed_two_tenants(db_session)

    response = client.get(
        f"/api/admin/audit?hospital_id={h1.id}",
        headers=_headers(doctor_a),
    )
    assert response.status_code == 403


def test_org_admin_must_supply_hospital_context(db_session: Session):
    _, _, admin_a, _, _, _ = _seed_two_tenants(db_session)

    dashboard = client.get("/api/admin/dashboard", headers=_headers(admin_a))
    audit = client.get("/api/admin/audit", headers=_headers(admin_a))

    assert dashboard.status_code == 400
    assert audit.status_code == 400


def test_platform_admin_can_scope_dashboard_and_audit_to_one_hospital(db_session: Session):
    h1, _, _, _, _, _ = _seed_two_tenants(db_session)
    platform_admin = User(
        email="tenant-platform-admin@test.com",
        hashed_password="hashed",
        role="platform_admin",
        full_name="Platform Admin",
        is_active=True,
    )
    db_session.add(platform_admin)
    db_session.commit()

    dashboard = client.get(
        f"/api/admin/dashboard?hospital_id={h1.id}",
        headers=_headers(platform_admin),
    )
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["metrics"]["active_consents"] == 1
    assert dashboard.json()["metrics"]["total_patients"] == 1
    assert all(
        item["organization_id"] == h1.id
        for item in dashboard.json()["recent_activity"]
    )

    audit = client.get(
        f"/api/admin/audit?hospital_id={h1.id}&limit=200",
        headers=_headers(platform_admin),
    )
    assert audit.status_code == 200, audit.text
    assert all(item["organization_id"] == h1.id for item in audit.json()["items"])


def test_inactive_platform_admin_is_rejected(db_session: Session):
    inactive = User(
        email="inactive-platform-admin@test.com",
        hashed_password="hashed",
        role="platform_admin",
        full_name="Inactive Admin",
        is_active=False,
    )
    db_session.add(inactive)
    db_session.commit()

    response = client.get("/api/admin/dashboard", headers=_headers(inactive))
    assert response.status_code == 401


def test_legacy_admin_system_role_has_no_global_admin_authority(db_session: Session):
    hospital = Hospital(name="Legacy Admin Isolation Hospital")
    legacy_admin = User(
        email="legacy-global-admin@test.com",
        hashed_password="hashed",
        role="admin",
        full_name="Legacy Admin",
        is_active=True,
    )
    db_session.add_all([hospital, legacy_admin])
    db_session.commit()

    dashboard = client.get(
        f"/api/admin/dashboard?hospital_id={hospital.id}",
        headers=_headers(legacy_admin),
    )
    audit = client.get(
        f"/api/admin/audit?hospital_id={hospital.id}",
        headers=_headers(legacy_admin),
    )

    assert dashboard.status_code == 403
    assert audit.status_code == 403
