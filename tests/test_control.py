"""Control-plane transaction and recovery tests."""

import pytest

from lakeguard.control import ControlStore


@pytest.fixture
def store(tmp_path):
    """Provide isolated on-disk metadata for each test."""
    result = ControlStore(tmp_path / "metadata.db")
    result.register("orders", {"source": "sample"})
    return result


def test_success_advances_watermark(store):
    run_id = store.start("orders")
    store.succeed(run_id, 12, "2026-11-12T00:00:00Z")
    assert store.watermark("orders") == "2026-11-12T00:00:00Z"
    with store.connection() as db:
        row = db.execute(
            "SELECT status, row_count FROM pipeline_execution_audit WHERE run_id=?",
            (run_id,),
        ).fetchone()
    assert (row["status"], row["row_count"]) == ("SUCCEEDED", 12)


def test_failure_does_not_advance_watermark(store):
    run_id = store.start("orders")
    store.fail(run_id, "Source unavailable")
    assert store.watermark("orders") is None
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM incident_events").fetchone()[0] == 1


def test_watermark_cannot_regress(store):
    first = store.start("orders")
    store.succeed(first, 1, "2026-11-12T00:00:00Z")
    second = store.start("orders")
    with pytest.raises(ValueError, match="backwards"):
        store.succeed(second, 1, "2026-11-11T00:00:00Z")
    assert store.watermark("orders") == "2026-11-12T00:00:00Z"


def test_duplicate_terminal_transition_rejected(store):
    run_id = store.start("orders")
    store.succeed(run_id, 1, "2026-11-12T00:00:00Z")
    with pytest.raises(ValueError):
        store.fail(run_id, "Too late")


def test_unregistered_pipeline_rejected(store):
    with pytest.raises(ValueError, match="Unknown"):
        store.start("unknown")
