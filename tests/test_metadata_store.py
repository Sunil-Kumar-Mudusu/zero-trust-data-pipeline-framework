"""Tests for ztdpf.metadata_store."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ztdpf.metadata_store import MetadataStore
from ztdpf.ingestion import IngestionResult
from ztdpf.schema_validator import SchemaReport
from ztdpf.policy_engine import PolicyReport
from ztdpf.trust_score import TrustReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trust_report(overall: float = 88.0, level: str = "HIGH") -> TrustReport:
    return TrustReport(
        schema_trust=90.0,
        policy_trust=100.0,
        integrity_trust=80.0,
        overall_trust=overall,
        trust_level=level,
        passes_threshold=overall >= 60.0,
    )


def _ingestion_result(run_id: str = "run-001") -> IngestionResult:
    return IngestionResult(
        run_id=run_id,
        source_name="test_source",
        source_path="/tmp/test.csv",
        row_count=100,
        column_count=5,
        columns=["a", "b", "c", "d", "e"],
        checksum="a" * 64,
        ingested_at=datetime.now(timezone.utc),
        inferred_dtypes={"a": "object"},
        warnings=[],
    )


def _schema_report() -> SchemaReport:
    return SchemaReport(
        missing_columns=[],
        column_reports=[],
        null_rate_violations=[],
        schema_score=95.0,
        is_valid=True,
    )


def _policy_report() -> PolicyReport:
    return PolicyReport(
        policies_checked=3,
        violations=[],
        sensitive_columns_detected=["email"],
        access_decisions=[],
        is_compliant=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMetadataStoreRuns:
    def test_save_and_get_run_roundtrip(self):
        store = MetadataStore()
        tr = _trust_report()
        store.save_run("run-001", "pipeline_alpha", tr, "PASS")
        row = store.get_run("run-001")
        assert row is not None
        assert row["run_id"] == "run-001"
        assert row["pipeline_name"] == "pipeline_alpha"
        assert row["trust_score"] == tr.overall_trust
        assert row["status"] == "PASS"

    def test_get_run_returns_none_for_unknown(self):
        store = MetadataStore()
        assert store.get_run("nonexistent") is None

    def test_list_runs_returns_all(self):
        store = MetadataStore()
        for i in range(3):
            store.save_run(f"run-{i:03d}", "pipeline", _trust_report(), "PASS")
        runs = store.list_runs()
        assert len(runs) == 3

    def test_list_runs_most_recent_first(self):
        store = MetadataStore()
        store.save_run("run-001", "pipeline", _trust_report(80.0), "PASS")
        store.save_run("run-002", "pipeline", _trust_report(90.0), "PASS")
        runs = store.list_runs()
        # Most recent is run-002 (saved last)
        assert runs[0]["run_id"] == "run-002"

    def test_trust_level_stored_correctly(self):
        store = MetadataStore()
        store.save_run("run-001", "pipeline", _trust_report(92.0, "HIGH"), "PASS")
        row = store.get_run("run-001")
        assert row["trust_level"] == "HIGH"


class TestMetadataStoreIngestion:
    def test_save_ingestion_persists_data(self):
        store = MetadataStore()
        ir = _ingestion_result("run-002")
        store.save_ingestion("run-002", ir)
        rows = store._conn.execute(
            "SELECT * FROM ingestion_results WHERE run_id = ?", ("run-002",)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][1] == "test_source"
        assert rows[0][2] == 100

    def test_save_ingestion_warnings_stored(self):
        store = MetadataStore()
        ir = _ingestion_result("run-003")
        ir.warnings.append("Null values in age")
        store.save_ingestion("run-003", ir)
        rows = store._conn.execute(
            "SELECT warnings FROM ingestion_results WHERE run_id = ?", ("run-003",)
        ).fetchall()
        import json
        warnings = json.loads(rows[0][0])
        assert "Null values in age" in warnings


class TestMetadataStoreSchema:
    def test_save_schema_persists_data(self):
        store = MetadataStore()
        sr = _schema_report()
        store.save_schema("run-010", sr)
        result = store.get_schema_result("run-010")
        assert result is not None
        assert result["schema_score"] == 95.0
        assert result["is_valid"] is True

    def test_schema_with_missing_columns(self):
        store = MetadataStore()
        sr = SchemaReport(
            missing_columns=["col_x", "col_y"],
            column_reports=[],
            null_rate_violations=[],
            schema_score=60.0,
            is_valid=False,
        )
        store.save_schema("run-011", sr)
        result = store.get_schema_result("run-011")
        assert result["missing_columns"] == ["col_x", "col_y"]
        assert result["is_valid"] is False


class TestMetadataStorePolicyAndTrust:
    def test_save_policy_persists_data(self):
        store = MetadataStore()
        pr = _policy_report()
        store.save_policy("run-020", pr)
        rows = store._conn.execute(
            "SELECT policies_checked, is_compliant FROM policy_results WHERE run_id = ?",
            ("run-020",),
        ).fetchall()
        assert rows[0][0] == 3
        assert rows[0][1] == 1

    def test_save_trust_and_retrieve(self):
        store = MetadataStore()
        tr = _trust_report(88.5, "HIGH")
        store.save_trust("run-030", tr)
        result = store.get_trust_result("run-030")
        assert result is not None
        assert result["overall_trust"] == 88.5
        assert result["trust_level"] == "HIGH"
        assert result["passes_threshold"] is True

    def test_get_trust_result_none_for_unknown(self):
        store = MetadataStore()
        assert store.get_trust_result("no-such-run") is None
