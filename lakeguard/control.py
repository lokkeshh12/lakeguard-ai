"""Local SQLite control plane; replace adapter with Unity Catalog for deployment."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def utc_now() -> str:
    """Return a comparable UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


class ControlStore:
    """Persist pipeline registrations, execution audit, watermarks and incidents."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Create a transactional SQLite connection."""
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA busy_timeout = 30000")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create local metadata schema if absent."""
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS pipeline_config (
                    pipeline_id TEXT PRIMARY KEY,
                    config_json TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS pipeline_execution_audit (
                    run_id TEXT PRIMARY KEY,
                    pipeline_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('RUNNING','SUCCEEDED','FAILED')),
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    row_count INTEGER,
                    error TEXT
                );
                CREATE TABLE IF NOT EXISTS pipeline_watermark (
                    pipeline_id TEXT PRIMARY KEY,
                    watermark TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS incident_events (
                    incident_id TEXT PRIMARY KEY,
                    pipeline_id TEXT NOT NULL,
                    run_id TEXT,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

    def register(self, pipeline_id: str, config: dict) -> None:
        """Register or update a pipeline's configuration."""
        with self.connection() as db:
            db.execute(
                """INSERT INTO pipeline_config(pipeline_id, config_json)
                   VALUES (?, ?) ON CONFLICT(pipeline_id)
                   DO UPDATE SET config_json=excluded.config_json""",
                (pipeline_id, json.dumps(config, sort_keys=True)),
            )

    def start(self, pipeline_id: str) -> str:
        """Begin a new audited run; return its unique ID."""
        run_id = str(uuid4())
        with self.connection() as db:
            if (
                db.execute(
                    "SELECT 1 FROM pipeline_config WHERE pipeline_id=? AND enabled=1",
                    (pipeline_id,),
                ).fetchone()
                is None
            ):
                raise ValueError(f"Unknown or disabled pipeline: {pipeline_id}")
            db.execute(
                """INSERT INTO pipeline_execution_audit
                   (run_id, pipeline_id, status, started_at)
                   VALUES (?, ?, 'RUNNING', ?)""",
                (run_id, pipeline_id, utc_now()),
            )
        return run_id

    def succeed(self, run_id: str, row_count: int, watermark: str) -> None:
        """Mark success and advance watermark in the same metadata transaction."""
        if row_count < 0:
            raise ValueError("row_count must not be negative")
        with self.connection() as db:
            row = db.execute(
                "SELECT pipeline_id, status FROM pipeline_execution_audit WHERE run_id=?",
                (run_id,),
            ).fetchone()
            if row is None or row["status"] != "RUNNING":
                raise ValueError("Run is missing or is not RUNNING")
            pipeline_id = row["pipeline_id"]
            old = db.execute(
                "SELECT watermark FROM pipeline_watermark WHERE pipeline_id=?",
                (pipeline_id,),
            ).fetchone()
            if old is not None and watermark < old["watermark"]:
                raise ValueError("Watermark must not move backwards")
            db.execute(
                """INSERT INTO pipeline_watermark(pipeline_id, watermark, updated_at)
                   VALUES (?, ?, ?) ON CONFLICT(pipeline_id)
                   DO UPDATE SET watermark=excluded.watermark,
                                 updated_at=excluded.updated_at""",
                (pipeline_id, watermark, utc_now()),
            )
            db.execute(
                """UPDATE pipeline_execution_audit SET status='SUCCEEDED',
                   finished_at=?, row_count=? WHERE run_id=?""",
                (utc_now(), row_count, run_id),
            )

    def fail(self, run_id: str, message: str) -> str:
        """Mark a running execution failed and create an incident."""
        incident_id = str(uuid4())
        with self.connection() as db:
            row = db.execute(
                "SELECT pipeline_id, status FROM pipeline_execution_audit WHERE run_id=?",
                (run_id,),
            ).fetchone()
            if row is None or row["status"] != "RUNNING":
                raise ValueError("Run is missing or is not RUNNING")
            db.execute(
                """UPDATE pipeline_execution_audit SET status='FAILED',
                   finished_at=?, error=? WHERE run_id=?""",
                (utc_now(), message, run_id),
            )
            db.execute(
                """INSERT INTO incident_events
                   (incident_id, pipeline_id, run_id, severity, message, created_at)
                   VALUES (?, ?, ?, 'ERROR', ?, ?)""",
                (incident_id, row["pipeline_id"], run_id, message, utc_now()),
            )
        return incident_id

    def watermark(self, pipeline_id: str) -> str | None:
        """Read last committed watermark, if any."""
        with self.connection() as db:
            row = db.execute(
                "SELECT watermark FROM pipeline_watermark WHERE pipeline_id=?",
                (pipeline_id,),
            ).fetchone()
            return None if row is None else str(row["watermark"])
