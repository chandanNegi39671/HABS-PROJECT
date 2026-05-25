"""
HABS — Appointments Repository
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Sequence

from sqlalchemy import and_, case, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from habs_db.models import Appointment, AppointmentStatus
from habs_db.repositories.base import BaseRepository


class AppointmentRepository(BaseRepository[Appointment]):
    model = Appointment

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def book(self, appointment: Appointment) -> Appointment:
        try:
            self.session.add(appointment)
            await self.session.flush()
            await self.session.refresh(appointment)
            return appointment
        except IntegrityError as exc:
            await self.session.rollback()
            if "uq_doctor_date_slot" in str(exc.orig):
                raise ValueError(
                    f"Slot already booked: doctor={appointment.doctor_id} "
                    f"date={appointment.appointment_date} slot={appointment.time_slot}"
                ) from exc
            raise

    async def get_doctor_upcoming(
        self,
        doctor_id: uuid.UUID,
        *,
        days_ahead: int = 7,
    ) -> Sequence[Appointment]:
        today    = date.today()
        end_date = today + timedelta(days=days_ahead)

        result = await self.session.execute(
            select(Appointment)
            .where(
                Appointment.doctor_id        == doctor_id,
                Appointment.appointment_date >= today,
                Appointment.appointment_date <= end_date,
                Appointment.status           == AppointmentStatus.BOOKED,
            )
            .order_by(Appointment.appointment_date, Appointment.time_slot)
        )
        return result.scalars().all()

    async def get_patient_ml_history(self, patient_id: uuid.UUID) -> dict:
        terminal_statuses = [
            AppointmentStatus.COMPLETED,
            AppointmentStatus.NO_SHOW,
            AppointmentStatus.CANCELLED,
        ]

        result = await self.session.execute(
            select(
                func.count().label("prior_appointment_count"),
                func.sum(
                    case(
                        (Appointment.status == AppointmentStatus.NO_SHOW, 1),
                        else_=0,
                    )
                ).label("prior_no_show_count"),
            ).where(
                Appointment.patient_id == patient_id,
                Appointment.status.in_(terminal_statuses),
            )
        )
        row = result.one()
        return {
            "prior_appointment_count": int(row.prior_appointment_count or 0),
            "prior_no_show_count":     int(row.prior_no_show_count     or 0),
        }

    async def cancel(self, appointment_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            update(Appointment)
            .where(
                Appointment.id     == appointment_id,
                Appointment.status == AppointmentStatus.BOOKED,
            )
            .values(status=AppointmentStatus.CANCELLED)
            .returning(Appointment.id)
        )
        return result.scalar_one_or_none() is not None

    async def mark_completed(self, appointment_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            update(Appointment)
            .where(
                Appointment.id     == appointment_id,
                Appointment.status == AppointmentStatus.BOOKED,
            )
            .values(status=AppointmentStatus.COMPLETED)
            .returning(Appointment.id)
        )
        return result.scalar_one_or_none() is not None

    async def mark_no_show(self, appointment_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            update(Appointment)
            .where(
                Appointment.id     == appointment_id,
                Appointment.status == AppointmentStatus.BOOKED,
            )
            .values(status=AppointmentStatus.NO_SHOW)
            .returning(Appointment.id)
        )
        return result.scalar_one_or_none() is not None

    async def update_risk_score(self, appointment_id: uuid.UUID, risk: float) -> bool:
        if not (0.0 <= risk <= 1.0):
            raise ValueError(f"no_show_risk must be in [0,1], got {risk}")
        result = await self.session.execute(
            update(Appointment)
            .where(Appointment.id == appointment_id)
            .values(no_show_risk=risk)
            .returning(Appointment.id)
        )
        return result.scalar_one_or_none() is not None

    async def get_high_risk_upcoming(
        self,
        *,
        risk_threshold: float = 0.4,
        days_ahead: int = 3,
        limit: int = 500,
    ) -> Sequence[Appointment]:
        today    = date.today()
        end_date = today + timedelta(days=days_ahead)

        result = await self.session.execute(
            select(Appointment)
            .where(
                Appointment.status           == AppointmentStatus.BOOKED,
                Appointment.appointment_date >= today,
                Appointment.appointment_date <= end_date,
                Appointment.no_show_risk     >= risk_threshold,
                Appointment.sms_reminder_sent == False,  # noqa: E712
            )
            .order_by(Appointment.no_show_risk.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def soft_delete(self, appointment_id: uuid.UUID) -> bool:
        return await self.cancel(appointment_id)
