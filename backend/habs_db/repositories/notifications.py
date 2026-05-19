"""
HABS — Notifications Repository
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from habs_db.models import Notification, NotificationStatus, NotificationType
from habs_db.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_pending(self, *, limit: int = 200) -> Sequence[Notification]:
        """Fetch pending notifications for the dispatch worker."""
        result = await self.session.execute(
            select(Notification)
            .where(Notification.status == NotificationStatus.PENDING)
            .order_by(Notification.created_at)
            .limit(limit)
        )
        return result.scalars().all()

    async def mark_sent(self, notification_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(
                status=NotificationStatus.SENT,
                sent_at=datetime.now(timezone.utc),
            )
            .returning(Notification.id)
        )
        return result.rowcount > 0

    async def mark_failed(self, notification_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(status=NotificationStatus.FAILED)
            .returning(Notification.id)
        )
        return result.rowcount > 0

    async def create_sms_reminder(
        self,
        user_id: uuid.UUID,
        appointment_id: uuid.UUID,
        message: str,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            appointment_id=appointment_id,
            type=NotificationType.SMS,
            message=message,
        )
        return await self.create(notif)
