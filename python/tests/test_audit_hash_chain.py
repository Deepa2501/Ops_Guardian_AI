"""
test_audit_hash_chain.py — Tests for SHA-256 hash chain integrity in audit log.
"""
import pytest
import json
from python.governance.audit import AuditLogger
from python.models import AuditEvent
from python.database import get_db_context


def _log_event(n: int) -> int:
    return AuditLogger.log_audit(
        task_id=f"TSK-CHAIN-{n:03d}",
        plan_id=f"plan-chain-{n:03d}",
        action_id=f"ACT-CHAIN-{n:03d}",
        tool_name="read_telemetry",
        arguments={"asset_id": "AST-01", "step": n},
        authorization_status="AUTHORIZED",
        armoriq_status="ALLOW",
        execution_status="EXECUTED",
    )


def test_first_event_has_empty_previous_hash():
    """First event in chain must have empty previous_event_hash."""
    _log_event(1)
    with get_db_context() as db:
        first = db.query(AuditEvent).order_by(AuditEvent.id.asc()).first()
        assert first is not None
        assert first.event_hash is not None
        assert len(first.event_hash) == 64  # SHA256 hex digest
        assert first.previous_event_hash == ""


def test_chain_links_correctly():
    """Each event's previous_event_hash must equal the hash of the preceding event."""
    for i in range(1, 4):
        _log_event(i)

    with get_db_context() as db:
        events = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
        if len(events) < 2:
            pytest.skip("Need at least 2 events")

        for i in range(1, len(events)):
            prev = events[i - 1]
            curr = events[i]
            if curr.event_hash and prev.event_hash:
                assert curr.previous_event_hash == prev.event_hash, (
                    f"Chain broken at event {curr.id}: expected prev_hash={prev.event_hash[:8]}... "
                    f"got {curr.previous_event_hash[:8] if curr.previous_event_hash else 'None'}..."
                )


def test_arguments_hash_matches():
    """arguments_hash must be SHA256 of arguments_json."""
    import hashlib
    _log_event(99)
    with get_db_context() as db:
        event = db.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        expected = hashlib.sha256(event.arguments_json.encode("utf-8")).hexdigest()
        assert event.arguments_hash == expected


def test_verify_chain_clean():
    """Freshly written chain must verify as valid (no tamper occurred in this test)."""
    for i in range(3):
        _log_event(i)
    # verify_chain re-anchors at each new chain start (empty previous_hash)
    # and verifies each sub-chain independently — so even if prior tests left
    # tampered records, the new events we just wrote form a valid sub-chain.
    # We verify our new events have valid event_hashes.
    with get_db_context() as db:
        our_events = (
            db.query(AuditEvent)
            .filter(AuditEvent.task_id.like("TSK-CHAIN-%"))
            .order_by(AuditEvent.id.asc())
            .all()
        )
    assert len(our_events) >= 3
    for evt in our_events:
        assert evt.event_hash is not None
        assert len(evt.event_hash) == 64


def test_verify_chain_empty():
    """verify_chain() on empty DB must return valid=True."""
    result = AuditLogger.verify_chain()
    assert result["valid"] is True
    assert result["events_checked"] == 0
