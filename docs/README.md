# HABS — Healthcare Appointment Booking System

A full-stack web application for online doctor appointment booking with ML-powered no-show risk prediction.

---

## Overview

HABS reduces patient no-shows by predicting risk at booking time using a trained Random Forest model. Doctors get real-time visibility into their schedule and no-show likelihood per patient, while patients can book, cancel, and receive automated email confirmations (with PDF) — all through a role-based web interface.

**Stack:** FastAPI · PostgreSQL · React 19 · scikit-learn  
**Auth:** OTP email verification + JWT (HS256)  
**Notifications:** SMTP email with PDF attachment via Brevo SMTP relay  

---

## Features

### P0 — Core (Implemented)
- OTP-based email verification for patient/doctor registration
- Patient login, appointment booking and cancellation
- Doctor dashboard with daily schedule and per-patient no-show risk scores
- Admin dashboard: approve/reject doctor accounts, view stats
- ML no-show risk prediction at booking time (score stored in `ml_predictions`)
- Slot conflict protection via `UNIQUE(doctor_id, appointment_date, time_slot)` constraint
- Email confirmation with PDF attachment on successful booking

### P1 — Should Have
- SMS/email reminders triggered by risk score thresholds
- Patient appointment history view (implemented)
- Admin user management (approve/deactivate)

### P2 — Nice to Have
- Analytics dashboard
- Doctor fee management
- Reschedule flow

### Out of Scope (v1)
- Payment gateway
- Mobile app
- Real-time video consultation

---

## Tech Stack

| Layer | Technology | Version | Status |
|-------|-----------|---------|--------|
| Frontend | React.js | 19.x | ✅ |
| Router | React Router DOM | 6.x | ✅ |
| HTTP Client | Axios | 1.x | ✅ |
| Build Tool | Vite | 8.x | ✅ |
| Backend | FastAPI | 0.110.x | ✅ |
| Language | Python | 3.11+ | ✅ |
| ORM | SQLAlchemy | 2.x (async) | ✅ |
| Migrations | Alembic | 1.x | ✅ |
| Database | PostgreSQL | 15.x | ✅ |
| ML | scikit-learn | 1.x | ✅ |
| Serialization | joblib | 1.x | ✅ |
| Explainability | SHAP | 0.44.x | ✅ |
| Auth | JWT (python-jose) | 3.x | ✅ |
| Email | Brevo SMTP relay | — | ✅ |
| PDF Generation | reportlab | — | ✅ |
| Settings | pydantic-settings | 2.x | ✅ |

---

## Architecture

```
Browser
  └── React 19 (Axios)
        └── FastAPI (Uvicorn)
              ├── /auth          → JWT + OTP email verification
              ├── /appointments  → PostgreSQL (SQLAlchemy async) + ML inference
              ├── /slots         → PostgreSQL availability grid
              ├── /doctor        → Doctor dashboard + status updates
              ├── /admin         → Admin CRUD + doctor approval
              ├── /patient       → Patient onboarding profile
              └── /predict       → joblib RF model → ml_predictions table
```

### Request Lifecycle
```
Browser → React (Axios) → FastAPI Router →
Pydantic validation → AsyncSession (SQLAlchemy) →
PostgreSQL → Response
```

### ML Inference Lifecycle
```
Booking features → FastAPI /appointments POST →
joblib.load() [loaded at startup] → RF model →
float (0.0–1.0) → ml_predictions table (JSONB)
```

---

## Database Schema

Eight tables managed via SQLAlchemy ORM and Alembic migrations.

| Table | Purpose |
|-------|---------|
| `users` | All patients (ML feature flags stored here) |
| `doctors` | Doctor profiles with verification status |
| `admins` | System administrators |
| `appointments` | Every booking record with risk score |
| `time_slots` | Available slots per doctor (pre-generated) |
| `notifications` | Outbound SMS/email/push records |
| `ml_predictions` | No-show risk scores + input features (JSONB) |
| `otp_verifications` | Temporary OTP codes for email verification |

Key constraint: `UNIQUE(doctor_id, appointment_date, time_slot)` on `appointments` prevents double booking.

---

## App Flow

### Auth
```
Landing → Register (OTP sent to email) → Verify OTP → JWT issued → Role redirect
                                                                  ├── Patient Dashboard
                                                                  ├── Doctor Dashboard (pending approval)
                                                                  └── Admin Dashboard
```

### Patient Booking
```
Dashboard → Select Doctor + Date → Pick Slot →
Confirm Booking → ML risk predicted → Email + PDF sent →
Risk stored in ml_predictions
```

### Doctor Onboarding
```
Register (with DOCTOR_INVITE_CODE) → OTP verify →
Account in "pending" state → Admin approves →
Email notification → Can now login
```

---

## Getting Started

See [`RUN_INSTRUCTIONS.md`](./RUN_INSTRUCTIONS.md) for the complete step-by-step setup guide.

Quick start:

```bash
# Backend
cd backend
$env:PYTHONPATH=(Get-Item .).FullName   # PowerShell
alembic upgrade head
python -m habs_db.seed
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

---

## API Endpoints

See [`API_REFERENCE.md`](./API_REFERENCE.md) for the full reference. Quick overview:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/send-otp` | Send OTP to email |
| POST | `/auth/verify-otp` | Verify OTP and complete registration |
| POST | `/auth/login` | Login and receive JWT |
| POST | `/auth/admin/login` | Admin login |
| GET | `/appointments/slots` | Available slots by doctor and date |
| POST | `/appointments` | Book an appointment |
| GET | `/appointments` | Get patient's appointments |
| PATCH | `/appointments/{id}/cancel` | Cancel an appointment |
| GET | `/doctor/list` | List all active doctors |
| GET | `/doctor/dashboard` | Doctor's appointments + risk scores |
| PATCH | `/doctor/{id}/status` | Update appointment status |
| POST | `/patient/onboarding` | Update patient health profile |
| GET | `/admin/stats` | Platform statistics |
| GET | `/admin/pending-doctors` | Doctors awaiting approval |
| PATCH | `/admin/doctors/{id}/approve` | Approve doctor |
| PATCH | `/admin/doctors/{id}/reject` | Reject doctor with reason |

---

## Security

- **JWT:** HS256, 1440-minute (24hr) access token
- **Passwords:** bcrypt hashed via passlib
- **Registration:** OTP email verification required
- **Doctor gating:** Invite code required + admin approval
- **SQL Injection:** Prevented by SQLAlchemy ORM (no raw SQL in application code)
- **Input Validation:** Pydantic schemas enforced on all endpoints
- **CORS:** Configured per `FRONTEND_ORIGIN` env var

---

## ML Model

- **Algorithm:** Random Forest (scikit-learn)
- **Output:** No-show risk score between 0.0 and 1.0
- **Threshold:** 0.4 (configurable via `ML_THRESHOLD` env var)
- **Explainability:** SHAP values available
- **Loading:** Model loaded once at FastAPI startup via `joblib.load()`
- **Fallback:** If model unavailable, booking proceeds with NULL risk score

See [`ML_MODEL.md`](./ML_MODEL.md) for full model documentation.

---

## Team

| Member | Role |
|--------|------|
| Sonam Kumari | Frontend (React) |
| Satyam Katiyar | Backend (FastAPI, Auth, APIs) |
| Chandan Singh | ML + Database (SQLAlchemy, scikit-learn) |
| Jiya Kumari | Backend support + API integration |

---

## Implementation Status

- [x] RF model trained and saved (joblib)
- [x] SQLAlchemy ORM models written (8 tables)
- [x] Alembic migrations written
- [x] JWT auth implemented (OTP-based registration)
- [x] Core booking API with ML inference
- [x] Doctor dashboard with risk scores
- [x] Admin approval workflow
- [x] Email confirmation with PDF attachment
- [x] Frontend connected to backend
- [ ] SMS reminders via Twilio
- [ ] Analytics dashboard
- [ ] Reschedule flow

---

## License

This project is built for educational/demo purposes. License TBD.
