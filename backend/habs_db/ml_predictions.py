"""
HABS — MLPredictions Repository
JSONB input_features validated before every insert.
One-to-one with Appointment.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from habs_db.models import MLPrediction
from habs_db.repositories.base import BaseRepository
from habs_db.schemas.ml_input import validate_ml_input


class MLPredictionRepository(BaseRepository[MLPrediction]):
    model = MLPrediction

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ─────────────────────────────────────────────────────────────────────────
    # SAFE INSERT — validates JSONB schema before touching the DB
    # ─────────────────────────────────────────────────────────────────────────

    async def record_prediction(
        self,
        *,
        appointment_id:       uuid.UUID,
        no_show_probability:  float,
        predicted_label:      bool,
        input_features:       dict,
        model_version:        str   = "habs_noshow_v1",
        threshold_used:       float = 0.4,
    ) -> MLPrediction:
        """
        Validates input_features against ML_INPUT_SCHEMA, then inserts.
        Raises ValueError on schema violation or range check failure.

        Steps:
          1. validate_ml_input(input_features)       — raises on bad features
          2. CHECK probability in [0,1]              — DB constraint backup
          3. session.add → flush → refresh

        Raw SQL equivalent:
            INSERT INTO ml_predictions
              (id, appointment_id, model_version, no_show_probability,
               predicted_label, threshold_used, input_features)
            VALUES
              (gen_random_uuid(), :appointment_id, :model_version,
               :prob, :label, :threshold, :features::jsonb)
            RETURNING *;

        Index used: uq constraint on appointment_id (one-to-one guard)
        """
        # ── Layer-1 validation: JSON schema ──
        validate_ml_input(input_features)

        # ── Layer-2 validation: probability range ──
        if not (0.0 <= no_show_probability <= 1.0):
            raise ValueError(
                f"no_show_probability must be in [0,1], got {no_show_probability}"
            )

        prediction = MLPrediction(
            appointment_id       = appointment_id,
            model_version        = model_version,
            no_show_probability  = no_show_probability,
            predicted_label      = predicted_label,
            threshold_used       = threshold_used,
            input_features       = input_features,
        )
        return await self.create(prediction)

    # ─────────────────────────────────────────────────────────────────────────
    # Lookups
    # ─────────────────────────────────────────────────────────────────────────

    async def get_by_appointment(
        self, appointment_id: uuid.UUID
    ) -> MLPrediction | None:
        """
        Raw SQL equivalent:
            SELECT * FROM ml_predictions
            WHERE appointment_id = :appointment_id;

        Index used: ix_ml_predictions_appointment_id
        """
        result = await self.session.execute(
            select(MLPrediction).where(
                MLPrediction.appointment_id == appointment_id
            )
        )
        return result.scalar_one_or_none()

    async def get_high_risk_predictions(
        self,
        *,
        threshold: float = 0.4,
        model_version: str = "habs_noshow_v1",
        limit: int = 1000,
    ) -> Sequence[MLPrediction]:
        """
        Fetches predictions above threshold for a given model version.
        Used by analytics and batch outreach jobs.

        Raw SQL equivalent:
            SELECT * FROM ml_predictions
            WHERE predicted_label = TRUE
              AND model_version = :version
              AND no_show_probability >= :threshold
            ORDER BY no_show_probability DESC
            LIMIT :limit;

        Index used: ix_ml_predictions_predicted_label, ix_ml_predictions_model_version
        """
        result = await self.session.execute(
            select(MLPrediction)
            .where(
                MLPrediction.predicted_label      == True,      # noqa: E712
                MLPrediction.model_version        == model_version,
                MLPrediction.no_show_probability  >= threshold,
            )
            .order_by(MLPrediction.no_show_probability.desc())
            .limit(limit)
        )
        return result.scalars().all()

    # ─────────────────────────────────────────────────────────────────────────
    # Model performance telemetry
    # ─────────────────────────────────────────────────────────────────────────

    async def prediction_stats(self, model_version: str = "habs_noshow_v1") -> dict:
        """
        Returns aggregate stats for monitoring model drift.

        Raw SQL equivalent:
            SELECT
                COUNT(*)                                          AS total,
                AVG(no_show_probability)                          AS avg_probability,
                SUM(CASE WHEN predicted_label THEN 1 ELSE 0 END) AS flagged_count
            FROM ml_predictions
            WHERE model_version = :version;
        """
        from sqlalchemy import func, case

        result = await self.session.execute(
            select(
                func.count().label("total"),
                func.avg(MLPrediction.no_show_probability).label("avg_probability"),
                func.sum(
                    case((MLPrediction.predicted_label == True, 1), else_=0)   # noqa: E712
                ).label("flagged_count"),
            ).where(MLPrediction.model_version == model_version)
        )
        row = result.one()
        return {
            "model_version": model_version,
            "total":         int(row.total or 0),
            "avg_probability": float(row.avg_probability or 0.0),
            "flagged_count": int(row.flagged_count or 0),
            "flag_rate":     round(
                (row.flagged_count or 0) / max(row.total or 1, 1), 4
            ),
        }
