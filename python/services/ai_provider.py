from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import os
import json
import traceback

from python.config import AI_PROVIDER

class DiagnosisOutput(BaseModel):
    failure_mechanism: str
    root_cause: str
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[str] = []
    recommended_actions: List[str] = []
    work_order: dict  # {title, priority, description}
    production_mitigation: dict  # {recommended, target_load_percent, rationale}

class AIProvider(ABC):
    @abstractmethod
    def diagnose_incident(self, asset_info: dict, telemetry: list, risk_data: dict) -> Dict[str, Any]:
        ...
        
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        ...
        
    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

class GeminiProvider(AIProvider):
    @property
    def provider_name(self) -> str:
        return "gemini"

    def diagnose_incident(self, asset_info: dict, telemetry: list, risk_data: dict) -> Dict[str, Any]:
        from google import genai
        from python.config import GEMINI_API_KEY
        
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
            
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            prompt = f"""
You are an expert industrial reliability engineer analyzing telemetry from asset {asset_info.get('id')} ({asset_info.get('name')}).
Risk Data: {json.dumps(risk_data, indent=2)}
Recent Telemetry: {json.dumps(telemetry, indent=2)}

Provide a root cause analysis and diagnosis. Output ONLY valid JSON matching this schema:
{{
  "failure_mechanism": "string",
  "root_cause": "string",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "confidence": float (0.0 to 1.0),
  "evidence": ["string"],
  "recommended_actions": ["string"],
  "work_order": {{
    "title": "string",
    "priority": "P1|P2|P3|P4",
    "description": "string"
  }},
  "production_mitigation": {{
    "recommended": boolean,
    "target_load_percent": integer (0 to 100),
    "rationale": "string"
  }}
}}
"""
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            
            raw_text = response.text
            parsed = json.loads(raw_text)
            validated = DiagnosisOutput(**parsed)
            return {
                "provider": self.provider_name,
                "fallback_used": False,
                "diagnostic_result": validated.model_dump()
            }
        except Exception as e:
            # Catch all exceptions: rate limit, quota, auth, timeout, malformed JSON, etc.
            raise Exception(f"Gemini API error: {str(e)}")

    def health_check(self) -> Dict[str, Any]:
        from python.config import GEMINI_API_KEY
        return {
            "status": "healthy" if GEMINI_API_KEY else "unconfigured",
            "provider": self.provider_name
        }

class DeterministicProvider(AIProvider):
    @property
    def provider_name(self) -> str:
        return "deterministic"

    def diagnose_incident(self, asset_info: dict, telemetry: list, risk_data: dict) -> Dict[str, Any]:
        # High-fidelity domain expert diagnosis based on telemetry values
        latest = telemetry[-1] if telemetry else {}
        vib = latest.get("vibration_mms", 0.0)
        temp = latest.get("temperature_c", 0.0)
        
        severity = "LOW"
        mechanism = "Normal wear"
        cause = "Standard operational degradation"
        confidence = 0.7
        evidence = []
        rec_actions = ["Continue monitoring"]
        wo = {"title": "Routine Inspection", "priority": "P4", "description": "Routine check."}
        mitigation = {"recommended": False, "target_load_percent": 100, "rationale": "Parameters nominal"}
        
        if temp > 100 or vib > 10.0:
            severity = "CRITICAL"
            mechanism = "Bearing Thermal Runaway"
            cause = "Lack of lubrication leading to metal-on-metal contact and thermal expansion"
            confidence = 0.95
            evidence = [f"Temperature exceeded 100C ({temp}C)", f"Vibration reached {vib} mm/s"]
            rec_actions = ["Derate production immediately", "Dispatch mechanic for bearing inspection"]
            wo = {"title": "Emergency Bearing Inspection", "priority": "P1", "description": "Immediate bearing inspection required due to thermal runaway."}
            mitigation = {"recommended": True, "target_load_percent": 50, "rationale": "Reduce load to mitigate thermal runaway"}
        elif temp > 80 or vib > 4.5:
            severity = "HIGH"
            mechanism = "Early Bearing Wear"
            cause = "Incipient bearing failure or lubrication degradation"
            confidence = 0.85
            evidence = [f"Elevated temperature ({temp}C)", f"Elevated vibration ({vib} mm/s)"]
            rec_actions = ["Schedule maintenance", "Monitor closely"]
            wo = {"title": "Bearing Inspection", "priority": "P2", "description": "Check bearing and lubrication."}
            mitigation = {"recommended": True, "target_load_percent": 80, "rationale": "Slight derate to reduce stress"}
            
        diag = DiagnosisOutput(
            failure_mechanism=mechanism,
            root_cause=cause,
            severity=severity,
            confidence=confidence,
            evidence=evidence,
            recommended_actions=rec_actions,
            work_order=wo,
            production_mitigation=mitigation
        )
        
        return {
            "provider": self.provider_name,
            "fallback_used": False,
            "diagnostic_result": diag.model_dump()
        }

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "provider": self.provider_name
        }

def get_ai_provider() -> AIProvider:
    if AI_PROVIDER == 'gemini':
        return GeminiProvider()
    return DeterministicProvider()
