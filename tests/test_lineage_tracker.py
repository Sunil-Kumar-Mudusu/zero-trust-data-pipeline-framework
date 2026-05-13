"""Tests for ztdpf.lineage_tracker."""
from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
import pytest

from ztdpf.lineage_tracker import LineageTracker, LineageRecord
from ztdpf.schema_validator import SchemaReport
from ztdpf.policy_engine import PolicyReport, AccessDecision
from tests.conftest import make_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _schema_report() -> SchemaReport:
    return SchemaReport(
        missing_columns=[],
        column_reports=[],
        null_rate_violations=[],
        schema_score=100.0,
        is_valid=True,
    )


def _policy_report() -> PolicyReport:
    return PolicyReport(
        policies_checked=2,
        violations=[],
        sensitive_columns_detected=["email"],
        access_decisions=[
            AccessDecision("email", "MASK", "masked"),
            AccessDecision("account_number", "MASK", "masked"),
        ],
        is_compliant=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLineageTrackerRecord:
    def test_record_returns_lineage_record(self, mock_ingestion_result):
        lt = LineageTracker()
        rec = lt.record(
            mock_ingestion_result,
            _schema_report(),
            _policy_report(),
            ["transaction_id", "email", "amount"],
            15,
        )
        assert isinstance(rec, LineageRecord)

    def test_lineage_id_is_valid_uuid(self, mock_ingestion_result):
        lt = LineageTracker()
        rec = lt.record(
            mock_ingestion_result, _schema_report(), _policy_report(),
            ["a", "b"], 10,
        )
        parsed = uuid.UUID(rec.lineage_id)
        assert str(parsed) == rec.lineage_id

    def test_run_id_matches_ingestion_result(self, mock_ingestion_result):
        lt = LineageTracker()
        rec = lt.record(
            mock_ingestion_result, _schema_report(), _policy_report(), ["a"], 5
        )
        assert rec.run_id == mock_ingestion_result.run_id

    def test_source_checksum_matches(self, mock_ingestion_result):
        lt = LineageTracker()
        rec = lt.record(
            mock_ingestion_result, _schema_report(), _policy_report(), ["a"], 5
        )
        assert rec.source_checksum == mock_ingestion_result.checksum

    def test_source_columns_match(self, mock_ingestion_result):
        lt = LineageTracker()
        rec = lt.record(
            mock_ingestion_result, _schema_report(), _policy_report(),
            mock_ingestion_result.columns, mock_ingestion_result.row_count,
        )
        assert rec.source_columns == mock_ingestion_result.columns

    def test_output_columns_stored_correctly(self, mock_ingestion_result):
        lt = LineageTracker()
        output_cols = ["transaction_id", "amount", "currency"]
        rec = lt.record(
            mock_ingestion_result, _schema_report(), _policy_report(),
            output_cols, 18,
        )
        assert rec.output_columns == output_cols

    def test_source_row_count_stored(self, mock_ingestion_result):
        lt = LineageTracker()
        rec = lt.record(
            mock_ingestion_result, _schema_report(), _policy_report(), ["a"], 10
        )
        assert rec.source_row_count == mock_ingestion_result.row_count

    def test_output_row_count_stored(self, mock_ingestion_result):
        lt = LineageTracker()
        rec = lt.record(
            mock_ingestion_result, _schema_report(), _policy_report(), ["a"], 13
        )
        assert rec.output_row_count == 13

    def test_policies_applied_populated(self, mock_ingestion_result):
        lt = LineageTracker()
        rec = lt.record(
            mock_ingestion_result, _schema_report(), _policy_report(), ["a"], 5
        )
        assert len(rec.policies_applied) == 2
        assert any("MASK" in p for p in rec.policies_applied)

    def test_recorded_at_is_datetime(self, mock_ingestion_result):
        lt = LineageTracker()
        rec = lt.record(
            mock_ingestion_result, _schema_report(), _policy_report(), ["a"], 5
        )
        assert isinstance(rec.recorded_at, datetime)


class TestLineageTrackerRetrieval:
    def test_get_record_retrieves_by_id(self, mock_ingestion_result):
        lt = LineageTracker()
        rec = lt.record(
            mock_ingestion_result, _schema_report(), _policy_report(), ["a"], 5
        )
        retrieved = lt.get_record(rec.lineage_id)
        assert retrieved is not None
        assert retrieved.lineage_id == rec.lineage_id

    def test_get_record_returns_none_for_unknown(self):
        lt = LineageTracker()
        result = lt.get_record("nonexistent-id-12345")
        assert result is None

    def test_multiple_records_stored(self, mock_ingestion_result):
        lt = LineageTracker()
        rec1 = lt.record(mock_ingestion_result, _schema_report(), _policy_report(), ["a"], 5)
        rec2 = lt.record(mock_ingestion_result, _schema_report(), _policy_report(), ["b"], 3)
        assert rec1.lineage_id != rec2.lineage_id
        all_recs = lt.list_records()
        assert len(all_recs) == 2
