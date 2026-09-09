from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_user, get_current_doctor
from app.models.user import User, PractitionerProfile
from app.schemas.user import PractitionerProfile as PractitionerProfileSchema, PractitionerProfileCreate

router = APIRouter()

@router.get("/practitioner-profile", response_model=PractitionerProfileSchema)
def get_practitioner_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_doctor)
):
    profile = db.query(PractitionerProfile).filter(PractitionerProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Practitioner profile not found")
    return profile

@router.post("/practitioner-profile", response_model=PractitionerProfileSchema)
def update_practitioner_profile(
    profile_in: PractitionerProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_doctor)
):
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
