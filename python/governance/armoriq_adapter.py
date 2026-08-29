"""
ArmorIQ Governance Adapter
Supports three modes: sdk | mock | disabled
"""
import hashlib
import json
import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import time

from python.config import ARMORIQ_MODE, ARMORIQ_API_KEY, ARMORIQ_ENDPOINT, AGENT_ID, DEFAULT_USER_EMAIL

logger = logging.getLogger("opsguardian.governance.adapter")


# ── Mock Intent Token ─────────────────────────────────────────────────────────

@dataclass
class MockIntentToken:
    """Lightweight mock of armoriq_sdk.IntentToken for dev/test mode."""
    plan_id: str
    plan_hash: str
    total_steps: int
    authorized_tools: List[str]
    token_id: str = field(default_factory=lambda: f"mock-tok-{uuid.uuid4().hex[:8]}")
    issued_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 3600)
    signature: str = "mock-signature-armoriq"
    composite_identity: str = f"operator@opsguardian.ai:agent-opsguardian-v1"
    step_proofs: List[str] = field(default_factory=list)
    policy: Dict[str, Any] = field(default_factory=dict)
    raw_token: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.raw_token:
            self.raw_token = {
                "plan_id": self.plan_id,
                "plan_hash": self.plan_hash,
                "plan": {
                    "steps": [
                        {"step": i + 1, "action": t, "mcp": "opsguardian_tools"}
                        for i, t in enumerate(self.authorized_tools)
                    ]
                },
            }
        if not self.step_proofs:
            self.step_proofs = [
                hashlib.sha256(f"step_{t}_{self.plan_hash}".encode()).hexdigest()
                for t in self.authorized_tools
            ]
        if not self.policy:
            self.policy = {"allowed_tools": self.authorized_tools}


# ── ArmorIQ Adapter ───────────────────────────────────────────────────────────

class ArmorIQAdapter:
    """
    Governance adapter supporting three modes:

    sdk      — Uses real ArmorIQ Python SDK (requires armoriq-sdk installed)
    mock     — Simulates ALLOW/HOLD/BLOCK deterministically (dev/test)
    disabled — READ_ONLY tools allowed; consequential mutations ALWAYS BLOCKED
    """

    def __init__(self, mode: str = "mock"):
        self._requested_mode = mode
        self.mode = mode
        self._sdk_engine = None

        if mode == "sdk":
            try:
                import armoriq_sdk
                from python.governance.armoriq_client import ArmorIQGovernanceEngine
                self._sdk_engine = ArmorIQGovernanceEngine()
                logger.info("ArmorIQ SDK mode active")
            except ImportError:
                logger.warning("armoriq-sdk not installed — falling back to mock mode")
                self.mode = "mock"
            except Exception as e:
                logger.warning("ArmorIQ SDK initialization failed (%s) — falling back to mock mode", e)
                self.mode = "mock"

        self._mock_tokens: Dict[str, Dict[str, Any]] = {}
        self._mock_delegations: Dict[str, Dict[str, Any]] = {}

        logger.info("ArmorIQ governance mode: %s", self.mode)

    # ── Public API (same interface regardless of mode) ─────────────────────

    def capture_authorized_plan(
        self,
        task_goal: str,
        authorized_tools: List[str],
        llm: str = "gemini-2.5-flash",
    ) -> Tuple[Any, Any]:
        """Returns (plan_capture, intent_token). plan_capture may be None in mock/disabled."""
        if self.mode == "sdk":
            return self._sdk_engine.capture_authorized_plan(task_goal, authorized_tools, llm)
        else:
            return None, self._mock_capture_plan(task_goal, authorized_tools)

    def verify_action_authorization(
        self,
        plan_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        if self.mode == "sdk":
            return self._sdk_engine.verify_action_authorization(plan_id, tool_name, arguments)
        elif self.mode == "mock":
            return self._mock_verify(plan_id, tool_name, arguments)
        else:  # disabled
            return self._disabled_verify(tool_name)

    def release_delegation(self, delegation_id: str, decision: str = "approved") -> Optional[Dict[str, Any]]:
        if self.mode == "sdk":
            return self._sdk_engine.release_delegation(delegation_id, decision)
        else:
            return self._mock_release(delegation_id, decision)

    def get_delegation(self, delegation_id: str) -> Optional[Dict[str, Any]]:
        if self.mode == "sdk":
            return self._sdk_engine.get_delegation(delegation_id)
        return self._mock_delegations.get(delegation_id)

    def get_mode(self) -> str:
        return self.mode

    def get_requested_mode(self) -> str:
        return self._requested_mode

    # ── Mock Implementation ────────────────────────────────────────────────

    def _mock_capture_plan(self, task_goal: str, authorized_tools: List[str]) -> MockIntentToken:
        plan_id = f"plan-mock-{uuid.uuid4().hex[:12]}"
        plan_dict = {
            "version": "1.0",
            "goal": task_goal,
            "mcp": "opsguardian_tools",
            "steps": [
                {"step": i + 1, "action": t, "mcp": "opsguardian_tools",
                 "purpose": f"Perform {t} for reliability operations"}
                for i, t in enumerate(authorized_tools)
            ],
        }
        plan_hash = hashlib.sha256(
            json.dumps(plan_dict, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

        self._mock_tokens[plan_id] = {
            "tools": authorized_tools,
            "plan_hash": plan_hash,
            "plan": plan_dict,
        }

        token = MockIntentToken(
            plan_id=plan_id,
            plan_hash=plan_hash,
            authorized_tools=authorized_tools,
            total_steps=len(authorized_tools),
        )
        return token

    def _mock_verify(
        self,
        plan_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        token_data = self._mock_tokens.get(plan_id)
        if not token_data:
            return {
                "decision": "BLOCK",
                "allowed": False,
                "reason": f"Plan ID '{plan_id}' not found in mock governance engine.",
                "delegation_id": None,
            }

        if tool_name in token_data["tools"]:
            return {
                "decision": "ALLOW",
                "allowed": True,
                "reason": f"Action '{tool_name}' verified within captured plan {plan_id}.",
                "plan_id": plan_id,
                "plan_hash": token_data["plan_hash"],
                "delegation_id": None,
            }

        # Out of scope — generate delegation hold
        delegation_id = f"delg-mock-{uuid.uuid4().hex[:10]}"
        hold_reason = (
            f"Action '{tool_name}' is OUTSIDE the captured authorization plan ({plan_id}). "
            f"Authorized actions: {token_data['tools']}. "
            f"Consequential execution halted by ArmorIQ MOCK — pending human supervisor approval."
        )
        self._mock_delegations[delegation_id] = {
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
            "plan_hash": token_data["plan_hash"],
            "delegation_id": delegation_id,
        }

    def _disabled_verify(self, tool_name: str) -> Dict[str, Any]:
        from python.governance.action_policy import get_tool_risk_level, ActionRiskLevel
        level = get_tool_risk_level(tool_name)
        if level == ActionRiskLevel.READ_ONLY:
            return {
                "decision": "ALLOW",
                "allowed": True,
                "reason": f"ARMORIQ_MODE=disabled: READ_ONLY tool '{tool_name}' is permitted.",
                "delegation_id": None,
            }
        return {
            "decision": "BLOCK",
            "allowed": False,
            "reason": (
                f"ARMORIQ_MODE=disabled: Consequential action '{tool_name}' is BLOCKED. "
                "Enable ARMORIQ_MODE=mock or ARMORIQ_MODE=sdk to allow governed execution."
            ),
            "delegation_id": None,
        }

    def _mock_release(self, delegation_id: str, decision: str) -> Optional[Dict[str, Any]]:
        delg = self._mock_delegations.get(delegation_id)
        if delg:
            delg["status"] = decision
            delg["decided_at"] = datetime.datetime.utcnow().isoformat()
        return delg


# ── Global Singleton ──────────────────────────────────────────────────────────
adapter = ArmorIQAdapter(mode=ARMORIQ_MODE)
