# OPSGuardian AI + ArmorIQ — Architecture Overview

OPSGuardian AI is an Industrial AI Operations Control Center combining autonomous reasoning with cryptographic governance policies enforced by ArmorIQ.

## High-Level Architecture

```
                                    +----------------------------------------+
                                    |     React 19 Control Center (UI)       |
                                    | (Vite / Tailwind / SVG Visualizations) |
                                    +-------------------+--------------------+
                                                        |
                                                  HTTP / SSE
                                                        v
                                    +----------------------------------------+
                                    |       Node.js / Express Proxy          |
                                    |   (Process Manager & API Gateway)      |
                                    +-------------------+--------------------+
                                                        |
                                                    Proxy :8001
                                                        v
                                    +----------------------------------------+
                                    |       FastAPI Python Gateway           |
                                    | (REST APIs, Validation, Orchestration) |
                                    +---------+--------------------+---------+
                                              |                    |
                         +--------------------+                    +--------------------+
                         v                                                              v
+------------------------------------+                                +------------------------------------+
|          Agent Subsystem           |                                |        Governance Subsystem        |
| - OperationsAgent (Lifecycle)      |                                | - ArmorIQAdapter (sdk/mock/off)   |
| - AgentPlanner (Plan Authorization)| <============================> | - ActionPolicy (Risk Ratings)     |
| - DiagnosticAgent (AI / Fallback)  |      Cryptographic Checks      | - GovernedInvoker (Enforcement)    |
| - RiskEngine (5 Threat Vectors)    |                                | - ApprovalManager (DB-backed HOLD)|
| - TelemetrySimulator (5 Scenarios) |                                | - AuditLogger (SHA-256 Chain)      |
+------------------------------------+                                +------------------------------------+
                         |                                                              |
                         +--------------------+                    +--------------------+
                                              v                    v
                                    +----------------------------------------+
                                    |          Persistence Layer             |
                                    |      (SQLite via SQLAlchemy 2.0)       |
                                    | Assets | Telemetry | Tasks | Incidents |
                                    | WorkOrders | Approvals | AuditEvents   |
                                    +----------------------------------------+
```

## Key Modules

1. **AI Provider Abstraction (`python/services/ai_provider.py`)**
   - Supports pluggable providers: `GeminiProvider` (LLM reasoning) and `DeterministicProvider` (domain-expert deterministic reasoning).
   - Graceful fallback: If Gemini fails (network, quota, timeout, API key missing), the system automatically falls back to DeterministicProvider with telemetry diagnostics.

2. **Five-Vector Risk Engine (`python/services/risk_engine.py`)**
   - Purely deterministic and ISO 10816 compliant:
     - Mechanical (ISO 10816 vibration zones A/B/C/D, RPM deviation)
     - Thermal (Bearing/process temperature excursions)
     - Lubrication (Oil pressure drops & flow constraints)
     - Production Stress (Load percentage & capacity thresholds)
     - Sensor Anomaly (Signal bounds & physical consistency)

3. **Cryptographic Governance (`python/governance/`)**
   - `ActionPolicy`: Whitelists known tools and assigns risk classifications (`READ_ONLY`, `LOW_RISK_WRITE`, `CRITICAL_CONTROL`).
   - `ArmorIQAdapter`: Bridges to ArmorIQ Python SDK or runs mock intent tokens with matching SHA-256 cryptographic verification.
   - `GovernedInvoker`: Ensures no consequential action executes without a valid, signed `ExecutionContext`.
   - `ApprovalManager`: Persistent SQLite queue for human-in-the-loop approvals when an action triggers a governance `HOLD`.
   - `AuditLogger`: Tamper-evident SHA-256 hash chaining over all agent operations.
