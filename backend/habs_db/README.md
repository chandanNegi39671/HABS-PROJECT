# HABS Database Handler — Architecture & Usage

## Structure

```
habs_db/
├── models.py                    # SQLAlchemy ORM — all 6 tables
├── database.py                  # Async engine, session factory, FastAPI dep
├── settings.py                  # Pydantic-settings config
├── uow.py                       # Unit of Work — atomic multi-repo transactions
├── seed.py                      # 5 doctors / 3 patients / 30d slots
├── schemas/
│   └── ml_input.py              # JSONB feature schema + validator
├── repositories/
│   ├── base.py                  # Generic CRUD + soft-delete
│   ├── users.py                 # + get_ml_flags()
│   ├── doctors.py               # + list_active(specialization)
│   ├── appointments.py          # ★ double-booking guard, dashboard, ML agg
│   ├── time_slots.py            # + bulk_generate(), availability_summary()
│   ├── notifications.py         # + mark_sent/failed, create_sms_reminder
│   └── ml_predictions.py        # + validate → record, prediction_stats()
└── migrations/
    ├── env.py                   # Alembic async env
    └── versions/
        └── 001_initial_schema.py
```

## Key Integrity Rules

| Rule | Enforcement |
|------|-------------|
| No hard deletes (users/doctors) | `is_active=False` via `soft_delete()` |
| No hard deletes (appointments) | `status` transitions only |
| Double-booking guard | `UNIQUE(doctor_id, appointment_date, time_slot)` |
| Risk score range | `CHECK(no_show_risk IS NULL OR 0 ≤ x ≤ 1)` |
| ML features valid before insert | `validate_ml_input()` → then DB CHECK |
| Slot booking idempotent | `INSERT … ON CONFLICT DO NOTHING` |

## Critical Indexes

| Index | Query it serves |
|-------|----------------|
| `ix_appointments_doctor_date` | Doctor dashboard (today + 7 days) |
| `ix_appointments_patient_status` | ML feature aggregation (no N+1) |
| `uq_doctor_date_slot` | Double-booking conflict arbiter |
| `uq_doctor_slot` | Slot bulk-generate conflict arbiter |
| `ix_ml_predictions_predicted_label` | High-risk batch outreach |

## FastAPI Integration

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from habs_db.database import init_db, close_db
from habs_db.settings import get_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(get_settings())
    yield
    await close_db()

app = FastAPI(lifespan=lifespan)
```

```python
# Endpoint using Unit of Work
from habs_db.uow import UnitOfWork, get_uow

@router.post("/appointments")
async def book(data: BookRequest, uow: UnitOfWork = Depends(get_uow)):
    async with uow:
        appt = Appointment(...)
        await uow.appointments.book(appt)           # conflict-safe
        await uow.time_slots.mark_unavailable(...)  # atomic
        await uow.notifications.create_sms_reminder(...)
        # auto-commit on clean exit
```

## Running Migrations

```bash
# First time
alembic upgrade head

# Autogenerate after model changes
alembic revision --autogenerate -m "add_field_xyz"
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Seeding

```bash
python -m habs_db.seed
```

## ML Model Integration

The model (habs_noshow_v1, threshold=0.4, AUC=0.616) generates a prediction
after every booking. Features are validated, stored as JSONB, and the risk
score is written back to `appointments.no_show_risk`.

Top SHAP features stored in `input_features`:
1. `Age`                   (dominant — SHAP + MDI)
2. `lead_time_days`        (dominant — SHAP + MDI)
3. `patient_age_group_enc`
4. `sms_reminder_sent`
5. `appointment_hour`

High-recall design (recall=0.86, precision=0.31 at threshold=0.4) means
~76% of flagged appointments will be false positives — size your outreach
batch jobs and notification budgets accordingly.
