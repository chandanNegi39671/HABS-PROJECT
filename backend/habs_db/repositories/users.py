"""
HABS — Users Repository
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from habs_db.models import User
from habs_db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ─────────────────────────── Lookups ─────────────────────────────────────

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def list_active(
        self, *, limit: int = 100, offset: int = 0
    ) -> Sequence[User]:
        result = await self.session.execute(
            select(User)
            .where(User.is_active == True)          # noqa: E712
            .order_by(User.full_name)
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    # ─────────────────────────── Soft-delete ─────────────────────────────────

    async def deactivate(self, user_id: uuid.UUID) -> bool:
        """Soft-delete: sets is_active=False. Never hard-deletes."""
        return await self.soft_delete(user_id)

    # ─────────────────────────── ML feature snapshot ─────────────────────────

    async def get_ml_flags(self, user_id: uuid.UUID) -> dict | None:
        """
        Returns the ML-relevant boolean flags for a patient.
        Used when building the input_features JSONB payload.
        Single query, no N+1.

        Raw SQL equivalent:
            SELECT gender, scholarship, hypertension, diabetes,
                   alcoholism, has_chronic_condition,
                   EXTRACT(YEAR FROM AGE(date_of_birth)) AS age
            FROM users
            WHERE id = :user_id AND is_active = TRUE;
        """
        result = await self.session.execute(
            select(
                User.gender,
                User.scholarship,
                User.hypertension,
                User.diabetes,
                User.alcoholism,
                User.has_chronic_condition,
                User.date_of_birth,
            ).where(User.id == user_id, User.is_active == True)  # noqa: E712
        )
        row = result.one_or_none()
        if row is None:
            return None

        from datetime import date
        today = date.today()
        age = (
            today.year - row.date_of_birth.year
            - ((today.month, today.day) < (row.date_of_birth.month, row.date_of_birth.day))
            if row.date_of_birth else 0
        )
        return {
            "Age":                  age,
            "Gender_M":             1 if row.gender == "M" else 0,
            "Scholarship":          int(row.scholarship),
            "Hipertension":         int(row.hypertension),
            "Diabetes":             int(row.diabetes),
            "Alcoholism":           int(row.alcoholism),
            "has_chronic_condition": int(row.has_chronic_condition),
            "Handcap":              0,
        }
