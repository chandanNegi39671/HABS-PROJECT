"""
HABS — Doctors Repository
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from habs_db.models import Doctor
from habs_db.repositories.base import BaseRepository


class DoctorRepository(BaseRepository[Doctor]):
    model = Doctor

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_active(
        self,
        specialization: str | None = None,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Doctor]:
        stmt = select(Doctor).where(Doctor.is_active == True)   # noqa: E712
        if specialization:
            stmt = stmt.where(Doctor.specialization == specialization)
        stmt = stmt.order_by(Doctor.full_name).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_email(self, email: str) -> Doctor | None:
        result = await self.session.execute(
            select(Doctor).where(Doctor.email == email)
        )
        return result.scalar_one_or_none()

    async def deactivate(self, doctor_id: uuid.UUID) -> bool:
        return await self.soft_delete(doctor_id)
