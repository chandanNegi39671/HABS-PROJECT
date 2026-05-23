from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import joblib
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from habs_db.settings import get_settings
from habs_db.repositories.database import init_db, close_db
from api.auth import router as auth_router
from api.appointments import router as appt_router
from api.doctor import router as doctor_router
from api.admin import router as admin_router
from api.patient import router as patient_router

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db(settings)
    try:
        model_path = os.path.join(os.path.dirname(__file__), "ml", settings.ML_MODEL_PATH)
        if os.path.exists(model_path):
            app.state.ml_model = joblib.load(model_path)
            print(f"ML Model loaded from {model_path}")
        else:
            print(f"ML Model not found at {model_path}. ML predictions will fail.")
            app.state.ml_model = None
    except Exception as e:
        print(f"Error loading model: {e}")
        app.state.ml_model = None

    yield
    # Shutdown
    await close_db()

app = FastAPI(title="HABS API", lifespan=lifespan)

from fastapi.responses import JSONResponse
from fastapi import Request
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log full traceback server-side only — never expose to client
    print(f"Global Error: {exc}")
    print(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."}
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://habsappointment.vercel.app", "http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(appt_router, prefix="/appointments", tags=["appointments"])
app.include_router(doctor_router, prefix="/doctor", tags=["doctor"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(patient_router, prefix="/patient", tags=["patient"])

@app.get("/")
def root():
    return {"message": "Welcome to HABS API"}
