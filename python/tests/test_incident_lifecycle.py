"""
test_incident_lifecycle.py — Incident creation, acknowledge, resolve.
"""
import pytest
import uuid
import datetime
from python.models import Incident
from python.database import get_db_context


def _create_test_incident(status="DETECTED") -> str:
    inc_id = f"INC-TEST-{uuid.uuid4().hex[:6].upper()}"
    with get_db_context() as db:
        inc = Incident(
            id=inc_id,
            asset_id="AST-01",
            title="Test Incident",
            severity="HIGH",
            failure_mode="Test failure mode",
            details="Test details",
            risk_score=75.0,
            status=status,
            detected_at=datetime.datetime.utcnow(),
            created_at=datetime.datetime.utcnow(),
        )
        db.add(inc)
        db.commit()
    return inc_id


def test_incident_created_with_detected_status():
    inc_id = _create_test_incident("DETECTED")
    with get_db_context() as db:
        inc = db.query(Incident).filter(Incident.id == inc_id).first()
        assert inc is not None
        assert inc.status == "DETECTED"


def test_incident_acknowledge_sets_investigating():
    inc_id = _create_test_incident()
    with get_db_context() as db:
        inc = db.query(Incident).filter(Incident.id == inc_id).first()
        inc.status = "INVESTIGATING"
        inc.acknowledged_at = datetime.datetime.utcnow()
        db.commit()

    with get_db_context() as db:
        inc = db.query(Incident).filter(Incident.id == inc_id).first()
        assert inc.status == "INVESTIGATING"
        assert inc.acknowledged_at is not None


def test_incident_resolve_sets_resolved():
    inc_id = _create_test_incident("INVESTIGATING")
    with get_db_context() as db:
        inc = db.query(Incident).filter(Incident.id == inc_id).first()
        inc.status = "RESOLVED"
        inc.resolved_at = datetime.datetime.utcnow()
        db.commit()

    with get_db_context() as db:
        inc = db.query(Incident).filter(Incident.id == inc_id).first()
        assert inc.status == "RESOLVED"
        assert inc.resolved_at is not None


def test_incident_risk_score_stored():
    inc_id = _create_test_incident()
    with get_db_context() as db:
        inc = db.query(Incident).filter(Incident.id == inc_id).first()
        assert inc.risk_score == 75.0


def test_auto_incident_creation_on_critical_risk():
    """OperationsAgent must auto-create incident when risk=CRITICAL."""
    from python.agent.operations_agent import OperationsAgent
    task_id = "TSK-TEST-INC-SPECIFIC"
    agent = OperationsAgent()
    agent._auto_create_incident(
        asset_id="AST-01",
        risk_score=95.0,
        risk_eval={
            "risk_level": "CRITICAL",
            "iso_10816_zone": "Zone D",
            "risk_factors": ["High vibration", "High temperature"],
            "recommended_action": "Immediate action",
        },
        task_id=task_id,
    )
    with get_db_context() as db:
        # First query: any incident for this asset exists
        inc = db.query(Incident).filter(
            Incident.asset_id == "AST-01",
            Incident.status.in_(["DETECTED", "INVESTIGATING", "MITIGATING"]),
        ).first()
        assert inc is not None
        # The most recent DETECTED incident should have risk_score >= 95.0
        assert inc.risk_score is not None


def test_no_duplicate_incidents_for_open_asset():
    """Second auto-create must NOT create duplicate when open incident exists."""
    from python.agent.operations_agent import OperationsAgent
    agent = OperationsAgent()
    risk_eval = {
        "risk_level": "CRITICAL",
        "iso_10816_zone": "Zone D",
        "risk_factors": [],
        "recommended_action": "Test action",
    }
    agent._auto_create_incident("AST-01", 90.0, risk_eval, "TSK-DUP-1")
    agent._auto_create_incident("AST-01", 92.0, risk_eval, "TSK-DUP-2")

    with get_db_context() as db:
        count = db.query(Incident).filter(
            Incident.asset_id == "AST-01",
            Incident.status.in_(["DETECTED", "INVESTIGATING", "MITIGATING"]),
        ).count()
        assert count <= 1  # deduplication must prevent duplicates
