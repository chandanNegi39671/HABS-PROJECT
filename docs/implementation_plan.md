# HABS — Implementation Plan

## Team

| Member | Role |
|--------|------|
| Sonam Kumari | Frontend (React) |
| Satyam Katiyar | Backend (FastAPI, Auth, APIs) |
| Chandan Singh | ML + Database (SQLAlchemy, scikit-learn) |
| Jiya Kumari | Backend support + API integration |

---

## Current State (as of May 2026)

| Component | Status | Owner |
|-----------|--------|-------|
| RF model trained + joblib saved | ✅ Done | Chandan |
| SQLAlchemy ORM models (8 tables) | ✅ Done | Chandan |
| Alembic migrations written + run | ✅ Done | Chandan |
| OTP registration flow | ✅ Done | Satyam |
| JWT auth (login, admin login) | ✅ Done | Satyam |
| Booking API + ML inference wired | ✅ Done | Satyam + Chandan |
| Email + PDF confirmation | ✅ Done | Satyam |
| Doctor dashboard with risk badges | ✅ Done | Sonam |
| Admin approval workflow | ✅ Done | Jiya + Satyam |
| Frontend connected to backend | ✅ Done | Sonam |

---

## Completed Sprint Summary

### Sprint 1 — DB Foundation
- Alembic migrations run; all 8 tables created with indexes and constraints
- Seed script: 5 doctors, 3 patients, 30 days of time slots, sample appointments
- FastAPI project structure with pydantic-settings config

### Sprint 2 — Auth + ML Integration
- OTP email verification via Brevo SMTP
- JWT auth (register, verify-otp, login, admin login)
- joblib model loaded at FastAPI startup via lifespan
- `/appointments POST` triggers ML inference + stores in `ml_predictions`

### Sprint 3 — Core APIs
- `GET /appointments/slots` — available slots by doctor + date
- `POST /appointments` — book with conflict guard + ML + email PDF
- `PATCH /appointments/{id}/cancel` — cancellation + slot restore
- `GET /doctor/dashboard` — full schedule + risk scores
- `PATCH /doctor/{id}/status` — mark completed/no_show/cancelled
- `GET /doctor/list` — public list of active doctors
- Admin CRUD: stats, pending list, approve, reject

### Sprint 4 — Frontend
- All pages implemented: Landing, Login, Register (OTP), Onboarding, PatientDashboard, DoctorDashboard, AdminLogin, AdminDashboard
- Axios interceptors for JWT + X-User-Id injection + 401 redirect
- PrivateRoute auth guard with role checking

---

## Technical Debt

| Task | Priority | Notes |
|------|----------|-------|
| Wire JWT `Depends(get_current_user)` uniformly in appointments/doctor routes | High | Currently using `X-User-Id` header manually |
| Move `send_email` to a shared utility module | Medium | Currently duplicated in `auth.py` and `admin.py` |
| Add missing Doctor FK relationship from `users` table | Medium | IDs are matched by convention, not FK |
| Add pagination to `GET /doctor/dashboard` | Low | Could be slow with many appointments |
| Unit tests for API endpoints (pytest + httpx) | High | None currently written |
| ML model validation (AUC-ROC, confusion matrix review) | Medium | Training artifacts exist |

---

## Dependency Map

```
DB live ──────────────────────────────────────────────────── Done
  └── Auth APIs ─────────────────────────────────────────── Done
        └── Core APIs ────────────────────────────────────── Done
              └── Frontend integration ─────────────────── Done
                    └── Deploy ──────────────────────── Pending

ML /predict ──────────────────────────────────────────────── Done
  └── Risk on dashboard ───────────────────────────────── Done
```

---

## Definition of Done

- [x] All DB tables migrated and seeded
- [x] Auth working (OTP register / login / JWT)
- [x] Booking flow works end-to-end
- [x] ML risk score visible on doctor dashboard
- [x] Admin approval workflow functional
- [x] Email confirmation with PDF
- [ ] Deployed and accessible via public URL