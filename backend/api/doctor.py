import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from habs_db.repositories.database import get_db
from habs_db.repositories.appointments import AppointmentRepository
from habs_db.models import Appointment, Doctor
from security import get_current_user

router = APIRouter()

@router.get("/list")
async def list_doctors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Doctor).where(Doctor.is_active == True)
    )
    doctors = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "full_name": d.full_name,
            "specialization": d.specialization or "Specialist",
        }
        for d in doctors
    ]


@router.get("/dashboard")
async def get_dashboard(req: Request, db: AsyncSession = Depends(get_db)):
    user_id_str = req.headers.get("X-User-Id")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Unauthorized")

    doctor_id = uuid.UUID(user_id_str)

    # Fetch upcoming appointments with patient details
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient))
        .where(Appointment.doctor_id == doctor_id)
        .order_by(Appointment.appointment_date.asc(), Appointment.time_slot.asc())
    )
    appts = result.scalars().all()

    return [{
        "id": str(a.id),
        "patient": a.patient.full_name,
        "date": str(a.appointment_date),
        "time": a.time_slot,
        "status": a.status.value,
        "risk": a.no_show_risk
    } for a in appts]


@router.patch("/{appointment_id}/status")
async def update_status(
    appointment_id: uuid.UUID,
    status: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # 1. Fetch the appointment first
    appt = await db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # 2. Ownership check — only the owning doctor can update
    if str(appt.doctor_id) != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden — not your appointment")

    # 3. Now do the status update
    appt_repo = AppointmentRepository(db)
    if status == "completed":
        success = await appt_repo.mark_completed(appointment_id)
    elif status == "no_show":
        success = await appt_repo.mark_no_show(appointment_id)
    elif status == "cancelled":
        success = await appt_repo.cancel(appointment_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid status")

    if not success:
        raise HTTPException(status_code=404, detail="Appointment not found or not in booked state")

    await db.commit()
    return {"message": f"Appointment marked as {status}"}