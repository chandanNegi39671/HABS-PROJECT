import uuid
from datetime import date
import pandas as pd
import io
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
from security import get_current_user

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
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
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
        slot = TimeSlot(
            doctor_id=booking.doctor_id,
            slot_date=booking.appointment_date,
            slot_time=booking.time_slot,
            is_available=True
        )
        db.add(slot)
        await db.flush()

    if not slot.is_available:
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

    slot.is_available = False
    db.add(slot)

    # ML Prediction
    try:
        patient = await db.get(User, patient_id)
        ml_model = getattr(request.app.state, "ml_model", None)
        risk_score = 0.5

        if ml_model is not None and patient is not None:
            try:
                features = pd.DataFrame([{
                    "scholarship": int(patient.scholarship),
                    "hypertension": int(patient.hypertension),
                    "diabetes": int(patient.diabetes),
                    "alcoholism": int(patient.alcoholism),
                    "has_chronic_condition": int(patient.has_chronic_condition),
                    "appointment_hour": hour,
                    "lead_time_days": lead_time,
                    "gender": 1 if getattr(patient, "gender", "Male") == "Female" else 0,
                    "age": 35  # default age
                }])
                prob = ml_model.predict_proba(features)[0][1]
                risk_score = float(prob)
                print(f"ML prediction for {patient.full_name}: {risk_score:.3f}")
            except Exception as e:
                print(f"ML predict error: {e}")
                risk_score = 0.5

        predicted_label = risk_score >= float(settings.ML_THRESHOLD)

        await ml_repo.record_prediction(
            appointment_id=saved_appt.id,
            no_show_probability=risk_score,
            predicted_label=predicted_label,
            input_features={},
            threshold_used=float(settings.ML_THRESHOLD)
        )
        await appt_repo.update_risk_score(saved_appt.id, risk_score)
        await db.commit()

        # Send confirmation email via Resend
        try:
            doctor = await db.get(Doctor, booking.doctor_id)
            doctor_name = doctor.full_name if doctor else "Specialist"
            doctor_spec = doctor.specialization if doctor else "General"

            # Generate PDF
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            p.setFillColorRGB(0.039, 0.039, 0.039)
            p.rect(0, 722, 612, 70, fill=1, stroke=0)
            p.setFillColorRGB(1, 1, 1)
            p.setFont("Helvetica-Bold", 28)
            p.drawString(40, 755, "HABS")
            p.setFont("Helvetica", 9)
            p.drawString(40, 735, "PRIVATE HEALTHCARE")
            p.drawRightString(555, 755, "APPOINTMENT CONFIRMATION")
            p.setStrokeColorRGB(0.788, 0.658, 0.298)
            p.setLineWidth(2)
            p.line(0, 720, 612, 720)
            p.setFillColorRGB(0.5, 0.5, 0.5)
            p.setFont("Helvetica", 8)
            p.drawString(450, 680, "REF NO.")
            p.setFillColorRGB(0.039, 0.039, 0.039)
            p.setFont("Courier", 11)
            p.drawString(450, 665, str(saved_appt.id)[:8].upper())
            p.setFillColorRGB(0.788, 0.658, 0.298)
            p.setFont("Helvetica", 8)
            p.drawString(40, 650, "PATIENT")
            p.setFillColorRGB(0.039, 0.039, 0.039)
            p.setFont("Helvetica-Bold", 22)
            p.drawString(40, 625, patient.full_name if patient else "Patient")
            p.setStrokeColorRGB(0.9, 0.9, 0.9)
            p.setLineWidth(1)
            p.line(40, 605, 555, 605)
            p.setFillColorRGB(0.788, 0.658, 0.298)
            p.setFont("Helvetica", 8)
            p.drawString(40, 580, "SPECIALIST")
            p.setFillColorRGB(0.039, 0.039, 0.039)
            p.setFont("Helvetica", 13)
            p.drawString(40, 560, f"Dr. {doctor_name}")
            p.setFillColorRGB(0.788, 0.658, 0.298)
            p.setFont("Helvetica", 8)
            p.drawString(40, 530, "DEPARTMENT")
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
            p.drawCentredString(306, 458, "CONFIRMED")
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
            p.drawCentredString(306, 35, "HABS Healthcare · Confidential · Not transferable")
            p.showPage()
            p.save()
            buffer.seek(0)
            pdf_bytes = buffer.read()

            import base64
            import httpx
            pdf_b64 = base64.b64encode(pdf_bytes).decode()

            resend_key = getattr(settings, "RESEND_API_KEY", None)
            if resend_key:
                httpx.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {resend_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": "HABS Healthcare <onboarding@resend.dev>",
                        "to": [patient.email if patient else settings.EMAIL_FROM],
                        "subject": "HABS — Appointment Confirmed",
                        "text": f"Dear {patient.full_name if patient else 'Patient'},\n\nYour appointment with Dr. {doctor_name} on {booking.appointment_date} at {booking.time_slot} is confirmed.\n\n— HABS Healthcare Team",
                        "attachments": [{
                            "filename": f"HABS_Appointment_{str(saved_appt.id)[:8].upper()}.pdf",
                            "content": pdf_b64
                        }]
                    },
                    timeout=10
                )
        except Exception as e:
            print(f"Email send error: {e}")

    except Exception as e:
        print(f"ML Error: {e}")
        await db.commit()

    return {"message": "Appointment booked successfully", "appointment_id": str(saved_appt.id)}

@router.get("")
async def get_patient_appointments(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
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
    current_user=Depends(get_current_user)
):
    appt_repo = AppointmentRepository(db)

    appt = await db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

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
