"""
HABS — Seed Data Script
5 doctors, 3 patients, 30 days × 20 slots per doctor, 6 sample appointments.
Run with:  python -m habs_db.seed
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, timedelta

from habs_db.repositories.database import close_db, db_session, init_db
from habs_db.models import Appointment, AppointmentStatus, Doctor, User, Admin
from habs_db.repositories.appointments import AppointmentRepository
from habs_db.repositories.doctors import DoctorRepository
from habs_db.repositories.time_slots import TimeSlotRepository
from habs_db.repositories.users import UserRepository
from habs_db.settings import get_settings
from security import get_password_hash
from sqlalchemy import select

# ─────────────────────────────── Fixtures ────────────────────────────────────

DOCTORS = [
    {"full_name": "Dr. Priya Sharma",    "specialization": "Cardiology",     "email": "p.sharma@habs.test",    "phone": "+91-9800000001"},
    {"full_name": "Dr. Arjun Mehta",     "specialization": "General Practice","email": "a.mehta@habs.test",     "phone": "+91-9800000002"},
    {"full_name": "Dr. Kavita Rao",      "specialization": "Paediatrics",     "email": "k.rao@habs.test",       "phone": "+91-9800000003"},
    {"full_name": "Dr. Sameer Kulkarni", "specialization": "Orthopaedics",    "email": "s.kulkarni@habs.test",  "phone": "+91-9800000004"},
    {"full_name": "Dr. Neha Joshi",      "specialization": "Dermatology",     "email": "n.joshi@habs.test",     "phone": "+91-9800000005"},
]

PATIENTS = [
    {
        "full_name": "Ramesh Gupta",     "email": "ramesh@test.com",
        "phone": "+91-9900000001",       "gender": "M",
        "date_of_birth": date(1975, 4, 12),
        "hypertension": True, "diabetes": True, "scholarship": False,
        "alcoholism": False,  "has_chronic_condition": True,
        "hashed_password": "$2b$12$FAKE_HASH_RAMESH",
    },
    {
        "full_name": "Sunita Verma",     "email": "sunita@test.com",
        "phone": "+91-9900000002",       "gender": "F",
        "date_of_birth": date(1990, 8, 22),
        "hypertension": False, "diabetes": False, "scholarship": True,
        "alcoholism": False,  "has_chronic_condition": False,
        "hashed_password": "$2b$12$FAKE_HASH_SUNITA",
    },
    {
        "full_name": "Amit Patel",       "email": "amit@test.com",
        "phone": "+91-9900000003",       "gender": "M",
        "date_of_birth": date(2005, 11, 5),
        "hypertension": False, "diabetes": False, "scholarship": False,
        "alcoholism": False,  "has_chronic_condition": False,
        "hashed_password": "$2b$12$FAKE_HASH_AMIT",
    },
]

# ─────────────────────────────── Seed runner ─────────────────────────────────

async def seed() -> None:
    settings = get_settings()
    init_db(settings)

    async with db_session() as session:
        doctor_repo    = DoctorRepository(session)
        user_repo      = UserRepository(session)
        slot_repo      = TimeSlotRepository(session)
        appt_repo      = AppointmentRepository(session)

        # ── 1. Doctors ────────────────────────────────────────────────────────
        print("Seeding doctors...")
        doctor_ids: list[uuid.UUID] = []
        for d in DOCTORS:
            existing = await doctor_repo.get_by_email(d["email"])
            if existing:
                doctor_ids.append(existing.id)
                print(f"  [skip] {d['full_name']} already exists")
                continue
            doc = Doctor(**d)
            await doctor_repo.create(doc)
            doctor_ids.append(doc.id)
            print(f"  [+] {d['full_name']} ({d['specialization']})")

        # ── 2. Patients ───────────────────────────────────────────────────────
        print("Seeding patients...")
        patient_ids: list[uuid.UUID] = []
        for p in PATIENTS:
            existing = await user_repo.get_by_email(p["email"])
            if existing:
                patient_ids.append(existing.id)
                print(f"  [skip] {p['full_name']} already exists")
                continue
            user = User(**p)
            await user_repo.create(user)
            patient_ids.append(user.id)
            print(f"  [+] {p['full_name']}")

        # ── 3. Time slots — 30 days per doctor ────────────────────────────────
        print("Generating time slots...")
        today = date.today()
        for doc_id in doctor_ids:
            inserted = await slot_repo.bulk_generate(
                doctor_id=doc_id,
                start_date=today,
                num_days=30,
            )
            print(f"  [+] doctor={doc_id} → {inserted} slots inserted")

        # ── 4. Sample appointments ────────────────────────────────────────────
        print("Creating sample appointments...")
        sample_appts = [
            {
                "patient_id":       patient_ids[0],
                "doctor_id":        doctor_ids[0],
                "appointment_date": today + timedelta(days=2),
                "time_slot":        "09:00",
                "appointment_hour": 9,
                "lead_time_days":   2,
                "no_show_risk":     0.72,   # high-risk — above threshold 0.4
                "sms_reminder_sent": False,
            },
            {
                "patient_id":       patient_ids[0],
                "doctor_id":        doctor_ids[1],
                "appointment_date": today + timedelta(days=5),
                "time_slot":        "14:30",
                "appointment_hour": 14,
                "lead_time_days":   5,
                "no_show_risk":     0.55,
                "sms_reminder_sent": True,
            },
            {
                "patient_id":       patient_ids[1],
                "doctor_id":        doctor_ids[2],
                "appointment_date": today + timedelta(days=1),
                "time_slot":        "10:00",
                "appointment_hour": 10,
                "lead_time_days":   1,
                "no_show_risk":     0.28,   # below threshold
                "sms_reminder_sent": False,
            },
            {
                "patient_id":       patient_ids[2],
                "doctor_id":        doctor_ids[3],
                "appointment_date": today + timedelta(days=7),
                "time_slot":        "11:30",
                "appointment_hour": 11,
                "lead_time_days":   7,
                "no_show_risk":     0.61,
                "sms_reminder_sent": False,
            },
            {
                "patient_id":       patient_ids[1],
                "doctor_id":        doctor_ids[4],
                "appointment_date": today - timedelta(days=3),   # past
                "time_slot":        "08:00",
                "appointment_hour": 8,
                "lead_time_days":   10,
                "status":           AppointmentStatus.COMPLETED,
                "no_show_risk":     0.33,
                "sms_reminder_sent": True,
            },
            {
                "patient_id":       patient_ids[0],
                "doctor_id":        doctor_ids[0],
                "appointment_date": today - timedelta(days=10),  # past no-show
                "time_slot":        "15:00",
                "appointment_hour": 15,
                "lead_time_days":   14,
                "status":           AppointmentStatus.NO_SHOW,
                "no_show_risk":     0.81,
                "sms_reminder_sent": True,
            },
        ]

        for a in sample_appts:
            appt = Appointment(**a)
            try:
                await appt_repo.book(appt)
                print(
                    f"  [+] {appt.appointment_date} {appt.time_slot} "
                    f"patient={appt.patient_id} doctor={appt.doctor_id} "
                    f"risk={appt.no_show_risk}"
                )
            except ValueError as exc:
                print(f"  [skip] {exc}")

        # ── 5. Default Admin ──────────────────────────────────────────────────
        print("Checking default admin...")
        admin_email = "ramola27041980@gmail.com"
        result = await session.execute(select(Admin).where(Admin.email == admin_email))
        existing_admin = result.scalar_one_or_none()
        
        if not existing_admin:
            new_admin = Admin(
                full_name="HABS Admin",
                email=admin_email,
                hashed_password=get_password_hash("habsadmin@120008")
            )
            session.add(new_admin)
            await session.commit()
            print(f"✅ Admin created: {admin_email}")
        else:
            print("Admin already exists, skipping")

    print("\n✅ Seed complete.")
    await close_db()


if __name__ == "__main__":
    asyncio.run(seed())
