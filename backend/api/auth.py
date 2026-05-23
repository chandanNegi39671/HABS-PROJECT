from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.schemas import UserCreate, UserLogin, Token, OTPRequest, OTPVerify
from security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import datetime, timedelta
import random
import httpx
from habs_db.repositories.database import get_db
from habs_db.repositories.users import UserRepository
from habs_db.repositories.doctors import DoctorRepository
from habs_db.models import User, Doctor, OTPVerification, Admin
from habs_db.settings import get_settings
from sqlalchemy import select

router = APIRouter()
settings = get_settings()

def send_email(to_email: str, subject: str, body: str) -> bool:
    try:
        import httpx
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": f"HABS Healthcare <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "text": body
            },
            timeout=10
        )
        if response.status_code == 200:
            print(f"Email sent via Resend to {to_email}")
            return True
        else:
            print(f"Resend error: {response.text}")
            return False
    except Exception as e:
        print(f"Email failed: {e}")
        return False
        
@router.post("/send-otp")
async def send_otp(req: OTPRequest, db: AsyncSession = Depends(get_db)):
    user_repo = UserRepository(db)
    existing_user = await user_repo.get_by_email(req.email)
    if existing_user:
        doc_repo = DoctorRepository(db)
        existing_doc = await doc_repo.get_by_email(req.email)
        if not (existing_doc and existing_doc.verification_status == "revoked"):
            raise HTTPException(status_code=400, detail="Email already registered")

    otp_code = str(random.randint(100000, 999999))
    from datetime import timezone
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    otp_record = OTPVerification(
        email=req.email,
        otp_code=otp_code,
        expires_at=expires_at
    )
    db.add(otp_record)
    await db.commit()

    subject = "HABS — Your OTP Code"
    body = f"""Your OTP for HABS registration is: {otp_code}
This code expires in 10 minutes.
Do not share this code with anyone."""

    email_sent = send_email(req.email, subject, body)

    if not email_sent:
        # FIX: never expose OTP in response — log server-side only
        print(f"[SERVER ONLY] OTP for {req.email}: {otp_code}")
        raise HTTPException(
            status_code=500,
            detail="Failed to send OTP email. Please try again."
        )

    return {"message": "OTP sent to your email"}

@router.post("/verify-otp")
async def verify_otp(data: OTPVerify, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OTPVerification)
        .where(OTPVerification.email == data.email)
        .order_by(OTPVerification.created_at.desc())
        .limit(1)
    )
    otp_record = result.scalar_one_or_none()

    if not otp_record:
        raise HTTPException(status_code=400, detail="OTP not found")
    if otp_record.is_used:
        raise HTTPException(status_code=400, detail="OTP already used")
    from datetime import timezone
    now = datetime.now(timezone.utc)
    exp = otp_record.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < now:
        raise HTTPException(status_code=400, detail="OTP expired")
    if otp_record.otp_code != data.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    otp_record.is_used = True
    db.add(otp_record)

    hashed_password = get_password_hash(data.password)

    if data.role == "doctor":
        if data.invite_code != settings.DOCTOR_INVITE_CODE:
            raise HTTPException(status_code=403, detail="Invalid invite code")

        user_repo = UserRepository(db)
        existing_user = await user_repo.get_by_email(data.email)
        if existing_user:
            doc_repo = DoctorRepository(db)
            existing_doc = await doc_repo.get_by_email(data.email)
            if existing_doc and existing_doc.verification_status == "revoked":
                existing_user.hashed_password = hashed_password
                existing_user.full_name = data.full_name
                existing_user.phone = data.phone
                existing_doc.full_name = data.full_name
                existing_doc.phone = data.phone
                existing_doc.specialization = data.specialization or "General"
                existing_doc.verification_status = "pending"
                db.add(existing_user)
                db.add(existing_doc)
                await db.commit()
                return {"message": "Re-registration submitted. Awaiting admin approval. You will be notified via email."}
            else:
                raise HTTPException(status_code=400, detail="Email already registered")

        new_user = User(
            full_name=data.full_name,
            email=data.email,
            hashed_password=hashed_password,
            phone=data.phone,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            is_active=False,
            is_email_verified=True,
            scholarship=data.scholarship,
            hypertension=data.hypertension,
            diabetes=data.diabetes,
            alcoholism=data.alcoholism,
            has_chronic_condition=data.has_chronic_condition
        )
        db.add(new_user)
        await db.flush()

        new_doc = Doctor(
            id=new_user.id,
            full_name=data.full_name,
            email=data.email,
            phone=data.phone,
            specialization=data.specialization or "General",
            is_active=False,
            verification_status="pending"
        )
        db.add(new_doc)
        await db.commit()

        return {"message": "Registration submitted. Awaiting admin approval. You will be notified via email."}

    else:  # role == "patient"
        new_user = User(
            full_name=data.full_name,
            email=data.email,
            hashed_password=hashed_password,
            phone=data.phone,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            is_active=True,
            is_email_verified=True,
            scholarship=data.scholarship,
            hypertension=data.hypertension,
            diabetes=data.diabetes,
            alcoholism=data.alcoholism,
            has_chronic_condition=data.has_chronic_condition
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": new_user.email, "role": "patient", "id": str(new_user.id)},
            expires_delta=access_token_expires
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {"id": str(new_user.id), "email": new_user.email, "role": "patient", "full_name": new_user.full_name}
        }

@router.post("/admin/login", response_model=Token)
async def admin_login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Admin).where(Admin.email == user_in.email))
    admin = result.scalar_one_or_none()

    if not admin or not verify_password(user_in.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": admin.email, "role": "admin", "id": str(admin.id)},
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(admin.id),
        "user": {"id": str(admin.id), "email": admin.email, "role": "admin", "full_name": admin.full_name}
    }

# FIX: /auth/register legacy endpoint removed — bypassed OTP entirely

@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(user_in.email)
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    doc_repo = DoctorRepository(db)
    doc = await doc_repo.get_by_email(user_in.email)
    role = "doctor" if doc else "patient"

    if role == "doctor":
        if doc.verification_status == "pending":
            raise HTTPException(status_code=403, detail="Account under review. Please wait for admin approval.")
        if doc.verification_status == "rejected":
            raise HTTPException(status_code=403, detail=f"Account rejected. Reason: {doc.rejection_reason}")
        if doc.verification_status == "revoked":
            raise HTTPException(status_code=403, detail="Account revoked. Please re-register to regain access.")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account not active.")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": role, "id": str(user.id)},
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "user": {"id": str(user.id), "email": user.email, "role": role, "full_name": user.full_name}
    }

@router.post("/forgot-password")
async def forgot_password(payload: dict, db: AsyncSession = Depends(get_db)):
    email = payload.get("email", "").strip().lower()

    result = await db.execute(
        select(User).where(User.email == email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email.")

    otp_code = str(random.randint(100000, 999999))

    from datetime import timezone
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)

    otp_entry = OTPVerification(
        email=email,
        otp_code=otp_code,
        expires_at=expires,
        is_used=False
    )
    db.add(otp_entry)
    await db.commit()

    # Log server-side only — never expose OTP in response
    print(f"[SERVER ONLY] Password reset OTP for {email}: {otp_code}")

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg['From'] = f"HABS Healthcare <{settings.EMAIL_FROM if settings.EMAIL_FROM else settings.EMAIL_USER}>"
        msg['Reply-To'] = settings.EMAIL_USER
        msg['To'] = email
        msg['Subject'] = "HABS — Password Reset OTP"

        body = f"""Dear {user.full_name},

Your password reset OTP is: {otp_code}

This OTP is valid for 10 minutes.
If you did not request this, ignore this email.

— HABS Healthcare Team"""
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.starttls()
        server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"[EMAIL ERROR] forgot_password: {type(e).__name__}: {e}")

    return {"message": "OTP sent to your email."}


@router.post("/verify-reset-otp")
async def verify_reset_otp(payload: dict, db: AsyncSession = Depends(get_db)):
    email = payload.get("email", "").strip().lower()
    otp_code = payload.get("otp_code", "").strip()

    from datetime import timezone
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(OTPVerification).where(
            OTPVerification.email == email,
            OTPVerification.otp_code == otp_code,
            OTPVerification.is_used == False,
            OTPVerification.expires_at > now,
        ).order_by(OTPVerification.created_at.desc())
    )
    otp_entry = result.scalar_one_or_none()

    if not otp_entry:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    otp_entry.is_used = True
    await db.commit()

    # FIX #2: issue a short-lived signed reset token instead of trusting raw email
    reset_token = create_access_token(
        data={"sub": email, "purpose": "password_reset"},
        expires_delta=timedelta(minutes=15)
    )

    return {"message": "OTP verified.", "reset_token": reset_token}


@router.post("/reset-password")
async def reset_password(payload: dict, db: AsyncSession = Depends(get_db)):
    # FIX #2: validate signed reset token — not raw email
    from security import decode_access_token

    reset_token = payload.get("reset_token", "")
    new_password = payload.get("new_password", "")

    token_data = decode_access_token(reset_token)
    if not token_data or token_data.get("purpose") != "password_reset":
        raise HTTPException(status_code=403, detail="Invalid or expired reset token.")

    email = token_data.get("sub", "").strip().lower()

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    result = await db.execute(
        select(User).where(User.email == email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.hashed_password = get_password_hash(new_password)
    await db.commit()

    return {"message": "Password reset successful."}
