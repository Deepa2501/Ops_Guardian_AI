import os
import sys
from pathlib import Path

# Add project root to sys.path for test discovery
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Override to use in-memory SQLite for tests
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ARMORIQ_MODE", "mock")
os.environ.setdefault("AI_PROVIDER", "deterministic")

import pytest
from python.database import init_db


@pytest.fixture(autouse=True)
def setup_test_db():
    """Resets database before each test."""
    init_db(reset=True)
    yield
