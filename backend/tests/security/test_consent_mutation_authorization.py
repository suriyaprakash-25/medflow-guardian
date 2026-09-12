from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.main import app
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState, ConsentStatus
from app.models.user import User


client = TestClient(app)


def _user(db: Session, email: str, role: str) -> User:
    user = User(
        email=email,
        hashed_password="not-used-by-bearer-token-tests",
        role=role,
        full_name=email.split("@")[0],
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.email)}"}


def _consent_chain(db: Session, patient: User) -> Consent:
    consent = Consent(
        patient_id=patient.id,
        status=ConsentStatus.ACTIVE.value,
    )
    db.add(consent)
    db.flush()

    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": ["read", "download"],
        },
        status="active",
    )
    db.add(policy)
    db.flush()

    db.add(
        ConsentState(
            consent_id=consent.id,
            policy_version_id=policy.id,
            status=ConsentStatus.ACTIVE.value,
            reason="test fixture",
        )
    )
    db.commit()
    db.refresh(consent)
    return consent


def test_patient_can_create_own_consent_through_cae(db_session: Session):
    patient = _user(db_session, "consent-owner-create@example.com", "patient")

    response = client.post(
        "/api/consents",
        headers=_headers(patient),
        json={
            "hospital_id": None,
            "doctor_id": None,
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": ["read"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["patient_id"] == patient.id


def test_non_patient_cannot_create_consent(db_session: Session):
    legacy_admin = _user(db_session, "legacy-admin-create@example.com", "admin")

    response = client.post(
        "/api/consents",
        headers=_headers(legacy_admin),
        json={
            "hospital_id": None,
            "doctor_id": None,
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": ["read"],
        },
    )

    assert response.status_code == 403
    assert db_session.query(Consent).filter(Consent.patient_id == legacy_admin.id).count() == 0


def test_owner_can_create_new_policy_version(db_session: Session):
    patient = _user(db_session, "consent-owner-policy@example.com", "patient")
    consent = _consent_chain(db_session, patient)

    response = client.post(
        f"/api/consents/{consent.id}/policy-versions",
        headers=_headers(patient),
        json={
            "allowed_purposes": ["TREATMENT", "RESEARCH"],
            "allowed_operations": ["read"],
            "reason": "patient changed sharing policy",
        },
    )

    assert response.status_code == 200
    assert response.json()["version_number"] == 2
    assert db_session.query(ConsentPolicyVersion).filter(
        ConsentPolicyVersion.consent_id == consent.id
    ).count() == 2
    assert db_session.query(ConsentState).filter(ConsentState.consent_id == consent.id).count() == 2


def test_other_patient_cannot_modify_policy(db_session: Session):
    owner = _user(db_session, "consent-owner-cross-patient@example.com", "patient")
    other_patient = _user(db_session, "other-patient-cross-patient@example.com", "patient")
    consent = _consent_chain(db_session, owner)
    before_versions = db_session.query(ConsentPolicyVersion).filter(
        ConsentPolicyVersion.consent_id == consent.id
    ).count()
    before_states = db_session.query(ConsentState).filter(ConsentState.consent_id == consent.id).count()

    response = client.post(
        f"/api/consents/{consent.id}/policy-versions",
        headers=_headers(other_patient),
        json={
            "allowed_purposes": ["RESEARCH"],
            "allowed_operations": ["read"],
            "reason": "unauthorized",
        },
    )

    assert response.status_code == 403
    assert db_session.query(ConsentPolicyVersion).filter(
        ConsentPolicyVersion.consent_id == consent.id
    ).count() == before_versions
    assert db_session.query(ConsentState).filter(ConsentState.consent_id == consent.id).count() == before_states


def test_legacy_system_admin_cannot_modify_patient_policy(db_session: Session):
    owner = _user(db_session, "consent-owner-admin-policy@example.com", "patient")
    legacy_admin = _user(db_session, "legacy-admin-policy@example.com", "admin")
    consent = _consent_chain(db_session, owner)
    before_versions = db_session.query(ConsentPolicyVersion).filter(
        ConsentPolicyVersion.consent_id == consent.id
    ).count()

    response = client.post(
        f"/api/consents/{consent.id}/policy-versions",
        headers=_headers(legacy_admin),
        json={
            "allowed_purposes": ["RESEARCH"],
            "allowed_operations": ["read"],
            "reason": "admin must not override patient consent",
        },
    )

    assert response.status_code == 403
    assert db_session.query(ConsentPolicyVersion).filter(
        ConsentPolicyVersion.consent_id == consent.id
    ).count() == before_versions


def test_platform_admin_cannot_modify_patient_policy(db_session: Session):
    owner = _user(db_session, "consent-owner-platform-policy@example.com", "patient")
    platform_admin = _user(db_session, "platform-admin-policy@example.com", "platform_admin")
    consent = _consent_chain(db_session, owner)
    before_versions = db_session.query(ConsentPolicyVersion).filter(
        ConsentPolicyVersion.consent_id == consent.id
    ).count()

    response = client.post(
        f"/api/consents/{consent.id}/policy-versions",
        headers=_headers(platform_admin),
        json={
            "allowed_purposes": ["RESEARCH"],
            "allowed_operations": ["read"],
            "reason": "platform admin must not override patient consent",
        },
    )

    assert response.status_code == 403
    assert db_session.query(ConsentPolicyVersion).filter(
        ConsentPolicyVersion.consent_id == consent.id
    ).count() == before_versions


def test_owner_can_revoke_own_consent(db_session: Session):
    owner = _user(db_session, "consent-owner-revoke@example.com", "patient")
    consent = _consent_chain(db_session, owner)

    response = client.post(
        f"/api/consents/{consent.id}/transition",
        headers=_headers(owner),
        json={"target_status": "revoked", "reason": "patient revoked access"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "revoked"
    db_session.refresh(consent)
    assert consent.status == ConsentStatus.REVOKED.value


def test_legacy_admin_cannot_transition_patient_consent(db_session: Session):
    owner = _user(db_session, "consent-owner-admin-transition@example.com", "patient")
    legacy_admin = _user(db_session, "legacy-admin-transition@example.com", "admin")
    consent = _consent_chain(db_session, owner)
    before_states = db_session.query(ConsentState).filter(ConsentState.consent_id == consent.id).count()

    response = client.post(
        f"/api/consents/{consent.id}/transition",
        headers=_headers(legacy_admin),
        json={"target_status": "revoked", "reason": "unauthorized admin transition"},
    )

    assert response.status_code == 403
    db_session.refresh(consent)
    assert consent.status == ConsentStatus.ACTIVE.value
    assert db_session.query(ConsentState).filter(ConsentState.consent_id == consent.id).count() == before_states


def test_other_patient_cannot_transition_consent(db_session: Session):
    owner = _user(db_session, "consent-owner-cross-transition@example.com", "patient")
    other_patient = _user(db_session, "other-patient-cross-transition@example.com", "patient")
    consent = _consent_chain(db_session, owner)
    before_states = db_session.query(ConsentState).filter(ConsentState.consent_id == consent.id).count()

    response = client.post(
        f"/api/consents/{consent.id}/transition",
        headers=_headers(other_patient),
        json={"target_status": "revoked", "reason": "unauthorized cross-patient transition"},
    )

    assert response.status_code == 403
    db_session.refresh(consent)
    assert consent.status == ConsentStatus.ACTIVE.value
    assert db_session.query(ConsentState).filter(ConsentState.consent_id == consent.id).count() == before_states
