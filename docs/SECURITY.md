# OPSGuardian AI + ArmorIQ — Security Model & Governance Invariants

## Core Security Invariants

OPSGuardian enforces strict multi-layered security controls to ensure autonomous agents cannot perform unauthorized or destructive mutations on critical infrastructure.

### 1. Invariant 1: No Governance Bypass
All consequential tool handlers (`set_production_load`, `create_work_order`, `assign_work_order`, etc.) inspect their received `ExecutionContext`.
- If `context is None` or `not context.verified_by_armoriq`, the tool immediately raises a `GovernanceBypassException`.
- Under no circumstances can direct function calls alter database state or physical configuration.

### 2. Invariant 2: Unknown Tools Blocked by Default
- The `ActionPolicy` maintains an explicit whitelist of registered tools.
- Any tool not in `TOOL_POLICY` is classified as `CRITICAL_CONTROL` and blocked before ArmorIQ evaluation takes place.

### 3. Invariant 3: Zero Frontend Exposure of Secrets
- `GEMINI_API_KEY`, `ARMORIQ_API_KEY`, and internal database credentials are kept exclusively on the server side.
- Frontend communicates with the Python gateway exclusively via reverse proxy in Node.js.

### 4. Invariant 4: Cryptographic Plan Authorizations (Intent Tokens)
- Before the agent performs tasks, `AgentPlanner` builds a formal execution plan.
- The plan is signed and hashed into an `IntentToken`.
- When the agent invokes tools:
  - Authorized tools present in the token $\rightarrow$ `ALLOW`
  - Consequential mutations out-of-scope $\rightarrow$ `HOLD` (triggers Human-in-the-Loop approval)
  - Disallowed tools $\rightarrow$ `BLOCK`

### 5. Invariant 5: Tamper-Evident SHA-256 Audit Trail
- Every invocation, hold, release, and execution records an `AuditEvent`.
- Each record stores:
  - `arguments_hash = SHA256(arguments_json)`
  - `previous_event_hash`
  - `event_hash = SHA256(canonical_event + previous_event_hash)`
- The endpoint `GET /api/audit/verify` detects any tampering or insertion in the audit chain.

### 6. Invariant 6: Persistent Approvals
- Approvals are backed by SQLite (`ApprovalRequest` table).
- Server restarts do not clear pending human approval holds.
