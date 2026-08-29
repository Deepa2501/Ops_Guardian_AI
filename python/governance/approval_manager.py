"""
Persistent Approval Manager — database-backed, survives backend restarts.
"""
import json
import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional

from python.database import get_db_context
from python.models import ApprovalRequest
from python.governance.audit import AuditLogger

logger = logging.getLogger("opsguardian.governance.approval")


class ApprovalManager:
    """
    Manages held actions waiting for human supervisory authorization.
    All state is persisted in SQLite — survives backend restarts.
    """

    def register_hold(
        self,
        task_id: str,
        plan_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        delegation_id: str,
        reason: str,
    ) -> str:
        """Registers an action intercepted and placed on HOLD by ArmorIQ. Returns action_id."""
        action_id = f"ACT-HOLD-{uuid.uuid4().hex[:8].upper()}"

        with get_db_context() as db:
            record = ApprovalRequest(
                action_id=action_id,
                task_id=task_id,
                plan_id=plan_id,
                tool_name=tool_name,
                arguments_json=json.dumps(arguments),
                delegation_id=delegation_id,
                status="PENDING_APPROVAL",
                armoriq_status="HOLD",
                reason=reason,
                created_at=datetime.datetime.utcnow(),
            )
            db.add(record)
            db.commit()

        logger.info("Registered hold: action_id=%s tool=%s", action_id, tool_name)
        return action_id

    def list_approvals(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all approval requests from DB, optionally filtered by status."""
        with get_db_context() as db:
            query = db.query(ApprovalRequest)
            if status:
                query = query.filter(ApprovalRequest.status == status)
            records = query.order_by(ApprovalRequest.created_at.desc()).all()
            return [self._serialize(r) for r in records]

    def get_approval(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Returns a single approval request by action_id."""
        with get_db_context() as db:
            record = db.query(ApprovalRequest).filter(ApprovalRequest.action_id == action_id).first()
            return self._serialize(record) if record else None

    def process_approval(
        self,
        action_id: str,
        reviewer: str,
        notes: str,
        invoker_func,
    ) -> Dict[str, Any]:
        """
        Executes human approval for a held action.
        1. Releases ArmorIQ delegation
        2. Executes the tool via GovernedInvoker
        3. Updates approval record in DB
        4. Logs audit events
        """
        with get_db_context() as db:
            record = db.query(ApprovalRequest).filter(ApprovalRequest.action_id == action_id).first()
            if not record:
                return {"status": "error", "message": f"Approval request {action_id} not found."}
            if record.status != "PENDING_APPROVAL":
                return {
                    "status": "error",
                    "message": f"Action {action_id} is already in state '{record.status}'.",
                }

            delegation_id = record.delegation_id
            tool_name = record.tool_name
            arguments = json.loads(record.arguments_json)
            plan_id = record.plan_id
            task_id = record.task_id

        # Release delegation through ArmorIQ adapter
        from python.governance.armoriq_adapter import adapter
        adapter.release_delegation(delegation_id, "approved")

        # Execute consequential tool through governed invoker
        exec_result = invoker_func(
            tool_name=tool_name,
            arguments=arguments,
            plan_id=plan_id,
            action_id=action_id,
            delegation_id=delegation_id,
            reviewer=reviewer,
        )

        # Update DB record
        with get_db_context() as db:
            record = db.query(ApprovalRequest).filter(ApprovalRequest.action_id == action_id).first()
            if record:
                record.status = "APPROVED"
                record.armoriq_status = "RELEASED"
                record.reviewed_by = reviewer
                record.reviewed_at = datetime.datetime.utcnow()
                record.review_notes = notes
                record.execution_result_json = json.dumps(exec_result)
                db.commit()

        # Audit events
        AuditLogger.log_audit(
            task_id=task_id,
            plan_id=plan_id,
            action_id=action_id,
            tool_name=tool_name,
            arguments=arguments,
            authorization_status="HUMAN_APPROVAL",
            armoriq_status="APPROVED",
            execution_status="PENDING_RELEASE",
            hold_reason=notes,
            human_approval="APPROVED",
            final_result=f"Approved by {reviewer}. Notes: {notes}",
        )
        AuditLogger.log_audit(
            task_id=task_id,
            plan_id=plan_id,
            action_id=action_id,
            tool_name=tool_name,
            arguments=arguments,
            authorization_status="RELEASED",
            armoriq_status="RELEASED",
            execution_status="EXECUTED",
            hold_reason=None,
            human_approval="APPROVED",
            final_result=str(exec_result),
        )

        return {
            "status": "success",
            "action_id": action_id,
            "delegation_id": delegation_id,
            "decision": "APPROVED",
            "execution_result": exec_result,
            "message": f"Action {tool_name} authorized by human supervisor and executed successfully.",
        }

    def process_rejection(
        self,
        action_id: str,
        reviewer: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Rejects a held action; tool remains completely unexecuted."""
        with get_db_context() as db:
            record = db.query(ApprovalRequest).filter(ApprovalRequest.action_id == action_id).first()
            if not record:
                return {"status": "error", "message": f"Approval request {action_id} not found."}
            if record.status != "PENDING_APPROVAL":
                return {
                    "status": "error",
                    "message": f"Action {action_id} is already in state '{record.status}'.",
                }

            delegation_id = record.delegation_id
            tool_name = record.tool_name
            arguments = json.loads(record.arguments_json)
            plan_id = record.plan_id
            task_id = record.task_id

            # Release/reject delegation
            from python.governance.armoriq_adapter import adapter
            adapter.release_delegation(delegation_id, "rejected")

            record.status = "REJECTED"
            record.armoriq_status = "BLOCKED"
            record.reviewed_by = reviewer
            record.reviewed_at = datetime.datetime.utcnow()
            record.review_notes = reason
            db.commit()

        AuditLogger.log_audit(
            task_id=task_id,
            plan_id=plan_id,
            action_id=action_id,
            tool_name=tool_name,
            arguments=arguments,
            authorization_status="HUMAN_REJECTION",
            armoriq_status="BLOCKED",
            execution_status="CANCELLED",
            hold_reason=reason,
            human_approval="REJECTED",
            final_result=f"Action rejected by {reviewer}. Reason: {reason}",
        )

        return {
            "status": "success",
            "action_id": action_id,
            "decision": "REJECTED",
            "message": f"Action {tool_name} rejected by human supervisor. Tool execution cancelled.",
        }

    @staticmethod
    def _serialize(r: ApprovalRequest) -> Dict[str, Any]:
        if r is None:
            return None
        return {
            "action_id": r.action_id,
            "task_id": r.task_id,
            "plan_id": r.plan_id,
            "tool_name": r.tool_name,
            "arguments": json.loads(r.arguments_json) if r.arguments_json else {},
            "delegation_id": r.delegation_id,
            "status": r.status,
            "armoriq_status": r.armoriq_status,
            "reason": r.reason,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "reviewed_by": r.reviewed_by,
            "review_notes": r.review_notes,
            "execution_result": json.loads(r.execution_result_json) if r.execution_result_json else None,
        }


# Global Singleton
approval_manager = ApprovalManager()
