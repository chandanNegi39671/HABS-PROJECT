# HABS — App Flow

## Auth Flow

### Patient Registration
```
Landing Page
  → "Register" → /register
  → Fill form (name, email, password, health flags)
  → POST /auth/send-otp  → OTP emailed
  → Enter OTP + complete form fields
  → POST /auth/verify-otp
  → JWT returned → localStorage.setItem('token', user)
  → Navigate to /onboarding (optional profile completion)
  → Navigate to /patient/dashboard
```

### Doctor Registration
```
Landing Page → /register → select role "Doctor"
  → Enter DOCTOR_INVITE_CODE ("HABS-DOCTOR-2026")
  → POST /auth/send-otp → OTP emailed
  → POST /auth/verify-otp
  → Response: "Awaiting admin approval"
  → Admin approves via /admin/dashboard
  → Approval email sent to doctor
  → Doctor can now POST /auth/login
  → Navigate to /doctor/dashboard
```

### Login
```
/login → POST /auth/login
  → JWT + user object returned
  → localStorage.setItem('token', user)
  → Role-based redirect:
       role == "patient" → /patient/dashboard
       role == "doctor"  → /doctor/dashboard
  → 403 if doctor pending/rejected/inactive
```

### Admin Login
```
/admin/login → POST /auth/admin/login
  → JWT returned → /admin/dashboard
  Default: ramola27041980@gmail.com / habsadmin@120008
```

---

## Protected Routes

React Router uses a `PrivateRoute` wrapper in `App.jsx`:

```
/patient/dashboard  → requires token + role == "patient"
/doctor/dashboard   → requires token + role == "doctor"
/admin/dashboard    → has its own auth check (no PrivateRoute wrapper)
```

If token is missing or role mismatches → redirect to `/`.

The `PrivateRoute` component also renders a nav bar with user initials avatar and a logout button.

---

## Patient Flow

```
/patient/dashboard
  ├── View upcoming appointments (GET /appointments)
  │     Shows: doctor name, specialization, date, time, status
  │     Action: "Cancel" → PATCH /appointments/{id}/cancel
  │
  └── Book New Appointment
        1. Select doctor from GET /doctor/list (dropdown)
        2. Pick appointment date (date input)
        3. GET /appointments/slots?doctor_id=...&slot_date=...
        4. Select available time slot
        5. POST /appointments
              ↓ ML inference runs
              ↓ risk stored in ml_predictions
              ↓ confirmation email + PDF sent
              ↓ success toast shown
```

---

## Doctor Flow

```
/doctor/dashboard
  ├── View all appointments (GET /doctor/dashboard)
  │     Shows: patient name, date, time, status, risk badge
  │     Red badge (≥ 40% risk) | Green badge (< 40% risk)
  │
  └── Update appointment outcome
        PATCH /doctor/{id}/status?status=completed
        PATCH /doctor/{id}/status?status=no_show
        PATCH /doctor/{id}/status?status=cancelled
```

---

## Admin Flow

```
/admin/dashboard
  ├── Stats card (GET /admin/stats)
  │     patients_count, approved_doctors, pending_doctors,
  │     appointments_count, high_risk_count
  │
  ├── Pending Doctors (GET /admin/pending-doctors)
  │     For each: "Approve" → PATCH /admin/doctors/{id}/approve
  │                            → doctor.verification_status = "approved"
  │                            → user.is_active = true
  │                            → approval email sent
  │             "Reject" → PATCH /admin/doctors/{id}/reject
  │                            → rejection_reason required
  │                            → rejection email sent
  │
  └── All Doctors (GET /admin/all-doctors)
        Shows verification status and rejection reasons
```

---

## ML Prediction Flow

```
POST /appointments triggered
  → slot validation + conflict check
  → Appointment row created (status=booked)
  → TimeSlot.is_available = false

  ML branch:
    → user_repo.get_ml_flags(patient_id)     [age, health booleans]
    → appt_repo.get_patient_ml_history(patient_id)  [prior counts]
    → Build 18-feature dict (ml_input)
    → pd.DataFrame([ml_input])
    → model.predict_proba(df)[0][1]          [risk float]
    → ml_repo.record_prediction(...)         [insert ml_predictions row]
    → appt_repo.update_risk_score(id, risk)  [update appointments.no_show_risk]

  Email branch:
    → Build PDF with reportlab (patient name, doctor, date, time, booking ID)
    → Send email via Brevo SMTP with PDF attachment

  Fallback: any exception in ML or email branch is caught silently
            booking still returns 200 with appointment_id
```

---

## Appointment State Machine

```
booked
  ├── → completed   (doctor marks attended)
  ├── → cancelled   (patient cancels OR doctor cancels)
  └── → no_show     (doctor marks no-show)
```

`cancelled` restores the `TimeSlot.is_available = true` so the slot can be rebooked.

---

## Notification Flow *(planned, not yet wired)*

```
On booking confirm → schedule reminder
If risk >= 0.7 → send reminder 48hr + 24hr before appointment
If risk < 0.7  → send reminder 24hr before appointment
Channel: SMS (primary) + Email (secondary)
```

Currently the `notifications` table exists but the scheduler/trigger is not implemented.

---

## Error Flows

| Error | Handling |
|-------|---------|
| Slot already taken | 409 Conflict — `UNIQUE(doctor_id, appointment_date, time_slot)` |
| Booking in the past | 400 Bad Request |
| ML service down | NULL risk score, booking proceeds normally |
| Invalid JWT | 401 Unauthorized, Axios interceptor → redirect to `/login` |
| Doctor pending/rejected | 403 Forbidden with descriptive message |
| Duplicate email registration | 400 Email already registered |
| OTP expired/invalid | 400 with specific message |