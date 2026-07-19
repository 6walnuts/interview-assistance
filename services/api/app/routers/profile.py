from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, UserProfile
from ..schemas import ProfileOut, ProfileResponse, ProfileUpdate, UserOut
from ..security import get_current_user

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _get_or_create_profile(db: Session, user: User) -> UserProfile:
    profile = db.scalars(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        db.commit()
    return profile


def _to_response(user: User, profile: UserProfile) -> ProfileResponse:
    return ProfileResponse(
        user=UserOut(id=user.id, email=user.email, name=user.name),
        profile=ProfileOut(
            target_role=profile.target_role, current_level=profile.current_level,
            target_level=profile.target_level, target_companies=profile.target_companies,
            interview_date=profile.interview_date, weekly_hours=profile.weekly_hours,
            preferred_language=profile.preferred_language, locale=profile.locale,
            strengths=profile.strengths,
            weaknesses=profile.weaknesses, onboarding_completed=profile.onboarding_completed,
        ),
    )


@router.get("", response_model=ProfileResponse)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProfileResponse:
    return _to_response(user, _get_or_create_profile(db, user))


@router.put("", response_model=ProfileResponse)
def update_profile(
    body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProfileResponse:
    profile = _get_or_create_profile(db, user)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    return _to_response(user, profile)
