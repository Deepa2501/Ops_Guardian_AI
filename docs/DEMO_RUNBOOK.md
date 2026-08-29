# OPSGuardian AI — Demo Runbook

Follow these steps to demonstrate the full industrial control center and ArmorIQ governance capabilities in under 3 minutes.

## Prerequisites
- Node.js 18+ and Python 3.10+
- Dependencies installed (`npm install` and `pip install -r requirements.txt`)

## Step 1: Start the Platform
```bash
# Windows PowerShell
$env:ARMORIQ_MODE="mock"
$env:AI_PROVIDER="deterministic"
npm start
```
Open your browser at `http://localhost:3000`.

---

## Step 2: Observe Asset Telemetry & Baseline Anomaly
1. Navigate to the **Overview** tab.
2. Note **Production Unit A (AST-01)**:
   - Operating at 100% capacity.
   - Vibration is elevated at **7.82 mm/s** (ISO 10816 Zone D - Unacceptable).
   - Bearing temperature at **88.5°C**, Lube pressure low at **1.85 bar**.
   - Five-Vector Risk score shows **CRITICAL (71.0/100)**.
   - Active Incident `INC-2026-084` is in `DETECTED` status.

---

## Step 3: Trigger the Governed Autonomous Agent
1. Navigate to the **Agent** tab.
2. Review the task prompt:
   > *"Monitor Production Unit A, analyze reliability problems, and autonomously create preventive maintenance work orders."*
3. Click **Deploy Autonomous Agent**.
4. Observe the step timeline in real time:
   - **Step 1 (read_telemetry)**: `ALLOW` $\rightarrow$ Executed
   - **Step 2 (read_asset_state)**: `ALLOW` $\rightarrow$ Executed
   - **Step 3 (create_work_order)**: `ALLOW` $\rightarrow$ Executed (`WO-2026-901` generated)
   - **Step 4 (assign_work_order)**: `ALLOW` $\rightarrow$ Executed (assigned to Crew 4)
   - **Step 5 (set_production_load)**: `HOLD` $\rightarrow$ Intercepted by ArmorIQ!
5. Notice task status: `HELD_PENDING_APPROVAL`.
6. Return to **Overview** — notice the production load is **STILL 100%** (Safety preserved).

---

## Step 4: Review and Release the Governance Hold
1. Navigate to the **Approvals** tab (shows badge `(1)`).
2. Inspect the approval card:
   - **Tool**: `set_production_load`
   - **Hold Reason**: Action is OUTSIDE captured plan.
   - **Arguments**: `{"asset_id": "AST-01", "load_percent": 65}`
   - **Delegation ID**: `delg-mock-...`
3. Enter supervisor notes: *"Verified bearing thermal runaway risk. Approved load curtailment to 65%."*
4. Click **APPROVE & EXECUTE**.
5. Switch to **Overview** tab:
   - Production load is now curtailed to **65%**.
   - The asset is protected from catastrophic failure.

---

## Step 5: Verify Cryptographic Audit Trail
1. Navigate to the **Audit** tab.
2. Observe all logged actions with their corresponding SHA-256 `event_hash` and `arguments_hash`.
3. Click **Verify** $\rightarrow$ Observe `CHAIN INTACT — No tampering detected`.

---

## Step 6: Test Telemetry Simulator Failure Scenarios
1. Navigate to the **Simulator** tab.
2. Select **Thermal Runaway** or **Combined Bearing Failure**.
3. Click **Tick** to advance the simulation and watch real-time sensor metrics and risk recalculations.
