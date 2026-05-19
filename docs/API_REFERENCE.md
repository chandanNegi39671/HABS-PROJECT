# HABS — API Reference

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs` (Swagger UI) · `http://localhost:8000/redoc`

All authenticated endpoints require the `Authorization: Bearer <token>` header.  
Booking endpoints additionally require `X-User-Id: <user_uuid>` in headers (injected by the Axios interceptor in `api.js`).

---

## Auth — `/auth`

### `POST /auth/send-otp`

Sends a 6-digit OTP to the provided email. Returns `dev_otp` in the response body if the SMTP server is unreachable (development convenience).

**Request body:**
```json
{ "email": "user@example.com" }
```

**Response:**
```json
{ "message": "OTP sent to your email" }
```

**Errors:**
- `400 Email already registered`

---

### `POST /auth/verify-otp`

Verifies OTP and completes registration. Creates the user (and doctor record if `role=doctor`). For patients, returns a JWT immediately. For doctors, returns a "pending approval" message.

**Request body:**
```json
{
  "email": "user@example.com",
  "otp_code": "123456",
  "full_name": "Jane Doe",
  "password": "StrongPass123!",
  "role": "patient",
  "phone": "+91-9876543210",
  "date_of_birth": "1990-05-15",
  "gender": "female",
  "invite_code": null,
  "scholarship": false,
  "hypertension": false,
  "diabetes": false,
  "alcoholism": false,
  "has_chronic_condition": false
}
```

For `role=doctor`, `invite_code` is required and must match `DOCTOR_INVITE_CODE` env var (`HABS-DOCTOR-2026`).

**Response (patient):**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": "<uuid>",
    "email": "user@example.com",
    "role": "patient",
    "full_name": "Jane Doe"
  }
}
```

**Response (doctor):**
```json
{
  "message": "Registration submitted. Awaiting admin approval. You will be notified via email."
}
```

**Errors:**
- `400 OTP not found / OTP already used / OTP expired / Invalid OTP`
- `403 Invalid invite code` (doctor registration)

---

### `POST /auth/login`

Standard email + password login for patients and doctors.

**Request body:**
```json
{ "email": "user@example.com", "password": "StrongPass123!" }
```

**Response:**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": { "id": "<uuid>", "email": "user@example.com", "role": "patient", "full_name": "Jane Doe" }
}
```

**Errors:**
- `401 Incorrect email or password`
- `403 Account under review. Please wait for admin approval.`
- `403 Account rejected. Reason: <reason>`
- `403 Account not active.`

---

### `POST /auth/admin/login`

Admin-only login. Checks the `admins` table (separate from `users`).

**Request body:**
```json
{ "email": "admin@habs.com", "password": "habsadmin@120008" }
```

**Response:** Same Token schema as `/auth/login` with `role: "admin"`.

**Errors:**
- `401 Invalid admin credentials`

---

### `POST /auth/register` *(legacy)*

Direct registration without OTP (kept for backward compatibility / Swagger testing). Creates user and optionally a doctor profile. Returns JWT immediately.

---

## Appointments — `/appointments`

### `GET /appointments/slots`

Returns available time slots for a doctor on a given date, ordered by time.

**Query params:**
- `doctor_id` (UUID, required)
- `slot_date` (date string `YYYY-MM-DD`, required)

**Response:**
```json
[
  { "id": "<uuid>", "time": "09:00" },
  { "id": "<uuid>", "time": "09:30" }
]
```

---

### `POST /appointments`

Books an appointment. Triggers ML inference, stores prediction, and emails a PDF confirmation to the patient.

**Headers required:**
- `Authorization: Bearer <token>`
- `X-User-Id: <patient_uuid>`

**Request body:**
```json
{
  "doctor_id": "<uuid>",
  "appointment_date": "2026-06-01",
  "time_slot": "10:00"
}
```

**Booking logic:**
1. Validates slot exists and `is_available = true`
2. Validates `appointment_date` is not in the past
3. Creates `Appointment` record (status: `booked`)
4. Marks `TimeSlot.is_available = false`
5. Runs ML inference (builds feature vector from patient profile + history)
6. Stores result in `ml_predictions` and updates `Appointment.no_show_risk`
7. Sends email with PDF confirmation

**Response:**
```json
{ "message": "Appointment booked successfully", "appointment_id": "<uuid>" }
```

**Errors:**
- `400 Slot not available`
- `400 Cannot book in the past`
- `409 <conflict message>` (double-booking guard)
- `401 Unauthorized` (missing `X-User-Id` header)

---

### `GET /appointments`

Returns all appointments for the authenticated patient, ordered by date descending.

**Headers required:** `X-User-Id: <patient_uuid>`

**Response:**
```json
[
  {
    "id": "<uuid>",
    "doctor_name": "Dr. Priya Sharma",
    "doctor_spec": "Cardiology",
    "date": "2026-06-01",
    "time": "10:00",
    "status": "booked"
  }
]
```

---

### `PATCH /appointments/{appointment_id}/cancel`

Cancels an appointment and restores the time slot to available.

**Path param:** `appointment_id` (UUID)

**Response:**
```json
{ "message": "Appointment cancelled successfully" }
```

---

## Doctor — `/doctor`

### `GET /doctor/list`

Returns all active (approved) doctors. No authentication required.

**Response:**
```json
[
  {
    "id": "<uuid>",
    "full_name": "Dr. Priya Sharma",
    "specialization": "Cardiology"
  }
]
```

---

### `GET /doctor/dashboard`

Returns all appointments for the authenticated doctor, ordered chronologically, including patient name and ML risk score.

**Headers required:** `X-User-Id: <doctor_uuid>`

**Response:**
```json
[
  {
    "id": "<uuid>",
    "patient": "Ramesh Gupta",
    "date": "2026-06-01",
    "time": "10:00",
    "status": "booked",
    "risk": 0.72
  }
]
```

`risk` is `null` if ML inference was not available at booking time.

---

### `PATCH /doctor/{appointment_id}/status`

Updates appointment status. Used by doctors to mark outcome.

**Query param:** `status` — one of `completed`, `no_show`, `cancelled`

**Response:**
```json
{ "message": "Appointment marked as completed" }
```

**Errors:**
- `400 Invalid status`
- `404 Appointment not found or not in booked state`

---

## Patient — `/patient`

### `POST /patient/onboarding`

Updates the patient's health profile fields used as ML features. Requires JWT (`Authorization` header).

**Request body:**
```json
{
  "date_of_birth": "1990-05-15",
  "gender": "female",
  "blood_group": "O+",
  "diabetes": true,
  "hypertension": false,
  "alcoholism": false,
  "has_chronic_condition": true
}
```

**Response:**
```json
{ "message": "Profile updated" }
```

---

## Admin — `/admin`

All admin endpoints require a valid admin JWT (`Authorization: Bearer <token>` with `role=admin`).

### `GET /admin/stats`

Returns platform-wide counters.

**Response:**
```json
{
  "patients_count": 42,
  "approved_doctors_count": 5,
  "pending_doctors_count": 2,
  "appointments_count": 128,
  "high_risk_appointments_count": 31
}
```

`high_risk_appointments_count` counts appointments with `no_show_risk >= 0.6`.

---

### `GET /admin/pending-doctors`

Returns doctors with `verification_status = "pending"`.

**Response:**
```json
[
  {
    "id": "<uuid>",
    "full_name": "Dr. New Doctor",
    "email": "doc@example.com",
    "phone": "+91-9876543210",
    "created_at": "2026-05-17 10:00:00"
  }
]
```

---

### `GET /admin/all-doctors`

Returns all doctors with verification status and rejection reason.

---

### `PATCH /admin/doctors/{doctor_id}/approve`

Approves a pending doctor. Sets `verification_status = "approved"`, `is_active = true` on both `doctors` and `users` tables, and sends an approval email.

**Response:**
```json
{ "message": "Doctor approved successfully" }
```

---

### `PATCH /admin/doctors/{doctor_id}/reject`

Rejects a pending doctor with a reason. Sends rejection email.

**Request body:**
```json
{ "reason": "Credentials could not be verified." }
```

**Response:**
```json
{ "message": "Doctor rejected" }
```

---

## Root

### `GET /`

Health check.

**Response:**
```json
{ "message": "Welcome to HABS API" }
```

---

## Error Format

FastAPI returns errors in the standard format:
```json
{ "detail": "Error message here" }
```

Validation errors (422 Unprocessable Entity) include field-level detail:
```json
{
  "detail": [
    { "loc": ["body", "email"], "msg": "value is not a valid email address", "type": "value_error.email" }
  ]
}
```

---

## Authentication Flow Summary

```
Registration:
  POST /auth/send-otp  →  POST /auth/verify-otp  →  JWT returned (patients)
                                                   →  "pending" message (doctors)

Login:
  POST /auth/login     →  JWT returned

Admin:
  POST /auth/admin/login  →  JWT returned

Token usage:
  Authorization: Bearer <jwt>
  X-User-Id: <uuid>    (injected by api.js interceptor for booking/dashboard routes)
```