"""
HABS — ML Input Features JSON Schema
Validated before every INSERT into ml_predictions.input_features.
Mirrors the 18 features used by habs_noshow_v1 (Random Forest, threshold=0.4).
"""

from __future__ import annotations

import json
import jsonschema
from jsonschema import ValidationError


# ─────────────────────────────── Schema ──────────────────────────────────────

ML_INPUT_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "HABSNoShowInputFeatures",
    "type": "object",
    "required": [
        "Age",
        "lead_time_days",
        "prior_no_show_count",
        "prior_appointment_count",
        "appointment_hour",
        "is_monday",
        "day_of_week",
        "has_chronic_condition",
        "sms_reminder_sent",
        "Scholarship",
        "Hipertension",
        "Diabetes",
        "Alcoholism",
        "Handcap",
        "patient_age_group_enc",
        "Gender_M",
        "fee_tier_low",
        "fee_tier_mid",
    ],
    "properties": {
        "Age": {
            "type": "number",
            "minimum": 0,
            "maximum": 130,
            "description": "Patient age in years",
        },
        "lead_time_days": {
            "type": "integer",
            "minimum": 0,
            "description": "Days between booking and appointment",
        },
        "prior_no_show_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Historical no-show count for this patient",
        },
        "prior_appointment_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Historical appointment count for this patient",
        },
        "appointment_hour": {
            "type": "integer",
            "minimum": 0,
            "maximum": 23,
            "description": "Hour of day for the appointment (24h)",
        },
        "is_monday": {
            "type": "integer",
            "enum": [0, 1],
            "description": "1 if the appointment falls on Monday",
        },
        "day_of_week": {
            "type": "integer",
            "minimum": 0,
            "maximum": 6,
            "description": "0=Monday … 6=Sunday",
        },
        "has_chronic_condition": {
            "type": "integer",
            "enum": [0, 1],
            "description": "1 if the patient has a chronic condition",
        },
        "sms_reminder_sent": {
            "type": "integer",
            "enum": [0, 1],
            "description": "1 if SMS reminder was sent",
        },
        "Scholarship": {"type": "integer", "enum": [0, 1]},
        "Hipertension": {"type": "integer", "enum": [0, 1]},
        "Diabetes": {"type": "integer", "enum": [0, 1]},
        "Alcoholism": {"type": "integer", "enum": [0, 1]},
        "Handcap": {
            "type": "integer",
            "minimum": 0,
            "description": "Handicap count used by the training pipeline",
        },
        "patient_age_group_enc": {
            "type": "integer",
            "minimum": 0,
            "description": "Ordinal-encoded age group from the training pipeline",
        },
        "Gender_M": {"type": "integer", "enum": [0, 1]},
        "fee_tier_low": {"type": "integer", "enum": [0, 1]},
        "fee_tier_mid": {"type": "integer", "enum": [0, 1]},
    },
    "additionalProperties": False,
}


# ─────────────────────────────── Validator ───────────────────────────────────

_validator = jsonschema.Draft7Validator(ML_INPUT_SCHEMA)


def validate_ml_input(features: dict) -> None:
    """
    Raises ValueError with a human-readable message if features is invalid.
    Call this before any INSERT into ml_predictions.

    Example:
        validate_ml_input(features)   # raises on bad data
        session.add(MLPrediction(input_features=features, ...))
    """
    errors = sorted(_validator.iter_errors(features), key=lambda e: str(e.path))
    if errors:
        messages = "; ".join(
            f"[{'/'.join(str(p) for p in e.path) or 'root'}] {e.message}"
            for e in errors
        )
        raise ValueError(f"ML input feature validation failed: {messages}")


def validate_ml_input_json(features_json: str) -> dict:
    """
    Parses a JSON string and validates it.
    Returns the parsed dict on success.
    """
    try:
        features = json.loads(features_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON for ML input features: {exc}") from exc
    validate_ml_input(features)
    return features
