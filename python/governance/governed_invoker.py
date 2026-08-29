import uuid
import logging
from typing import Dict, Any, Optional

from python.governance.armoriq_adapter import adapter as armoriq_engine
from python.governance.action_policy import get_tool_risk_level, ActionRiskLevel, is_known_tool
from python.governance.audit import AuditLogger
from python.tools import ExecutionContext, GovernanceBypassException

import python.tools.telemetry_tools as telemetry_tools
import python.tools.maintenance_tools as maintenance_tools
import python.tools.production_tools as production_tools

logger = logging.getLogger("opsguardian.governance.invoker")


class GovernedInvoker:
    """
    Authoritative Governance Gateway for Autonomous Agent Actions.
    ALL consequential and diagnostic tool calls MUST pass through this class.

    Security invariants:
    - Unknown tools are ALWAYS BLOCKED (never silently allowed)
    - ExecutionContext is ONLY minted here after ArmorIQ authorization
    - AI reasoning never directly executes tools
    """

    def __init__(self):
        self.engine = armoriq_engine

    def invoke(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        task_id: str,
        plan_id: str,
    ) -> Dict[str, Any]:
        """
        Governed execution entrypoint for agent actions.
        """
        action_id = f"ACT-{uuid.uuid4().hex[:8].upper()}"

        # ── Block unknown tools immediately ───────────────────────────────
        if not is_known_tool(tool_name):
            reason = f"SECURITY BLOCK: Tool '{tool_name}' is not registered in ActionPolicy. Unknown tools are never permitted."
            logger.error(reason)
            AuditLogger.log_audit(
                task_id=task_id,
                plan_id=plan_id,
                action_id=action_id,
                tool_name=tool_name,
                arguments=arguments,
                authorization_status="POLICY_BLOCKED",
                armoriq_status="BLOCK",
                execution_status="NOT_EXECUTED",
                hold_reason=reason,
            )
            return {
                "action_id": action_id,
                "status": "BLOCKED",
                "armoriq_decision": "BLOCK",
                "authorized": False,
                "reason": reason,
            }

        # ── Cryptographic Plan Verification via ArmorIQ ───────────────────
        auth_check = self.engine.verify_action_authorization(
            plan_id=plan_id,
            tool_name=tool_name,
            arguments=arguments,
        )

        decision = auth_check["decision"]

        if decision == "ALLOW":
            AuditLogger.record_authorization_event(
                task_id=task_id,
                plan_id=plan_id,
                action_id=action_id,
                tool_name=tool_name,
                auth_status="ALLOWED",
                reason=auth_check["reason"],
            )

            context = ExecutionContext(
                plan_id=plan_id,
                action_id=action_id,
                intent_token=auth_check.get("plan_hash", ""),
                verified_by_armoriq=True,
                authorized_by="ArmorIQ",
            )

            try:
                tool_result = self._dispatch_tool(tool_name, arguments, context)
                AuditLogger.log_audit(
                    task_id=task_id,
                    plan_id=plan_id,
                    action_id=action_id,
                    tool_name=tool_name,
                    arguments=arguments,
                    authorization_status="AUTHORIZED",
                    armoriq_status="ALLOW",
                    execution_status="EXECUTED",
                    hold_reason=None,
                    human_approval="NONE",
                    final_result=str(tool_result),
                )
                return {
                    "action_id": action_id,
                    "status": "EXECUTED",
                    "armoriq_decision": "ALLOW",
                    "authorized": True,
                    "tool_name": tool_name,
                    "result": tool_result,
                }
            except Exception as e:
                logger.error("Tool execution failed: %s", e)
                AuditLogger.log_audit(
                    task_id=task_id,
                    plan_id=plan_id,
                    action_id=action_id,
                    tool_name=tool_name,
                    arguments=arguments,
                    authorization_status="AUTHORIZED",
                    armoriq_status="ALLOW",
                    execution_status="FAILED",
                    hold_reason=str(e),
                    human_approval="NONE",
                    final_result=f"Execution error: {e}",
                )
                return {
                    "action_id": action_id,
                    "status": "FAILED",
                    "armoriq_decision": "ALLOW",
                    "authorized": True,
                    "error": str(e),
                }

        elif decision == "HOLD":
            from python.governance.approval_manager import approval_manager
            delegation_id = auth_check["delegation_id"]
            reason = auth_check["reason"]

            AuditLogger.record_authorization_event(
                task_id=task_id,
                plan_id=plan_id,
                action_id=action_id,
                tool_name=tool_name,
                auth_status="HELD",
                reason=reason,
            )

            held_action_id = approval_manager.register_hold(
                task_id=task_id,
                plan_id=plan_id,
                tool_name=tool_name,
                arguments=arguments,
                delegation_id=delegation_id,
                reason=reason,
            )

            # CRITICAL: Do NOT execute the tool. Resource remains unchanged.
            AuditLogger.log_audit(
                task_id=task_id,
                plan_id=plan_id,
                action_id=held_action_id,
                tool_name=tool_name,
                arguments=arguments,
                authorization_status="OUT_OF_SCOPE",
                armoriq_status="HOLD",
                execution_status="NOT_EXECUTED",
                hold_reason=reason,
                human_approval="NONE",
                final_result="Execution intercepted and halted by ArmorIQ. Pending human approval.",
            )

            return {
                "action_id": held_action_id,
                "status": "HELD",
                "armoriq_decision": "HOLD",
                "authorized": False,
                "tool_name": tool_name,
                "arguments": arguments,
                "delegation_id": delegation_id,
                "reason": reason,
                "execution_status": "NOT_EXECUTED",
                "message": "ARMORIQ ACTION HOLD: Action is outside captured authorization plan. Waiting for human supervisor approval.",
            }

        else:
            # BLOCKED
            AuditLogger.log_audit(
                task_id=task_id,
                plan_id=plan_id,
                action_id=action_id,
                tool_name=tool_name,
                arguments=arguments,
                authorization_status="POLICY_BLOCKED",
                armoriq_status="BLOCK",
                execution_status="NOT_EXECUTED",
                hold_reason=auth_check.get("reason"),
            )
            return {
                "action_id": action_id,
                "status": "BLOCKED",
                "armoriq_decision": "BLOCK",
                "authorized": False,
                "reason": auth_check.get("reason"),
            }

    def execute_approved_action(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        plan_id: str,
        action_id: str,
        delegation_id: str,
        reviewer: str,
    ) -> Dict[str, Any]:
        """
        Called EXCLUSIVELY by ApprovalManager after human supervisor approval.
        Mints a released ExecutionContext and dispatches tool execution.
        """
        context = ExecutionContext(
            plan_id=plan_id,
            action_id=action_id,
            intent_token=f"delegation_token_{delegation_id}",
            verified_by_armoriq=True,
            delegation_id=delegation_id,
            authorized_by=f"Human Supervisor ({reviewer}) via ArmorIQ Release",
        )
        return self._dispatch_tool(tool_name, arguments, context)

    def _dispatch_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: ExecutionContext,
    ) -> Any:
        """Internal dispatch table. Never add an else-fallthrough that allows unknown tools."""
        if tool_name == "read_telemetry":
            return telemetry_tools.get_asset_telemetry(arguments["asset_id"])

        elif tool_name == "read_asset_state":
            return telemetry_tools.get_asset_state(arguments["asset_id"])

        elif tool_name == "create_work_order":
            return maintenance_tools.create_work_order(
                asset_id=arguments["asset_id"],
                title=arguments.get("title", "Preventive Maintenance Work Order"),
                priority=arguments.get("priority", "P1"),
                description=arguments.get("description", ""),
                context=context,
            )

        elif tool_name == "assign_work_order":
            return maintenance_tools.assign_work_order(
                work_order_id=arguments["work_order_id"],
                assignee=arguments.get("assignee", "Turbomachinery Reliability Crew 4"),
                context=context,
            )

        elif tool_name == "set_production_load":
            return production_tools.set_production_load(
                asset_id=arguments["asset_id"],
                load_percent=int(arguments["load_percent"]),
                context=context,
            )

        else:
            # This branch should only be reached for known-but-unimplemented tools
            # Unknown tools are blocked before reaching this method
            raise ValueError(f"Tool '{tool_name}' is registered in policy but not implemented in dispatch table.")


# Global Singleton
governed_invoker = GovernedInvoker()
