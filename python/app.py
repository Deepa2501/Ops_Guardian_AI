import os
import sys
from pathlib import Path

# Add project root to sys.path for module resolution
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import datetime
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from python.config import DEFAULT_ASSET_ID, DEFAULT_ASSET_NAME
from python.database import get_db, init_db
from python.models import (
    Asset,
    TelemetryRecord,
    Incident,
    WorkOrder,
    ProductionConfig,
    AgentTask,
    AuditEvent,
    ApprovalRequest,
    AuthorizationEvent,
    TaskRunRequest,
    ApprovalDecisionRequest,
    RejectionDecisionRequest,
    ProductionConfigUpdate,
    ScenarioRequest,
)
from python.agent.orchestrator import orchestrator
from python.governance.approval_manager import approval_manager
from python.governance.governed_invoker import governed_invoker
from python.governance.audit import AuditLogger

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("opsguardian.api")

# Initialize FastAPI App
app = FastAPI(
    title="OpsGuardian AI + ArmorIQ Governance Platform",
    description="Authoritative Python Backend — Autonomous, until it shouldn't be",
    version="2.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    import uuid
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.on_event("startup")
def on_startup():
    """Initializes the database schema and seeds baseline telemetry."""
    init_db()
    logger.info("OpsGuardian API started. DB initialized.")


# ==========================================
# Health Endpoints
# ==========================================

@app.get("/api/health")
def health_check():
    from python.governance.armoriq_adapter import adapter
    from python.services.ai_provider import get_ai_provider
    provider = get_ai_provider()
    ai_health = provider.health_check()
    gov_mode = adapter.get_mode()
    return {
        "status": "healthy",
        "service": "OpsGuardian AI + ArmorIQ Python Gateway",
        "version": "2.0.0",
        "components": {
            "database": "healthy",
            "ai": ai_health.get("status", "unknown"),
            "ai_provider": ai_health.get("provider", "unknown"),
            "governance": "healthy" if gov_mode != "disabled" else "restricted",
            "governance_mode": gov_mode,
        },
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


@app.get("/api/health/ai")
def health_ai():
    from python.services.ai_provider import get_ai_provider
    provider = get_ai_provider()
    return provider.health_check()


@app.get("/api/health/governance")
def health_governance():
    from python.governance.armoriq_adapter import adapter
    mode = adapter.get_mode()
    requested = adapter.get_requested_mode()
    return {
        "status": "healthy" if mode != "disabled" else "restricted",
        "mode": mode,
        "requested_mode": requested,
        "fallback_from_sdk": (requested == "sdk" and mode != "sdk"),
        "consequential_actions": "ENABLED" if mode in ("sdk", "mock") else "BLOCKED",
        "description": {
            "sdk": "Real ArmorIQ SDK enforcement active",
            "mock": "Mock governance simulation (dev/test mode)",
            "disabled": "Governance disabled — only READ_ONLY tools permitted",
        }.get(mode, "Unknown"),
    }


@app.get("/api/health/database")
def health_database(db: Session = Depends(get_db)):
    try:
        asset_count = db.query(Asset).count()
        task_count = db.query(AgentTask).count()
        audit_count = db.query(AuditEvent).count()
        approval_count = db.query(ApprovalRequest).count()
        return {
            "status": "healthy",
            "record_counts": {
                "assets": asset_count,
                "agent_tasks": task_count,
                "audit_events": audit_count,
                "approval_requests": approval_count,
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ==========================================
# Asset & Telemetry Endpoints
# ==========================================

@app.get("/api/assets")
def get_assets(db: Session = Depends(get_db)):
    assets = db.query(Asset).all()
    result = []
    for a in assets:
        prod_cfg = db.query(ProductionConfig).filter(ProductionConfig.asset_id == a.id).first()
        latest_tel = (
            db.query(TelemetryRecord)
            .filter(TelemetryRecord.asset_id == a.id)
            .order_by(TelemetryRecord.timestamp.desc())
            .first()
        )
        result.append({
            "id": a.id,
            "name": a.name,
            "type": a.type,
            "location": a.location,
            "critical_level": a.critical_level,
            "status": a.status,
            "health_score": a.health_score,
            "load_percent": prod_cfg.load_percent if prod_cfg else 100,
            "vibration_mms": latest_tel.vibration_mms if latest_tel else 7.82,
            "temperature_c": latest_tel.temperature_c if latest_tel else 88.5,
            "pressure_bar": latest_tel.pressure_bar if latest_tel else 1.85,
        })
    return result


@app.get("/api/telemetry/{asset_id}")
def get_telemetry_history(asset_id: str, limit: int = 30, db: Session = Depends(get_db)):
    records = (
        db.query(TelemetryRecord)
        .filter(TelemetryRecord.asset_id == asset_id)
        .order_by(TelemetryRecord.timestamp.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat(),
            "vibration_mms": r.vibration_mms,
            "temperature_c": r.temperature_c,
            "pressure_bar": r.pressure_bar,
            "rpm": r.rpm,
            "load_percent": r.load_percent,
            "anomaly_flag": r.anomaly_flag,
            "summary": r.metric_summary,
        }
        for r in records
    ]


# ==========================================
# Incident Endpoints
# ==========================================

@app.get("/api/incidents")
def get_incidents(db: Session = Depends(get_db)):
    incidents = db.query(Incident).order_by(Incident.created_at.desc()).all()
    return [_serialize_incident(i) for i in incidents]


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _serialize_incident(inc)


@app.post("/api/incidents/{incident_id}/acknowledge")
def acknowledge_incident(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    inc.status = "INVESTIGATING"
    inc.acknowledged_at = datetime.datetime.utcnow()
    db.commit()
    return {"status": "acknowledged", "incident_id": incident_id, "new_status": "INVESTIGATING"}


@app.post("/api/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    inc.status = "RESOLVED"
    inc.resolved_at = datetime.datetime.utcnow()
    db.commit()
    return {"status": "resolved", "incident_id": incident_id, "new_status": "RESOLVED"}


def _serialize_incident(i: Incident) -> Dict[str, Any]:
    return {
        "id": i.id,
        "asset_id": i.asset_id,
        "title": i.title,
        "severity": i.severity,
        "failure_mode": i.failure_mode,
        "details": i.details,
        "description": i.description,
        "risk_score": i.risk_score,
        "status": i.status,
        "detected_at": i.detected_at.isoformat() if i.detected_at else None,
        "acknowledged_at": i.acknowledged_at.isoformat() if i.acknowledged_at else None,
        "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
        "created_at": i.created_at.isoformat() if i.created_at else None,
        "created_by_task_id": i.created_by_task_id,
    }


# ==========================================
# Work Orders
# ==========================================

@app.get("/api/work-orders")
def get_work_orders(db: Session = Depends(get_db)):
    work_orders = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).all()
    return [
        {
            "id": w.id,
            "asset_id": w.asset_id,
            "title": w.title,
            "description": w.description,
            "priority": w.priority,
            "assigned_to": w.assigned_to,
            "status": w.status,
            "plan_id": w.plan_id,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in work_orders
    ]


# ==========================================
# Production Config
# ==========================================

@app.get("/api/production-config")
def get_all_production_configs(db: Session = Depends(get_db)):
    configs = db.query(ProductionConfig).all()
    return [
        {
            "asset_id": c.asset_id,
            "load_percent": c.load_percent,
            "max_allowed_load": c.max_allowed_load,
            "safety_interlock": c.safety_interlock,
            "last_modified": c.last_modified.isoformat() if c.last_modified else None,
        }
        for c in configs
    ]


@app.get("/api/production-config/{asset_id}")
def get_production_config(asset_id: str, db: Session = Depends(get_db)):
    cfg = db.query(ProductionConfig).filter(ProductionConfig.asset_id == asset_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Production config not found")
    return {
        "asset_id": cfg.asset_id,
        "load_percent": cfg.load_percent,
        "max_allowed_load": cfg.max_allowed_load,
        "safety_interlock": cfg.safety_interlock,
        "last_modified": cfg.last_modified.isoformat() if cfg.last_modified else None,
    }


# ==========================================
# Agent Endpoints
# ==========================================

@app.post("/api/agent/run")
def run_agent_task(request: TaskRunRequest):
    """Executes the autonomous agent pipeline with full ArmorIQ governance."""
    result = orchestrator.run_operational_task(
        task_prompt=request.task,
        asset_id=request.asset_id,
    )
    return result


@app.get("/api/agent/tasks")
def list_agent_tasks():
    return orchestrator.list_tasks()


@app.get("/api/agent/tasks/{task_id}")
def get_agent_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize_task(task)


@app.post("/api/agent/tasks/{task_id}/cancel")
def cancel_agent_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in ("COMPLETED", "FAILED", "CANCELLED"):
        raise HTTPException(status_code=400, detail=f"Task already in terminal state: {task.status}")
    task.status = "CANCELLED"
    task.completed_at = datetime.datetime.utcnow()
    db.commit()
    return {"status": "cancelled", "task_id": task_id}


def _serialize_task(t: AgentTask) -> Dict[str, Any]:
    return {
        "id": t.id,
        "goal": t.goal,
        "asset_id": t.asset_id,
        "status": t.status,
        "plan_id": t.plan_id,
        "plan_hash": t.plan_hash,
        "steps_count": t.steps_count,
        "current_step": t.current_step,
        "summary": t.summary,
        "risk_score": t.risk_score,
        "risk_level": t.risk_level,
        "requires_approval": t.requires_approval,
        "approval_action_id": t.approval_action_id,
        "started_at": t.started_at.isoformat() if t.started_at else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


# ==========================================
# Approval Endpoints
# ==========================================

@app.get("/api/approvals")
def get_pending_approvals(status: Optional[str] = Query(None)):
    return approval_manager.list_approvals(status=status)


@app.get("/api/approvals/{action_id}")
def get_approval_details(action_id: str):
    approval = approval_manager.get_approval(action_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval


@app.post("/api/approvals/{action_id}/approve")
def approve_held_action(action_id: str, req: Optional[ApprovalDecisionRequest] = None):
    """Human supervisor approves the held action. Triggers ArmorIQ release and governed execution."""
    reviewer = req.reviewer if req else "lead_operations_engineer@opsguardian.ai"
    notes = req.notes if req else "Verified bearing thermal runaway risk. Approved derating setpoint."

    def execute_callback(tool_name, arguments, plan_id, action_id, delegation_id, reviewer):
        return governed_invoker.execute_approved_action(
            tool_name=tool_name,
            arguments=arguments,
            plan_id=plan_id,
            action_id=action_id,
            delegation_id=delegation_id,
            reviewer=reviewer,
        )

    result = approval_manager.process_approval(
        action_id=action_id,
        reviewer=reviewer,
        notes=notes,
        invoker_func=execute_callback,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@app.post("/api/approvals/{action_id}/reject")
def reject_held_action(action_id: str, req: Optional[RejectionDecisionRequest] = None):
    """Human supervisor rejects the held action. Tool remains unexecuted."""
    reviewer = req.reviewer if req else "lead_operations_engineer@opsguardian.ai"
    reason = req.reason if req else "Curtailment rejected due to peak grid tariff commitment."

    result = approval_manager.process_rejection(
        action_id=action_id,
        reviewer=reviewer,
        reason=reason,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


# ==========================================
# Audit & Governance Endpoints
# ==========================================

@app.get("/api/audit")
def get_audit_trail(limit: int = 50):
    return AuditLogger.get_audit_trail(limit=limit)


@app.get("/api/audit/verify")
def verify_audit_chain():
    """Verifies the SHA-256 hash chain integrity of the audit trail."""
    return AuditLogger.verify_chain()


# ==========================================
# Telemetry Simulator Endpoints
# ==========================================

@app.post("/api/simulator/scenario")
def set_simulator_scenario(req: ScenarioRequest):
    """Set a scenario for an asset and write first telemetry tick."""
    from python.services.telemetry_simulator import telemetry_simulator
    return telemetry_simulator.set_scenario(req.asset_id, req.scenario)


@app.post("/api/simulator/tick")
def advance_simulator_tick(req: ScenarioRequest):
    """Advance the simulator by one tick for the given asset."""
    from python.services.telemetry_simulator import telemetry_simulator
    result = telemetry_simulator.advance_tick(req.asset_id)
    if result is None:
        raise HTTPException(status_code=400, detail=f"No active scenario for asset {req.asset_id}")
    return result


@app.post("/api/simulator/stop")
def stop_simulator():
    """Stop all active simulator scenarios."""
    from python.services.telemetry_simulator import telemetry_simulator
    return telemetry_simulator.stop_all()


@app.get("/api/simulator/status")
def get_simulator_status():
    from python.services.telemetry_simulator import telemetry_simulator
    return telemetry_simulator.get_status()


# ==========================================
# Risk Engine Endpoint
# ==========================================

@app.get("/api/risk/{asset_id}")
def get_asset_risk(asset_id: str, db: Session = Depends(get_db)):
    """Calculate current risk score for asset based on latest telemetry."""
    from python.services.risk_engine import risk_engine
    latest = (
        db.query(TelemetryRecord)
        .filter(TelemetryRecord.asset_id == asset_id)
        .order_by(TelemetryRecord.timestamp.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No telemetry found for asset")
    prod_cfg = db.query(ProductionConfig).filter(ProductionConfig.asset_id == asset_id).first()
    load = prod_cfg.load_percent if prod_cfg else 100
    return risk_engine.calculate_asset_risk(
        vibration_mms=latest.vibration_mms,
        temperature_c=latest.temperature_c,
        pressure_bar=latest.pressure_bar,
        rpm=latest.rpm,
        load_percent=load,
    )


# ==========================================
# Demo Reset Endpoint
# ==========================================

@app.post("/api/demo/reset")
def reset_demo_state(db: Session = Depends(get_db)):
    """Resets SQLite database to the baseline demo state."""
    init_db(reset=True)
    return {
        "status": "success",
        "message": "Demo state reset successfully. Production Unit A load is 100%, vibration anomaly is present, and approval queue is cleared.",
        "asset_id": DEFAULT_ASSET_ID,
        "load_percent": 100,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("python.app:app", host="127.0.0.1", port=8001, reload=True)
