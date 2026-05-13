"""SQLite-backed metadata catalog for pipeline run history."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from .ingestion import IngestionResult
from .schema_validator import SchemaReport
from .policy_engine import PolicyReport
from .trust_score import TrustReport
from .exceptions import MetadataStoreError


class MetadataStore:
    """Persists per-run metadata across five tables in a SQLite database."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id        TEXT PRIMARY KEY,
                pipeline_name TEXT,
                trust_score   REAL,
                trust_level   TEXT,
                status        TEXT,
                created_at    TEXT
            );
            CREATE TABLE IF NOT EXISTS ingestion_results (
                run_id        TEXT PRIMARY KEY,
                source_name   TEXT,
                row_count     INTEGER,
                column_count  INTEGER,
                checksum      TEXT,
                warnings      TEXT,
                ingested_at   TEXT
            );
            CREATE TABLE IF NOT EXISTS schema_results (
                run_id           TEXT PRIMARY KEY,
                schema_score     REAL,
                missing_columns  TEXT,
                null_violations  TEXT,
                is_valid         INTEGER
            );
            CREATE TABLE IF NOT EXISTS policy_results (
                run_id            TEXT PRIMARY KEY,
                policies_checked  INTEGER,
                violations        TEXT,
                sensitive_columns TEXT,
                is_compliant      INTEGER
            );
            CREATE TABLE IF NOT EXISTS trust_results (
                run_id            TEXT PRIMARY KEY,
                schema_trust      REAL,
                policy_trust      REAL,
                integrity_trust   REAL,
                overall_trust     REAL,
                trust_level       TEXT,
                passes_threshold  INTEGER
            );
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    def save_run(
        self,
        run_id: str,
        pipeline_name: str,
        trust_report: TrustReport,
        status: str,
    ) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO pipeline_runs VALUES (?,?,?,?,?,?)",
            (
                run_id,
                pipeline_name,
                trust_report.overall_trust,
                trust_report.trust_level,
                status,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()

    def save_ingestion(self, run_id: str, result: IngestionResult) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO ingestion_results VALUES (?,?,?,?,?,?,?)",
            (
                run_id,
                result.source_name,
                result.row_count,
                result.column_count,
                result.checksum,
                json.dumps(result.warnings),
                result.ingested_at.isoformat(),
            ),
        )
        self._conn.commit()

    def save_schema(self, run_id: str, report: SchemaReport) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO schema_results VALUES (?,?,?,?,?)",
            (
                run_id,
                report.schema_score,
                json.dumps(report.missing_columns),
                json.dumps(report.null_rate_violations),
                int(report.is_valid),
            ),
        )
        self._conn.commit()

    def save_policy(self, run_id: str, report: PolicyReport) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO policy_results VALUES (?,?,?,?,?)",
            (
                run_id,
                report.policies_checked,
                json.dumps(report.violations),
                json.dumps(report.sensitive_columns_detected),
                int(report.is_compliant),
            ),
        )
        self._conn.commit()

    def save_trust(self, run_id: str, report: TrustReport) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO trust_results VALUES (?,?,?,?,?,?,?)",
            (
                run_id,
                report.schema_trust,
                report.policy_trust,
                report.integrity_trust,
                report.overall_trust,
                report.trust_level,
                int(report.passes_threshold),
            ),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    def list_runs(self) -> list[dict]:
        """Return all pipeline runs, most recent first."""
        rows = self._conn.execute(
            """
            SELECT run_id, pipeline_name, trust_score, trust_level, status, created_at
            FROM pipeline_runs
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [
            {
                "run_id": r[0],
                "pipeline_name": r[1],
                "trust_score": r[2],
                "trust_level": r[3],
                "status": r[4],
                "created_at": r[5],
            }
            for r in rows
        ]

    def get_run(self, run_id: str) -> dict | None:
        """Return a single pipeline run record, or None if not found."""
        row = self._conn.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "run_id": row[0],
            "pipeline_name": row[1],
            "trust_score": row[2],
            "trust_level": row[3],
            "status": row[4],
            "created_at": row[5],
        }

    def get_schema_result(self, run_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM schema_results WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "run_id": row[0],
            "schema_score": row[1],
            "missing_columns": json.loads(row[2]),
            "null_violations": json.loads(row[3]),
            "is_valid": bool(row[4]),
        }

    def get_trust_result(self, run_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM trust_results WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "run_id": row[0],
            "schema_trust": row[1],
            "policy_trust": row[2],
            "integrity_trust": row[3],
            "overall_trust": row[4],
            "trust_level": row[5],
            "passes_threshold": bool(row[6]),
        }
