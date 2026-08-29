import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship
from pydantic import BaseModel, Field

Base = declarative_base()

# ==========================================
# SQLAlchemy ORM Models
# ==========================================

class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(100), nullable=False)
    location = Column(String(100), nullable=False)
    critical_level = Column(String(50), default="CRITICAL")  # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(50), default="OPERATIONAL")  # OPERATIONAL, DEGRADED, WARNING, MAINTENANCE
    health_score = Column(Float, default=100.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    telemetry_records = relationship("TelemetryRecord", back_populates="asset")
    incidents = relationship("Incident", back_populates="asset")
    work_orders = relationship("WorkOrder", back_populates="asset")
    production_config = relationship("ProductionConfig", back_populates="asset", uselist=False)


class TelemetryRecord(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String(50), ForeignKey("assets.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    vibration_mms = Column(Float, nullable=False)
    temperature_c = Column(Float, nullable=False)
    pressure_bar = Column(Float, nullable=False)
    rpm = Column(Float, nullable=False)
    load_percent = Column(Integer, nullable=False)
    anomaly_flag = Column(Boolean, default=False)
    metric_summary = Column(String(255), nullable=True)

    asset = relationship("Asset", back_populates="telemetry_records")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(50), primary_key=True, index=True)
    asset_id = Column(String(50), ForeignKey("assets.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    severity = Column(String(50), nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    failure_mode = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    description = Column(Text, nullable=True)  # alias for details
    risk_score = Column(Float, nullable=True)
    status = Column(String(50), default="DETECTED")  # DETECTED, INVESTIGATING, MITIGATING, AWAITING_APPROVAL, RESOLVED, CLOSED
    detected_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_by_task_id = Column(String(50), nullable=True)

    asset = relationship("Asset", back_populates="incidents")


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(String(50), primary_key=True, index=True)
    asset_id = Column(String(50), ForeignKey("assets.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(50), default="P1")  # P1, P2, P3, P4
    assigned_to = Column(String(100), default="UNASSIGNED")
    status = Column(String(50), default="CREATED")  # CREATED, ASSIGNED, IN_PROGRESS, COMPLETED
    plan_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    asset = relationship("Asset", back_populates="work_orders")


class ProductionConfig(Base):
    __tablename__ = "production_config"

    asset_id = Column(String(50), ForeignKey("assets.id"), primary_key=True, index=True)
    load_percent = Column(Integer, default=100, nullable=False)
    max_allowed_load = Column(Integer, default=100, nullable=False)
    safety_interlock = Column(String(50), default="NORMAL")  # NORMAL, RESTRICTED, OVERRIDE
    last_modified = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    asset = relationship("Asset", back_populates="production_config")


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(String(50), primary_key=True, index=True)
    goal = Column(Text, nullable=False)
    asset_id = Column(String(50), nullable=True)
    status = Column(String(50), default="QUEUED")
    # QUEUED | PLANNING | RUNNING | ANALYZING | EXECUTING | HELD_PENDING_APPROVAL | COMPLETED | FAILED | CANCELLED
    plan_id = Column(String(100), nullable=True)
    plan_hash = Column(String(100), nullable=True)
    steps_count = Column(Integer, default=0)
    current_step = Column(Integer, default=0)
    summary = Column(Text, nullable=True)
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String(50), nullable=True)
    requires_approval = Column(Boolean, default=False)
    approval_action_id = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class ApprovalRequest(Base):
    """Persistent approval queue — survives backend restarts."""
    __tablename__ = "approval_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(String(100), unique=True, nullable=False, index=True)
    task_id = Column(String(50), nullable=False, index=True)
    plan_id = Column(String(100), nullable=True)
    tool_name = Column(String(100), nullable=False)
    arguments_json = Column(Text, nullable=False)
    delegation_id = Column(String(100), nullable=True)
    status = Column(String(50), default="PENDING_APPROVAL")
    # PENDING_APPROVAL | APPROVED | REJECTED | EXPIRED | EXECUTED | FAILED
    armoriq_status = Column(String(50), default="HOLD")
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(200), nullable=True)
    review_notes = Column(Text, nullable=True)
    execution_result_json = Column(Text, nullable=True)


class AuthorizationEvent(Base):
    __tablename__ = "authorization_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), nullable=False, index=True)
    plan_id = Column(String(100), nullable=True)
    action_id = Column(String(100), nullable=True)
    tool_name = Column(String(100), nullable=False)
    auth_status = Column(String(50), nullable=False)  # ALLOWED, HELD, BLOCKED, RELEASED, REJECTED
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class AuditEvent(Base):
    """Append-only audit log with SHA-256 hash chaining for tamper detection."""
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    task_id = Column(String(50), nullable=False, index=True)
    plan_id = Column(String(100), nullable=True)
    action_id = Column(String(100), nullable=True, index=True)
    agent_id = Column(String(100), default="OpsGuardian-Agent")
    tool_name = Column(String(100), nullable=False)
    arguments_json = Column(Text, nullable=False)
    authorization_status = Column(String(50), nullable=False)
    armoriq_status = Column(String(50), nullable=False)
    execution_status = Column(String(50), nullable=False)
    hold_reason = Column(Text, nullable=True)
    human_approval = Column(String(50), default="NONE")
    final_result = Column(Text, nullable=True)
    # Hash chain fields
    arguments_hash = Column(String(64), nullable=True)   # SHA256(arguments_json)
    previous_event_hash = Column(String(64), nullable=True)
    event_hash = Column(String(64), nullable=True)       # SHA256(canonical_event + previous_hash)


# ==========================================
# Pydantic Schemas for API
# ==========================================

class TaskRunRequest(BaseModel):
    task: str = Field(
        default="Monitor Production Unit A, analyze reliability problems, and autonomously create preventive maintenance work orders.",
        description="The operational objective given to the autonomous agent"
    )
    asset_id: str = Field(default="AST-01")
    allow_gemini: bool = Field(default=True)


class ApprovalDecisionRequest(BaseModel):
    action_id: str
    reviewer: str = Field(default="lead_operations_engineer@opsguardian.ai")
    notes: Optional[str] = Field(default="Verified bearing thermal risk. Authorized load curtailment to 65%.")


class RejectionDecisionRequest(BaseModel):
    action_id: str
    reviewer: str = Field(default="lead_operations_engineer@opsguardian.ai")
    reason: Optional[str] = Field(default="Production curtailment rejected; alternate redundant train must be spun up first.")


class ProductionConfigUpdate(BaseModel):
    asset_id: str
    load_percent: int


class ScenarioRequest(BaseModel):
    asset_id: str = Field(default="AST-01")
    scenario: str = Field(description="NORMAL|VIBRATION_RISE|THERMAL_RUNAWAY|LOW_LUBE_PRESSURE|COMBINED_BEARING_FAILURE")
