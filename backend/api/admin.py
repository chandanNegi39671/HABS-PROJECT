import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from habs_db.repositories.database import get_db
from habs_db.models import User, Doctor, Appointment, AppointmentStatus
from habs_db.settings import get_settings
from jose import jwt, JWTError

router = APIRouter()
settings = get_settings()

async def verify_admin(req: Request):
    auth_header = req.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def send_email(to_email, subject, body):
    try:
        import httpx
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": "HABS Healthcare <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "text": body
            },
            timeout=10
        )
        if response.status_code == 200:
            print(f"Email sent via Resend to {to_email}")
            return True
        else:
            print(f"Resend error: {response.text}")
            return False
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

@router.get("/pending-doctors", dependencies=[Depends(verify_admin)])
async def get_pending_doctors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Doctor).where(Doctor.verification_status == "pending")
    )
    doctors = result.scalars().all()
    return [{
        "id": str(d.id),
        "full_name": d.full_name,
        "email": d.email,
        "phone": d.phone,
        "specialization": d.specialization or "General",
        "created_at": str(d.created_at)
    } for d in doctors]

@router.get("/all-doctors", dependencies=[Depends(verify_admin)])
async def get_all_doctors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Doctor))
    doctors = result.scalars().all()
    return [{
        "id": str(d.id),
        "full_name": d.full_name,
        "email": d.email,
        "phone": d.phone,
        "specialization": d.specialization or "General",
        "verification_status": d.verification_status,
        "rejection_reason": d.rejection_reason
    } for d in doctors]

@router.get("/stats", dependencies=[Depends(verify_admin)])
async def get_stats(db: AsyncSession = Depends(get_db)):
    # Count only real patients — LEFT JOIN is more reliable than NOT IN
    patients_count = await db.scalar(
        select(func.count(User.id))
        .outerjoin(Doctor, User.id == Doctor.id)
        .where(Doctor.id == None)
    )
    
    # Approved doctors
    approved_doctors_count = await db.scalar(
        select(func.count(Doctor.id)).where(Doctor.verification_status == "approved")
    )
    
    # Pending doctors
    pending_doctors_count = await db.scalar(
        select(func.count(Doctor.id)).where(Doctor.verification_status == "pending")
    )
    
    # Total appointments
    appointments_count = await db.scalar(select(func.count(Appointment.id)))
    
    # Total high risk appointments
    high_risk_count = await db.scalar(
        select(func.count(Appointment.id)).where(Appointment.no_show_risk >= 0.6)
    )
    
    return {
        "patients_count": patients_count,
        "approved_doctors_count": approved_doctors_count,
        "pending_doctors_count": pending_doctors_count,
        "appointments_count": appointments_count,
        "high_risk_appointments_count": high_risk_count
    }


@router.get("/patients", dependencies=[Depends(verify_admin)])
async def get_patients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User)
        .outerjoin(Doctor, User.id == Doctor.id)
        .where(Doctor.id == None)
        .order_by(User.created_at.desc())
    )
    patients = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "full_name": p.full_name,
            "email": p.email,
            "phone": p.phone,
            "gender": p.gender,
            "is_active": p.is_active,
            "created_at": str(p.created_at),
        }
        for p in patients
    ]

@router.patch("/doctors/{doctor_id}/approve", dependencies=[Depends(verify_admin)])
async def approve_doctor(doctor_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    doctor = await db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    doctor.verification_status = "approved"
    doctor.is_active = True  # FIX: was missing — doctor list queries Doctor.is_active
    db.add(doctor)
    
    user = await db.get(User, doctor_id)
    if user:
        user.is_active = True
        db.add(user)
    
    await db.commit()
    
    subject = "HABS — Your account has been approved!"
    body = f"""Congratulations {doctor.full_name}!
Your HABS doctor account has been approved.
You can now login at: http://localhost:5173/login
Welcome to the HABS Healthcare Team!"""
    
    send_email(doctor.email, subject, body)
    
    return {"message": "Doctor approved successfully"}

@router.patch("/doctors/{doctor_id}/reject", dependencies=[Depends(verify_admin)])
async def reject_doctor(doctor_id: uuid.UUID, data: dict, db: AsyncSession = Depends(get_db)):
    reason = data.get("reason")
    if not reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
        
    doctor = await db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    doctor.verification_status = "rejected"
    doctor.rejection_reason = reason
    db.add(doctor)
    
    # User stays is_active = False (default)
    
    await db.commit()
    
    subject = "HABS — Account Verification Update"
    body = f"""Dear {doctor.full_name},
We reviewed your HABS account application.
Unfortunately it was not approved.
Reason: {reason}
For queries contact: ramola27041980@gmail.com"""
    
    send_email(doctor.email, subject, body)
    
    return {"message": "Doctor rejected"}

@router.patch("/doctors/{doctor_id}/revoke", dependencies=[Depends(verify_admin)])
async def revoke_doctor_access(doctor_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Revoke an approved doctor's access. They must re-apply to regain entry."""
    doctor = await db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    doctor.is_active = False
    doctor.verification_status = "revoked"
    db.add(doctor)

    user = await db.get(User, doctor_id)
    if user:
        user.is_active = False
        db.add(user)

    await db.commit()

    subject = "HABS — Access Revoked"
    body = f"""Dear {doctor.full_name},

Your HABS doctor account access has been revoked by the administrator.

If you believe this is an error or wish to re-apply in the future,
please contact us at: ramola27041980@gmail.com

Thank you for your time with HABS Healthcare."""

    send_email(doctor.email, subject, body)

    return {"message": "Doctor access revoked successfully"}
