"""
HABS — Appointments API Router
Handles booking, listing, and cancellation for patients.
"""

import uuid
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from habs_db.repositories.database import get_db
from habs_db.repositories.appointments import AppointmentRepository
from habs_db.models import Appointment, AppointmentStatus, User, Doctor
from api.schemas import AppointmentBook
from api.auth import send_email          # ← ADDED: booking confirmation email
from security import get_current_user

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# BOOK — patient books an appointment
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/book", status_code=status.HTTP_201_CREATED)
async def book_appointment(
    data: AppointmentBook,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    patient_id = uuid.UUID(current_user.id)

    # Validate appointment date is not in the past
    if data.appointment_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot book an appointment in the past")

    # Derive appointment_hour and lead_time_days from slot and date
    try:
        appointment_hour = int(data.time_slot.split(":")[0])
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid time_slot format — expected HH:MM")

    lead_time_days = (data.appointment_date - date.today()).days

    # Fetch patient ML history for risk prediction
    appt_repo = AppointmentRepository(db)
    ml_history = await appt_repo.get_patient_ml_history(patient_id)

    # Fetch patient record for ML features
    patient_result = await db.execute(select(User).where(User.id == patient_id))
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found")

    # Build appointment object
    appointment = Appointment(
        id=uuid.uuid4(),
        patient_id=patient_id,
        doctor_id=data.doctor_id,
        appointment_date=data.appointment_date,
        time_slot=data.time_slot,
        appointment_hour=appointment_hour,
        lead_time_days=lead_time_days,
        status=AppointmentStatus.BOOKED,
    )

    # Try to save (double-booking guard via UNIQUE constraint in DB)
    try:
        saved = await appt_repo.book(appointment)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    # Run ML risk prediction if model is loaded
    no_show_risk = None
    try:
        ml_model = getattr(request.app.state, "ml_model", None)
        if ml_model is not None:
            age = None
            if patient.date_of_birth:
                age = (date.today() - patient.date_of_birth).days // 365

            features = [[
                age or 30,
                1 if (patient.gender or "").lower() == "female" else 0,
                int(getattr(patient, "scholarship", False) or False),
                int(getattr(patient, "hypertension", False) or False),
                int(getattr(patient, "diabetes", False) or False),
                int(getattr(patient, "alcoholism", False) or False),
                int(getattr(patient, "has_chronic_condition", False) or False),
                lead_time_days,
                appointment_hour,
                ml_history["prior_appointment_count"],
                ml_history["prior_no_show_count"],
            ]]
            prob = ml_model.predict_proba(features)[0][1]
            no_show_risk = round(float(prob), 4)
            await appt_repo.update_risk_score(saved.id, no_show_risk)
    except Exception as e:
        print(f"ML prediction failed (non-fatal): {e}")

    await db.commit()

    # ── ADDED: Booking confirmation email ────────────────────────────────────
    try:
        doctor_result = await db.execute(select(Doctor).where(Doctor.id == data.doctor_id))
        doctor = doctor_result.scalar_one_or_none()
        doctor_name = doctor.full_name if doctor else "your doctor"

        subject = "HABS — Appointment Confirmation ✅"
        body = (
            f"Hi {patient.full_name},\n\n"
            f"Your appointment has been successfully booked!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  Doctor   : {doctor_name}\n"
            f"  Date     : {data.appointment_date}\n"
            f"  Time     : {data.time_slot}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Please arrive 10 minutes before your scheduled time.\n\n"
            f"To cancel, visit your dashboard on the HABS app.\n\n"
            f"— HABS Healthcare Team"
        )
        send_email(patient.email, subject, body)
    except Exception as e:
        print(f"Booking confirmation email failed (non-fatal): {e}")
    # ─────────────────────────────────────────────────────────────────────────

    return {
        "id": str(saved.id),
        "doctor_id": str(saved.doctor_id),
        "appointment_date": str(saved.appointment_date),
        "time_slot": saved.time_slot,
        "status": saved.status.value,
        "no_show_risk": no_show_risk,
        "message": "Appointment booked successfully",
    }


# ─────────────────────────────────────────────────────────────────────────────
# LIST — patient sees their own appointments
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/my")
async def get_my_appointments(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    patient_id = uuid.UUID(current_user.id)

    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.doctor))
        .where(Appointment.patient_id == patient_id)
        .order_by(Appointment.appointment_date.desc(), Appointment.time_slot.desc())
    )
    appts = result.scalars().all()

    return [
        {
            "id": str(a.id),
            "doctor_name": a.doctor.full_name if a.doctor else "Unknown",
            "specialization": (a.doctor.specialization or "Specialist") if a.doctor else "Unknown",
            "appointment_date": str(a.appointment_date),
            "time_slot": a.time_slot,
            "status": a.status.value,
            "no_show_risk": a.no_show_risk,
            "booked_at": str(a.booked_at),
        }
        for a in appts
    ]


# ─────────────────────────────────────────────────────────────────────────────
# CANCEL — patient cancels their own booked appointment
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    patient_id = uuid.UUID(current_user.id)

    appt = await db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appt.patient_id != patient_id:
        raise HTTPException(status_code=403, detail="Forbidden — not your appointment")

    appt_repo = AppointmentRepository(db)
    success = await appt_repo.cancel(appointment_id)

    if not success:
        raise HTTPException(status_code=400, detail="Appointment cannot be cancelled (already completed or cancelled)")

    await db.commit()
    return {"message": "Appointment cancelled successfully"}


# ─────────────────────────────────────────────────────────────────────────────
# AVAILABLE SLOTS — check which slots are free for a doctor on a date
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/available-slots")
async def get_available_slots(
    doctor_id: uuid.UUID,
    appointment_date: date,
    db: AsyncSession = Depends(get_db),
):
    if appointment_date < date.today():
        raise HTTPException(status_code=400, detail="Date cannot be in the past")

    # All possible slots
    all_slots = [
        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "12:00", "12:30", "14:00", "14:30", "15:00", "15:30",
        "16:00", "16:30", "17:00",
    ]

    # Fetch already-booked slots for this doctor on this date
    result = await db.execute(
        select(Appointment.time_slot).where(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status == AppointmentStatus.BOOKED,
        )
    )
    booked_slots = {row[0] for row in result.fetchall()}

    return {
        "doctor_id": str(doctor_id),
        "date": str(appointment_date),
        "available_slots": [s for s in all_slots if s not in booked_slots],
        "booked_slots": list(booked_slots),
    }
