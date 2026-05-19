# HABS — Tech Stack

## Quick Reference

| Layer | Technology | Version | Status |
|-------|-----------|---------|--------|
| Frontend | React.js | 19.x | ✅ |
| Router | React Router DOM | 6.30.x | ✅ |
| HTTP Client | Axios | 1.8.x | ✅ |
| Icons | lucide-react | 0.513.x | ✅ |
| Build Tool | Vite | 8.x | ✅ |
| Backend | FastAPI | 0.110.x | ✅ |
| Language | Python | 3.11+ | ✅ |
| ORM | SQLAlchemy | 2.x (async) | ✅ |
| Migrations | Alembic | 1.x | ✅ |
| Database | PostgreSQL | 15.x | ✅ |
| DB Driver | asyncpg (async) / psycopg2 (Alembic) | — | ✅ |
| ML | scikit-learn | 1.x | ✅ |
| ML Persistence | joblib | 1.x | ✅ |
| Explainability | SHAP | 0.44.x | ✅ |
| Data Processing | pandas | — | ✅ |
| Auth | JWT — python-jose | 3.x | ✅ |
| Password Hashing | passlib (bcrypt) | — | ✅ |
| Settings | pydantic-settings | 2.x | ✅ |
| Email | Brevo SMTP relay | SMTP port 587 | ✅ |
| PDF Generation | reportlab | — | ✅ |
| Version Control | Git + GitHub | — | ✅ |

---

## Architecture

```
Browser
  └── React 19 (Axios)
        └── FastAPI (Uvicorn, async)
              ├── /auth          → JWT + OTP (python-jose, passlib)
              ├── /appointments  → PostgreSQL via SQLAlchemy async
              ├── /slots         → PostgreSQL
              ├── /doctor        → PostgreSQL
              ├── /admin         → PostgreSQL
              ├── /patient       → PostgreSQL
              └── /predict       → joblib RF model → ml_predictions (JSONB)
```

---

## Request Lifecycle

```
Browser
  → React (Axios interceptor adds Authorization + X-User-Id headers)
  → FastAPI Router
  → Pydantic model validation
  → AsyncSession (SQLAlchemy + asyncpg)
  → PostgreSQL
  → Response JSON
```

## ML Inference Lifecycle

```
Booking request
  → user_repo.get_ml_flags()       [DB: async select users]
  → appt_repo.get_patient_ml_history()  [DB: async aggregate]
  → Build pandas DataFrame (18 features)
  → model.predict_proba(df)[0][1]  [in-process, ~1–3ms]
  → float (0.0–1.0) stored in ml_predictions (JSONB)
```

---

## Frontend Stack Details

| File | Purpose |
|------|---------|
| `src/main.jsx` | React 19 root render |
| `src/App.jsx` | Router + PrivateRoute auth guard + Nav |
| `src/api.js` | Axios instance with JWT + X-User-Id interceptors |
| `src/pages/LandingPage.jsx` | Public landing page |
| `src/pages/Login.jsx` | Patient/doctor login |
| `src/pages/Register.jsx` | OTP-based registration |
| `src/pages/Onboarding.jsx` | Post-registration health profile |
| `src/pages/PatientDashboard.jsx` | View/book/cancel appointments |
| `src/pages/DoctorDashboard.jsx` | Schedule view + risk badges + status updates |
| `src/pages/AdminLogin.jsx` | Admin-only login page |
| `src/pages/AdminDashboard.jsx` | Stats, doctor approval workflow |

---

## Backend Stack Details

| File/Module | Purpose |
|-------------|---------|
| `main.py` | FastAPI app, CORS, lifespan (DB init + ML load) |
| `security.py` | JWT encode/decode, bcrypt, `get_current_user` dependency |
| `api/auth.py` | OTP send/verify, register (legacy), login, admin login |
| `api/appointments.py` | Slots, book, list, cancel |
| `api/doctor.py` | Doctor list, dashboard, status update |
| `api/patient.py` | Onboarding profile update |
| `api/admin.py` | Stats, pending doctors, approve/reject |
| `api/schemas.py` | Pydantic request/response models |
| `habs_db/models.py` | SQLAlchemy ORM (8 tables) |
| `habs_db/settings.py` | pydantic-settings config from `.env` |
| `habs_db/database.py` | Async engine creation |
| `habs_db/repositories/` | Repository pattern per entity |
| `habs_db/ml_predictions.py` | ML prediction repository |
| `habs_db/schemas/ml_input.py` | JSON schema validator for ML features |
| `habs_db/seed.py` | Seed script (5 doctors, 3 patients, 30 days of slots) |
| `habs_db/migrations/` | Alembic migration files |
| `ml/model/habs_noshow_model_v1.joblib` | Trained RF model |
| `ml/habs_kaggle_final.py` | Model training script |

---

## Key Design Decisions

| Choice | Why | Rejected Alternative |
|--------|-----|----------------------|
| FastAPI | Native async, auto Swagger docs, Pydantic | Django REST (sync-heavy, over-engineered for scope) |
| SQLAlchemy 2.x async | True async with `asyncpg`, type-safe ORM | Raw psycopg2 (sync only), Tortoise ORM |
| PostgreSQL | JSONB for ML features, robust UNIQUE/CHECK constraints | MySQL (weaker JSONB support) |
| Random Forest | Best AUC-ROC on no-show dataset, fast inference | XGBoost (marginally better but overkill), deep learning |
| JWT (stateless) | Easy to implement with FastAPI + python-jose | Server-side sessions (stateful, needs Redis) |
| OTP email verification | Prevents fake registrations, doctor gating | Magic link (more complex), no verification |
| Brevo SMTP | Free tier, reliable, no IP warmup | Twilio SendGrid (credit card required), direct SMTP |
| Vite 8 + React 19 | Fastest HMR, latest React features | Create React App (deprecated) |
| pydantic-settings | `.env` file + environment var loading, type coercion | python-dotenv (manual parsing) |
| joblib | scikit-learn standard, fast serialization | pickle (less safe), ONNX (over-engineered) |

---

## Security Architecture

| Concern | Implementation |
|---------|---------------|
| Password storage | bcrypt via passlib (`CryptContext`) |
| Token type | JWT HS256, 24-hour expiry |
| Token transmission | `Authorization: Bearer <token>` header |
| User identification | `X-User-Id` header (injected by Axios) |
| Doctor gating | Invite code + admin approval |
| Input validation | Pydantic schemas on all endpoints |
| SQL injection | SQLAlchemy ORM (no raw SQL in app code) |
| CORS | Configured per `FRONTEND_ORIGIN` env var |
| Admin isolation | Separate `admins` table, separate login endpoint |

---

## Environment Variables

```env
# Database
POSTGRES_USER=habs
POSTGRES_PASSWORD=polpol
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=habs_db

# App
SECRET_KEY=habs_local_secret_change_me
FRONTEND_ORIGIN=http://localhost:5173

# ML
ML_MODEL_PATH=model/habs_noshow_model_v1.joblib
ML_MODEL_VERSION=habs_noshow_v1
ML_THRESHOLD=0.4

# Email (Brevo SMTP)
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USER=<brevo-smtp-user>
EMAIL_PASSWORD=<brevo-smtp-key>
EMAIL_FROM=<from-address>

# Doctor registration gate
DOCTOR_INVITE_CODE=HABS-DOCTOR-2026
```