# OPSGuardian AI — Autonomous Agent Execution Flow

## End-to-End Governance Lifecycle

This document describes what happens when a user or scheduler initiates an autonomous maintenance run.

```
 User / Scheduler (POST /api/agent/run)
               │
               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 1. Intent Plan Capture (AgentPlanner)                       │
 │    - Translates task prompt into structured tool plan       │
 │    - Mints IntentToken with authorized tools                │
 │    - Computes SHA-256 Plan Hash                             │
 └─────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 2. Telemetry Ingestion (GovernedInvoker)                    │
 │    - Tool: read_telemetry (AST-01)                          │
 │    - Decision: ALLOW (Authorized in Plan)                   │
 │    - Execution: Returns high-vibe & thermal sensor readings │
 └─────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 3. Asset State Read (GovernedInvoker)                       │
 │    - Tool: read_asset_state (AST-01)                        │
 │    - Decision: ALLOW (Authorized in Plan)                   │
 └─────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 4. Cognitive Diagnostics & Deterministic Risk Scoring       │
 │    - 5-Vector Risk Engine computes ISO 10816 Zone D (71.0)  │
 │    - AI Provider reasons on failure mechanism & work order  │
 │    - Auto-creates DETECTED Incident for Critical Risk       │
 └─────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 5. Work Order Creation & Assignment (GovernedInvoker)       │
 │    - Tool: create_work_order & assign_work_order            │
 │    - Decision: ALLOW (Authorized in Plan)                   │
 │    - Execution: P1 Emergency Work Order Created             │
 └─────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 6. Consequential Load Curtailment Attempt                   │
 │    - Tool: set_production_load(asset_id="AST-01", load=65)  │
 │    - Action Policy: CRITICAL_CONTROL (Consequential Mutation│
 │    - ArmorIQ Decision: HOLD (Out of Authorized Plan Scope)  │
 │    - Execution: NOT_EXECUTED (Database load remains 100%)   │
 │    - Persistence: Registered in ApprovalRequest Queue       │
 └─────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 7. Human-in-the-Loop Supervision (Control Center UI)        │
 │    - Supervisor inspects hold reason & delegation ID        │
 │    - Enters review notes and signs approval                 │
 │    - Triggers POST /api/approvals/{id}/approve              │
 │    - ArmorIQ releases delegation                            │
 │    - GovernedInvoker executes curtailment (Load -> 65%)     │
 └─────────────────────────────────────────────────────────────┘
```
