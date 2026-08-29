# OPSGuardian AI — API Reference

All APIs are available under the `/api` prefix.

## 1. System & Health

- `GET /api/health`: Composite system status (Database, AI Provider, Governance Mode).
- `GET /api/health/ai`: AI Provider health status.
- `GET /api/health/governance`: Governance mode details (`sdk`, `mock`, `disabled`).
- `GET /api/health/database`: Database record counts and connection status.

## 2. Asset & Telemetry

- `GET /api/assets`: List monitored industrial assets with latest sensor values and health score.
- `GET /api/telemetry/{asset_id}?limit=30`: Time-series sensor data points (vibration, temperature, pressure, RPM, load).
- `GET /api/risk/{asset_id}`: Live Five-Vector risk assessment (Mechanical, Thermal, Lubrication, Production Stress, Sensor Anomaly).
- `GET /api/production-config`: List production load settings for all assets.
- `GET /api/production-config/{asset_id}`: Get production load settings for a specific asset.

## 3. Incident Management

- `GET /api/incidents`: List all detected and active incidents.
- `GET /api/incidents/{id}`: Detailed incident information.
- `POST /api/incidents/{id}/acknowledge`: Mark incident status as `INVESTIGATING`.
- `POST /api/incidents/{id}/resolve`: Mark incident status as `RESOLVED`.

## 4. Autonomous Agent Operations

- `POST /api/agent/run`: Trigger end-to-end governed agent task run.
  - Body: `{"task": "string", "asset_id": "AST-01"}`
- `GET /api/agent/tasks`: List historical agent executions.
- `GET /api/agent/tasks/{task_id}`: Get detailed step timeline and status of an agent task.
- `POST /api/agent/tasks/{task_id}/cancel`: Cancel an active agent task.

## 5. Governance & Approvals

- `GET /api/approvals?status=PENDING_APPROVAL`: List pending human review holds.
- `GET /api/approvals/{action_id}`: Get specific approval hold details.
- `POST /api/approvals/{action_id}/approve`: Supervisor approves held action.
  - Body: `{"reviewer": "string", "notes": "string"}`
- `POST /api/approvals/{action_id}/reject`: Supervisor rejects held action.
  - Body: `{"reviewer": "string", "reason": "string"}`

## 6. Cryptographic Audit

- `GET /api/audit?limit=50`: Fetch recent audit trail records.
- `GET /api/audit/verify`: Verify SHA-256 hash chain integrity.

## 7. Telemetry Simulator

- `POST /api/simulator/scenario`: Set scenario (`NORMAL`, `VIBRATION_RISE`, `THERMAL_RUNAWAY`, `LOW_LUBE_PRESSURE`, `COMBINED_BEARING_FAILURE`).
- `POST /api/simulator/tick`: Advance scenario by one tick.
- `POST /api/simulator/stop`: Stop active scenarios.
- `GET /api/simulator/status`: Query active simulator state and tick counts.

## 8. Demo Reset

- `POST /api/demo/reset`: Reset database to baseline demo state (Asset load 100%, vibration excursion, clear approvals).
