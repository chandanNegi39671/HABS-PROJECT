"""
HABS — Appointments Repository
Most critical repo: double-booking guard, dashboard query,
ML feature aggregation (single subquery), soft-delete via status.
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

    # ─────────────────────────────────────────────────────────────────────────
    # BOOKING — double-booking guard via UNIQUE constraint
    # ─────────────────────────────────────────────────────────────────────────

    async def book(self, appointment: Appointment) -> Appointment:
        """
        Safe INSERT.  The UNIQUE(doctor_id, appointment_date, time_slot) constraint
        is the authoritative guard.  We let PostgreSQL raise the IntegrityError
        rather than doing a SELECT + INSERT (TOCTOU race).

        ORM version:
            session.add(appointment)
            await session.flush()

        Raw SQL equivalent:
            INSERT INTO appointments (id, patient_id, doctor_id, appointment_date,
                time_slot, appointment_hour, lead_time_days, status, ...)
            VALUES (:id, :patient_id, :doctor_id, :appointment_date,
                :time_slot, :appointment_hour, :lead_time_days, 'booked', ...)
            ON CONFLICT (doctor_id, appointment_date, time_slot) DO NOTHING
            RETURNING id;

        EXPLAIN ANALYZE (expected):
            Insert on appointments (cost=0.00..0.01 rows=1 width=...)
              Conflict Resolution: NOTHING
              Conflict Arbiter Indexes: uq_doctor_date_slot
              -> Result (cost=0.00..0.01 rows=1)

        Index used: uq_doctor_date_slot (UNIQUE)
        """
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

    # ─────────────────────────────────────────────────────────────────────────
    # DOCTOR DASHBOARD — today + 7 days, uses composite index
    # ─────────────────────────────────────────────────────────────────────────

    async def get_doctor_upcoming(
        self,
        doctor_id: uuid.UUID,
        *,
        days_ahead: int = 7,
    ) -> Sequence[Appointment]:
        """
        Appointments for a doctor from today through the next `days_ahead` days.
        Orders by date + time_slot for the scheduling view.

        ORM version: (below)

        Raw SQL equivalent:
            SELECT a.*
            FROM appointments a
            WHERE a.doctor_id = :doctor_id
              AND a.appointment_date BETWEEN CURRENT_DATE
                                         AND CURRENT_DATE + INTERVAL ':days days'
              AND a.status = 'booked'
            ORDER BY a.appointment_date, a.time_slot;

        EXPLAIN ANALYZE (expected):
            Index Scan using ix_appointments_doctor_date on appointments
              Index Cond: (doctor_id = ? AND appointment_date >= today AND ...)
              Filter: (status = 'booked')

        Optimising index: ix_appointments_doctor_date (doctor_id, appointment_date)
        """
        today    = date.today()
        end_date = today + timedelta(days=days_ahead)

        result = await self.session.execute(
            select(Appointment)
            .where(
                Appointment.doctor_id       == doctor_id,
                Appointment.appointment_date >= today,
                Appointment.appointment_date <= end_date,
                Appointment.status           == AppointmentStatus.BOOKED,
            )
            .order_by(Appointment.appointment_date, Appointment.time_slot)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────────────────────────────────
    # ML FEATURE AGGREGATION — single subquery, no N+1
    # ─────────────────────────────────────────────────────────────────────────

    async def get_patient_ml_history(
        self, patient_id: uuid.UUID
    ) -> dict:
        """
        Aggregates prior_appointment_count and prior_no_show_count for ML
        feature building.  Single query — never call this in a loop.

        ORM version: (below)

        Raw SQL equivalent:
            SELECT
                COUNT(*)                                         AS prior_appointment_count,
                SUM(CASE WHEN status = 'no_show' THEN 1 ELSE 0 END) AS prior_no_show_count
            FROM appointments
            WHERE patient_id = :patient_id
              AND status IN ('completed', 'no_show', 'cancelled');

        EXPLAIN ANALYZE (expected):
            Aggregate (cost=8.50..8.51 rows=1 width=16)
              -> Index Scan using ix_appointments_patient_status on appointments
                   Index Cond: (patient_id = ?)
                   Filter: (status = ANY ('{completed,no_show,cancelled}'))

        Optimising index: ix_appointments_patient_status (patient_id, status)
        """
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

    # ─────────────────────────────────────────────────────────────────────────
    # STATUS TRANSITIONS — soft-delete pattern via status field
    # ─────────────────────────────────────────────────────────────────────────

    async def cancel(self, appointment_id: uuid.UUID) -> bool:
        """
        Soft-delete: transitions booked → cancelled.
        Returns True if affected, False if not found or not in booked state.
        """
        result = await self.session.execute(
            update(Appointment)
            .where(
                Appointment.id     == appointment_id,
                Appointment.status == AppointmentStatus.BOOKED,
            )
            .values(status=AppointmentStatus.CANCELLED)
            .returning(Appointment.id)
        )
        return result.scalar() is not None

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
        return result.scalar() is not None

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
        return result.scalar() is not None

    async def update_risk_score(
        self, appointment_id: uuid.UUID, risk: float
    ) -> bool:
        """
        Stores the ML no-show probability on the appointment row.
        CHECK(0 <= no_show_risk <= 1) enforced at DB level.
        """
        if not (0.0 <= risk <= 1.0):
            raise ValueError(f"no_show_risk must be in [0,1], got {risk}")
        result = await self.session.execute(
            update(Appointment)
            .where(Appointment.id == appointment_id)
            .values(no_show_risk=risk)
            .returning(Appointment.id)
        )
        return result.scalar() is not None

    # ─────────────────────────────────────────────────────────────────────────
    # HIGH-RISK PATIENTS — for proactive outreach batch
    # ─────────────────────────────────────────────────────────────────────────

    async def get_high_risk_upcoming(
        self,
        *,
        risk_threshold: float = 0.4,
        days_ahead: int = 3,
        limit: int = 500,
    ) -> Sequence[Appointment]:
        """
        Fetches booked appointments within `days_ahead` days where
        no_show_risk >= threshold. Used by the reminder/outreach batch job.

        Raw SQL equivalent:
            SELECT a.*
            FROM appointments a
            WHERE a.status = 'booked'
              AND a.appointment_date BETWEEN CURRENT_DATE
                                         AND CURRENT_DATE + :days
              AND a.no_show_risk >= :threshold
              AND a.sms_reminder_sent = FALSE
            ORDER BY a.no_show_risk DESC
            LIMIT :limit;

        Index used: ix_appointments_doctor_date (partial scan) + filter on risk
        """
        today    = date.today()
        end_date = today + timedelta(days=days_ahead)

        result = await self.session.execute(
            select(Appointment)
            .where(
                Appointment.status           == AppointmentStatus.BOOKED,
                Appointment.appointment_date >= today,
                Appointment.appointment_date <= end_date,
                Appointment.no_show_risk     >= risk_threshold,
                Appointment.sms_reminder_sent == False,   # noqa: E712
            )
            .order_by(Appointment.no_show_risk.desc())
            .limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────────────────────────────────
    # Soft-delete override (status-based, not is_active)
    # ─────────────────────────────────────────────────────────────────────────

    async def soft_delete(self, appointment_id: uuid.UUID) -> bool:
        """Overrides BaseRepository — appointments use status, not is_active."""
        return await self.cancel(appointment_id)
