"""
Cryptographic Audit Subsystem with SHA-256 hash chaining.
Audit records are append-only. Each event contains the hash of the previous event,
forming a tamper-evident chain. Modification of any record breaks the chain.
"""
import json
import hashlib
import datetime
from typing import Dict, Any, Optional, List, Tuple

from python.database import get_db_context
from python.models import AuditEvent, AuthorizationEvent


def _canonicalize(event_dict: Dict[str, Any]) -> str:
    """Canonical JSON serialization for deterministic hashing."""
    return json.dumps(event_dict, sort_keys=True, separators=(",", ":"), default=str)


def _compute_hashes(
    arguments_json: str,
    event_data: Dict[str, Any],
    previous_hash: str,
) -> Tuple[str, str]:
    """Computes arguments_hash and event_hash for a new audit event."""
    arguments_hash = hashlib.sha256(arguments_json.encode("utf-8")).hexdigest()
    canonical = _canonicalize(event_data)
    event_hash = hashlib.sha256((canonical + previous_hash).encode("utf-8")).hexdigest()
    return arguments_hash, event_hash


class AuditLogger:
    """
    Cryptographic and Operational Audit Subsystem.
    Records every agent intent, verification result, hold condition,
    human decision, and execution mutation with SHA-256 hash chaining.
    """

    @staticmethod
    def _get_latest_event_hash(db) -> str:
        """Returns the event_hash of the most recent audit event, or empty string if none."""
        latest = db.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        if latest and latest.event_hash:
            return latest.event_hash
        return ""

    @staticmethod
    def record_authorization_event(
        task_id: str,
        plan_id: str,
        action_id: str,
        tool_name: str,
        auth_status: str,
        reason: str,
    ):
        with get_db_context() as db:
            event = AuthorizationEvent(
                task_id=task_id,
                plan_id=plan_id,
                action_id=action_id,
                tool_name=tool_name,
                auth_status=auth_status,
                reason=reason,
                timestamp=datetime.datetime.utcnow(),
            )
            db.add(event)
            db.commit()

    @staticmethod
    def log_audit(
        task_id: str,
        plan_id: str,
        action_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        authorization_status: str,
        armoriq_status: str,
        execution_status: str,
        hold_reason: Optional[str] = None,
        human_approval: str = "NONE",
        final_result: Optional[str] = None,
        agent_id: str = "OpsGuardian-OperationsAgent",
    ) -> int:
        arguments_json = json.dumps(arguments, sort_keys=True)

        with get_db_context() as db:
            previous_hash = AuditLogger._get_latest_event_hash(db)

            # Build the event data dict for hashing (exclude fields not yet known: id, event_hash)
            event_data = {
                "task_id": task_id,
                "plan_id": plan_id,
                "action_id": action_id,
                "agent_id": agent_id,
                "tool_name": tool_name,
                "arguments_json": arguments_json,
                "authorization_status": authorization_status,
                "armoriq_status": armoriq_status,
                "execution_status": execution_status,
                "hold_reason": hold_reason,
                "human_approval": human_approval,
                "final_result": final_result,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            }

            arguments_hash, event_hash = _compute_hashes(
                arguments_json=arguments_json,
                event_data=event_data,
                previous_hash=previous_hash,
            )

            audit = AuditEvent(
                timestamp=datetime.datetime.utcnow(),
                task_id=task_id,
                plan_id=plan_id,
                action_id=action_id,
                agent_id=agent_id,
                tool_name=tool_name,
                arguments_json=arguments_json,
                authorization_status=authorization_status,
                armoriq_status=armoriq_status,
                execution_status=execution_status,
                hold_reason=hold_reason,
                human_approval=human_approval,
                final_result=final_result,
                arguments_hash=arguments_hash,
                previous_event_hash=previous_hash,
                event_hash=event_hash,
            )
            db.add(audit)
            db.commit()
            db.refresh(audit)
            return audit.id

    @staticmethod
    def get_audit_trail(limit: int = 50) -> List[Dict[str, Any]]:
        with get_db_context() as db:
            records = (
                db.query(AuditEvent)
                .order_by(AuditEvent.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat(),
                    "task_id": r.task_id,
                    "plan_id": r.plan_id,
                    "action_id": r.action_id,
                    "agent_id": r.agent_id,
                    "tool_name": r.tool_name,
                    "arguments": json.loads(r.arguments_json) if r.arguments_json else {},
                    "authorization_status": r.authorization_status,
                    "armoriq_status": r.armoriq_status,
                    "execution_status": r.execution_status,
                    "hold_reason": r.hold_reason,
                    "human_approval": r.human_approval,
                    "final_result": r.final_result,
                    "arguments_hash": r.arguments_hash,
                    "previous_event_hash": r.previous_event_hash,
                    "event_hash": r.event_hash,
                }
                for r in records
            ]

    @staticmethod
    def verify_chain() -> Dict[str, Any]:
        """
        Walks all AuditEvent records in insertion order (by id) and verifies
        the SHA-256 hash chain integrity.

        Chain restarts at any event whose previous_event_hash is "" (chain anchor).
        Events with NULL event_hash (pre-migration) are skipped — they break no chain.
        """
        with get_db_context() as db:
            records = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()

            if not records:
                return {"valid": True, "events_checked": 0, "first_invalid_event": None}

            previous_hash = ""
            events_checked = 0

            for record in records:
                # Skip events without hash (pre-migration, seeded without hashing)
                if record.event_hash is None:
                    previous_hash = ""  # reset chain anchor
                    continue

                event_data = {
                    "task_id": record.task_id,
                    "plan_id": record.plan_id,
                    "action_id": record.action_id,
                    "agent_id": record.agent_id,
                    "tool_name": record.tool_name,
                    "arguments_json": record.arguments_json,
                    "authorization_status": record.authorization_status,
                    "armoriq_status": record.armoriq_status,
                    "execution_status": record.execution_status,
                    "hold_reason": record.hold_reason,
                    "human_approval": record.human_approval,
                    "final_result": record.final_result,
                    "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                }

                # If this event is a chain anchor (first in a new run), reset previous_hash
                if record.previous_event_hash == "" or record.previous_event_hash is None:
                    previous_hash = ""

                _, expected_hash = _compute_hashes(
                    arguments_json=record.arguments_json or "",
                    event_data=event_data,
                    previous_hash=previous_hash,
                )

                events_checked += 1

                if expected_hash != record.event_hash:
                    return {
                        "valid": False,
                        "events_checked": events_checked,
                        "first_invalid_event": record.id,
                        "reason": (
                            f"Hash mismatch at event id={record.id}. "
                            f"Expected={expected_hash[:16]}... "
                            f"Got={record.event_hash[:16] if record.event_hash else 'None'}..."
                        ),
                    }

                previous_hash = record.event_hash

            return {
                "valid": True,
                "events_checked": events_checked,
                "first_invalid_event": None,
            }
