import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = (PROJECT_ROOT / "opsguardian.db").resolve()

# ── API Keys (never expose to frontend) ──────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
ARMORIQ_API_KEY: str = os.getenv("ARMORIQ_API_KEY", "ak_test_opsguardian_automata_2026_demo_key")
ARMORIQ_ENDPOINT: str = os.getenv("ARMORIQ_ENDPOINT", "https://customer-proxy.armoriq.ai")

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH.as_posix()}")

# ── Application ───────────────────────────────────────────────────────────────
APP_URL: str = os.getenv("APP_URL", "http://localhost:3000")

# ── AI Provider configuration ─────────────────────────────────────────────────
# 'gemini'        — Use Gemini API, fall back to deterministic on errors
# 'deterministic' — Use deterministic provider only (no API key required)
AI_PROVIDER: str = os.getenv("AI_PROVIDER", "deterministic")

# ── ArmorIQ Governance Mode ───────────────────────────────────────────────────
# 'sdk'      — Real ArmorIQ Python SDK enforcement
# 'mock'     — Simulate ALLOW/HOLD/BLOCK deterministically (dev/test)
# 'disabled' — READ_ONLY tools allowed; consequential mutations BLOCKED
ARMORIQ_MODE: str = os.getenv("ARMORIQ_MODE", "mock")

# ── Asset / Agent defaults ────────────────────────────────────────────────────
DEFAULT_ASSET_ID: str = "AST-01"
DEFAULT_ASSET_NAME: str = "Production Unit A - Gas Compressor Train 1"
DEFAULT_USER_EMAIL: str = "operator@opsguardian.ai"
AGENT_ID: str = "agent-opsguardian-v1"
