from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session as DBSession
from datetime import datetime, timedelta, timezone
import logging
import pyotp
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import (
    verify_password, create_access_token, get_password_hash,
    create_refresh_token, hash_refresh_token,
    encrypt_mfa_secret, decrypt_mfa_secret
)
from app.models.user import User
from app.models.hospital import HospitalStaff, Hospital
from app.models.auth import Session, RefreshTokenHistory, UserMFA
from app.api.dependencies import (
    get_current_active_user,
    get_current_user,
    get_mfa_verification_context,
    MFAVerificationContext,
)
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None

class MFAVerifyRequest(BaseModel):
    code: str

class MFAResponse(BaseModel):
    mfa_required: bool
    access_token: str | None = None
    token_type: str | None = None
    role: str | None = None
    detail: str | None = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def set_refresh_cookie(response: Response, refresh_token: str):
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENV == "production",
        samesite="lax",
        max_age=7 * 24 * 60 * 60, # 7 days
        path="/api/auth"
    )

def clear_refresh_cookie(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/api/auth",
        secure=settings.ENV == "production",
        httponly=True,
        samesite="lax"
    )


def _revoke_token_family(db: DBSession, user_id: int, token_family: str) -> None:
    """Revoke every active session belonging to one refresh-token family."""
    revoked_at = datetime.now(timezone.utc)
    sessions = db.query(Session).filter(
        Session.user_id == user_id,
        Session.token_family == token_family,
        Session.revoked_at == None,
    ).all()
    for session_record in sessions:
        session_record.revoked_at = revoked_at


def _issue_tokens(db: DBSession, response: Response, user: User) -> MFAResponse:
    """Issue an access token bound to a rotating server-side session."""
    raw_refresh_token = create_refresh_token()
    token_family = str(uuid.uuid4())

    session_record = Session(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(raw_refresh_token),
        token_family=token_family,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(session_record)
    # The session primary key is required before the access JWT is minted so
    # logout/password/session revocation can invalidate that JWT immediately.
    db.flush()

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.email,
        expires_delta=access_token_expires,
        session_id=session_record.id,
    )
    db.commit()

    set_refresh_cookie(response, raw_refresh_token)

    return MFAResponse(
        mfa_required=False,
        access_token=access_token,
        token_type="bearer",
        role=user.role
    )

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=MFAResponse)
@limiter.limit("5/minute")
def login(request: Request, response: Response, db: DBSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user account")

    mfa_record = db.query(UserMFA).filter(UserMFA.user_id == user.id, UserMFA.is_enabled == True).first()
    if mfa_record:
        # A pre-auth token proves only the password stage. It is intentionally
        # unusable on normal HTTP endpoints and WebSockets until MFA succeeds.
        pre_auth_token = create_access_token(
            subject=user.email,
            expires_delta=timedelta(minutes=2),
            token_type="preauth",
            mfa_verified=False,
        )
        return MFAResponse(
            mfa_required=True,
            access_token=pre_auth_token,
            token_type="pre-auth",
            role=user.role,
            detail="MFA verification required."
        )

    return _issue_tokens(db, response, user)

@router.post("/mfa/verify", response_model=MFAResponse)
def verify_mfa(
    request: MFAVerifyRequest,
    response: Response,
    verification: MFAVerificationContext = Depends(get_mfa_verification_context),
    db: DBSession = Depends(get_db)
):
    current_user = verification.user
    mfa_record = db.query(UserMFA).filter(UserMFA.user_id == current_user.id).first()
    if not mfa_record or not mfa_record.secret_encrypted:
        raise HTTPException(status_code=400, detail="MFA not configured")

    # Enrollment verification must originate from a fully authenticated access
    # token. Once MFA is enabled, login verification must originate from the
    # short-lived password-stage pre-auth token instead.
    if mfa_record.is_enabled and verification.token_type != "preauth":
        raise HTTPException(status_code=401, detail="MFA challenge token required")
    if not mfa_record.is_enabled and verification.token_type != "access":
        raise HTTPException(status_code=401, detail="Authenticated access token required for MFA enrollment")

    secret = decrypt_mfa_secret(mfa_record.secret_encrypted)
    totp = pyotp.TOTP(secret)

    if not totp.verify(request.code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    if not mfa_record.is_enabled:
        mfa_record.is_enabled = True
        mfa_record.verified_at = datetime.now(timezone.utc)
        db.commit()

    return _issue_tokens(db, response, current_user)

@router.post("/mfa/enroll")
def enroll_mfa(current_user: User = Depends(get_current_active_user), db: DBSession = Depends(get_db)):
    mfa_record = db.query(UserMFA).filter(UserMFA.user_id == current_user.id).first()
    if mfa_record and mfa_record.is_enabled:
        raise HTTPException(status_code=400, detail="MFA is already enabled")

    secret = pyotp.random_base32()
    encrypted_secret = encrypt_mfa_secret(secret)

    if mfa_record:
        mfa_record.secret_encrypted = encrypted_secret
    else:
        mfa_record = UserMFA(user_id=current_user.id, secret_encrypted=encrypted_secret, is_enabled=False)
        db.add(mfa_record)

    db.commit()

    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.email, issuer_name="MedFlow Guardian")

    return {"secret": secret, "uri": uri, "detail": "Scan the URI with your authenticator app and call /mfa/verify to enable."}

@router.post("/refresh")
@limiter.limit("10/minute")
def refresh_token(request: Request, response: Response, db: DBSession = Depends(get_db)):
    raw_refresh_token = request.cookies.get("refresh_token")
    if not raw_refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    hashed_token = hash_refresh_token(raw_refresh_token)

    # Serialize rotation of a current refresh token. A concurrent second use
    # cannot rotate the same token twice; after the first transaction commits it
    # falls through to the spent-token replay check below.
    session_record = (
        db.query(Session)
        .filter(Session.refresh_token_hash == hashed_token)
        .with_for_update()
        .first()
    )

    if not session_record:
        spent_token = db.query(RefreshTokenHistory).filter(
            RefreshTokenHistory.refresh_token_hash == hashed_token
        ).first()
        if spent_token:
            _revoke_token_family(db, spent_token.user_id, spent_token.token_family)
            db.commit()
            logger.warning(
                "Refresh-token replay detected; revoked family=%s user_id=%s",
                spent_token.token_family,
                spent_token.user_id,
            )
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if session_record.revoked_at:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Session revoked")

    if session_record.expires_at < datetime.now(timezone.utc):
        db.delete(session_record)
        db.commit()
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.query(User).filter(User.id == session_record.user_id).first()
    if not user or not user.is_active:
        session_record.revoked_at = datetime.now(timezone.utc)
        db.commit()
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="User is inactive or deleted")

    # Preserve the spent fingerprint before rotating the current token. Only the
    # hash is retained; a database reader cannot recover the raw bearer token.
    db.add(RefreshTokenHistory(
        user_id=session_record.user_id,
        token_family=session_record.token_family,
        refresh_token_hash=session_record.refresh_token_hash,
        used_at=datetime.now(timezone.utc),
    ))

    new_raw_refresh = create_refresh_token()
    session_record.refresh_token_hash = hash_refresh_token(new_raw_refresh)
    session_record.last_used_at = datetime.now(timezone.utc)
    db.commit()

    set_refresh_cookie(response, new_raw_refresh)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.email,
        expires_delta=access_token_expires,
        session_id=session_record.id,
    )

    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@router.post("/logout")
def logout(request: Request, response: Response, db: DBSession = Depends(get_db)):
    raw_refresh_token = request.cookies.get("refresh_token")
    if raw_refresh_token:
        hashed_token = hash_refresh_token(raw_refresh_token)
        session_record = db.query(Session).filter(Session.refresh_token_hash == hashed_token).first()
        if session_record:
            session_record.revoked_at = datetime.now(timezone.utc)
            db.commit()

    clear_refresh_cookie(response)
    return {"detail": "Successfully logged out"}

@router.post("/logout-all")
def logout_all(
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: DBSession = Depends(get_db)
):
    sessions = db.query(Session).filter(Session.user_id == current_user.id, Session.revoked_at == None).all()
    for s in sessions:
        s.revoked_at = datetime.now(timezone.utc)
    db.commit()
    clear_refresh_cookie(response)
    return {"detail": "All sessions revoked successfully"}

@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: DBSession = Depends(get_db)
):
    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    current_user.hashed_password = get_password_hash(request.new_password)

    sessions = db.query(Session).filter(Session.user_id == current_user.id, Session.revoked_at == None).all()
    for s in sessions:
        s.revoked_at = datetime.now(timezone.utc)

    db.commit()
    clear_refresh_cookie(response)
    return {"detail": "Password changed successfully. Please log in again."}

@router.get("/me")
def get_me(current_user: User = Depends(get_current_active_user), db: DBSession = Depends(get_db)):
    memberships = db.query(HospitalStaff).filter(
        HospitalStaff.user_id == current_user.id,
        HospitalStaff.is_active == True
    ).all()

    organizations = []
    for mem in memberships:
        hospital = db.query(Hospital).filter(Hospital.id == mem.hospital_id).first()
        if hospital:
            organizations.append({
                "hospital_id": hospital.id,
                "hospital_name": hospital.name,
                "role": mem.role
            })

    has_patient_profile = current_user.patient_profile is not None
    has_practitioner_profile = current_user.practitioner_profile is not None

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "system_role": current_user.role,
        "profiles": {
            "patient": has_patient_profile,
            "practitioner": has_practitioner_profile
        },
        "memberships": organizations
    }

@router.patch("/me")
def update_me(request: UpdateProfileRequest, current_user: User = Depends(get_current_active_user), db: DBSession = Depends(get_db)):
    if request.full_name is not None:
        current_user.full_name = request.full_name
    if request.email is not None:
        if request.email != current_user.email:
            existing = db.query(User).filter(User.email == request.email).first()
            if existing:
                raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = request.email

    db.commit()
    return {"detail": "Profile updated successfully"}
