from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date
import uuid

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    role: str = "patient" # 'patient', 'doctor', 'admin'
    invite_code: Optional[str] = None
    specialization: Optional[str] = None  # for doctor registration

    # ML features
    scholarship: bool = False
    hypertension: bool = False
    diabetes: bool = False
    alcoholism: bool = False
    has_chronic_condition: bool = False

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerify(UserCreate):
    otp_code: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class AppointmentBook(BaseModel):
    doctor_id: uuid.UUID
    appointment_date: date
    time_slot: str
