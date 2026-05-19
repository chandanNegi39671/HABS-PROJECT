"""
HABS — Alembic Migration: 001 Initial Schema
Revision: 001_initial_schema
Creates all 6 tables with constraints, indexes, and enums.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enums ────────────────────────────────────────────────────────────────
    appointment_status_enum = postgresql.ENUM(
        "booked", "completed", "cancelled", "no_show",
        name="appointment_status_enum",
    )
    notification_type_enum = postgresql.ENUM(
        "sms", "email", "push",
        name="notification_type_enum",
    )
    notification_status_enum = postgresql.ENUM(
        "pending", "sent", "failed",
        name="notification_status_enum",
    )
    appointment_status_enum.create(op.get_bind(), checkfirst=True)
    notification_type_enum.create(op.get_bind(), checkfirst=True)
    notification_status_enum.create(op.get_bind(), checkfirst=True)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name",           sa.String(255), nullable=False),
        sa.Column("email",               sa.String(255), nullable=False),
        sa.Column("phone",               sa.String(20)),
        sa.Column("hashed_password",     sa.String(255), nullable=False),
        sa.Column("date_of_birth",       sa.Date()),
        sa.Column("gender",              sa.String(10)),
        sa.Column("scholarship",         sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("hypertension",        sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("diabetes",            sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("alcoholism",          sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_chronic_condition", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active",           sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email",     "users", ["email"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # ── doctors ───────────────────────────────────────────────────────────────
    op.create_table(
        "doctors",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name",      sa.String(255), nullable=False),
        sa.Column("specialization", sa.String(100), nullable=False),
        sa.Column("email",          sa.String(255), nullable=False),
        sa.Column("phone",          sa.String(20)),
        sa.Column("is_active",      sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at",     sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at",     sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("email", name="uq_doctors_email"),
    )
    op.create_index("ix_doctors_specialization", "doctors", ["specialization"])
    op.create_index("ix_doctors_is_active",      "doctors", ["is_active"])

    # ── appointments ──────────────────────────────────────────────────────────
    op.create_table(
        "appointments",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id",       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id",        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_date", sa.Date(),      nullable=False),
        sa.Column("time_slot",        sa.String(10),  nullable=False),
        sa.Column("appointment_hour", sa.Integer(),   nullable=False),
        sa.Column("lead_time_days",   sa.Integer(),   nullable=False),
        sa.Column("status",           postgresql.ENUM("booked","completed","cancelled","no_show",
                              name="appointment_status_enum",
                              create_type=False),
                  nullable=False, server_default="booked"),
        sa.Column("no_show_risk",      sa.Float()),
        sa.Column("sms_reminder_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes",             sa.Text()),
        sa.Column("booked_at",         sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at",        sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        # ── FKs ──
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"],   ondelete="RESTRICT",
                                name="fk_appointments_patient"),
        sa.ForeignKeyConstraint(["doctor_id"],  ["doctors.id"], ondelete="RESTRICT",
                                name="fk_appointments_doctor"),
        # ── Integrity ──
        sa.UniqueConstraint("doctor_id", "appointment_date", "time_slot",
                            name="uq_doctor_date_slot"),
        sa.CheckConstraint(
            "no_show_risk IS NULL OR (no_show_risk >= 0 AND no_show_risk <= 1)",
            name="ck_no_show_risk_range",
        ),
        sa.CheckConstraint("lead_time_days >= 0",               name="ck_lead_time_positive"),
        sa.CheckConstraint("appointment_hour >= 0 AND appointment_hour <= 23",
                           name="ck_appointment_hour_range"),
    )
    op.create_index("ix_appointments_patient_id",    "appointments", ["patient_id"])
    op.create_index("ix_appointments_doctor_id",     "appointments", ["doctor_id"])
    op.create_index("ix_appointments_status",        "appointments", ["status"])
    op.create_index("ix_appointments_doctor_date",   "appointments", ["doctor_id", "appointment_date"])
    op.create_index("ix_appointments_patient_status","appointments", ["patient_id", "status"])
    op.create_index("ix_appointments_booked_at",     "appointments", ["booked_at"])

    # ── time_slots ────────────────────────────────────────────────────────────
    op.create_table(
        "time_slots",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("doctor_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slot_date",    sa.Date(),      nullable=False),
        sa.Column("slot_time",    sa.String(10),  nullable=False),
        sa.Column("is_available", sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE",
                                name="fk_time_slots_doctor"),
        sa.UniqueConstraint("doctor_id", "slot_date", "slot_time", name="uq_doctor_slot"),
    )
    op.create_index("ix_time_slots_doctor_date",  "time_slots", ["doctor_id", "slot_date"])
    op.create_index("ix_time_slots_available",    "time_slots", ["is_available", "slot_date"])

    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True)),
        sa.Column("type",           postgresql.ENUM("sms","email","push",
                            name="notification_type_enum",
                            create_type=False), nullable=False),
        sa.Column("status",         postgresql.ENUM("pending","sent","failed",
                            name="notification_status_enum",
                            create_type=False),
                  nullable=False, server_default="pending"),
        sa.Column("message",        sa.Text(), nullable=False),
        sa.Column("sent_at",        sa.DateTime(timezone=True)),
        sa.Column("created_at",     sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["user_id"],        ["users.id"],        ondelete="RESTRICT",
                                name="fk_notifications_user"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="SET NULL",
                                name="fk_notifications_appointment"),
    )
    op.create_index("ix_notifications_user_id",        "notifications", ["user_id"])
    op.create_index("ix_notifications_appointment_id", "notifications", ["appointment_id"])
    op.create_index("ix_notifications_status",         "notifications", ["status"])
    op.create_index("ix_notifications_created_at",     "notifications", ["created_at"])

    # ── ml_predictions ────────────────────────────────────────────────────────
    op.create_table(
        "ml_predictions",
        sa.Column("id",                   postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("appointment_id",       postgresql.UUID(as_uuid=True), nullable=False,
                  unique=True),
        sa.Column("model_version",        sa.String(50),  nullable=False,
                  server_default="habs_noshow_v1"),
        sa.Column("no_show_probability",  sa.Float(),     nullable=False),
        sa.Column("predicted_label",      sa.Boolean(),   nullable=False),
        sa.Column("threshold_used",       sa.Float(),     nullable=False, server_default="0.4"),
        sa.Column("input_features",       postgresql.JSONB(), nullable=False),
        sa.Column("created_at",           sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="CASCADE",
                                name="fk_ml_predictions_appointment"),
        sa.CheckConstraint(
            "no_show_probability >= 0 AND no_show_probability <= 1",
            name="ck_no_show_prob_range",
        ),
        sa.CheckConstraint(
            "threshold_used >= 0 AND threshold_used <= 1",
            name="ck_threshold_range",
        ),
    )
    op.create_index("ix_ml_predictions_appointment_id",  "ml_predictions", ["appointment_id"])
    op.create_index("ix_ml_predictions_predicted_label", "ml_predictions", ["predicted_label"])
    op.create_index("ix_ml_predictions_model_version",   "ml_predictions", ["model_version"])

    # ── updated_at auto-update trigger ───────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    for table in ("users", "doctors", "appointments"):
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
        """)


def downgrade() -> None:
    # ── Drop triggers ─────────────────────────────────────────────────────────
    for table in ("users", "doctors", "appointments"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table};")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at();")

    # ── Drop tables (reverse FK order) ────────────────────────────────────────
    op.drop_table("ml_predictions")
    op.drop_table("notifications")
    op.drop_table("time_slots")
    op.drop_table("appointments")
    op.drop_table("doctors")
    op.drop_table("users")

    # ── Drop enums ────────────────────────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS appointment_status_enum;")
    op.execute("DROP TYPE IF EXISTS notification_type_enum;")
    op.execute("DROP TYPE IF EXISTS notification_status_enum;")
