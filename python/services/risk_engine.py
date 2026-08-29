"""
Five-Vector Deterministic Risk Engine (ISO 10816 / industrial standards)
Risk scoring is deterministic and explainable — never AI/LLM based.
Produces mechanical, thermal, lubrication, production_stress, and sensor_anomaly vectors.
"""
from typing import Dict, Any, List, Optional


class RiskEngine:
    """
    Deterministic Industrial Risk Assessment Engine.
    Evaluates five threat vectors and produces a composite risk score 0-100.
    """

    @staticmethod
    def calculate_asset_risk(
        vibration_mms: float,
        temperature_c: float,
        pressure_bar: float,
        rpm: float,
        load_percent: int,
        bearing_temperature: Optional[float] = None,
        flow_rate: Optional[float] = None,
        power_kw: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculates holistic operational risk score (0-100) across five threat vectors.
        """
        vectors: Dict[str, Dict[str, Any]] = {}

        # ── 1. Mechanical Vector (vibration, rpm) ─────────────────────────
        # ISO 10816 Class IV (Large Turbomachinery):
        # Zone A: < 2.8 mm/s  (Good)
        # Zone B: 2.8–4.5     (Acceptable)
        # Zone C: 4.5–7.1     (Restricted)
        # Zone D: > 7.1       (Dangerous)
        mech_score = 0.0
        mech_factors: List[str] = []

        if vibration_mms >= 7.1:
            mech_score += 90.0
            mech_factors.append(f"CRITICAL ISO 10816 Zone D Vibration: {vibration_mms:.2f} mm/s (Trip >7.1 mm/s)")
        elif vibration_mms >= 4.5:
            mech_score += 60.0
            mech_factors.append(f"ELEVATED ISO 10816 Zone C Vibration: {vibration_mms:.2f} mm/s")
        elif vibration_mms >= 2.8:
            mech_score += 25.0
            mech_factors.append(f"ISO 10816 Zone B Vibration: {vibration_mms:.2f} mm/s")

        # RPM deviation check (nominal ≈ 4800 for this asset)
        rpm_deviation = abs(rpm - 4800) / 4800
        if rpm_deviation > 0.05:
            mech_score = min(mech_score + 10.0, 100.0)
            mech_factors.append(f"RPM deviation {rpm_deviation*100:.1f}% from nominal (actual: {rpm:.0f})")

        mech_score = min(mech_score, 100.0)
        iso_zone = (
            "Zone D (Unacceptable)" if vibration_mms >= 7.1
            else "Zone C (Restricted)" if vibration_mms >= 4.5
            else "Zone B (Acceptable)" if vibration_mms >= 2.8
            else "Zone A (Good)"
        )
        vectors["mechanical"] = {
            "score": round(mech_score, 1),
            "factors": mech_factors,
            "iso_10816_zone": iso_zone,
            "vibration_mms": vibration_mms,
        }

        # ── 2. Thermal Vector (temperature, bearing temp) ─────────────────
        therm_score = 0.0
        therm_factors: List[str] = []
        effective_temp = max(temperature_c, bearing_temperature or 0)

        if effective_temp >= 100.0:
            therm_score += 95.0
            therm_factors.append(f"EXTREME Thermal Excursion: {effective_temp:.1f}°C (Emergency >100°C)")
        elif effective_temp >= 90.0:
            therm_score += 80.0
            therm_factors.append(f"CRITICAL Thermal Excursion: {effective_temp:.1f}°C (Alarm >85°C)")
        elif effective_temp >= 85.0:
            therm_score += 60.0
            therm_factors.append(f"HIGH Thermal Excursion: {effective_temp:.1f}°C (Threshold 85°C)")
        elif effective_temp >= 75.0:
            therm_score += 35.0
            therm_factors.append(f"Elevated bearing temperature: {effective_temp:.1f}°C")
        elif effective_temp >= 65.0:
            therm_score += 15.0

        if bearing_temperature and bearing_temperature != temperature_c:
            delta = abs(bearing_temperature - temperature_c)
            if delta > 15:
                therm_score = min(therm_score + 15.0, 100.0)
                therm_factors.append(f"High bearing-to-process thermal gradient: {delta:.1f}°C")

        therm_score = min(therm_score, 100.0)
        vectors["thermal"] = {
            "score": round(therm_score, 1),
            "factors": therm_factors,
            "temperature_c": temperature_c,
            "bearing_temperature_c": bearing_temperature,
        }

        # ── 3. Lubrication Vector (lube oil pressure, flow) ───────────────
        lube_score = 0.0
        lube_factors: List[str] = []
        # Normal lube pressure: 2.3–2.5 bar

        if pressure_bar <= 1.7:
            lube_score += 90.0
            lube_factors.append(f"CRITICAL LOW Lube Oil Pressure: {pressure_bar:.2f} bar (Emergency <1.7 bar)")
        elif pressure_bar <= 1.9:
            lube_score += 65.0
            lube_factors.append(f"LOW Lube Oil Pressure: {pressure_bar:.2f} bar (Normal: 2.3–2.5 bar)")
        elif pressure_bar <= 2.1:
            lube_score += 35.0
            lube_factors.append(f"Marginally low lube pressure: {pressure_bar:.2f} bar")
        elif pressure_bar > 2.8:
            lube_score += 20.0
            lube_factors.append(f"High lube pressure: {pressure_bar:.2f} bar (possible blockage)")

        if flow_rate is not None and flow_rate < 0.8:
            lube_score = min(lube_score + 25.0, 100.0)
            lube_factors.append(f"Low lube flow rate: {flow_rate:.2f} L/s")

        lube_score = min(lube_score, 100.0)
        vectors["lubrication"] = {
            "score": round(lube_score, 1),
            "factors": lube_factors,
            "pressure_bar": pressure_bar,
            "flow_rate": flow_rate,
        }

        # ── 4. Production Stress Vector (load percent) ────────────────────
        stress_score = 0.0
        stress_factors: List[str] = []

        if load_percent >= 100:
            stress_score += 70.0
            stress_factors.append(f"Maximum Capacity Stress: Unit at {load_percent}% (nameplate limit)")
        elif load_percent >= 95:
            stress_score += 50.0
            stress_factors.append(f"Near-Maximum Stress: {load_percent}% operational load")
        elif load_percent >= 85:
            stress_score += 30.0
            stress_factors.append(f"High operational load: {load_percent}%")
        elif load_percent >= 75:
            stress_score += 15.0

        # High load compounds thermal risk
        if load_percent >= 90 and effective_temp >= 80:
            stress_score = min(stress_score + 15.0, 100.0)
            stress_factors.append(f"Load-thermal compound risk: {load_percent}% load at {effective_temp:.1f}°C")

        if power_kw is not None:
            # Rough nameplate power = 2500 kW
            power_ratio = power_kw / 2500.0
            if power_ratio > 1.05:
                stress_score = min(stress_score + 20.0, 100.0)
                stress_factors.append(f"Power overload: {power_kw:.0f} kW ({power_ratio*100:.0f}% of nameplate)")

        stress_score = min(stress_score, 100.0)
        vectors["production_stress"] = {
            "score": round(stress_score, 1),
            "factors": stress_factors,
            "load_percent": load_percent,
            "power_kw": power_kw,
        }

        # ── 5. Sensor Anomaly Vector ──────────────────────────────────────
        sensor_score = 0.0
        sensor_factors: List[str] = []

        # Detect physically implausible reading combinations
        if vibration_mms > 12.0:
            sensor_score += 30.0
            sensor_factors.append(f"Possibly saturated vibration sensor: {vibration_mms:.2f} mm/s")
        if temperature_c > 200.0:
            sensor_score += 30.0
            sensor_factors.append(f"Possibly saturated temperature sensor: {temperature_c:.1f}°C")
        if pressure_bar < 0.0:
            sensor_score += 50.0
            sensor_factors.append("Negative pressure reading — sensor fault suspected")
        if rpm < 100 and load_percent > 50:
            sensor_score += 40.0
            sensor_factors.append(f"RPM={rpm} inconsistent with load={load_percent}% — possible tachometer fault")

        # High vibration + normal temp at full load might be sensor issue
        if vibration_mms > 8.0 and temperature_c < 60.0 and load_percent > 80:
            sensor_score += 20.0
            sensor_factors.append("Thermal-vibration inconsistency: high vib without expected thermal signature")

        sensor_score = min(sensor_score, 100.0)
        vectors["sensor_anomaly"] = {
            "score": round(sensor_score, 1),
            "factors": sensor_factors,
        }

        # ── Composite Risk Score ──────────────────────────────────────────
        # Weights: mechanical=35%, thermal=30%, lubrication=20%, production_stress=10%, sensor=5%
        WEIGHTS = {
            "mechanical": 0.35,
            "thermal": 0.30,
            "lubrication": 0.20,
            "production_stress": 0.10,
            "sensor_anomaly": 0.05,
        }
        composite = sum(
            vectors[v]["score"] * WEIGHTS[v] for v in WEIGHTS
        )
        composite = min(round(composite, 1), 100.0)

        if composite >= 70.0:
            level = "CRITICAL"
            recommended_action = "Immediate P1 work order + emergency curtailment to 65% load"
            confidence = 0.95
        elif composite >= 50.0:
            level = "HIGH"
            recommended_action = "Schedule urgent mechanical inspection within 24 hours"
            confidence = 0.85
        elif composite >= 25.0:
            level = "MEDIUM"
            recommended_action = "Continuous acoustic monitoring and routine lubrication check"
            confidence = 0.75
        else:
            level = "LOW"
            recommended_action = "Nominal operation — continue routine monitoring"
            confidence = 0.90

        # Collect all risk factors from all vectors
        all_factors = []
        for v in vectors.values():
            all_factors.extend(v.get("factors", []))

        return {
            "risk_score": composite,
            "risk_level": level,
            "threat_vectors": vectors,
            "risk_factors": all_factors,
            "recommended_action": recommended_action,
            "confidence": confidence,
            "failure_probability_24h": round(min(composite * 0.92, 95.0), 1),
            "iso_10816_zone": vectors["mechanical"]["iso_10816_zone"],
        }


# Global Singleton
risk_engine = RiskEngine()
