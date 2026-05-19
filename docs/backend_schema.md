# HABS — Backend Schema

All models are in `backend/habs_db/models.py` using SQLAlchemy 2.x declarative ORM with async session support.

---

## Tables Overview

| Table | SQLAlchemy Model | Purpose |
|-------|-----------------|---------|
| `users` | `User` | Patients — stores auth + ML feature flags |
| `doctors` | `Doctor` | Doctor profiles + verification workflow |
| `admins` | `Admin` | Platform administrators |
| `appointments` | `Appointment` | Every booking record |
| `time_slots` | `TimeSlot` | Pre-generated availability grid |
| `notifications` | `Notification` | Outbound SMS / email / push records |
| `ml_predictions` | `MLPrediction` | No-show risk score + input features (JSONB) |
| `otp_verifications` | `OTPVerification` | Temporary OTP codes for email verification |

---

## Schema Definitions

### `users`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK, `default=uuid4` |
| `full_name` | VARCHAR(255) | NOT NULL |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL |
| `phone` | VARCHAR(20) | nullable |
| `hashed_password` | VARCHAR(255) | NOT NULL (bcrypt) |
| `date_of_birth` | DATE | nullable |
| `gender` | VARCHAR(10) | nullable |
| `is_email_verified` | BOOLEAN | DEFAULT false |
| `scholarship` | BOOLEAN | DEFAULT false — ML feature |
| `hypertension` | BOOLEAN | DEFAULT false — ML feature |
| `diabetes` | BOOLEAN | DEFAULT false — ML feature |
| `alcoholism` | BOOLEAN | DEFAULT false — ML feature |
| `has_chronic_condition` | BOOLEAN | DEFAULT false — ML feature |
| `is_active` | BOOLEAN | DEFAULT true (soft-delete) |
| `created_at` | TIMESTAMPTZ | server_default now() |
| `updated_at` | TIMESTAMPTZ | server_default now(), onupdate |

**Indexes:** `ix_users_email`, `ix_users_is_active`

---

### `doctors`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK — **shared with `users.id`** for doctor accounts |
| `full_name` | VARCHAR(255) | NOT NULL |
| `specialization` | VARCHAR(100) | NOT NULL |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL |
| `phone` | VARCHAR(20) | nullable |
| `is_active` | BOOLEAN | DEFAULT true |
| `verification_status` | VARCHAR(20) | DEFAULT `"pending"` → `"approved"` / `"rejected"` |
| `rejection_reason` | TEXT | nullable |
| `created_at` | TIMESTAMPTZ | server_default now() |
| `updated_at` | TIMESTAMPTZ | server_default now(), onupdate |

**Indexes:** `ix_doctors_specialization`, `ix_doctors_is_active`

**Note:** When a doctor registers, both a `users` row and a `doctors` row are created, sharing the same UUID as their primary key. The `Doctor.id` is not a FK — it is set to match `User.id` at creation time.

---

### `admins`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK, `default=uuid4` |
| `full_name` | VARCHAR(255) | NOT NULL |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL |
| `hashed_password` | VARCHAR(255) | NOT NULL |
| `created_at` | TIMESTAMPTZ | server_default now() |

Admin accounts are seeded directly in the database; there is no self-registration flow for admins.

---

### `appointments`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK, `default=uuid4` |
| `patient_id` | UUID | FK → `users.id` RESTRICT |
| `doctor_id` | UUID | FK → `doctors.id` RESTRICT |
| `appointment_date` | DATE | NOT NULL |
| `time_slot` | VARCHAR(10) | NOT NULL (`"09:00"`) |
| `appointment_hour` | INTEGER | NOT NULL, CHECK 0–23 |
| `lead_time_days` | INTEGER | NOT NULL, CHECK ≥ 0 |
| `status` | ENUM | `booked/completed/cancelled/no_show`, DEFAULT `booked` |
| `no_show_risk` | FLOAT | nullable, CHECK 0.0–1.0 |
| `sms_reminder_sent` | BOOLEAN | DEFAULT false |
| `notes` | TEXT | nullable |
| `booked_at` | TIMESTAMPTZ | server_default now() |
| `updated_at` | TIMESTAMPTZ | server_default now(), onupdate |

**Unique constraint:** `uq_doctor_date_slot` — `(doctor_id, appointment_date, time_slot)` — prevents double booking at DB level.

**Check constraints:**
- `ck_no_show_risk_range`: `no_show_risk IS NULL OR (0.0 <= no_show_risk <= 1.0)`
- `ck_lead_time_positive`: `lead_time_days >= 0`
- `ck_appointment_hour_range`: `0 <= appointment_hour <= 23`

**Indexes:** `ix_appointments_patient_id`, `ix_appointments_doctor_id`, `ix_appointments_status`, `ix_appointments_doctor_date` (composite), `ix_appointments_patient_status` (composite), `ix_appointments_booked_at`

---

### `time_slots`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK, `default=uuid4` |
| `doctor_id` | UUID | FK → `doctors.id` CASCADE |
| `slot_date` | DATE | NOT NULL |
| `slot_time` | VARCHAR(10) | NOT NULL (`"09:00"`) |
| `is_available` | BOOLEAN | DEFAULT true |
| `created_at` | TIMESTAMPTZ | server_default now() |

**Unique constraint:** `uq_doctor_slot` — `(doctor_id, slot_date, slot_time)`

**Indexes:** `ix_time_slots_doctor_date` (composite), `ix_time_slots_available` (`is_available`, `slot_date`)

---

### `notifications`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK, `default=uuid4` |
| `user_id` | UUID | FK → `users.id` RESTRICT |
| `appointment_id` | UUID | FK → `appointments.id` SET NULL, nullable |
| `type` | ENUM | `sms/email/push` |
| `status` | ENUM | `pending/sent/failed`, DEFAULT `pending` |
| `message` | TEXT | NOT NULL |
| `sent_at` | TIMESTAMPTZ | nullable |
| `created_at` | TIMESTAMPTZ | server_default now() |

**Indexes:** `ix_notifications_user_id`, `ix_notifications_appointment_id`, `ix_notifications_status`, `ix_notifications_created_at`

---

### `ml_predictions`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK, `default=uuid4` |
| `appointment_id` | UUID | FK → `appointments.id` CASCADE, UNIQUE (1:1) |
| `model_version` | VARCHAR(50) | NOT NULL, DEFAULT `"habs_noshow_v1"` |
| `no_show_probability` | FLOAT | NOT NULL, CHECK 0.0–1.0 |
| `predicted_label` | BOOLEAN | NOT NULL (`true` = predicted no-show) |
| `threshold_used` | FLOAT | NOT NULL, DEFAULT 0.4, CHECK 0.0–1.0 |
| `input_features` | JSONB | NOT NULL — full feature vector snapshot |
| `created_at` | TIMESTAMPTZ | server_default now() |

**Check constraints:**
- `ck_no_show_prob_range`
- `ck_threshold_range`

**Indexes:** `ix_ml_predictions_appointment_id`, `ix_ml_predictions_predicted_label`, `ix_ml_predictions_model_version`

---

### `otp_verifications`

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK, `default=uuid4` |
| `email` | VARCHAR(255) | NOT NULL |
| `otp_code` | VARCHAR(6) | NOT NULL |
| `expires_at` | TIMESTAMPTZ | NOT NULL (10 minutes from creation) |
| `is_used` | BOOLEAN | DEFAULT false |
| `created_at` | TIMESTAMPTZ | server_default now() |

**Indexes:** `ix_otp_email`

---

## Enums

```python
class AppointmentStatus(str, enum.Enum):
    BOOKED    = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW   = "no_show"

class NotificationType(str, enum.Enum):
    SMS   = "sms"
    EMAIL = "email"
    PUSH  = "push"

class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT    = "sent"
    FAILED  = "failed"
```

---

## ER Relationships

```
users (1) ─────────── (many) appointments  [patient_id FK]
users (1) ─────────── (many) notifications [user_id FK]

doctors (1) ────────── (many) appointments  [doctor_id FK]
doctors (1) ────────── (many) time_slots    [doctor_id FK]

appointments (1) ────── (1)    ml_predictions [appointment_id FK, UNIQUE]
appointments (1) ────── (many) notifications  [appointment_id FK, nullable]
```

---

## Key Queries

### Available slots for a doctor on a date
```sql
SELECT id, slot_time FROM time_slots
WHERE doctor_id = $1
  AND slot_date = $2
  AND is_available = true
ORDER BY slot_time;
```
Index used: `ix_time_slots_doctor_date`

### Patient no-show history (ML feature)
```sql
SELECT
  COUNT(*) AS prior_appointment_count,
  SUM(CASE WHEN status = 'no_show' THEN 1 ELSE 0 END) AS prior_no_show_count
FROM appointments
WHERE patient_id = $1;
```
Index used: `ix_appointments_patient_status`

### Doctor dashboard
```sql
SELECT a.*, u.full_name AS patient_name, a.no_show_risk
FROM appointments a
JOIN users u ON a.patient_id = u.id
WHERE a.doctor_id = $1
ORDER BY a.appointment_date ASC, a.time_slot ASC;
```
Index used: `ix_appointments_doctor_date`

### High-risk predictions (admin/analytics)
```sql
SELECT * FROM ml_predictions
WHERE predicted_label = TRUE
  AND model_version = 'habs_noshow_v1'
  AND no_show_probability >= 0.4
ORDER BY no_show_probability DESC
LIMIT 1000;
```
Indexes used: `ix_ml_predictions_predicted_label`, `ix_ml_predictions_model_version`

---

## Migration Status

```bash
# Apply all migrations
alembic upgrade head

# Check current revision
alembic current

# View migration history
alembic history
```

Migration files are in `backend/habs_db/migrations/versions/`. The current head migration is `9143d94f242b_full_update.py`.