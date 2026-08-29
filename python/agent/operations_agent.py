import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional

from python.agent.planner import AgentPlanner
from python.agent.diagnostic_agent import DiagnosticAgent
from python.governance.governed_invoker import governed_invoker
from python.database import get_db_context
from python.models import AgentTask, ProductionConfig, Incident

logger = logging.getLogger("opsguardian.agent.operations")


class OperationsAgent:
    """
    Autonomous Operations Agent for Industrial Reliability & Maintenance.
    Performs telemetry analysis, incident diagnosis, and autonomous work order dispatch.
    All actions are governed by ArmorIQ cryptographic policies.

    Security: AI never directly executes tools. GovernedInvoker is the sole executor.
    """

    def __init__(self):
        self.planner = AgentPlanner()
        self.diagnostic_agent = DiagnosticAgent()
        self.governed_invoker = governed_invoker

    def run(
        self,
        task_prompt: str,
        asset_id: str = "AST-01",
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end autonomous operational workflow:
        1. Capture authorized plan via ArmorIQ
        2. Ingest telemetry (Authorized)
        3. Read asset state (Authorized)
        4. Diagnose bearing fault & calculate risk
        5. Auto-create incident if risk is CRITICAL
        6. Autonomously create work order (Authorized → Executed)
        7. Autonomously assign work order (Authorized → Executed)
        8. Propose load curtailment: set_production_load(asset_id, 65)
        9. ArmorIQ Governance Interception: HOLD → Resource unchanged → Awaits Human Approval
        """
        task_id = f"TSK-{uuid.uuid4().hex[:8].upper()}"
        started_at = datetime.datetime.utcnow()

        # 1. Capture Intent Plan via ArmorIQ
        plan_capture, intent_token, plan_summary = self.planner.build_and_capture_plan(
            task_prompt=task_prompt,
            asset_id=asset_id,
        )
        plan_id = intent_token.plan_id

        # Register task in SQLite
        with get_db_context() as db:
            task_record = AgentTask(
                id=task_id,
                goal=task_prompt,
                asset_id=asset_id,
                status="RUNNING",
                plan_id=plan_id,
                plan_hash=intent_token.plan_hash,
                steps_count=0,
                current_step=0,
                summary="Agent started autonomous execution.",
                started_at=started_at,
                created_at=started_at,
            )
            db.add(task_record)
            db.commit()

        execution_steps: List[Dict[str, Any]] = []

        # 2. Ingest Telemetry (Authorized Step 1)
        self._update_task_step(task_id, 1, "RUNNING")
        step_1 = self.governed_invoker.invoke(
            tool_name="read_telemetry",
            arguments={"asset_id": asset_id},
            task_id=task_id,
            plan_id=plan_id,
        )
        execution_steps.append({
            "step_number": 1,
            "label": "Telemetry Ingestion",
            "action": "read_telemetry",
            "armoriq_status": "ALLOW",
            "execution": "EXECUTED",
            "details": step_1,
        })
        telemetry_data = step_1.get("result", {})

        # 3. Read Asset State (Authorized Step 2)
        self._update_task_step(task_id, 2, "RUNNING")
        step_2 = self.governed_invoker.invoke(
            tool_name="read_asset_state",
            arguments={"asset_id": asset_id},
            task_id=task_id,
            plan_id=plan_id,
        )
        execution_steps.append({
            "step_number": 2,
            "label": "Asset State Read",
            "action": "read_asset_state",
            "armoriq_status": "ALLOW",
            "execution": "EXECUTED",
            "details": step_2,
        })
        asset_state = step_2.get("result", {})

        # 4. Cognitive Diagnostic Reasoning & Risk Engine
        self._update_task_step(task_id, 3, "ANALYZING")
        diagnosis_bundle = self.diagnostic_agent.analyze(
            asset_state=asset_state,
            telemetry=telemetry_data,
        )
        risk_eval = diagnosis_bundle["risk_evaluation"]
        diagnosis = diagnosis_bundle["diagnosis"]
        wo_plan = diagnosis_bundle["work_order_plan"]
        mitigation = diagnosis_bundle["recommended_mitigation"]

        risk_score = risk_eval.get("risk_score", 0)
        risk_level = risk_eval.get("risk_level", "LOW")

        # Update task with risk info
        with get_db_context() as db:
            task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
            if task:
                task.risk_score = risk_score
                task.risk_level = risk_level
                db.commit()

        # 5. Auto-create incident if CRITICAL risk
        if risk_level == "CRITICAL":
            self._auto_create_incident(asset_id, risk_score, risk_eval, task_id, db_close=True)

        # 6. Autonomously Create Maintenance Work Order (Authorized Step 3)
        self._update_task_step(task_id, 4, "EXECUTING")
        step_3 = self.governed_invoker.invoke(
            tool_name="create_work_order",
            arguments={
                "asset_id": asset_id,
                "title": wo_plan["title"],
                "priority": "P1",
                "description": wo_plan["description"],
            },
            task_id=task_id,
            plan_id=plan_id,
        )
        execution_steps.append({
            "step_number": 3,
            "label": "Work Order Created",
            "action": "create_work_order",
            "armoriq_status": "ALLOW",
            "execution": "EXECUTED",
            "details": step_3,
        })
        wo_result = step_3.get("result", {})
        wo_id = wo_result.get("work_order_id", "WO-DEFAULT")

        # 7. Autonomously Assign Work Order (Authorized Step 4)
        self._update_task_step(task_id, 5, "EXECUTING")
        step_4 = self.governed_invoker.invoke(
            tool_name="assign_work_order",
            arguments={
                "work_order_id": wo_id,
                "assignee": "Specialized Turbomachinery Reliability Crew 4",
            },
            task_id=task_id,
            plan_id=plan_id,
        )
        execution_steps.append({
            "step_number": 4,
            "label": "Work Order Assigned",
            "action": "assign_work_order",
            "armoriq_status": "ALLOW",
            "execution": "EXECUTED",
            "details": step_4,
        })

        # 8. Agent proposes load curtailment — this is OUT OF SCOPE and triggers HOLD
        target_load = mitigation.get("target_load_percent", 65)
        self._update_task_step(task_id, 6, "EXECUTING")
        step_5 = self.governed_invoker.invoke(
            tool_name="set_production_load",
            arguments={
                "asset_id": asset_id,
                "load_percent": target_load,
            },
            task_id=task_id,
            plan_id=plan_id,
        )

        execution_steps.append({
            "step_number": 5,
            "label": "Production Load Curtailment",
            "action": "set_production_load",
            "armoriq_status": step_5.get("armoriq_decision", "HOLD"),
            "execution": step_5.get("execution_status", "NOT_EXECUTED"),
            "details": step_5,
        })

        held = step_5.get("status") == "HELD"

        # Verify load not mutated (safety check)
        with get_db_context() as db:
            prod_cfg = db.query(ProductionConfig).filter(ProductionConfig.asset_id == asset_id).first()
            current_db_load = prod_cfg.load_percent if prod_cfg else 100

            task_record = db.query(AgentTask).filter(AgentTask.id == task_id).first()
            if task_record:
                task_record.status = "HELD_PENDING_APPROVAL" if held else "COMPLETED"
                task_record.steps_count = len(execution_steps)
                task_record.current_step = len(execution_steps)
                task_record.requires_approval = held
                task_record.approval_action_id = step_5.get("action_id") if held else None
                task_record.completed_at = datetime.datetime.utcnow() if not held else None
                task_record.summary = (
                    f"Agent created work order {wo_id} and assigned to crew. "
                    f"Production curtailment to {target_load}% {'intercepted and HELD by ArmorIQ' if held else 'executed'}."
                )
                db.commit()

        return {
            "task_id": task_id,
            "plan_id": plan_id,
            "plan_hash": intent_token.plan_hash,
            "goal": task_prompt,
            "status": "HELD_PENDING_APPROVAL" if held else "COMPLETED",
            "plan_summary": plan_summary,
            "execution_steps": execution_steps,
            "work_order_created": wo_result,
            "risk_evaluation": risk_eval,
            "diagnosis_summary": diagnosis.get("diagnostic_result", {}),
            "diagnosis_provider": diagnosis.get("source"),
            "fallback_used": diagnosis.get("fallback_used", False),
            "held_action": step_5 if held else None,
            "current_database_load_percent": current_db_load,
        }

    def _update_task_step(self, task_id: str, step: int, status: str):
        try:
            with get_db_context() as db:
                task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
                if task:
                    task.current_step = step
                    task.status = status
                    db.commit()
        except Exception as e:
            logger.warning("Failed to update task step: %s", e)

    def _auto_create_incident(
        self,
        asset_id: str,
        risk_score: float,
        risk_eval: Dict[str, Any],
        task_id: str,
        db_close: bool = True,
    ):
        """Auto-creates a DETECTED incident when risk is CRITICAL."""
        try:
            with get_db_context() as db:
                existing = db.query(Incident).filter(
                    Incident.asset_id == asset_id,
                    Incident.status.in_(["DETECTED", "INVESTIGATING", "MITIGATING"]),
                ).first()
                if not existing:
                    inc_id = f"INC-AUTO-{uuid.uuid4().hex[:8].upper()}"
                    factors = risk_eval.get("risk_factors", [])
                    description = f"Automatically detected by OperationsAgent. Risk score: {risk_score}/100. Factors: {'; '.join(factors[:3])}"
                    incident = Incident(
                        id=inc_id,
                        asset_id=asset_id,
                        title=f"CRITICAL: Automated Risk Incident — {risk_eval.get('recommended_action', 'Immediate action required')}",
                        severity="CRITICAL",
                        failure_mode=risk_eval.get("iso_10816_zone", "Unknown"),
                        details=description,
                        description=description,
                        risk_score=risk_score,
                        status="DETECTED",
                        detected_at=datetime.datetime.utcnow(),
                        created_by_task_id=task_id,
                    )
                    db.add(incident)
                    db.commit()
                    logger.info("Auto-created incident %s for asset %s (risk=%.1f)", inc_id, asset_id, risk_score)
        except Exception as e:
            logger.error("Failed to auto-create incident: %s", e)
