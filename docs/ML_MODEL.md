# HABS — ML Model Documentation

## Overview

HABS uses a trained **Random Forest** classifier to predict patient no-show probability at appointment booking time. The model is loaded once at FastAPI startup and runs synchronously during the booking request.

- **Model file:** `backend/ml/model/habs_noshow_model_v1.joblib`
- **Training script:** `backend/ml/habs_kaggle_final.py`
- **Model card:** `backend/ml/habs_model_card.txt`
- **Artifacts:** `backend/ml/artifacts/` (ROC/confusion matrix, SHAP summary, feature importance plots)

---

## Model Specification

| Property | Value |
|----------|-------|
| Algorithm | Random Forest (scikit-learn) |
| Task | Binary classification (no-show = 1) |
| Output | Probability `float` in `[0.0, 1.0]` |
| Default threshold | 0.4 (configurable via `ML_THRESHOLD` env var) |
| Target latency | < 5ms per inference on CPU |
| Explainability | SHAP values (computed during training) |
| Persistence | `joblib.dump()` / `joblib.load()` |
| Version string | `habs_noshow_v1` |

---

## Feature Vector

The model receives 18 features, constructed at booking time in `api/appointments.py`:

| Feature | Source | Type | Description |
|---------|--------|------|-------------|
| `Age` | `users` table (`date_of_birth`) | int | Patient age in years |
| `lead_time_days` | `appointment_date - date.today()` | int | Days between booking and appointment |
| `prior_no_show_count` | `appointments` aggregate | int | Historical no-show count for this patient |
| `prior_appointment_count` | `appointments` aggregate | int | Total historical appointments |
| `appointment_hour` | `time_slot.split(":")[0]` | int | Hour of appointment (0–23) |
| `is_monday` | `appointment_date.weekday() == 0` | int (0/1) | Whether appointment is on Monday |
| `day_of_week` | `appointment_date.weekday()` | int (0–6) | Day of week (0=Mon, 6=Sun) |
| `has_chronic_condition` | `users.has_chronic_condition` | int (0/1) | Patient has chronic condition |
| `sms_reminder_sent` | Hardcoded `0` at booking | int (0/1) | Reminder not yet sent at booking time |
| `Scholarship` | `users.scholarship` | int (0/1) | Patient receives scholarship |
| `Hipertension` | `users.hypertension` | int (0/1) | Patient has hypertension |
| `Diabetes` | `users.diabetes` | int (0/1) | Patient has diabetes |
| `Alcoholism` | `users.alcoholism` | int (0/1) | Patient has alcoholism |
| `Handcap` | `users` (if present) | int (0/1) | Physical handicap flag |
| `patient_age_group_enc` | Derived from `Age` | int | 1=under 18, 0=18–59, 2=60+ |
| `Gender_M` | Derived from `users.gender` | int (0/1) | 1 if male |
| `fee_tier_low` | `1 if scholarship else 0` | int (0/1) | Low fee tier |
| `fee_tier_mid` | Hardcoded `0` | int (0/1) | Mid fee tier (placeholder) |

---

## Inference Pipeline

```python
# 1. Collect patient features from DB
features = await user_repo.get_ml_flags(patient_id)
history  = await appt_repo.get_patient_ml_history(patient_id)

# 2. Build feature dict
ml_input = {
    "Age": age,
    "lead_time_days": lead_time,
    "prior_no_show_count": history["prior_no_show_count"],
    ...
}

# 3. Score with loaded model
df = pd.DataFrame([ml_input])
risk_score = float(model.predict_proba(df)[0][1])  # probability of class 1 (no-show)

# 4. Store result
await ml_repo.record_prediction(
    appointment_id=saved_appt.id,
    no_show_probability=risk_score,
    predicted_label=bool(risk_score >= settings.ML_THRESHOLD),
    input_features=ml_input,
    threshold_used=settings.ML_THRESHOLD
)
```

---

## Startup Loading

The model is loaded **once** in `main.py` during the FastAPI `lifespan` startup event:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = os.path.join(os.path.dirname(__file__), "ml", settings.ML_MODEL_PATH)
    if os.path.exists(model_path):
        app.state.ml_model = joblib.load(model_path)
    else:
        app.state.ml_model = None
    yield
    await close_db()
```

The model instance is accessed per-request via `req.app.state.ml_model`.

---

## Fallback Behavior

If ML inference fails for any reason (model not loaded, feature extraction error, etc.), the booking **proceeds normally** with `no_show_risk = NULL`:

```python
try:
    # ... ML inference ...
except Exception as e:
    print(f"ML Error: {e}")
    pass  # booking is not blocked
```

---

## JSONB Schema Validation

Before inserting into `ml_predictions`, `MLPredictionRepository.record_prediction()` calls `validate_ml_input(input_features)` defined in `habs_db/schemas/ml_input.py`. This validates:

- All 18 required feature keys are present
- Value types match expected types
- Raises `ValueError` on schema violation

---

## Risk Display on Doctor Dashboard

The doctor dashboard uses a color-coded badge based on `no_show_risk`:

| Risk | Display |
|------|---------|
| `>= 0.4` (threshold) | 🔴 Red badge — predicted no-show |
| `< 0.4` | 🟢 Green badge — likely to attend |
| `null` | No badge shown |

The frontend threshold for red/green is `0.4` (matching `ML_THRESHOLD` default), implemented in `DoctorDashboard.jsx`.

---

## Training Artifacts

Located in `backend/ml/artifacts/`:

| File | Description |
|------|-------------|
| `habs_roc_confusion.png` | ROC curve + confusion matrix |
| `habs_shap_summary.png` | SHAP feature importance summary plot |
| `habs_feature_importance.png` | Random Forest feature importance bar chart |

---

## Model Performance

See `backend/ml/habs_model_card.txt` for full model card details including:
- Training dataset description (Kaggle no-show appointments dataset)
- Preprocessing steps
- Hyperparameters
- AUC-ROC, precision, recall metrics

---

## Environment Config

```env
ML_MODEL_PATH=model/habs_noshow_model_v1.joblib
ML_MODEL_VERSION=habs_noshow_v1
ML_THRESHOLD=0.4
```

The path is resolved relative to the `ml/` directory inside `backend/`.