import json

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationDecision,
    AuthorizationService,
    DenialReason,
    Operation,
    ResourceType,
)


def _actor(db: Session, email: str = "audit-fail-closed@test.com") -> User:
    actor = User(
        email=email,
        hashed_password="hash",
        role="patient",
        is_active=True,
        full_name="Audit Test Patient",
    )
    db.add(actor)
    db.commit()
    db.refresh(actor)
    return actor


def _fail_next_flush(monkeypatch, db: Session):
    """Fail exactly one audit flush, then restore normal Session behavior."""
    original_flush = db.flush
    failed = {"done": False}

    def fail_audit_flush(*args, **kwargs):
        if not failed["done"]:
            failed["done"] = True
            raise RuntimeError("simulated audit persistence outage")
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(db, "flush", fail_audit_flush)
    return original_flush


def test_allowed_operation_fails_closed_when_authorization_audit_cannot_flush(
    db_session: Session,
    monkeypatch,
):
    actor = _actor(db_session)
    original_flush = _fail_next_flush(monkeypatch, db_session)

    decision = AuthorizationService(db_session).authorize(
        AuthorizationContext(
            actor=actor,
            operation=Operation.READ,
            resource_type=ResourceType.HOSPITAL,
            db=db_session,
        )
    )

    assert decision.allowed is False
    assert decision.reason == DenialReason.AUDIT_PERSISTENCE_FAILED
    assert decision.detail == "Authorization audit unavailable; operation denied"

    # An injected audit failure must not leave the request Session unusable.
    assert db_session.is_active is True
    original_flush()


def test_existing_denial_remains_denied_when_its_audit_write_fails(
    db_session: Session,
    monkeypatch,
):
    actor = _actor(db_session, "audit-deny@test.com")
    _fail_next_flush(monkeypatch, db_session)

    decision = AuthorizationService(db_session).authorize(
        AuthorizationContext(
            actor=actor,
            operation=Operation.CREATE,
            resource_type=ResourceType.DOCUMENT,
            db=db_session,
        )
    )

    assert decision.allowed is False
    assert decision.reason == DenialReason.ROLE_NOT_PERMITTED
    assert "practitioners" in decision.detail
    assert db_session.is_active is True


def test_authorization_audit_metadata_is_valid_json(db_session: Session):
    actor = _actor(db_session, "audit-json@test.com")
    detail = 'quoted "detail" with a newline\nand unicode ✓'
    ctx = AuthorizationContext(
        actor=actor,
        operation=Operation.READ,
        resource_type=ResourceType.HOSPITAL,
        db=db_session,
    )

    AuthorizationService(db_session)._audit_decision(
        ctx,
        AuthorizationDecision.deny(DenialReason.INVALID_CONTEXT, detail),
    )

    row = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.actor_id == actor.id,
            AuditLog.operation == Operation.READ.value,
            AuditLog.resource_type == ResourceType.HOSPITAL.value,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )

    assert row is not None
    assert json.loads(row.metadata_json) == {"detail": detail}
