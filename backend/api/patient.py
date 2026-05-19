from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel

from habs_db.repositories.database import get_db
from habs_db.models import User
from security import get_current_user
from datetime import date

router = APIRouter()


class OnboardingUpdate(BaseModel):
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    diabetes: bool = False
    hypertension: bool = False
    alcoholism: bool = False
    has_chronic_condition: bool = False


@router.post("/onboarding")
async def patient_onboarding(
    data: OnboardingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if data.date_of_birth is not None:
        user.date_of_birth = date.fromisoformat(str(data.date_of_birth))
    if data.gender is not None:
        user.gender = data.gender

    user.diabetes = data.diabetes
    user.hypertension = data.hypertension
    user.alcoholism = data.alcoholism
    user.has_chronic_condition = data.has_chronic_condition

    if hasattr(user, "blood_group"):
        user.blood_group = data.blood_group

    db.add(user)
    await db.commit()

    return {"message": "Profile updated"}
