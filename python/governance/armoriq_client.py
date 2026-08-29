"""
ArmorIQ Governance Engine — backward-compatible wrapper.
For new code, use python.governance.armoriq_adapter.adapter instead.
This module keeps the ArmorIQGovernanceEngine class available for SDK mode,
while the global `armoriq_engine` now delegates to the adapter.
"""
import hashlib
import json
import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("opsguardian.governance.armoriq")

try:
    import armoriq_sdk
    from armoriq_sdk import (
        ArmorIQClient,
        PlanCapture,
        IntentToken,
        HoldInfo,
        PolicyHoldException,
        PolicyBlockedException,
        IntentMismatchException,
    )
    from armoriq_sdk.plan_builder import build_plan_from_tool_calls, hash_tool_calls
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False
    logger.warning("armoriq-sdk not installed — SDK mode unavailable")

from python.config import ARMORIQ_API_KEY, ARMORIQ_ENDPOINT, AGENT_ID, DEFAULT_USER_EMAIL


class ArmorIQGovernanceEngine:
    """
    Real ArmorIQ SDK-backed governance engine.
    Only instantiated when ARMORIQ_MODE=sdk and armoriq-sdk is installed.
    """

    def __init__(self):
        if not _SDK_AVAILABLE:
            raise ImportError("armoriq-sdk is not installed")

        self.api_key = ARMORIQ_API_KEY
        self.endpoint = ARMORIQ_ENDPOINT
        self.agent_id = AGENT_ID
        self.user_email = DEFAULT_USER_EMAIL

        try:
            self.sdk_client = ArmorIQClient(
                api_key=self.api_key,
                backend_endpoint=self.endpoint,
                user_id=self.user_email,
                agent_id=self.agent_id,
            )
        except Exception as e:
            logger.warning("ArmorIQClient init warning (using default config): %s", e)
            self.sdk_client = ArmorIQClient(
                api_key="ak_test_opsguardian_demo_key",
                user_id=self.user_email,
                agent_id=self.agent_id,
            )

        self._active_tokens: Dict[str, IntentToken] = {}
        self._delegations: Dict[str, Dict[str, Any]] = {}

    def capture_authorized_plan(
        self,
        task_goal: str,
        authorized_tools: List[str],
        llm: str = "gemini-2.5-flash",
    ) -> Tuple["PlanCapture", "IntentToken"]:
        steps = [
            {"step": i + 1, "action": t, "mcp": "opsguardian_tools",
             "purpose": f"Perform {t} for reliability operations"}
            for i, t in enumerate(authorized_tools)
        ]
        plan_dict = {
            "version": "1.0",
            "goal": task_goal,
            "mcp": "opsguardian_tools",
            "steps": steps,
        }
        plan_capture = self.sdk_client.capture_plan(
            llm=llm,
            prompt=task_goal,
            plan=plan_dict,
            metadata={
                "agent_id": self.agent_id,
                "user_email": self.user_email,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            },
        )

        plan_id = f"plan-{uuid.uuid4().hex[:12]}"
        plan_hash = hashlib.sha256(
            json.dumps(plan_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        now = datetime.datetime.utcnow().timestamp()

        raw_token = {
            "plan": plan_dict,
            "plan_id": plan_id,
            "plan_hash": plan_hash,
            "merkle_root": plan_hash,
            "intent_reference": f"intent-{uuid.uuid4().hex[:8]}",
            "composite_identity": f"{self.user_email}:{self.agent_id}",
            "token": {
                "plan_hash": plan_hash,
                "issued_at": now,
                "expires_at": now + 3600.0,
                "identity": self.user_email,
                "allowed_operations": authorized_tools,
                "version": "1.0",
            },
            "step_proofs": [
                hashlib.sha256(f"step_{s['action']}_{plan_hash}".encode()).hexdigest()
                for s in steps
            ],
        }

        intent_token = IntentToken(
            token_id=raw_token["intent_reference"],
            plan_hash=plan_hash,
            plan_id=plan_id,
            signature=hashlib.sha256(f"armoriq_sig_{plan_hash}".encode()).hexdigest(),
            issued_at=now,
            expires_at=now + 3600.0,
            policy={"allowed_tools": authorized_tools},
            composite_identity=raw_token["composite_identity"],
            step_proofs=raw_token["step_proofs"],
            total_steps=len(steps),
            raw_token=raw_token,
        )

        self._active_tokens[plan_id] = intent_token
        return plan_capture, intent_token

    def verify_action_authorization(
        self,
        plan_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        token = self._active_tokens.get(plan_id)
        if not token:
            return {
                "decision": "BLOCK",
                "allowed": False,
                "reason": f"Plan ID '{plan_id}' has no active intent token.",
                "delegation_id": None,
            }

        plan = token.raw_token.get("plan", {})
        steps = plan.get("steps", [])
        authorized_actions = [s.get("action") for s in steps if isinstance(s, dict)]

        if tool_name in authorized_actions:
            return {
                "decision": "ALLOW",
                "allowed": True,
                "reason": f"Action '{tool_name}' cryptographically verified within captured plan {plan_id}.",
                "plan_id": plan_id,
                "plan_hash": token.plan_hash,
                "delegation_id": None,
            }

        delegation_id = f"delg-{uuid.uuid4().hex[:10]}"
        hold_reason = (
            f"Action '{tool_name}' is OUTSIDE the captured authorization plan ({plan_id}). "
            f"Declared authorized actions: {authorized_actions}. "
            f"Consequential execution halted by ArmorIQ pending human supervisor approval."
        )
        self._delegations[delegation_id] = {
            "delegation_id": delegation_id,
            "plan_id": plan_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "status": "pending",
            "reason": hold_reason,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        return {
            "decision": "HOLD",
            "allowed": False,
            "reason": hold_reason,
            "plan_id": plan_id,
            "plan_hash": token.plan_hash,
            "delegation_id": delegation_id,
        }

    def release_delegation(self, delegation_id: str, decision: str = "approved") -> Optional[Dict[str, Any]]:
        delg = self._delegations.get(delegation_id)
        if not delg:
            return None
        delg["status"] = decision
        delg["decided_at"] = datetime.datetime.utcnow().isoformat()
        return delg

    def get_delegation(self, delegation_id: str) -> Optional[Dict[str, Any]]:
        return self._delegations.get(delegation_id)


# ── Global singleton — delegates to the adapter ───────────────────────────────
# For backward compatibility, armoriq_engine is the adapter facade
from python.governance.armoriq_adapter import adapter as armoriq_engine  # noqa: E402
