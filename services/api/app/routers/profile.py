import io
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, UserProfile
from ..schemas import ProfileOut, ProfileResponse, ProfileUpdate, UserOut
from ..security import get_current_user

router = APIRouter(prefix="/api/profile", tags=["profile"])

MAX_RESUME_PDF_BYTES = 10 * 1024 * 1024
MAX_RESUME_CHARS = 20_000


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
            resume_text=profile.resume_text or "",
        ),
    )


@router.get("", response_model=ProfileResponse)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProfileResponse:
    return _to_response(user, _get_or_create_profile(db, user))


@router.post("/resume-upload", response_model=ProfileResponse)
async def upload_resume_pdf(
    request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProfileResponse:
    """Raw PDF body -> extracted text stored as resume_text (shown back for review)."""
    data = await request.body()
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件（未检测到 PDF 文件头）")
    if len(data) > MAX_RESUME_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF 太大（上限 10 MB）")
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception as exc:  # noqa: BLE001 — surface a readable parse error
        raise HTTPException(status_code=400, detail=f"PDF 解析失败：{exc}") from exc
    if not text:
        raise HTTPException(
            status_code=422,
            detail="这个 PDF 提取不到文字（可能是扫描件/图片型 PDF）。请改为粘贴纯文本简历。")
    text = re.sub(r"\n{3,}", "\n\n", text)[:MAX_RESUME_CHARS]
    profile = _get_or_create_profile(db, user)
    profile.resume_text = text
    db.commit()
    return _to_response(user, profile)


@router.put("", response_model=ProfileResponse)
def update_profile(
    body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProfileResponse:
    profile = _get_or_create_profile(db, user)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    return _to_response(user, profile)
