import json
import logging
from typing import Dict, Any, Optional
from python.services.ai_provider import get_ai_provider

logger = logging.getLogger("opsguardian.services.gemini")

class GeminiDiagnosticService:
    """
    Diagnostic & Analytical Reasoning Service utilizing the Google Gemini Python SDK.
    Responsible for root-cause analysis, hydrodynamic bearing fault classification,
    and mitigation proposals.
    Note: Gemini provides cognitive reasoning; ArmorIQ provides security & authorization.
    """

    def __init__(self):
        self.provider = get_ai_provider()

    def diagnose_incident(
        self,
        asset_info: Dict[str, Any],
        telemetry: Dict[str, Any],
        risk_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Synthesizes technical telemetry and risk data into root cause diagnosis and mitigation plan.
        """
        # Backward compatibility format wrapper
        metrics = telemetry.get("current_metrics", {})
        
        # Telemetry is expected as a list in new provider
        telemetry_list = [metrics] if metrics else []
        
        result = self.provider.diagnose_incident(
            asset_info=asset_info,
            telemetry=telemetry_list,
            risk_data=risk_data
        )
        
        # Map back to old expected format
        diag = result.get("diagnostic_result", {})
        
        # Convert Mitigation format
        old_mitigation = {
            "curtail_load": diag.get("production_mitigation", {}).get("recommended", False),
            "target_load_percent": diag.get("production_mitigation", {}).get("target_load_percent", 100),
            "rationale": diag.get("production_mitigation", {}).get("rationale", "")
        }
        
        # Convert Work Order format
        wo_title = diag.get("work_order", {}).get("title", "")
        wo_desc = diag.get("work_order", {}).get("description", "")
        
        fallback_data = {
            "failure_mechanism": diag.get("failure_mechanism", ""),
            "root_cause": diag.get("root_cause", ""),
            "severity": diag.get("severity", ""),
            "work_order_title": wo_title,
            "work_order_description": wo_desc,
            "proposed_production_mitigation": old_mitigation
        }

        return {
            "source": result.get("provider", "gemini-reliability-engine"),
            "diagnostic_result": fallback_data,
            "raw_summary": f"Diagnosis: {diag.get('failure_mechanism')}. {diag.get('root_cause')}.",
        }

# Global Singleton
gemini_service = GeminiDiagnosticService()

