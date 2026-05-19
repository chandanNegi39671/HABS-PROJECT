"""
HABS — SQLAlchemy 2.x ORM Models
6 tables, 3NF, UUIDs, DateTime(timezone=True), proper FKs, UNIQUE guards, soft-delete pattern.
"""

from __future__ import annotations

import uuid
import enum
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Enum, Float,
    ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


# ─────────────────────────────── Base ────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ─────────────────────────────── Enums ───────────────────────────────────────

class AppointmentStatus(str, enum.Enum):
    BOOKED    = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW   = "no_show"


class NotificationType(str, enum.Enum):
    SMS   = "sms"
    EMAIL = "email"
    PUSH  = "push"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT    = "sent"
    FAILED  = "failed"


# ─────────────────────────────── users ───────────────────────────────────────

class User(Base):
    """
    Patients / end-users.
    Soft-delete via is_active — never hard-delete.
    ML features (hypertension, diabetes, etc.) stored directly; no separate profile table.
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str]           = mapped_column(String(255), nullable=False)
    email: Mapped[str]               = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[Optional[str]]     = mapped_column(String(20))
    hashed_password: Mapped[str]     = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    gender: Mapped[Optional[str]]    = mapped_column(String(10))
    is_email_verified: Mapped[bool]  = mapped_column(Boolean, default=False, nullable=False)

    # ── ML feature flags ──
    scholarship: Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    hypertension: Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    diabetes: Mapped[bool]              = mapped_column(Boolean, default=False, nullable=False)
    alcoholism: Mapped[bool]            = mapped_column(Boolean, default=False, nullable=False)
    has_chronic_condition: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Lifecycle ──
    is_active: Mapped[bool]    = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # ── Relationships ──
    appointments: Mapped[list[Appointment]] = relationship(
        "Appointment", back_populates="patient", foreign_keys="[Appointment.patient_id]",
        lazy="selectin",
    )
    notifications: Mapped[list[Notification]] = relationship(
        "Notification", back_populates="user", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_users_email",     "email"),
        Index("ix_users_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} active={self.is_active}>"


class OTPVerification(Base):
    """
    Temporary OTP storage for email verification.
    """
    __tablename__ = "otp_verifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str]       = mapped_column(String(255), nullable=False)
    otp_code: Mapped[str]    = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool]    = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_otp_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<OTPVerification email={self.email} code={self.otp_code} used={self.is_used}>"


# ─────────────────────────────── doctors ─────────────────────────────────────

class Doctor(Base):
    """
    Doctors / providers.
    Soft-delete via is_active.
    """
    __tablename__ = "doctors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str]       = mapped_column(String(255), nullable=False)
    specialization: Mapped[str]  = mapped_column(String(100), nullable=False)
    email: Mapped[str]           = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    appointments: Mapped[list[Appointment]] = relationship(
        "Appointment", back_populates="doctor", lazy="selectin"
    )
    time_slots: Mapped[list[TimeSlot]] = relationship(
        "TimeSlot", back_populates="doctor", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_doctors_specialization", "specialization"),
        Index("ix_doctors_is_active",      "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Doctor id={self.id} name={self.full_name} spec={self.specialization}>"


# ─────────────────────────────── admins ──────────────────────────────────────

class Admin(Base):
    """
    HABS System Administrators.
    """
    __tablename__ = "admins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str]       = mapped_column(String(255), nullable=False)
    email: Mapped[str]           = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Admin id={self.id} email={self.email}>"


# ─────────────────────────────── appointments ────────────────────────────────

class Appointment(Base):
    """
    Core booking entity.

    Double-booking guard  : UNIQUE(doctor_id, appointment_date, time_slot)
    No-show risk guard    : CHECK(0 <= no_show_risk <= 1)
    Status transitions    : booked → completed | cancelled | no_show
    Soft-delete           : status field — never hard-delete rows
    """
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id",    ondelete="RESTRICT"),
        nullable=False,
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id",  ondelete="RESTRICT"),
        nullable=False,
    )

    appointment_date: Mapped[date] = mapped_column(Date, nullable=False)
    time_slot: Mapped[str]         = mapped_column(String(10), nullable=False)   # "09:00"
    appointment_hour: Mapped[int]  = mapped_column(Integer,    nullable=False)   # 0–23
    lead_time_days: Mapped[int]    = mapped_column(Integer,    nullable=False)   # booking lag

    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(
            AppointmentStatus,
            name="appointment_status_enum",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=AppointmentStatus.BOOKED,
        nullable=False,
    )
    no_show_risk: Mapped[Optional[float]] = mapped_column(Float)
    sms_reminder_sent: Mapped[bool]       = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[Optional[str]]          = mapped_column(Text)

    booked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # ── Relationships ──
    patient: Mapped[User]                      = relationship(
        "User",          back_populates="appointments", foreign_keys=[patient_id]
    )
    doctor: Mapped[Doctor]                     = relationship(
        "Doctor",        back_populates="appointments"
    )
    ml_prediction: Mapped[Optional[MLPrediction]] = relationship(
        "MLPrediction",  back_populates="appointment", uselist=False, lazy="selectin"
    )
    notifications: Mapped[list[Notification]]  = relationship(
        "Notification",  back_populates="appointment", lazy="selectin"
    )

    __table_args__ = (
        # ── Integrity ──
        UniqueConstraint(
            "doctor_id", "appointment_date", "time_slot",
            name="uq_doctor_date_slot",
        ),
        CheckConstraint(
            "no_show_risk IS NULL OR (no_show_risk >= 0 AND no_show_risk <= 1)",
            name="ck_no_show_risk_range",
        ),
        CheckConstraint("lead_time_days >= 0",               name="ck_lead_time_positive"),
        CheckConstraint(
            "appointment_hour >= 0 AND appointment_hour <= 23",
            name="ck_appointment_hour_range",
        ),

        # ── Indexes ──
        Index("ix_appointments_patient_id",    "patient_id"),
        Index("ix_appointments_doctor_id",     "doctor_id"),
        Index("ix_appointments_status",        "status"),
        Index("ix_appointments_doctor_date",   "doctor_id", "appointment_date"),   # dashboard query
        Index("ix_appointments_patient_status","patient_id", "status"),             # ML aggregation
        Index("ix_appointments_booked_at",     "booked_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Appointment id={self.id} patient={self.patient_id} "
            f"doctor={self.doctor_id} date={self.appointment_date} status={self.status}>"
        )


# ─────────────────────────────── time_slots ──────────────────────────────────

class TimeSlot(Base):
    """
    Pre-generated availability grid for each doctor.
    UNIQUE(doctor_id, slot_date, slot_time) — the conflict guard used by
    INSERT … ON CONFLICT DO NOTHING during booking.
    """
    __tablename__ = "time_slots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
    )
    slot_date: Mapped[date] = mapped_column(Date,       nullable=False)
    slot_time: Mapped[str]  = mapped_column(String(10), nullable=False)  # "09:00"
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    doctor: Mapped[Doctor] = relationship("Doctor", back_populates="time_slots")

    __table_args__ = (
        UniqueConstraint("doctor_id", "slot_date", "slot_time", name="uq_doctor_slot"),
        Index("ix_time_slots_doctor_date",  "doctor_id", "slot_date"),
        Index("ix_time_slots_available",    "is_available", "slot_date"),
    )

    def __repr__(self) -> str:
        return f"<TimeSlot doctor={self.doctor_id} {self.slot_date} {self.slot_time} avail={self.is_available}>"


# ─────────────────────────────── notifications ───────────────────────────────

class Notification(Base):
    """
    Outbound notifications (SMS / email / push).
    appointment_id is nullable — supports non-appointment system messages.
    """
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    appointment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
    )

    type: Mapped[NotificationType] = mapped_column(
        Enum(
            NotificationType,
            name="notification_type_enum",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(
            NotificationStatus,
            name="notification_status_enum",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=NotificationStatus.PENDING,
        nullable=False,
    )
    message: Mapped[str]              = mapped_column(Text, nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime]      = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User]                       = relationship("User",        back_populates="notifications")
    appointment: Mapped[Optional[Appointment]] = relationship("Appointment", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_user_id",        "user_id"),
        Index("ix_notifications_appointment_id", "appointment_id"),
        Index("ix_notifications_status",         "status"),
        Index("ix_notifications_created_at",     "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user={self.user_id} type={self.type} status={self.status}>"


# ─────────────────────────────── ml_predictions ──────────────────────────────

class MLPrediction(Base):
    """
    One-to-one with Appointment.
    input_features stored as JSONB — validated against ML_INPUT_SCHEMA before insert.
    no_show_probability CHECK(0 <= p <= 1), threshold stored for model versioning.
    """
    __tablename__ = "ml_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,                              # enforces one-to-one
    )
    model_version: Mapped[str]           = mapped_column(
        String(50), nullable=False, default="habs_noshow_v1"
    )
    no_show_probability: Mapped[float]   = mapped_column(Float, nullable=False)
    predicted_label: Mapped[bool]        = mapped_column(Boolean, nullable=False)   # True = no-show
    threshold_used: Mapped[float]        = mapped_column(Float, nullable=False, default=0.4)
    input_features: Mapped[dict]         = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    appointment: Mapped[Appointment] = relationship(
        "Appointment", back_populates="ml_prediction"
    )

    __table_args__ = (
        CheckConstraint(
            "no_show_probability >= 0 AND no_show_probability <= 1",
            name="ck_no_show_prob_range",
        ),
        CheckConstraint(
            "threshold_used >= 0 AND threshold_used <= 1",
            name="ck_threshold_range",
        ),
        Index("ix_ml_predictions_appointment_id",  "appointment_id"),
        Index("ix_ml_predictions_predicted_label", "predicted_label"),
        Index("ix_ml_predictions_model_version",   "model_version"),
    )

    def __repr__(self) -> str:
        return (
            f"<MLPrediction appt={self.appointment_id} "
            f"prob={self.no_show_probability:.3f} label={self.predicted_label} "
            f"model={self.model_version}>"
        )