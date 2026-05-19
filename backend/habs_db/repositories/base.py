"""
HABS — Base Repository
Generic async CRUD + soft-delete pattern.
All domain repositories inherit from this.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, Sequence, Type, TypeVar

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from habs_db.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic async repository.
    Subclasses set `model` class variable.

    Soft-delete:
        - Tables with `is_active`  → soft_delete() sets is_active=False
        - Tables with `status`     → domain repo overrides to set status=cancelled/etc.
        - Hard deletes are NEVER exposed at this layer.
    """

    model: Type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ─────────────────────────── Read ────────────────────────────────────────

    async def get_by_id(self, record_id: uuid.UUID) -> ModelT | None:
        result = await self.session.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, record_id: uuid.UUID) -> ModelT:
        obj = await self.get_by_id(record_id)
        if obj is None:
            raise ValueError(
                f"{self.model.__name__} with id={record_id} not found."
            )
        return obj

    async def list_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        order_by: Any = None,
    ) -> Sequence[ModelT]:
        stmt = select(self.model)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ─────────────────────────── Write ───────────────────────────────────────

    async def create(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()   # get server-generated defaults without committing
        await self.session.refresh(obj)
        return obj

    async def update_fields(
        self, record_id: uuid.UUID, **kwargs: Any
    ) -> int:
        """
        Partial update by primary key.
        Returns number of rows affected (0 or 1).
        """
        result = await self.session.execute(
            update(self.model)
            .where(self.model.id == record_id)
            .values(**kwargs)
            .returning(self.model.id)
        )
        return result.rowcount

    # ─────────────────────────── Soft delete ─────────────────────────────────

    async def soft_delete(self, record_id: uuid.UUID) -> bool:
        """
        Sets is_active=False for tables that support it.
        Override for tables using a status field instead.
        Returns True if a row was affected.
        """
        rows = await self.update_fields(record_id, is_active=False)
        return rows > 0

    # ─────────────────────────── Existence check ─────────────────────────────

    async def exists(self, record_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(self.model.id).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none() is not None
