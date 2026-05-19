import uuid
from datetime import date
import pandas as pd
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from habs_db.repositories.database import get_db
from habs_db.repositories.appointments import AppointmentRepository
from habs_db.repositories.time_slots import TimeSlotRepository
from habs_db.repositories.users import UserRepository
from habs_db.ml_predictions import MLPredictionRepository
from habs_db.models import Appointment, TimeSlot, AppointmentStatus, User, Doctor
from api.schemas import AppointmentBook
from habs_db.settings import get_settings
from security import get_current_user  # FIX #1: use verified JWT identity

router = APIRouter()
settings = get_settings()

@router.get("/slots")
async def get_slots(doctor_id: uuid.UUID, slot_date: date, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TimeSlot).where(
            TimeSlot.doctor_id == doctor_id,
            TimeSlot.slot_date == slot_date,
            TimeSlot.is_available == True
        ).order_by(TimeSlot.slot_time)
    )
    slots = result.scalars().all()
    return [{"id": str(s.id), "time": s.slot_time} for s in slots]

@router.post("")
async def book_appointment(
    booking: AppointmentBook,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)  # FIX #1: JWT-verified identity
):
    # Identity comes from verified JWT — not from an arbitrary request header
    try:
        patient_id = uuid.UUID(current_user.id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token identity")

    appt_repo = AppointmentRepository(db)
    user_repo = UserRepository(db)
    ml_repo = MLPredictionRepository(db)

    # Check if slot exists
    result = await db.execute(
        select(TimeSlot).where(
            TimeSlot.doctor_id == booking.doctor_id,
            TimeSlot.slot_date == booking.appointment_date,
            TimeSlot.slot_time == booking.time_slot
        )
    )
    slot = result.scalar_one_or_none()

    if not slot:
        # Auto-create the slot on demand since the frontend hardcodes slots
        slot = TimeSlot(
            doctor_id=booking.doctor_id,
            slot_date=booking.appointment_date,
            slot_time=booking.time_slot,
            is_available=True
        )
        db.add(slot)
        await db.flush()

    if not slot.is_available:
        # Check if an active (non-cancelled) appointment actually holds this slot.
        active_check = await db.execute(
            select(Appointment).where(
                Appointment.doctor_id == booking.doctor_id,
                Appointment.appointment_date == booking.appointment_date,
                Appointment.time_slot == booking.time_slot,
                Appointment.status != AppointmentStatus.CANCELLED
            )
        )
        active_appt = active_check.scalar_one_or_none()
        if active_appt:
            raise HTTPException(status_code=400, detail="Slot not available — already booked")
        # No active appointment found → previous attempt crashed; reclaim the slot
        slot.is_available = True
        db.add(slot)
        await db.flush()

    lead_time = (booking.appointment_date - date.today()).days
    if lead_time < 0:
        raise HTTPException(status_code=400, detail="Cannot book in the past")

    hour = int(booking.time_slot.split(":")[0])

    new_appt = Appointment(
        patient_id=patient_id,
        doctor_id=booking.doctor_id,
        appointment_date=booking.appointment_date,
        time_slot=booking.time_slot,
        appointment_hour=hour,
        lead_time_days=lead_time,
        status=AppointmentStatus.BOOKED
    )

    try:
        saved_appt = await appt_repo.book(new_appt)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Mark slot unavailable
    slot.is_available = False
    db.add(slot)

    # ML Prediction + Email Confirmation
    try:
        # Use the loaded ML model if available, otherwise fall back to 0.5
        ml_model = None
        try:
            from fastapi import Request as FastAPIRequest
            # Access model from app state via the request
        except Exception:
            pass

        risk_score = 0.5  # TODO: wire real model call: request.app.state.ml_model.predict(features)

        await ml_repo.record_prediction(
            appointment_id=saved_appt.id,
            no_show_probability=risk_score,
            predicted_label=False,
            input_features={},
            threshold_used=0.4
        )

        await appt_repo.update_risk_score(saved_appt.id, risk_score)
        await db.commit()
        try:
            # 1. Fetch details
            patient = await db.get(User, patient_id)
            doctor = await db.get(Doctor, booking.doctor_id)

            doctor_name = doctor.full_name if doctor else "Specialist"
            doctor_spec = doctor.specialization if doctor else "General"

            # 2. Generate PDF in memory
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)

            # 1. HEADER BAR
            p.setFillColorRGB(0.039, 0.039, 0.039)
            p.rect(0, 722, 612, 70, fill=1, stroke=0)

            p.setFillColorRGB(1, 1, 1)
            p.setFont("Helvetica-Bold", 28)
            p.drawString(40, 755, "HABS")

            p.setFont("Helvetica", 9)
            p.drawString(40, 735, "PRIVATE HEALTHCARE")

            p.drawRightString(555, 755, "APPOINTMENT CONFIRMATION")

            # 2. GOLD ACCENT LINE
            p.setStrokeColorRGB(0.788, 0.658, 0.298)
            p.setLineWidth(2)
            p.line(0, 720, 612, 720)

            # 3. BOOKING ID BLOCK
            p.setFillColorRGB(0.5, 0.5, 0.5)
            p.setFont("Helvetica", 8)
            p.drawString(450, 680, "REF NO.")
            p.setFillColorRGB(0.039, 0.039, 0.039)
            p.setFont("Courier", 11)
            p.drawString(450, 665, str(saved_appt.id)[:8])

            # 4. MAIN CONTENT
            p.setFillColorRGB(0.788, 0.658, 0.298)
            p.setFont("Helvetica", 8)
            p.drawString(40, 650, "PATIENT")

            p.setFillColorRGB(0.039, 0.039, 0.039)
            p.setFont("Helvetica-Bold", 22)
            p.drawString(40, 625, patient.full_name)

            p.setStrokeColorRGB(0.9, 0.9, 0.9)
            p.setLineWidth(1)
            p.line(40, 605, 555, 605)

            p.setFillColorRGB(0.788, 0.658, 0.298)
            p.setFont("Helvetica", 8)
            p.drawString(40, 580, "DOCTOR")

            p.setFillColorRGB(0.039, 0.039, 0.039)
            p.setFont("Helvetica", 13)
            p.drawString(40, 560, f"Dr. {doctor_name}")

            p.setFillColorRGB(0.788, 0.658, 0.298)
            p.setFont("Helvetica", 8)
            p.drawString(40, 530, "SPECIALIZATION")

            p.setFillColorRGB(0.039, 0.039, 0.039)
            p.setFont("Helvetica", 13)
            p.drawString(40, 510, doctor_spec)

            p.setFillColorRGB(0.788, 0.658, 0.298)
            p.setFont("Helvetica", 8)
            p.drawString(300, 580, "DATE")

            p.setFillColorRGB(0.039, 0.039, 0.039)
            p.setFont("Helvetica", 13)
            formatted_date = booking.appointment_date.strftime("%A, %d %B %Y")
            p.drawString(300, 560, formatted_date)

            p.setFillColorRGB(0.788, 0.658, 0.298)
            p.setFont("Helvetica", 8)
            p.drawString(300, 530, "TIME")

            p.setFillColorRGB(0.039, 0.039, 0.039)
            p.setFont("Helvetica", 13)
            p.drawString(300, 510, booking.time_slot)

            p.setFillColorRGB(0.788, 0.658, 0.298)
            p.roundRect(246, 450, 120, 24, 12, fill=1, stroke=0)

            p.setFillColorRGB(1, 1, 1)
            p.setFont("Helvetica-Bold", 10)
            p.drawCentredString(306, 458, "CONFIRMED ✓")

            p.setFillColorRGB(0.96, 0.96, 0.96)
            p.roundRect(40, 390, 515, 40, 4, fill=1, stroke=0)

            p.setFillColorRGB(0.788, 0.658, 0.298)
            p.rect(40, 390, 3, 40, fill=1, stroke=0)

            p.setFillColorRGB(0.33, 0.33, 0.33)
            p.setFont("Helvetica", 10)
            p.drawString(55, 406, "Please arrive 10 minutes early. Carry this document.")

            p.setStrokeColorRGB(0.788, 0.658, 0.298)
            p.setLineWidth(1)
            p.line(40, 50, 555, 50)

            p.setFillColorRGB(0.5, 0.5, 0.5)
            p.setFont("Helvetica", 8)
            p.drawCentredString(306, 35, "HABS Healthcare \u00B7 Confidential \u00B7 Not transferable")

            p.showPage()
            p.save()
            buffer.seek(0)

            # 3. Send email
            msg = MIMEMultipart()
            msg['From'] = settings.EMAIL_USER
            msg['To'] = patient.email
            msg['Subject'] = "HABS — Appointment Confirmed 🏥"

            body = f"""Dear {patient.full_name},

Your appointment has been confirmed!
Please find your appointment details in the attached PDF.

Doctor : Dr. {doctor_name}
Date   : {booking.appointment_date}
Time   : {booking.time_slot}

Please arrive 10 minutes early.
To cancel, login to your HABS account.

— HABS Healthcare Team"""
            msg.attach(MIMEText(body, 'plain'))

            part = MIMEBase('application', 'octet-stream')
            part.set_payload(buffer.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename=HABS_Appointment_{saved_appt.id}.pdf")
            msg.attach(part)

            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()

        except Exception as e:
            print(f"Failed to send confirmation email: {e}")
            pass

    except Exception as e:
        print(f"ML Error: {e}")
        pass

    return {"message": "Appointment booked successfully", "appointment_id": str(saved_appt.id)}

@router.get("")
async def get_patient_appointments(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)  # FIX #1: JWT-verified identity
):
    try:
        patient_id = uuid.UUID(current_user.id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token identity")

    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.doctor))
        .where(Appointment.patient_id == patient_id)
        .order_by(Appointment.appointment_date.desc(), Appointment.time_slot.desc())
    )
    appts = result.scalars().all()

    return [{
        "id": str(a.id),
        "doctor_name": a.doctor.full_name,
        "doctor_spec": a.doctor.specialization,
        "date": str(a.appointment_date),
        "time": a.time_slot,
        "status": a.status.value if hasattr(a.status, 'value') else str(a.status)
    } for a in appts]

@router.patch("/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)  # ensure caller is authenticated
):
    appt_repo = AppointmentRepository(db)

    appt = await db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Ensure the patient can only cancel their own appointments
    try:
        caller_id = uuid.UUID(current_user.id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token identity")

    if current_user.role == "patient" and appt.patient_id != caller_id:
        raise HTTPException(status_code=403, detail="Cannot cancel another patient's appointment")

    if appt.status == AppointmentStatus.CANCELLED:
        return {"message": "Appointment already cancelled"}

    appt.status = AppointmentStatus.CANCELLED
    db.add(appt)

    result = await db.execute(
        select(TimeSlot).where(
            TimeSlot.doctor_id == appt.doctor_id,
            TimeSlot.slot_date == appt.appointment_date,
            TimeSlot.slot_time == appt.time_slot
        )
    )
    slot = result.scalar_one_or_none()
    if slot:
        slot.is_available = True
        db.add(slot)

    await db.commit()
    return {"message": "Appointment cancelled successfully"}