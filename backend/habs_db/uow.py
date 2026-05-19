"""
HABS — Unit of Work
Ties all repositories to a single AsyncSession.
Guarantees atomic multi-repository operations (e.g. book appointment +
mark slot unavailable + create notification in one transaction).

Usage with FastAPI:
    async def book_appointment(
        data: BookingRequest,
        uow: UnitOfWork = Depends(get_uow),
    ):
        async with uow:
            appt = await uow.appointments.book(...)
            await uow.time_slots.mark_unavailable(...)
            await uow.notifications.create_sms_reminder(...)
            # auto-committed on __aexit__ if no exception
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from habs_db.repositories.appointments  import AppointmentRepository
from habs_db.repositories.doctors       import DoctorRepository
from habs_db.repositories.notifications  import NotificationRepository
from habs_db.repositories.time_slots    import TimeSlotRepository
from habs_db.repositories.users         import UserRepository
from habs_db.ml_predictions             import MLPredictionRepository


class UnitOfWork:
    """
    Context manager that owns one AsyncSession and exposes all repositories.
    Commits on clean exit, rolls back on exception.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

        self.users          = UserRepository(session)
        self.doctors        = DoctorRepository(session)
        self.appointments   = AppointmentRepository(session)
        self.time_slots     = TimeSlotRepository(session)
        self.notifications  = NotificationRepository(session)
        self.ml_predictions = MLPredictionRepository(session)

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            await self._session.commit()
        else:
            await self._session.rollback()

    async def flush(self) -> None:
        """Flush without committing — useful to get server-generated IDs mid-transaction."""
        await self._session.flush()

    async def rollback(self) -> None:
        await self._session.rollback()


# ─────────────────────────────── FastAPI dependency ──────────────────────────

async def get_uow() -> UnitOfWork:   # type: ignore[return]
    """
    FastAPI dependency — yields a UoW per request.

    Inject with:
        uow: UnitOfWork = Depends(get_uow)
    """
    from habs_db.repositories.database import get_db
    async for session in get_db():
        yield UnitOfWork(session)
