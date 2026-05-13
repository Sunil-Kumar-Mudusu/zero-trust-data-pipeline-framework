"""Immutable audit event trail backed by SQLite."""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class AuditEvent:
    """A single immutable audit event."""

    event_id: str
    run_id: str
    stage: str
    action: str
    status: str
    detail: str
    timestamp: datetime


class AuditLogger:
    """Write-once audit log persisted in a SQLite database."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id  TEXT PRIMARY KEY,
                run_id    TEXT NOT NULL,
                stage     TEXT,
                action    TEXT,
                status    TEXT,
                detail    TEXT,
                timestamp TEXT
            )
            """
        )
        self._conn.commit()

    def log(
        self,
        run_id: str,
        stage: str,
        action: str,
        status: str = "success",
        detail: str = "",
    ) -> AuditEvent:
        """Append an audit event and return it."""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            stage=stage,
            action=action,
            status=status,
            detail=detail,
            timestamp=datetime.now(timezone.utc),
        )
        self._conn.execute(
            "INSERT INTO audit_events VALUES (?,?,?,?,?,?,?)",
            (
                event.event_id,
                run_id,
                stage,
                action,
                status,
                detail,
                event.timestamp.isoformat(),
            ),
        )
        self._conn.commit()
        return event

    def get_events(self, run_id: str | None = None) -> list[AuditEvent]:
        """Return audit events, optionally filtered by run_id."""
        if run_id:
            rows = self._conn.execute(
                "SELECT * FROM audit_events WHERE run_id = ? ORDER BY timestamp",
                (run_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM audit_events ORDER BY timestamp"
            ).fetchall()
        return [
            AuditEvent(
                event_id=r[0],
                run_id=r[1],
                stage=r[2],
                action=r[3],
                status=r[4],
                detail=r[5],
                timestamp=datetime.fromisoformat(r[6]),
            )
            for r in rows
        ]

    def event_count(self, run_id: str | None = None) -> int:
        """Return the number of audit events, optionally filtered by run_id."""
        return len(self.get_events(run_id))
