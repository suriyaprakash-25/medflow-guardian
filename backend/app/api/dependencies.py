from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import ACCESS_TOKEN_TYPE, PRE_AUTH_TOKEN_TYPE
from app.models.user import User, PractitionerProfile
from app.models.hospital import HospitalStaff

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _load_user_for_token(
    token: str,
    db: Session,
    *,
    allowed_token_types: set[str],
) -> User:
    credentials_exception = _credentials_exception()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        token_type = payload.get("token_type")
        mfa_verified = payload.get("mfa_verified")
        if email is None or token_type not in allowed_token_types:
            raise credentials_exception
        if token_type == ACCESS_TOKEN_TYPE and mfa_verified is not True:
            raise credentials_exception
        if token_type == PRE_AUTH_TOKEN_TYPE and mfa_verified is not False:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Return a user only for a fully authenticated access token."""
    return _load_user_for_token(
        token,
        db,
        allowed_token_types={ACCESS_TOKEN_TYPE},
    )


def get_mfa_verification_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Allow either an enrolled-session access token or an MFA pre-auth token.

    This dependency exists only for `/mfa/verify`. Ordinary protected endpoints
    must use `get_current_user`/`get_current_active_user`, which reject pre-auth
    tokens.
    """
    return _load_user_for_token(
        token,
        db,
        allowed_token_types={ACCESS_TOKEN_TYPE, PRE_AUTH_TOKEN_TYPE},
    )


def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user account")
    return current_user


def get_practitioner_identity(current_user: User = Depends(get_current_active_user)):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Not a practitioner identity")
    return current_user


def get_patient_identity(current_user: User = Depends(get_current_active_user)):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Not a patient identity")
    return current_user


def get_current_organization_context(hospital_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    membership = db.query(HospitalStaff).filter(
        HospitalStaff.user_id == current_user.id,
        HospitalStaff.hospital_id == hospital_id,
        HospitalStaff.is_active == True
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a valid active member of this organization context")
    return membership


def get_authorization_service(db: Session = Depends(get_db)):
    """FastAPI dependency that provides the Central Authorization Service."""
    from app.services.authorization import AuthorizationService
    return AuthorizationService(db)


def require_authorization(decision_factory):
    """Enforce an AuthorizationDecision by raising HTTP 403 when denied."""
    from app.services.authorization import AuthorizationDecision
    from fastapi import HTTPException
    decision: AuthorizationDecision = decision_factory
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail or str(decision.reason))
    return decision
