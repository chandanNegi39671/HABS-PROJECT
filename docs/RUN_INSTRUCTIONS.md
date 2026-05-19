# HABS — Complete Run Instructions

This document contains all commands required to set up and run the HABS appointment booking system.

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 15+**
- **Node.js 18+** with npm
- **Git** (optional)

```powershell
python --version     # 3.11+
node --version       # 18+
npm --version        # 8+
```

---

## Step 1: PostgreSQL Setup

### 1.1 Start PostgreSQL

```powershell
# Check if running
Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue

# Start if needed
Start-Service postgresql-x64-18   # adjust version number
```

### 1.2 Create User and Database

```powershell
psql -U postgres -h localhost
```

In psql:
```sql
CREATE USER habs WITH PASSWORD 'polpol';
CREATE DATABASE habs_db OWNER habs;
\q
```

---

## Step 2: Backend Setup

### 2.1 Configure Environment Variables

```powershell
cd backend
Copy-Item .env.example .env
```

Ensure `backend/.env` contains:
```env
POSTGRES_USER=habs
POSTGRES_PASSWORD=polpol
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=habs_db
SECRET_KEY=habs_local_secret_change_me
FRONTEND_ORIGIN=http://localhost:5173
ML_MODEL_PATH=model/habs_noshow_model_v1.joblib
ML_MODEL_VERSION=habs_noshow_v1
ML_THRESHOLD=0.4
DOCTOR_INVITE_CODE=HABS-DOCTOR-2026
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USER=<your-brevo-user>
EMAIL_PASSWORD=<your-brevo-key>
EMAIL_FROM=<your-from-address>
```

### 2.2 Install Backend Dependencies

```powershell
cd backend
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## Step 3: Database Migrations and Seeding

### 3.1 Run Alembic Migrations

```powershell
cd backend
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema
INFO  [alembic.runtime.migration] Running upgrade 001 -> 9143d94f242b_full_update
```

If you get `type "appointment_status_enum" already exists`, the migration is already applied — safe to ignore.

### 3.2 Seed Sample Data

```powershell
python -m habs_db.seed
```

Seeds: 5 doctors, 3 patients, 30 days of time slots, sample appointments.

Expected output:
```
Seeding doctors...
  [+] Dr. Priya Sharma (Cardiology)
  ...
✅ Seed complete.
```

---

## Step 4: Start the Backend

Open a **new terminal** and run:

```powershell
cd backend
$env:PYTHONPATH=(Get-Item .).FullName
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Expected output:
```
ML Model loaded from ...\backend\ml\model/habs_noshow_model_v1.joblib
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

URLs:
- **API:** http://127.0.0.1:8000
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

---

## Step 5: Start the Frontend

Open a **second terminal**:

```powershell
cd frontend
npm install       # first time only
npm run dev
```

Expected output:
```
VITE v8.x  ready in X ms
➜  Local:   http://127.0.0.1:5173/
```

---

## Step 6: Verify

```powershell
# Backend health check
Invoke-WebRequest -Uri 'http://127.0.0.1:8000/' -UseBasicParsing
# Expected: {"message":"Welcome to HABS API"}
```

Open http://127.0.0.1:5173 — landing page should load.

---

## Quick Reference — All Commands

**Terminal 1 — Backend:**
```powershell
cd backend
$env:PYTHONPATH=(Get-Item .).FullName
alembic upgrade head
python -m habs_db.seed
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — Frontend:**
```powershell
cd frontend
npm install
npm run dev
```

**Admin Access:**
- URL: http://localhost:5173/admin/login
- Email: ramola27041980@gmail.com
- Password: habsadmin@120008

**Doctor Invite Code:** `HABS-DOCTOR-2026`

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `could not connect to server` | PostgreSQL not running | `Start-Service postgresql-x64-18` |
| `password authentication failed for user "habs"` | Wrong `.env` password | Verify `POSTGRES_PASSWORD=polpol` in `.env` |
| `type "appointment_status_enum" already exists` | Migration re-run | Safe to ignore — migrations are idempotent |
| `ML Model not found` | Missing joblib file | Ensure `backend/ml/model/habs_noshow_model_v1.joblib` exists |
| `ModuleNotFoundError: No module named 'habs_db'` | PYTHONPATH not set | Run `$env:PYTHONPATH=(Get-Item .).FullName` from `backend/` |
| `Address already in use` (port 8000) | Another process on port | `Get-Process \| Where-Object {$_.Name -like '*python*'} \| Stop-Process` |
| CORS error in browser | Wrong FRONTEND_ORIGIN | Set `FRONTEND_ORIGIN=http://localhost:5173` in `.env`, restart backend |

---

## Project Structure Reference

```
HABS-project/
├── backend/
│   ├── .env                          # Environment variables
│   ├── .env.example                  # Config template
│   ├── requirements.txt              # Python dependencies
│   ├── alembic.ini                   # Alembic config
│   ├── main.py                       # FastAPI app entry + lifespan
│   ├── security.py                   # JWT + bcrypt + get_current_user
│   ├── api/
│   │   ├── auth.py                   # OTP, register, login, admin login
│   │   ├── appointments.py           # Slots, book, list, cancel
│   │   ├── doctor.py                 # Doctor list, dashboard, status update
│   │   ├── patient.py                # Patient onboarding
│   │   ├── admin.py                  # Admin stats, approve/reject doctors
│   │   └── schemas.py                # Pydantic request/response models
│   ├── habs_db/
│   │   ├── models.py                 # SQLAlchemy ORM (8 tables)
│   │   ├── settings.py               # pydantic-settings config
│   │   ├── seed.py                   # Seed script
│   │   ├── ml_predictions.py         # ML prediction repository
│   │   ├── repositories/             # Data access layer per entity
│   │   │   ├── base.py
│   │   │   ├── users.py
│   │   │   ├── doctors.py
│   │   │   ├── appointments.py
│   │   │   ├── time_slots.py
│   │   │   ├── notifications.py
│   │   │   └── database.py
│   │   ├── schemas/
│   │   │   └── ml_input.py           # ML feature vector JSON schema validator
│   │   └── migrations/
│   │       └── versions/             # Alembic migration files
│   └── ml/
│       ├── model/habs_noshow_model_v1.joblib  # Trained RF model
│       ├── habs_kaggle_final.py      # Training pipeline
│       ├── habs_model_card.txt       # Model card
│       └── artifacts/                # ROC, SHAP, feature importance plots
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx                   # Router + PrivateRoute + Navbar
│       ├── api.js                    # Axios client with interceptors
│       ├── main.jsx                  # React 19 entry point
│       └── pages/
│           ├── LandingPage.jsx
│           ├── Login.jsx
│           ├── Register.jsx          # OTP-based registration
│           ├── Onboarding.jsx
│           ├── PatientDashboard.jsx
│           ├── DoctorDashboard.jsx
│           ├── AdminLogin.jsx
│           └── AdminDashboard.jsx
└── docs/
    ├── README.md
    ├── API_REFERENCE.md
    ├── RUN_INSTRUCTIONS.md           # THIS FILE
    ├── backend_schema.md
    ├── app_flow.md
    ├── tech_stack.md
    ├── ML_MODEL.md
    ├── PRD.md
```