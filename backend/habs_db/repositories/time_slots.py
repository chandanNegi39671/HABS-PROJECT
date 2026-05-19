"""
HABS — TimeSlots Repository
Availability check uses UNIQUE constraint as conflict guard.
Bulk slot generation for seed / scheduling.
"""

from __future__ import annotations

import uuid
from datetime import date, time, timedelta
from typing import Sequence

from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from habs_db.models import TimeSlot
from habs_db.repositories.base import BaseRepository

# Default clinic hours: 08:00–17:00, 30-min slots
DEFAULT_SLOT_TIMES: list[str] = [
    f"{h:02d}:{m:02d}"
    for h in range(8, 18)
    for m in (0, 30)
]


class TimeSlotRepository(BaseRepository[TimeSlot]):
    model = TimeSlot

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ─────────────────────────────────────────────────────────────────────────
    # AVAILABILITY CHECK
    # ─────────────────────────────────────────────────────────────────────────

    async def get_available_slots(
        self,
        doctor_id: uuid.UUID,
        slot_date: date,
    ) -> Sequence[TimeSlot]:
        """
        Returns available slots for a doctor on a given date.
        Uses ix_time_slots_doctor_date composite index.

        Raw SQL equivalent:
            SELECT *
            FROM time_slots
            WHERE doctor_id   = :doctor_id
              AND slot_date   = :slot_date
              AND is_available = TRUE
            ORDER BY slot_time;

        EXPLAIN ANALYZE (expected):
            Index Scan using ix_time_slots_doctor_date on time_slots
              Index Cond: (doctor_id = ? AND slot_date = ?)
              Filter: (is_available = true)

        Index used: ix_time_slots_doctor_date (doctor_id, slot_date)
        """
        result = await self.session.execute(
            select(TimeSlot)
            .where(
                TimeSlot.doctor_id    == doctor_id,
                TimeSlot.slot_date    == slot_date,
                TimeSlot.is_available == True,      # noqa: E712
            )
            .order_by(TimeSlot.slot_time)
        )
        return result.scalars().all()

    async def mark_unavailable(
        self,
        doctor_id: uuid.UUID,
        slot_date: date,
        slot_time: str,
    ) -> bool:
        """
        Called atomically after a booking is committed.
        Uses the UNIQUE constraint as the look-up key.

        Raw SQL equivalent:
            UPDATE time_slots
            SET is_available = FALSE
            WHERE doctor_id = :doctor_id
              AND slot_date  = :slot_date
              AND slot_time  = :slot_time
            RETURNING id;
        """
        result = await self.session.execute(
            update(TimeSlot)
            .where(
                TimeSlot.doctor_id == doctor_id,
                TimeSlot.slot_date == slot_date,
                TimeSlot.slot_time == slot_time,
            )
            .values(is_available=False)
            .returning(TimeSlot.id)
        )
        return result.rowcount > 0

    async def mark_available(
        self,
        doctor_id: uuid.UUID,
        slot_date: date,
        slot_time: str,
    ) -> bool:
        """Re-opens a slot when an appointment is cancelled."""
        result = await self.session.execute(
            update(TimeSlot)
            .where(
                TimeSlot.doctor_id == doctor_id,
                TimeSlot.slot_date == slot_date,
                TimeSlot.slot_time == slot_time,
            )
            .values(is_available=True)
            .returning(TimeSlot.id)
        )
        return result.rowcount > 0

    # ─────────────────────────────────────────────────────────────────────────
    # BULK GENERATION — upsert-safe via ON CONFLICT DO NOTHING
    # ─────────────────────────────────────────────────────────────────────────

    async def bulk_generate(
        self,
        doctor_id: uuid.UUID,
        start_date: date,
        num_days: int = 30,
        slot_times: list[str] | None = None,
    ) -> int:
        """
        Generates `num_days` × len(slot_times) rows for a doctor.
        Idempotent: ON CONFLICT (uq_doctor_slot) DO NOTHING.
        Returns count of rows actually inserted.

        Raw SQL equivalent:
            INSERT INTO time_slots (id, doctor_id, slot_date, slot_time, is_available)
            SELECT gen_random_uuid(), :doctor_id, d.day, s.slot, TRUE
            FROM generate_series(
                :start_date,
                :start_date + :num_days - 1,
                '1 day'
            ) AS d(day)
            CROSS JOIN unnest(:slots) AS s(slot)
            ON CONFLICT (doctor_id, slot_date, slot_time) DO NOTHING;

        Index used: uq_doctor_slot (UNIQUE) as conflict arbiter
        """
        if slot_times is None:
            slot_times = DEFAULT_SLOT_TIMES

        rows = [
            {
                "id":           uuid.uuid4(),
                "doctor_id":    doctor_id,
                "slot_date":    start_date + timedelta(days=d),
                "slot_time":    st,
                "is_available": True,
            }
            for d in range(num_days)
            for st in slot_times
        ]

        stmt = (
            pg_insert(TimeSlot)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_doctor_slot")
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    # ─────────────────────────────────────────────────────────────────────────
    # Date range availability summary
    # ─────────────────────────────────────────────────────────────────────────

    async def availability_summary(
        self,
        doctor_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> dict[str, int]:
        """
        Returns {date_str: available_count} mapping for a date range.
        Useful for front-end calendar views.

        Raw SQL equivalent:
            SELECT slot_date, COUNT(*) AS available_count
            FROM time_slots
            WHERE doctor_id   = :doctor_id
              AND slot_date BETWEEN :start AND :end
              AND is_available = TRUE
            GROUP BY slot_date
            ORDER BY slot_date;
        """
        from sqlalchemy import func as sa_func

        result = await self.session.execute(
            select(
                TimeSlot.slot_date,
                sa_func.count().label("available_count"),
            )
            .where(
                TimeSlot.doctor_id    == doctor_id,
                TimeSlot.slot_date    >= start_date,
                TimeSlot.slot_date    <= end_date,
                TimeSlot.is_available == True,      # noqa: E712
            )
            .group_by(TimeSlot.slot_date)
            .order_by(TimeSlot.slot_date)
        )
        return {str(row.slot_date): row.available_count for row in result}
