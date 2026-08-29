import logging
from typing import Dict, Any

from python.services.risk_engine import risk_engine
from python.services.ai_provider import get_ai_provider, DeterministicProvider

logger = logging.getLogger("opsguardian.agent.diagnostic")


class DiagnosticAgent:
    """
    Cognitive Agent Module responsible for processing sensor telemetry,
    evaluating deterministic risk indices, and invoking AI reasoning.

    Security: AI output is structured/validated — AI never directly executes tools.
    GovernedInvoker is the sole executor of tools.
    """

    def __init__(self):
        self.risk_engine = risk_engine

    def analyze(
        self,
        asset_state: Dict[str, Any],
        telemetry: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executes diagnostic reasoning pipeline:
        Telemetry → Risk Engine → AI Provider → Synthesis
        """
        metrics = telemetry.get("current_metrics", {})
        vib = float(metrics.get("vibration_mms", 7.82))
        temp = float(metrics.get("temperature_c", 88.5))
        press = float(metrics.get("pressure_bar", 1.85))
        rpm = float(metrics.get("rpm", 4740))
        load = int(metrics.get("load_percent", 100))

        # 1. Deterministic Risk Evaluation (always runs — no LLM dependency)
        risk_evaluation = self.risk_engine.calculate_asset_risk(
            vibration_mms=vib,
            temperature_c=temp,
            pressure_bar=press,
            rpm=rpm,
            load_percent=load,
        )

        # 2. AI Diagnosis with graceful fallback
        provider = get_ai_provider()
        telemetry_history = telemetry.get("telemetry_history", [metrics])
        fallback_used = False
        fallback_reason = None

        try:
            diagnosis_result = provider.diagnose_incident(
                asset_info=asset_state,
                telemetry=telemetry_history,
                risk_data=risk_evaluation,
            )
        except Exception as e:
            # If primary provider fails (e.g., Gemini quota), fall back to deterministic
            fallback_reason = str(e)
            logger.warning(
                "AI provider '%s' failed (%s). Falling back to DeterministicProvider.",
                provider.provider_name, e,
            )
            fallback_provider = DeterministicProvider()
            diagnosis_result = fallback_provider.diagnose_incident(
                asset_info=asset_state,
                telemetry=telemetry_history,
                risk_data=risk_evaluation,
            )
            fallback_used = True
            diagnosis_result["fallback_used"] = True
            diagnosis_result["fallback_reason"] = fallback_reason

        diag_data = diagnosis_result.get("diagnostic_result", {})

        # 3. Extract structured work order and mitigation plan from validated AI output
        work_order_plan = diag_data.get("work_order", {})
        mitigation = diag_data.get("production_mitigation", {})

        # Normalize work_order fields (backward compat with old gemini_service format)
        if not work_order_plan.get("title"):
            work_order_plan = {
                "title": diag_data.get("work_order_title", "Emergency P1 Turbomachinery Work Order"),
                "priority": diag_data.get("severity", "P1"),
                "description": diag_data.get("work_order_description", "Inspect stage-2 bearing and overhaul lubrication system."),
            }
        if not mitigation:
            legacy_mit = diag_data.get("proposed_production_mitigation", {})
            mitigation = {
                "recommended": legacy_mit.get("curtail_load", True),
                "target_load_percent": legacy_mit.get("target_load_percent", 65),
                "rationale": legacy_mit.get("rationale", "Reduce load to mitigate failure risk."),
            }

        return {
            "risk_evaluation": risk_evaluation,
            "diagnosis": {
                "source": diagnosis_result.get("provider", provider.provider_name),
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason,
                "diagnostic_result": diag_data,
            },
            "recommended_mitigation": mitigation,
            "work_order_plan": {
                "title": work_order_plan.get("title", "Emergency Maintenance Work Order"),
                "priority": work_order_plan.get("priority", "P1"),
                "description": work_order_plan.get("description", "Emergency inspection required."),
            },
        }
