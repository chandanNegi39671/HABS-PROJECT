# HABS — QA Testing Plan

This document outlines manual testing scenarios to verify the HABS implementation. Tests are organized by feature area and follow the actual implemented flows.

---

## 1. OTP Registration Flow

**Test 1.1 — Patient OTP registration:**
- Navigate to `/register`, fill in name/email/password, leave role as "patient"
- Click "Send OTP" → verify OTP email arrives or `dev_otp` is returned in response
- Enter OTP and submit
- Verify redirect to `/patient/dashboard` and JWT stored in `localStorage`

**Test 1.2 — Doctor OTP registration:**
- Register as "doctor" with `HABS-DOCTOR-2026` as invite code
- Submit OTP
- Verify response: "Registration submitted. Awaiting admin approval."
- Verify doctor cannot login (403 "Account under review")

**Test 1.3 — Invalid invite code:**
- Register as doctor with wrong invite code
- Verify 403: "Invalid invite code"

**Test 1.4 — Duplicate email:**
- Attempt to send OTP with an already-registered email
- Verify 400: "Email already registered"

**Test 1.5 — OTP expiry:**
- Request OTP, wait > 10 minutes, attempt to verify
- Verify 400: "OTP expired"

---

## 2. Login & Role-Based Redirect

**Test 2.1 — Patient login:**
- Login with patient credentials
- Verify redirect to `/patient/dashboard`
- Verify token and user object in `localStorage`

**Test 2.2 — Doctor login (after approval):**
- Login with an admin-approved doctor account
- Verify redirect to `/doctor/dashboard`

**Test 2.3 — Wrong credentials:**
- Login with incorrect password
- Verify 401: "Incorrect email or password"

**Test 2.4 — Unauthorized route access:**
- Attempt to navigate to `/patient/dashboard` without token
- Verify redirect to `/` (PrivateRoute guard)

**Test 2.5 — Cross-role access:**
- Login as patient, navigate to `/doctor/dashboard`
- Verify redirect to `/` (role mismatch guard)

**Test 2.6 — Admin login:**
- Navigate to `/admin/login`
- Login with `ramola27041980@gmail.com` / `habsadmin@120008`
- Verify redirect to `/admin/dashboard`

---

## 3. Appointment Booking Flow

**Test 3.1 — Available slots:**
- Login as patient, go to "Book Appointment"
- Select a valid doctor and a future date
- Verify slots are fetched from `GET /appointments/slots`
- Verify only `is_available = true` slots are shown

**Test 3.2 — Successful booking:**
- Select an available slot and confirm
- Verify: success message shown, `appointment_id` returned
- Verify: `GET /appointments` shows the new booking
- Verify: confirmation email with PDF arrives at patient email

**Test 3.3 — Double booking guard:**
- Using a second patient account, attempt to book the same doctor + date + time slot
- Verify: 409 Conflict error returned
- Verify: original booking is unaffected

**Test 3.4 — Past date booking:**
- Attempt to book a date in the past
- Verify: 400 "Cannot book in the past"

**Test 3.5 — Cancellation:**
- Cancel an existing `booked` appointment
- Verify: status changes to `cancelled`
- Verify: the time slot becomes available again (slot can be rebooked)

---

## 4. ML Risk Prediction

**Test 4.1 — Risk score on doctor dashboard:**
- Login as doctor (after patient books with that doctor)
- View dashboard
- Verify ML risk badge appears on the appointment row
- Verify green badge for risk < 40%, red badge for risk ≥ 40%

**Test 4.2 — Risk stored in DB:**
- After booking, verify `ml_predictions` table has a row with `appointment_id`
- Verify `no_show_probability` is between 0.0 and 1.0
- Verify `input_features` JSONB is populated with 18 features

**Test 4.3 — ML fallback:**
- Temporarily rename/remove the `.joblib` model file
- Book an appointment
- Verify booking still succeeds with `no_show_risk = null` on the appointment
- Restore model file

---

## 5. Doctor Dashboard

**Test 5.1 — Mark as completed:**
- Login as doctor, find a `booked` appointment
- Click "Completed" / call `PATCH /doctor/{id}/status?status=completed`
- Verify status updates to `completed` in UI

**Test 5.2 — Mark as no-show:**
- Find a `booked` appointment, mark as `no_show`
- Verify status updates in UI

**Test 5.3 — Invalid status:**
- Call `PATCH /doctor/{id}/status?status=invalid_status`
- Verify 400: "Invalid status"

---

## 6. Admin Workflow

**Test 6.1 — Stats:**
- Login as admin, view dashboard
- Verify `patients_count`, `approved_doctors_count`, `pending_doctors_count` appear

**Test 6.2 — Approve doctor:**
- Register a new doctor (OTP + invite code)
- Login as admin → navigate to "Pending Doctors"
- Click "Approve"
- Verify `verification_status = "approved"` in DB
- Verify doctor can now login

**Test 6.3 — Reject doctor:**
- Reject a pending doctor with a reason string
- Verify `verification_status = "rejected"` and `rejection_reason` stored
- Verify rejected doctor gets 403 with reason on login attempt
- Verify rejection email sent

**Test 6.4 — Admin cannot access patient routes:**
- Use admin JWT to call `GET /appointments` (patient route)
- Verify 401 (missing `X-User-Id` header) or appropriate error

---

## 7. Frontend UI

**Test 7.1 — Landing page:**
- Verify landing page loads at `/`
- Verify "Book Appointment" / "Login" CTAs navigate correctly

**Test 7.2 — Responsive layout:**
- Test on mobile viewport (375px width)
- Verify grid layout stacks properly

**Test 7.3 — Logout:**
- Click Logout in nav
- Verify `localStorage` is cleared
- Verify redirect to `/`

**Test 7.4 — Axios interceptor:**
- Let token expire or manually clear it
- Make an authenticated API call
- Verify 401 response triggers automatic redirect to `/login`

---

## 8. Email Notifications

**Test 8.1 — OTP email:**
- Register new patient
- Verify OTP email arrives with 6-digit code and 10-minute expiry message

**Test 8.2 — Booking confirmation email:**
- Book an appointment
- Verify email arrives with PDF attachment (`HABS_Appointment_<id>.pdf`)
- Verify PDF contains: patient name, doctor name, date, time, booking ID

**Test 8.3 — Doctor approval email:**
- Admin approves a pending doctor
- Verify doctor receives approval email with login URL

**Test 8.4 — Doctor rejection email:**
- Admin rejects a doctor with reason
- Verify doctor receives rejection email containing the reason

---

## 9. Security

**Test 9.1 — JWT required for protected routes:**
- Call `GET /doctor/dashboard` without `Authorization` header
- Verify 401 or missing header error

**Test 9.2 — Admin role enforcement:**
- Use patient JWT to call `GET /admin/pending-doctors`
- Verify 403: "Forbidden: Admin access required"

**Test 9.3 — Password hashing:**
- Register user, inspect `users.hashed_password` in DB
- Verify value is a bcrypt hash (starts with `$2b$`)
