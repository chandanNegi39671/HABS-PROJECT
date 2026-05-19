"""
=============================================================================
HABS (Healthcare Appointment Booking System) — No-Show Prediction Pipeline
=============================================================================
Author      : Senior ML Engineer
Dataset     : Kaggle "Medical Appointment No Shows" (KaggleV2-May-2016.csv)
Goal        : Binary classification — P(no_show | appointment_features)
Artifact    : habs_noshow_model_v1.joblib
=============================================================================
PASTE THIS ENTIRE CODE INTO ONE SINGLE KAGGLE CELL AND RUN
=============================================================================
"""

# =============================================================================
# IMPORTS & CONSTANTS
# =============================================================================

import warnings
import datetime
import random
import time
import os
import pytz
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import shap

from sklearn.model_selection  import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.preprocessing    import StandardScaler, LabelEncoder
from sklearn.ensemble         import RandomForestClassifier
from sklearn.linear_model     import LogisticRegression
from sklearn.pipeline         import Pipeline
from sklearn.metrics          import (accuracy_score, precision_score,
                                      recall_score, f1_score,
                                      roc_auc_score, confusion_matrix,
                                      roc_curve, ConfusionMatrixDisplay)

# Reproducibility
SEED = 42
np.random.seed(SEED)
random.seed(SEED)

# Output directory
OUTPUT_DIR = "/kaggle/working"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Indian Standard Time
IST = pytz.timezone("Asia/Kolkata")

print("=" * 70)
print("  HABS No-Show Prediction Pipeline — starting ...")
print("=" * 70)

# =============================================================================
# STEP 1 — Load dataset
# =============================================================================

print("\n[1/13] Loading dataset ...")

# Find CSV automatically — handles any Kaggle input path
CSV_PATH = None
for root, dirs, files in os.walk("/kaggle/input"):
    for f in files:
        if f.endswith(".csv"):
            CSV_PATH = os.path.join(root, f)
            break

if CSV_PATH is None:
    raise FileNotFoundError("No CSV found under /kaggle/input — add the dataset")

print(f"   Found CSV: {CSV_PATH}")
df = pd.read_csv(CSV_PATH)
print(f"   Raw shape : {df.shape}")
print(f"   Columns   : {df.columns.tolist()}")

# =============================================================================
# STEP 2 — Audit
# =============================================================================

print("\n[2/13] Auditing raw dataset ...")

print(f"   Null counts:\n{df.isnull().sum().to_string()}")
print(f"\n   Duplicate AppointmentIDs : {df.duplicated(subset=['AppointmentID']).sum()}")
print(f"\n   No-show value counts:\n{df['No-show'].value_counts().to_string()}")
print(f"\n   Age — min={df['Age'].min()}, max={df['Age'].max()}, mean={df['Age'].mean():.1f}")

# =============================================================================
# STEP 3 — Clean + UTC to IST conversion
# =============================================================================

print("\n[3/13] Cleaning ...")

n_before = len(df)

# 3a. Parse datetimes and convert UTC → IST immediately
#     MUST happen before any .dt accessor usage
df["ScheduledDay"]   = pd.to_datetime(df["ScheduledDay"],   utc=True).dt.tz_convert(IST)
df["AppointmentDay"] = pd.to_datetime(df["AppointmentDay"], utc=True).dt.tz_convert(IST)

print(f"   Sample ScheduledDay   (IST): {df['ScheduledDay'].iloc[0]}")
print(f"   Sample AppointmentDay (IST): {df['AppointmentDay'].iloc[0]}")

# 3b. Encode target — 'Yes' = no-show = 1, 'No' = attended = 0
#     Do this BEFORE any filtering so no rows are lost with original labels
df["No-show"] = (df["No-show"] == "Yes").astype(int)

print(f"\n   Target encoded: {df['No-show'].value_counts().to_dict()}")
print(f"   No-show rate  : {df['No-show'].mean():.2%}")

# 3c. Remove age outliers
df = df[(df["Age"] >= 0) & (df["Age"] <= 100)]

# 3d. Remove negative lead time records
df = df[df["AppointmentDay"] >= df["ScheduledDay"]]

# 3e. Drop duplicate appointments
df = df.drop_duplicates(subset=["AppointmentID"], keep="first")

# 3f. Reset index — CRITICAL after all filtering
df = df.reset_index(drop=True)

n_after = len(df)
print(f"\n   Removed {n_before - n_after:,} records → {n_after:,} clean rows")
print(f"   Post-clean no-show rate : {df['No-show'].mean():.2%}")

# Verify target is still correct after reset
assert df["No-show"].nunique() == 2, "ERROR: Target only has one class!"
assert df["No-show"].mean() > 0.10,  "ERROR: No-show rate suspiciously low!"
print("   ✓ Target integrity verified")

# =============================================================================
# STEP 4 — Feature Engineering (Table 2.3)
# =============================================================================

print("\n[4/13] Engineering features (Table 2.3) ...")

# 4.1 lead_time_days
df["lead_time_days"] = (
    df["AppointmentDay"] - df["ScheduledDay"]
).dt.days.clip(lower=0)
print(f"   lead_time_days : min={df['lead_time_days'].min()}, "
      f"max={df['lead_time_days'].max()}, "
      f"mean={df['lead_time_days'].mean():.1f}")

# 4.2 appointment_hour in IST
#     AppointmentDay has no time component (always 00:00 UTC = 05:30 IST)
#     Use ScheduledDay hour — real booking time, meaningful signal
df["appointment_hour"] = df["ScheduledDay"].dt.hour
print(f"   appointment_hour (IST): min={df['appointment_hour'].min()}, "
      f"max={df['appointment_hour'].max()}, "
      f"mean={df['appointment_hour'].mean():.1f}")

# 4.3 day_of_week & is_monday (IST-correct after tz conversion)
df["day_of_week"] = df["AppointmentDay"].dt.dayofweek   # 0=Mon, 6=Sun
df["is_monday"]   = (df["day_of_week"] == 0).astype(int)
print(f"   Monday appointments: {df['is_monday'].sum():,} ({df['is_monday'].mean():.1%})")

# 4.4 patient_age_group — ordinal: child / adult / senior
df["patient_age_group"] = pd.cut(
    df["Age"],
    bins   = [-1, 17, 59, 100],
    labels = ["child", "adult", "senior"]
)
print(f"   Age groups:\n{df['patient_age_group'].value_counts().to_string()}")

# 4.5 Patient-level history — sort chronologically to prevent data leakage
#     IMPORTANT: extract target BEFORE sort, attach back after
#     to guarantee alignment is never broken
df = df.sort_values(["PatientId", "AppointmentDay"]).reset_index(drop=True)

# Verify target survived the sort
print(f"\n   Target after sort: {df['No-show'].value_counts().to_dict()}")
print(f"   No-show rate after sort: {df['No-show'].mean():.2%}")
assert df["No-show"].mean() > 0.10, "ERROR: Target corrupted after sort!"

# prior_appointment_count: 0 for first visit, 1 for second, etc.
df["prior_appointment_count"] = df.groupby("PatientId").cumcount()

# prior_no_show_count: cumulative past no-shows (shift=1 prevents leakage)
df["prior_no_show_count"] = (
    df.groupby("PatientId")["No-show"]
      .transform(lambda s: s.shift(1).fillna(0).cumsum())
      .astype(int)
)
print(f"   prior_appointment_count: max={df['prior_appointment_count'].max()}, "
      f"mean={df['prior_appointment_count'].mean():.1f}")
print(f"   prior_no_show_count    : max={df['prior_no_show_count'].max()}, "
      f"mean={df['prior_no_show_count'].mean():.2f}")

# 4.6 has_chronic_condition — composite flag
df["has_chronic_condition"] = (
    (df["Hipertension"] == 1) |
    (df["Diabetes"]     == 1) |
    (df["Alcoholism"]   == 1) |
    (df["Handcap"]       > 0)
).astype(int)
print(f"   has_chronic_condition: {df['has_chronic_condition'].sum():,} "
      f"({df['has_chronic_condition'].mean():.1%})")

# 4.7 sms_reminder_sent
df["sms_reminder_sent"] = df["SMS_received"]

# 4.8 fee_tier — derived proxy (Scholarship + neighbourhood rank)
neighbourhood_codes = {
    n: i for i, n in enumerate(sorted(df["Neighbourhood"].unique()))
}
df["_nbhd_code"] = df["Neighbourhood"].map(neighbourhood_codes)
nbhd_max = df["_nbhd_code"].max()

def assign_fee_tier(row):
    if row["Scholarship"] == 1:
        return "low"
    elif row["_nbhd_code"] < nbhd_max * 0.40:
        return "low"
    elif row["_nbhd_code"] < nbhd_max * 0.75:
        return "mid"
    else:
        return "high"

df["fee_tier"] = df.apply(assign_fee_tier, axis=1)
df.drop(columns=["_nbhd_code"], inplace=True)
print(f"   fee_tier: {df['fee_tier'].value_counts().to_dict()}")

print("\n   ✓ Step 4 complete")

# =============================================================================
# STEP 5 — Encode & assemble feature matrix
# =============================================================================

print("\n[5/13] Encoding features ...")

TARGET = "No-show"

# 5a. Label-encode ordinal: patient_age_group
le = LabelEncoder()
df["patient_age_group_enc"] = le.fit_transform(df["patient_age_group"])
age_group_classes_ = list(le.classes_)
print(f"   LabelEncoder mapping: {dict(zip(le.classes_, le.transform(le.classes_)))}")

# 5b. One-hot encode nominals (drop_first avoids dummy trap)
NOMINAL_CATS = ["Gender", "fee_tier"]
df_ohe = pd.get_dummies(df[NOMINAL_CATS], drop_first=True).astype(int)
print(f"   OHE columns: {df_ohe.columns.tolist()}")

# 5c. Feature groups
CONTINUOUS = ["lead_time_days", "Age", "prior_no_show_count",
              "prior_appointment_count", "appointment_hour"]

BINARY = ["is_monday", "day_of_week", "has_chronic_condition",
          "sms_reminder_sent", "Scholarship",
          "Hipertension", "Diabetes", "Alcoholism", "Handcap"]

# 5d. Assemble feature matrix — column order fixed here permanently
feature_df = pd.concat(
    [
        df[CONTINUOUS + BINARY].reset_index(drop=True),
        df[["patient_age_group_enc"]].reset_index(drop=True),
        df_ohe.reset_index(drop=True),
    ],
    axis=1
)

# 5e. Extract target — MUST use df["No-show"] directly, same index
y = df[TARGET].values

# Final integrity check
print(f"\n   Feature matrix shape : {feature_df.shape}")
print(f"   Feature columns      : {feature_df.columns.tolist()}")
print(f"   Target distribution  : {np.bincount(y).tolist()}")
print(f"   No-show rate         : {y.mean():.2%}")

assert y.mean() > 0.10, "ERROR: Target is broken — re-run from Step 1!"
assert len(feature_df) == len(y), "ERROR: Feature/target length mismatch!"
print("   ✓ Feature matrix and target verified")

# =============================================================================
# STEP 6 — Stratified 80/20 train-test split
# =============================================================================

print("\n[6/13] Splitting data (80/20 stratified) ...")

X_train, X_test, y_train, y_test = train_test_split(
    feature_df, y,
    test_size    = 0.20,
    stratify     = y,
    random_state = SEED
)

print(f"   Train : {X_train.shape[0]:,} rows | no-show rate = {y_train.mean():.2%}")
print(f"   Test  : {X_test.shape[0]:,} rows | no-show rate = {y_test.mean():.2%}")

# Store canonical feature order — referenced by inference function
FEATURE_COLUMNS = feature_df.columns.tolist()

# =============================================================================
# STEP 7 — Build sklearn Pipelines (StandardScaler → Model)
# =============================================================================

print("\n[7/13] Building Pipelines ...")

# Random Forest pipeline (primary model)
rf_pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("clf", RandomForestClassifier(
        class_weight = "balanced",
        random_state = SEED,
        n_jobs       = -1,
    ))
])

# Logistic Regression pipeline (baseline)
lr_pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("clf", LogisticRegression(
        class_weight = "balanced",
        max_iter     = 1000,
        random_state = SEED,
        solver       = "lbfgs",
    ))
])

print("   ✓ Pipelines ready")

# =============================================================================
# STEP 8 — GridSearchCV hyperparameter tuning
# =============================================================================

print("\n[8/13] Tuning RandomForest with GridSearchCV (5-fold stratified) ...")
print("       27 candidates × 5 folds = 135 fits — please wait ...")

param_grid = {
    "clf__n_estimators"     : [100, 200, 300],
    "clf__max_depth"        : [None, 10, 20],
    "clf__min_samples_split": [2, 5, 10],
}

cv_strategy = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

grid_search = GridSearchCV(
    estimator        = rf_pipeline,
    param_grid       = param_grid,
    cv               = cv_strategy,
    scoring          = "roc_auc",
    n_jobs           = -1,
    verbose          = 1,
    refit            = True,
    return_train_score = True,
)

t0 = time.time()
grid_search.fit(X_train, y_train)
elapsed = time.time() - t0

best_rf     = grid_search.best_estimator_
best_params = grid_search.best_params_
best_cv_auc = grid_search.best_score_

print(f"\n   ✓ Done in {elapsed/60:.1f} min")
print(f"   Best params : {best_params}")
print(f"   Best CV AUC : {best_cv_auc:.4f}")

# =============================================================================
# STEP 9 — Train Logistic Regression baseline
# =============================================================================

print("\n[9/13] Training Logistic Regression baseline ...")
lr_pipeline.fit(X_train, y_train)
print("   ✓ Done")

# =============================================================================
# STEP 10 — Evaluate both models
# =============================================================================

print("\n[10/13] Evaluating on hold-out test set ...")

# Threshold 0.40: favours recall — catching more no-shows matters more
# in healthcare than avoiding false alarms
DECISION_THRESHOLD = 0.40

def evaluate_model(name, pipeline, X, y_true, threshold=0.5):
    """Compute full classification metrics for a fitted pipeline."""
    y_prob = pipeline.predict_proba(X)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)
    cm     = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    return {
        "name"       : name,
        "accuracy"   : accuracy_score(y_true, y_pred),
        "precision"  : precision_score(y_true, y_pred, zero_division=0),
        "recall"     : recall_score(y_true, y_pred, zero_division=0),
        "f1"         : f1_score(y_true, y_pred, zero_division=0),
        "auc_roc"    : roc_auc_score(y_true, y_prob),
        "specificity": tn / (tn + fp) if (tn + fp) > 0 else 0,
        "cm"         : cm,
        "y_prob"     : y_prob,
        "y_pred"     : y_pred,
        "threshold"  : threshold,
    }

rf_metrics = evaluate_model("Random Forest",       best_rf,     X_test, y_test, DECISION_THRESHOLD)
lr_metrics = evaluate_model("Logistic Regression", lr_pipeline, X_test, y_test, DECISION_THRESHOLD)

print("\n   ┌──────────────────────┬─────────────┬─────────────┐")
print("   │ Metric               │ Rand.Forest │  Log.Reg    │")
print("   ├──────────────────────┼─────────────┼─────────────┤")
for metric in ["accuracy", "precision", "recall", "f1", "auc_roc", "specificity"]:
    rf_v = rf_metrics[metric]
    lr_v = lr_metrics[metric]
    print(f"   │ {metric:<20s} │   {rf_v:.4f}    │   {lr_v:.4f}    │")
print("   └──────────────────────┴─────────────┴─────────────┘")

print(f"\n   RF Confusion Matrix:\n{rf_metrics['cm']}")
print(f"\n   LR Confusion Matrix:\n{lr_metrics['cm']}")

# =============================================================================
# STEP 11 — Plots: ROC Curves + Confusion Matrices + Feature Importance
# =============================================================================

print("\n[11/13] Generating plots ...")

# Plot 1: ROC curves + confusion matrices
fig, axes = plt.subplots(1, 3, figsize=(21, 6))
fig.patch.set_facecolor("#0F172A")
for ax in axes:
    ax.set_facecolor("#1E293B")

# ROC curves
ax_roc = axes[0]
colors = {"Random Forest": "#38BDF8", "Logistic Regression": "#F472B6"}
for metrics, ls in [(rf_metrics, "-"), (lr_metrics, "--")]:
    fpr, tpr, _ = roc_curve(y_test, metrics["y_prob"])
    ax_roc.plot(fpr, tpr,
                label=f"{metrics['name']}  AUC={metrics['auc_roc']:.3f}",
                color=colors[metrics["name"]], lw=2.5, linestyle=ls)
ax_roc.plot([0, 1], [0, 1], color="#475569", lw=1, linestyle=":", label="Random baseline")
ax_roc.set(xlabel="False Positive Rate", ylabel="True Positive Rate",
           title="ROC Curves", xlim=[0, 1], ylim=[0, 1.02])
ax_roc.legend(loc="lower right", fontsize=9, facecolor="#0F172A", labelcolor="white")
for item in [ax_roc.title, ax_roc.xaxis.label, ax_roc.yaxis.label]:
    item.set_color("white")
ax_roc.tick_params(colors="white")
ax_roc.grid(alpha=0.2, color="#475569")

# Confusion matrices
for ax, metrics in zip(axes[1:], [rf_metrics, lr_metrics]):
    sns.heatmap(metrics["cm"], annot=True, fmt="d", ax=ax,
                cmap="Blues", cbar=False,
                xticklabels=["Attended", "No-Show"],
                yticklabels=["Attended", "No-Show"])
    ax.set(title=f"Confusion Matrix\n{metrics['name']}",
           xlabel="Predicted", ylabel="Actual")
    for item in [ax.title, ax.xaxis.label, ax.yaxis.label]:
        item.set_color("white")
    ax.tick_params(colors="white")

plt.suptitle("HABS No-Show Prediction — Model Evaluation",
             fontsize=14, color="white", y=1.02)
plt.tight_layout()
p1 = f"{OUTPUT_DIR}/habs_roc_confusion.png"
plt.savefig(p1, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"   Saved: {p1}")

# Plot 2: Feature importance
rf_clf      = best_rf.named_steps["clf"]
importances = rf_clf.feature_importances_
feat_imp_df = (
    pd.DataFrame({"feature": FEATURE_COLUMNS, "importance": importances})
    .sort_values("importance", ascending=False)
    .head(15)
)

fig2, ax2 = plt.subplots(figsize=(11, 7))
fig2.patch.set_facecolor("#0F172A")
ax2.set_facecolor("#1E293B")
ax2.barh(feat_imp_df["feature"][::-1], feat_imp_df["importance"][::-1],
         color="#38BDF8", alpha=0.85, edgecolor="#0F172A")
ax2.set(title="Top-15 Feature Importances — Random Forest",
        xlabel="Mean Decrease in Impurity")
for item in [ax2.title, ax2.xaxis.label, ax2.yaxis.label]:
    item.set_color("white")
ax2.tick_params(colors="white")
ax2.grid(axis="x", alpha=0.3, color="#475569")
plt.tight_layout()
p2 = f"{OUTPUT_DIR}/habs_feature_importance.png"
fig2.savefig(p2, dpi=150, bbox_inches="tight", facecolor=fig2.get_facecolor())
plt.close()
print(f"   Saved: {p2}")

# =============================================================================
# STEP 12 — SHAP values (top-10 features)
# =============================================================================

print("\n[12/13] Computing SHAP values ...")

SHAP_SAMPLE  = min(2000, len(X_test))
X_shap       = X_test.sample(n=SHAP_SAMPLE, random_state=SEED)
scaler_step  = best_rf.named_steps["scaler"]
rf_clf_step  = best_rf.named_steps["clf"]

X_shap_scaled = pd.DataFrame(
    scaler_step.transform(X_shap),
    columns=FEATURE_COLUMNS
)

explainer   = shap.TreeExplainer(rf_clf_step)
shap_values = explainer.shap_values(X_shap_scaled)

# For binary classifier shap_values is [class0, class1] — we want class1
shap_vals_class1 = shap_values[1] if isinstance(shap_values, list) else shap_values

# SHAP summary plot
plt.figure(figsize=(11, 7))
shap.summary_plot(
    shap_vals_class1,
    X_shap_scaled,
    feature_names = FEATURE_COLUMNS,
    max_display   = 10,
    show          = False,
    plot_type     = "dot",
)
plt.title("SHAP Summary — Top-10 Feature Impact on No-Show Probability", pad=12)
plt.tight_layout()
p3 = f"{OUTPUT_DIR}/habs_shap_summary.png"
plt.savefig(p3, dpi=150, bbox_inches="tight")
plt.close()
print(f"   Saved: {p3}")

# Mean absolute SHAP ranking
mean_abs_shap = pd.DataFrame({
    "feature"      : FEATURE_COLUMNS,
    "mean_abs_shap": np.abs(shap_vals_class1).mean(axis=0)
}).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

print("\n   Top-10 SHAP feature importances:")
print(mean_abs_shap.head(10).to_string(index=False))

# =============================================================================
# STEP 13a — Serialize artifact
# =============================================================================

print("\n[13a/13] Saving model artifact ...")

artifact = {
    # Full fitted pipeline: StandardScaler + RandomForestClassifier
    "model"             : best_rf,

    # Scaler reference (same object as pipeline step)
    "scaler"            : best_rf.named_steps["scaler"],

    # Canonical feature list — ALWAYS use this for inference
    "feature_columns"   : FEATURE_COLUMNS,

    # Encoding metadata
    "age_group_classes" : age_group_classes_,

    # Decision threshold
    "threshold"         : DECISION_THRESHOLD,

    # Evaluation snapshot (no large arrays)
    "eval_metrics"      : {
        k: v for k, v in rf_metrics.items()
        if k not in ("cm", "y_prob", "y_pred")
    },

    # SHAP results
    "top10_shap_features": mean_abs_shap["feature"].head(10).tolist(),
    "top10_shap_scores"  : mean_abs_shap["mean_abs_shap"].head(10).tolist(),

    # Training provenance
    "model_version"     : "habs_noshow_v1",
    "training_date"     : datetime.date.today().isoformat(),
    "best_cv_auc"       : float(best_cv_auc),
    "best_params"       : best_params,
    "top5_features"     : mean_abs_shap["feature"].head(5).tolist(),
    "n_train_samples"   : int(len(X_train)),
    "n_test_samples"    : int(len(X_test)),
}

ARTIFACT_PATH = f"{OUTPUT_DIR}/habs_noshow_model_v1.joblib"
joblib.dump(artifact, ARTIFACT_PATH, compress=3)
size_mb = os.path.getsize(ARTIFACT_PATH) / (1024 ** 2)
print(f"   ✓ Saved → {ARTIFACT_PATH}  ({size_mb:.1f} MB)")

# =============================================================================
# STEP 13b — Model Card
# =============================================================================

model_card = f"""
╔══════════════════════════════════════════════════════════════════╗
║          HABS NO-SHOW PREDICTION — MODEL CARD                   ║
╠══════════════════════════════════════════════════════════════════╣
║  Model version    : {artifact['model_version']:<44}║
║  Training date    : {artifact['training_date']:<44}║
║  Algorithm        : RandomForestClassifier (class_weight=balanced)║
╠══════════════════════════════════════════════════════════════════╣
║  BEST HYPERPARAMETERS (GridSearchCV 5-fold)                     ║
║  n_estimators     : {str(best_params['clf__n_estimators']):<44}║
║  max_depth        : {str(best_params['clf__max_depth']):<44}║
║  min_samples_split: {str(best_params['clf__min_samples_split']):<44}║
╠══════════════════════════════════════════════════════════════════╣
║  PERFORMANCE (hold-out test, threshold={DECISION_THRESHOLD})                 ║
║  CV AUC-ROC       : {best_cv_auc:<.4f}                                    ║
║  Test AUC-ROC     : {rf_metrics['auc_roc']:<.4f}                                    ║
║  Test F1          : {rf_metrics['f1']:<.4f}                                    ║
║  Test Recall      : {rf_metrics['recall']:<.4f}                                    ║
║  Test Precision   : {rf_metrics['precision']:<.4f}                                    ║
║  Test Accuracy    : {rf_metrics['accuracy']:<.4f}                                    ║
╠══════════════════════════════════════════════════════════════════╣
║  TOP-5 FEATURES (SHAP)                                          ║"""
for i, feat in enumerate(artifact["top5_features"], 1):
    model_card += f"\n║  {i}. {feat:<62}║"
model_card += f"""
╠══════════════════════════════════════════════════════════════════╣
║  Train samples    : {artifact['n_train_samples']:<44,}║
║  Test samples     : {artifact['n_test_samples']:<44,}║
║  Features         : {len(FEATURE_COLUMNS):<44}║
╚══════════════════════════════════════════════════════════════════╝
"""

print(model_card)

card_path = f"{OUTPUT_DIR}/habs_model_card.txt"
with open(card_path, "w") as f:
    f.write(model_card)
print(f"   Model card saved → {card_path}")

# =============================================================================
# FastAPI inference function
# =============================================================================

def predict_no_show(appointment_dict: dict) -> dict:
    """
    FastAPI-compatible inference function.

    Load artifact once at FastAPI startup:
        loaded = joblib.load("habs_noshow_model_v1.joblib")

    Then call this function per request.

    Parameters
    ----------
    appointment_dict : dict
        Example:
        {
            "Gender"                 : "F",
            "Age"                    : 45,
            "lead_time_days"         : 14,
            "appointment_hour"       : 15,   # IST hour (ScheduledDay.dt.hour)
            "day_of_week"            : 2,
            "is_monday"              : 0,
            "patient_age_group"      : "adult",
            "prior_no_show_count"    : 1,
            "prior_appointment_count": 5,
            "has_chronic_condition"  : 1,
            "sms_reminder_sent"      : 1,
            "Scholarship"            : 0,
            "Hipertension"           : 1,
            "Diabetes"               : 0,
            "Alcoholism"             : 0,
            "Handcap"                : 0,
            "fee_tier"               : "mid"
        }

    Returns
    -------
    dict:
        no_show_probability : float (0-1)
        predicted_label     : int (0=attend, 1=no-show)
        threshold           : float
        latency_ms          : float
    """
    loaded          = artifact   # in FastAPI: joblib.load("habs_noshow_model_v1.joblib")
    model           = loaded["model"]
    feature_cols    = loaded["feature_columns"]
    age_classes     = loaded["age_group_classes"]
    threshold       = loaded["threshold"]

    d = appointment_dict.copy()

    # Ordinal encode patient_age_group
    age_group = d.get("patient_age_group", "adult")
    if age_group not in age_classes:
        raise ValueError(f"patient_age_group must be one of {age_classes}")
    d["patient_age_group_enc"] = age_classes.index(age_group)

    # One-hot encode Gender and fee_tier (must match training schema)
    d["Gender_M"]     = int(d.get("Gender", "F") == "M")
    d["fee_tier_low"] = int(d.get("fee_tier", "low") == "low")
    d["fee_tier_mid"] = int(d.get("fee_tier", "low") == "mid")

    # Build DataFrame in canonical column order
    try:
        row = pd.DataFrame([{col: d[col] for col in feature_cols}])
    except KeyError as e:
        raise ValueError(f"Missing feature: {e}. Required: {feature_cols}")

    # Predict — Pipeline applies StandardScaler internally
    t0   = time.perf_counter()
    prob = float(model.predict_proba(row)[0, 1])
    ms   = (time.perf_counter() - t0) * 1000

    return {
        "no_show_probability": round(prob, 4),
        "predicted_label"    : int(prob >= threshold),
        "threshold"          : threshold,
        "latency_ms"         : round(ms, 3),
    }


# =============================================================================
# Smoke tests
# =============================================================================

print("\n── Inference smoke-tests ────────────────────────────────────────────")

test_cases = [
    {
        "case"                   : "HIGH RISK (long wait, prior no-shows, no SMS)",
        "Gender"                 : "M",
        "Age"                    : 28,
        "lead_time_days"         : 45,
        "appointment_hour"       : 8,
        "day_of_week"            : 0,
        "is_monday"              : 1,
        "patient_age_group"      : "adult",
        "prior_no_show_count"    : 3,
        "prior_appointment_count": 5,
        "has_chronic_condition"  : 0,
        "sms_reminder_sent"      : 0,
        "Scholarship"            : 1,
        "Hipertension"           : 0,
        "Diabetes"               : 0,
        "Alcoholism"             : 1,
        "Handcap"                : 0,
        "fee_tier"               : "low",
    },
    {
        "case"                   : "LOW RISK (same-day, SMS sent, chronic senior)",
        "Gender"                 : "F",
        "Age"                    : 68,
        "lead_time_days"         : 1,
        "appointment_hour"       : 10,
        "day_of_week"            : 2,
        "is_monday"              : 0,
        "patient_age_group"      : "senior",
        "prior_no_show_count"    : 0,
        "prior_appointment_count": 10,
        "has_chronic_condition"  : 1,
        "sms_reminder_sent"      : 1,
        "Scholarship"            : 0,
        "Hipertension"           : 1,
        "Diabetes"               : 1,
        "Alcoholism"             : 0,
        "Handcap"                : 0,
        "fee_tier"               : "high",
    },
]

for tc in test_cases:
    case_label = tc.pop("case")
    result = predict_no_show(tc)
    flag = "⚠  NO-SHOW" if result["predicted_label"] == 1 else "✓  WILL ATTEND"
    sla  = "✓ within 5ms" if result["latency_ms"] < 5 else "✗ exceeds 5ms"
    print(f"\n   [{case_label}]")
    print(f"     P(no-show)  = {result['no_show_probability']:.4f}")
    print(f"     Prediction  = {flag}")
    print(f"     Latency     = {result['latency_ms']:.2f} ms  {sla}")

# =============================================================================
# Final summary
# =============================================================================

print("\n" + "=" * 70)
print("  ✓ Pipeline complete!")
print(f"\n  Output files in {OUTPUT_DIR}/:")
output_files = [
    "habs_roc_confusion.png",
    "habs_feature_importance.png",
    "habs_shap_summary.png",
    "habs_noshow_model_v1.joblib",
    "habs_model_card.txt",
]
for fname in output_files:
    fpath = f"{OUTPUT_DIR}/{fname}"
    size  = f"{os.path.getsize(fpath)/1024:.0f} KB" if os.path.exists(fpath) else "not found"
    print(f"    • {fname:<40} {size}")
print("=" * 70)
