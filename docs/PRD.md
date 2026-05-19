# HABS — Product Requirements Document

## Overview

**Product:** Healthcare Appointment Booking System (HABS)  
**Stack:** FastAPI + PostgreSQL + React 19 + scikit-learn  
**Status:** Core features implemented and integrated

---

## Goals

- Reduce patient no-shows via ML-powered risk prediction
- Enable online doctor appointment booking with email confirmation
- Provide doctor visibility into daily schedule and no-show risk per patient
- Admin-controlled doctor onboarding with approval workflow

## Non-Goals

- No payment gateway (v1)
- No mobile app (web only)
- No real-time video consultation

---

## User Personas

| Role | Pain Point | Solution |
|------|-----------|---------|
| Patient | Can't book easily, forgets appointments | Online booking + email PDF confirmation |
| Doctor | Wastes time on no-shows, no schedule visibility | Dashboard with ML risk score per patient |
| Admin | No central control over doctor accounts | Approve/reject workflow with email notifications |

---

## Feature List

### P0 — Must Have (Implemented)
- Patient: OTP email verification → Register → Login → Book/Cancel appointment
- Doctor: Register with invite code → Admin approval → Login → View daily schedule → Mark attendance
- Admin: Login → Approve/reject doctors → View platform stats
- ML: Predict no-show risk at booking → store in `ml_predictions` → display on doctor dashboard
- DB: Slot conflict guard (`UNIQUE` constraint)
- Email: PDF confirmation sent on successful booking

### P1 — Should Have
- Patient appointment history (implemented — GET /appointments)
- Admin user management (approve/deactivate)

---

## User Stories

**Patient:**
- As a patient, I want to register with OTP email verification so my account is secure
- As a patient, I want to book an available time slot with a doctor
- As a patient, I want to receive an email confirmation with appointment details as a PDF
- As a patient, I want to cancel an appointment if my plans change

**Doctor:**
- As a doctor, I want to see my daily schedule with patient names and no-show risk scores
- As a doctor, I want to mark appointments as attended, no-show, or cancelled
- As a doctor registering, I want to know if my account is pending admin approval

**Admin:**
- As an admin, I want to review and approve/reject pending doctor registrations
- As an admin, I want a statistics overview of the platform

---

## Acceptance Criteria (P0)

| Feature | Criteria |
|---------|---------|
| Registration | OTP verified before account created; doctor invite code validated |
| Booking | Slot locks on confirm; duplicate blocked by `UNIQUE(doctor_id, appointment_date, time_slot)` |
| ML Prediction | Risk score (0.0–1.0) stored in `ml_predictions` within booking request; fallback if model unavailable |
| Auth | JWT issued on login; role-based redirect (`patient/doctor/admin`) |
| Doctor approval | Doctor cannot login until admin sets `verification_status = "approved"` |
| Email confirmation | PDF attachment sent on booking success |

---

## KPIs

| Metric | Target |
|--------|--------|
| No-show rate reduction | 20% |
| Booking completion rate | > 85% |
| ML prediction latency | < 5ms on CPU |
| OTP delivery | < 30 seconds |

---

## Risks

| Risk | Mitigation |
|------|-----------|
| ML model unavailable | Booking proceeds with `no_show_risk = NULL`; fallback is logged |
| DB migration conflicts | `alembic upgrade head` is idempotent; enum-exists error is safe to ignore |
| Double booking race condition | `UNIQUE(doctor_id, appointment_date, time_slot)` enforced at DB level |
| Email delivery failure | SMTP errors caught and logged; `dev_otp` returned in OTP response during dev |
| Doctor invite code leaked | Code is env-var configurable; admin approval is a second gate |

---

## Implementation Status

| Feature | Status |
|---------|--------|
| RF model trained and saved (joblib) | ✅ |
| SQLAlchemy ORM models (8 tables) | ✅ |
| Alembic migrations | ✅ |
| OTP registration flow | ✅ |
| JWT auth | ✅ |
| Booking API with ML inference | ✅ |
| Email + PDF confirmation | ✅ |
| Doctor dashboard with risk | ✅ |
| Admin approval workflow | ✅ |
| Frontend connected to backend | ✅ |