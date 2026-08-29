from typing import Dict, Any, List
from python.database import get_db_context
from python.models import Asset, TelemetryRecord, Incident, ProductionConfig


def get_asset_telemetry(asset_id: str) -> Dict[str, Any]:
    """
    Reads real-time operational sensor telemetry for the given asset from SQLite database.
    This is an authorized diagnostic inspection tool.
    """
    with get_db_context() as db:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            return {"error": f"Asset {asset_id} not found"}

        latest_records: List[TelemetryRecord] = (
            db.query(TelemetryRecord)
            .filter(TelemetryRecord.asset_id == asset_id)
            .order_by(TelemetryRecord.timestamp.desc())
            .limit(10)
            .all()
        )

        current = latest_records[0] if latest_records else None

        prod_cfg = db.query(ProductionConfig).filter(ProductionConfig.asset_id == asset_id).first()
        current_load = prod_cfg.load_percent if prod_cfg else 100

        history = [
            {
                "timestamp": r.timestamp.isoformat(),
                "vibration_mms": r.vibration_mms,
                "temperature_c": r.temperature_c,
                "pressure_bar": r.pressure_bar,
                "rpm": r.rpm,
                "load_percent": r.load_percent,
                "anomaly_flag": r.anomaly_flag,
                "summary": r.metric_summary,
            }
            for r in reversed(latest_records)
        ]

        return {
            "asset_id": asset.id,
            "asset_name": asset.name,
            "status": asset.status,
            "health_score": asset.health_score,
            "current_metrics": {
                "vibration_mms": current.vibration_mms if current else 7.82,
                "temperature_c": current.temperature_c if current else 88.5,
                "pressure_bar": current.pressure_bar if current else 1.85,
                "rpm": current.rpm if current else 4740,
                "load_percent": current_load,
                "anomaly_flag": current.anomaly_flag if current else True,
            },
            "telemetry_history": history,
        }


def get_asset_state(asset_id: str) -> Dict[str, Any]:
    """
    Retrieves the comprehensive state, production configuration, and active incidents for the asset.
    """
    with get_db_context() as db:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            return {"error": f"Asset {asset_id} not found"}

        incidents = db.query(Incident).filter(Incident.asset_id == asset_id).all()
        prod_cfg = db.query(ProductionConfig).filter(ProductionConfig.asset_id == asset_id).first()

        return {
            "asset_id": asset.id,
            "name": asset.name,
            "type": asset.type,
            "location": asset.location,
            "critical_level": asset.critical_level,
            "status": asset.status,
            "health_score": asset.health_score,
            "production_config": {
                "load_percent": prod_cfg.load_percent if prod_cfg else 100,
                "max_allowed_load": prod_cfg.max_allowed_load if prod_cfg else 100,
                "safety_interlock": prod_cfg.safety_interlock if prod_cfg else "NORMAL",
            },
            "active_incidents": [
                {
                    "id": inc.id,
                    "title": inc.title,
                    "severity": inc.severity,
                    "failure_mode": inc.failure_mode,
                    "details": inc.details,
                    "status": inc.status,
                }
                for inc in incidents
            ],
        }
