# OPSGuardian AI + ArmorIQ

> **Industrial AI Operations Control Center**  
> *Autonomous reliability engineering with cryptographic policy governance.*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.128.1-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?logo=typescript)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-70%20Passed-brightgreen)](file:///C:/Users/deepa/.gemini/antigravity/scratch/opsguardian/python/tests)
[![ArmorIQ](https://img.shields.io/badge/ArmorIQ-Cryptographic%20Governance-orange)](#governance-architecture)

---

## Overview

OPSGuardian AI transforms industrial maintenance workflows by coupling autonomous AI decision-making with **ArmorIQ cryptographic policy governance**.

When high-frequency telemetry indicates abnormal asset degradation (e.g., ISO 10816 Zone D vibration excursions, thermal runaway), OPSGuardian's autonomous agents can inspect asset state, run multi-vector risk evaluations, and autonomously create/assign emergency work orders. 

However, when an agent attempts a **consequential mutation** outside its authorized intent plan (such as derating a production compressor load), ArmorIQ cryptographically intercepts the action into a **HOLD** state until a human supervisor reviews and signs off.

---

## Key Features

- 🛡️ **ArmorIQ Cryptographic Governance**: Intent token signing, out-of-scope interception, and persistent human approval workflows.
- ⚡ **Five-Vector Deterministic Risk Engine**: ISO 10816 compliant scoring evaluating mechanical, thermal, lubrication, production stress, and sensor anomaly vectors.
- 🤖 **Pluggable AI Reasoning with Fallback**: Full Google Gemini Flash diagnostics with automatic fallback to deterministic domain models.
- 🔗 **Tamper-Evident Audit Chain**: Append-only SHA-256 hash chaining of all agent intents, authorizations, approvals, and mutations.
- 📊 **Industrial Control Center UI**: Multi-tab dashboard built with React 19, Tailwind CSS, and lightweight SVG sparklines.
- 🕹️ **Realistic Telemetry Simulator**: 5 configurable failure scenarios with Gaussian sensor noise generation.

---

## Quick Start

### 1. Prerequisites
- Node.js 18+
- Python 3.10+

### 2. Installation
```bash
# Clone repository and enter directory
cd opsguardian

# Install Node dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Run Development Server
```bash
# Set environment (defaults to mock governance and deterministic AI)
$env:ARMORIQ_MODE="mock"
$env:AI_PROVIDER="deterministic"

# Start unified frontend and backend
npm start
```
Access the application at `http://localhost:3000`.

---

## Running Tests

```bash
# Run complete test suite (70 tests)
python -m pytest python/tests/ -v

# Run TypeScript typecheck
npm run typecheck
```

---

## Docker Deployment

```bash
# Build and run containerized stack
docker compose up --build -d

# Check health
curl http://localhost:3000/api/health
```

---

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Security Model & Governance Invariants](docs/SECURITY.md)
- [API Reference](docs/API.md)
- [Autonomous Agent Execution Flow](docs/AGENT_FLOW.md)
- [Interactive Demo Runbook](docs/DEMO_RUNBOOK.md)

---

## License
Apache-2.0
