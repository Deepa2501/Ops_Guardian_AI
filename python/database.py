import datetime
import os
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from python.config import DATABASE_URL, DEFAULT_ASSET_ID, DEFAULT_ASSET_NAME
from python.models import (
    Base,
    Asset,
    TelemetryRecord,
    Incident,
    WorkOrder,
    ProductionConfig,
    AgentTask,
    ApprovalRequest,
    AuthorizationEvent,
    AuditEvent,
)

# Ensure SQLite directory exists if file path
if "sqlite" in DATABASE_URL and ":memory:" not in DATABASE_URL:
    db_file_path = DATABASE_URL.replace("sqlite:///", "")
    if db_file_path:
        Path(db_file_path).parent.mkdir(parents=True, exist_ok=True)

# Connect engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30} if "sqlite" in DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _migrate_sqlite_schema():
    """Ensures all new columns exist in SQLite database if upgraded in-place."""
    try:
        with engine.connect() as conn:
            # Check agent_tasks columns
            res = conn.execute(text("PRAGMA table_info(agent_tasks);")).fetchall()
            existing_cols = {row[1] for row in res}
            if existing_cols:
                cols_to_add = [
                    ("asset_id", "VARCHAR(50)"),
                    ("current_step", "INTEGER DEFAULT 0"),
                    ("started_at", "DATETIME"),
                    ("risk_score", "FLOAT"),
                    ("risk_level", "VARCHAR(50)"),
                    ("requires_approval", "BOOLEAN DEFAULT 0"),
                    ("approval_action_id", "VARCHAR(100)"),
                ]
                for col_name, col_type in cols_to_add:
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE agent_tasks ADD COLUMN {col_name} {col_type};"))

            # Check audit_events columns
            res = conn.execute(text("PRAGMA table_info(audit_events);")).fetchall()
            existing_audit = {row[1] for row in res}
            if existing_audit:
                audit_cols = [
                    ("arguments_hash", "VARCHAR(64)"),
                    ("previous_event_hash", "VARCHAR(64)"),
                    ("event_hash", "VARCHAR(64)"),
                ]
                for col_name, col_type in audit_cols:
                    if col_name not in existing_audit:
                        conn.execute(text(f"ALTER TABLE audit_events ADD COLUMN {col_name} {col_type};"))

            # Check incidents columns
            res = conn.execute(text("PRAGMA table_info(incidents);")).fetchall()
            existing_inc = {row[1] for row in res}
            if existing_inc:
                inc_cols = [
                    ("description", "TEXT"),
                    ("risk_score", "FLOAT"),
                    ("detected_at", "DATETIME"),
                    ("acknowledged_at", "DATETIME"),
                    ("resolved_at", "DATETIME"),
                    ("created_by_task_id", "VARCHAR(50)"),
                ]
                for col_name, col_type in inc_cols:
                    if col_name not in existing_inc:
                        conn.execute(text(f"ALTER TABLE incidents ADD COLUMN {col_name} {col_type};"))
            conn.commit()
    except Exception as e:
        pass


def init_db(reset: bool = False):
    """Initializes the database tables and seeds initial production baseline."""
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema()

    with SessionLocal() as db:
        existing_asset = db.query(Asset).filter(Asset.id == DEFAULT_ASSET_ID).first()
        if not existing_asset:
            # Create Primary Production Asset
            asset = Asset(
                id=DEFAULT_ASSET_ID,
                name=DEFAULT_ASSET_NAME,
                type="Centrifugal Gas Compressor (Multi-Stage)",
                location="Refinery Sector 4 - High Pressure Compression Unit",
                critical_level="CRITICAL",
                status="WARNING",
                health_score=46.5,
                created_at=datetime.datetime.utcnow() - datetime.timedelta(days=30),
            )
            db.add(asset)

            # Baseline Production Config (100% Load)
            prod_config = ProductionConfig(
                asset_id=DEFAULT_ASSET_ID,
                load_percent=100,
                max_allowed_load=100,
                safety_interlock="NORMAL",
                last_modified=datetime.datetime.utcnow(),
            )
            db.add(prod_config)

            # Seed realistic high-risk telemetry series
            base_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
            telemetry_samples = [
                (base_time + datetime.timedelta(minutes=0),  3.1,  68.2, 2.38, 4800, 100, False, "Nominal baseline"),
                (base_time + datetime.timedelta(minutes=5),  4.2,  71.4, 2.30, 4810, 100, False, "Slight vibration rise"),
                (base_time + datetime.timedelta(minutes=10), 5.5,  76.0, 2.15, 4790, 100, True,  "ISO 10816 Class C threshold exceeded"),
                (base_time + datetime.timedelta(minutes=15), 6.4,  81.2, 2.02, 4780, 100, True,  "Bearing thermal runaway warning"),
                (base_time + datetime.timedelta(minutes=20), 7.1,  84.8, 1.94, 4760, 100, True,  "Lube oil delta P drop detected"),
                (base_time + datetime.timedelta(minutes=25), 7.82, 88.5, 1.85, 4740, 100, True,  "Critical Vibration 7.82 mm/s, Temp 88.5 C"),
            ]

            for ts, vib, temp, press, rpm, load, anomaly, desc in telemetry_samples:
                record = TelemetryRecord(
                    asset_id=DEFAULT_ASSET_ID,
                    timestamp=ts,
                    vibration_mms=vib,
                    temperature_c=temp,
                    pressure_bar=press,
                    rpm=rpm,
                    load_percent=load,
                    anomaly_flag=anomaly,
                    metric_summary=desc,
                )
                db.add(record)

            # Seed detected incident
            incident = Incident(
                id="INC-2026-084",
                asset_id=DEFAULT_ASSET_ID,
                title="Stage-2 Radial Bearing High Vibration & Thermal Gradient",
                severity="CRITICAL",
                failure_mode="Sub-synchronous hydrodynamic bearing instability & race micro-pitting",
                details="Peak vibration velocity reached 7.82 mm/s (Alarm Limit: 4.5 mm/s). Thrust collar temperature elevated to 88.5°C with 0.55 bar lube pressure degradation.",
                description="Peak vibration velocity reached 7.82 mm/s (Alarm Limit: 4.5 mm/s). Thrust collar temperature elevated to 88.5°C with 0.55 bar lube pressure degradation.",
                risk_score=100.0,
                status="DETECTED",
                detected_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=15),
                created_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=15),
            )
            db.add(incident)

            db.commit()


@contextmanager
def get_db_context():
    """Context manager for standalone python modules/scripts."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
