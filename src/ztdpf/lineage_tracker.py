"""Data lineage recording: source schema, policies applied, output schema."""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .config import PipelineConfig
from .ingestion import IngestionResult
from .schema_validator import SchemaReport
from .policy_engine import PolicyReport
from .exceptions import LineageError


@dataclass
class LineageRecord:
    """Immutable lineage record for a single pipeline run."""

    lineage_id: str
    run_id: str
    source_path: str
    source_checksum: str
    source_columns: list[str]
    output_columns: list[str]
    policies_applied: list[str]
    source_row_count: int
    output_row_count: int
    recorded_at: datetime


class LineageTracker:
    """Persists lineage records in a SQLite database."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lineage_records (
                lineage_id       TEXT PRIMARY KEY,
                run_id           TEXT NOT NULL,
                source_path      TEXT,
                source_checksum  TEXT,
                source_columns   TEXT,
                output_columns   TEXT,
                policies_applied TEXT,
                source_row_count INTEGER,
                output_row_count INTEGER,
                recorded_at      TEXT
            )
            """
        )
        self._conn.commit()

    def record(
        self,
        ingestion_result: IngestionResult,
        schema_report: SchemaReport,
        policy_report: PolicyReport,
        output_columns: list[str],
        output_row_count: int,
    ) -> LineageRecord:
        """
        Persist a lineage record and return it.

        Raises:
            LineageError: if the database write fails.
        """
        lineage_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        policies = [
            f"{d.column}:{d.decision}" for d in policy_report.access_decisions
        ]

        rec = LineageRecord(
            lineage_id=lineage_id,
            run_id=ingestion_result.run_id,
            source_path=ingestion_result.source_path,
            source_checksum=ingestion_result.checksum,
            source_columns=ingestion_result.columns,
            output_columns=output_columns,
            policies_applied=policies,
            source_row_count=ingestion_result.row_count,
            output_row_count=output_row_count,
            recorded_at=now,
        )
        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO lineage_records VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    lineage_id,
                    ingestion_result.run_id,
                    ingestion_result.source_path,
                    ingestion_result.checksum,
                    json.dumps(ingestion_result.columns),
                    json.dumps(output_columns),
                    json.dumps(policies),
                    ingestion_result.row_count,
                    output_row_count,
                    now.isoformat(),
                ),
            )
            self._conn.commit()
        except Exception as exc:
            raise LineageError(f"Failed to record lineage: {exc}") from exc

        return rec

    def get_record(self, lineage_id: str) -> LineageRecord | None:
        """Retrieve a lineage record by ID, or None if not found."""
        row = self._conn.execute(
            "SELECT * FROM lineage_records WHERE lineage_id = ?", (lineage_id,)
        ).fetchone()
        if row is None:
            return None
        return LineageRecord(
            lineage_id=row[0],
            run_id=row[1],
            source_path=row[2],
            source_checksum=row[3],
            source_columns=json.loads(row[4]),
            output_columns=json.loads(row[5]),
            policies_applied=json.loads(row[6]),
            source_row_count=row[7],
            output_row_count=row[8],
            recorded_at=datetime.fromisoformat(row[9]),
        )

    def list_records(self, run_id: str | None = None) -> list[LineageRecord]:
        """Return all lineage records, optionally filtered by run_id."""
        if run_id:
            rows = self._conn.execute(
                "SELECT * FROM lineage_records WHERE run_id = ? ORDER BY recorded_at",
                (run_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM lineage_records ORDER BY recorded_at"
            ).fetchall()
        return [
            LineageRecord(
                lineage_id=r[0],
                run_id=r[1],
                source_path=r[2],
                source_checksum=r[3],
                source_columns=json.loads(r[4]),
                output_columns=json.loads(r[5]),
                policies_applied=json.loads(r[6]),
                source_row_count=r[7],
                output_row_count=r[8],
                recorded_at=datetime.fromisoformat(r[9]),
            )
            for r in rows
        ]
