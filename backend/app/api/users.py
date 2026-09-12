from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_authorization_service, get_practitioner_identity, get_patient_identity
from app.models.user import User, PractitionerProfile, PatientProfile
from app.schemas.user import PractitionerProfile as PractitionerProfileSchema, PractitionerProfileCreate, PatientProfileUpdate
from app.schemas.user import User as UserSchema
from app.services.authorization import AuthorizationContext, AuthorizationService, Operation, ResourceType

router = APIRouter()

@router.get("/practitioner-profile", response_model=PractitionerProfileSchema)
def get_practitioner_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_practitioner_identity),
    auth_svc: AuthorizationService = Depends(get_authorization_service),
):
    decision = auth_svc.authorize(AuthorizationContext(
        actor=current_user, operation=Operation.READ,
        resource_type=ResourceType.PRACTITIONER_PROFILE, db=db,
    ))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)
    profile = db.query(PractitionerProfile).filter(PractitionerProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Practitioner profile not found")
    return profile

@router.post("/practitioner-profile", response_model=PractitionerProfileSchema)
def update_practitioner_profile(
    profile_in: PractitionerProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_practitioner_identity),
    auth_svc: AuthorizationService = Depends(get_authorization_service),
):
    decision = auth_svc.authorize(AuthorizationContext(
        actor=current_user, operation=Operation.UPDATE,
        resource_type=ResourceType.PRACTITIONER_PROFILE, db=db,
    ))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)
    profile = db.query(PractitionerProfile).filter(PractitionerProfile.user_id == current_user.id).first()
    if profile:
        profile.specialty = profile_in.specialty
        profile.license_number = profile_in.license_number
        profile.bio = profile_in.bio
    else:
        profile = PractitionerProfile(
            user_id=current_user.id,
            specialty=profile_in.specialty,
            license_number=profile_in.license_number,
            bio=profile_in.bio,
            is_verified=False
        )
        db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

@router.get("/patient-profile", response_model=UserSchema)
def get_patient_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_patient_identity),
    auth_svc: AuthorizationService = Depends(get_authorization_service),
):
    decision = auth_svc.authorize(AuthorizationContext(
        actor=current_user, operation=Operation.READ,
        resource_type=ResourceType.PATIENT_PROFILE, db=db, patient_id=current_user.id,
    ))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user.patient_profile:
        # Create an empty profile if none exists
        profile = PatientProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(user)
    return user

@router.post("/patient-profile", response_model=UserSchema)
def update_patient_profile(
    profile_in: PatientProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_patient_identity),
    auth_svc: AuthorizationService = Depends(get_authorization_service),
):
    decision = auth_svc.authorize(AuthorizationContext(
        actor=current_user, operation=Operation.UPDATE,
        resource_type=ResourceType.PATIENT_PROFILE, db=db, patient_id=current_user.id,
    ))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)
    user = db.query(User).filter(User.id == current_user.id).first()
    
    # Update User fields
    if profile_in.full_name is not None:
        user.full_name = profile_in.full_name
    if profile_in.phone_number is not None:
        user.phone_number = profile_in.phone_number
        
    # Update PatientProfile fields
    profile = user.patient_profile
    if not profile:
        profile = PatientProfile(user_id=user.id)
        db.add(profile)
        
    if profile_in.medical_history is not None:
        profile.medical_history = profile_in.medical_history
    if profile_in.date_of_birth is not None:
        profile.date_of_birth = profile_in.date_of_birth
    if profile_in.address is not None:
        profile.address = profile_in.address
    if profile_in.emergency_contact_name is not None:
        profile.emergency_contact_name = profile_in.emergency_contact_name
    if profile_in.emergency_contact_phone is not None:
        profile.emergency_contact_phone = profile_in.emergency_contact_phone
    if profile_in.blood_type is not None:
        profile.blood_type = profile_in.blood_type
    if profile_in.allergies is not None:
        profile.allergies = profile_in.allergies

    db.commit()
    db.refresh(user)
    return user
