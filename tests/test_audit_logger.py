"""Tests for ztdpf.audit_logger."""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from ztdpf.audit_logger import AuditLogger, AuditEvent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAuditLoggerBasics:
    def test_log_returns_audit_event(self):
        logger = AuditLogger()
        event = logger.log("run-1", "ingestion", "ingest_source")
        assert isinstance(event, AuditEvent)

    def test_event_id_is_valid_uuid(self):
        logger = AuditLogger()
        event = logger.log("run-1", "ingestion", "ingest_source")
        parsed = uuid.UUID(event.event_id)
        assert str(parsed) == event.event_id

    def test_run_id_stored_correctly(self):
        logger = AuditLogger()
        event = logger.log("my-run-42", "schema_validation", "validate_schema")
        assert event.run_id == "my-run-42"

    def test_stage_stored_correctly(self):
        logger = AuditLogger()
        event = logger.log("run-1", "policy_enforcement", "enforce_policies")
        assert event.stage == "policy_enforcement"

    def test_action_stored_correctly(self):
        logger = AuditLogger()
        event = logger.log("run-1", "trust_scoring", "calculate_trust")
        assert event.action == "calculate_trust"

    def test_status_defaults_to_success(self):
        logger = AuditLogger()
        event = logger.log("run-1", "ingestion", "ingest_source")
        assert event.status == "success"

    def test_status_stored_correctly(self):
        logger = AuditLogger()
        event = logger.log("run-1", "policy_enforcement", "enforce", status="violation")
        assert event.status == "violation"

    def test_detail_stored_correctly(self):
        logger = AuditLogger()
        event = logger.log("run-1", "ingestion", "ingest_source", detail="rows=100")
        assert event.detail == "rows=100"

    def test_timestamp_is_datetime(self):
        logger = AuditLogger()
        event = logger.log("run-1", "ingestion", "ingest_source")
        assert isinstance(event.timestamp, datetime)

    def test_empty_detail_by_default(self):
        logger = AuditLogger()
        event = logger.log("run-1", "pipeline", "run_complete")
        assert event.detail == ""


class TestAuditLoggerRetrieval:
    def test_get_events_filters_by_run_id(self):
        logger = AuditLogger()
        logger.log("run-A", "ingestion", "ingest_source")
        logger.log("run-A", "schema_validation", "validate_schema")
        logger.log("run-B", "ingestion", "ingest_source")

        events_a = logger.get_events("run-A")
        assert len(events_a) == 2
        assert all(e.run_id == "run-A" for e in events_a)

    def test_get_events_without_filter_returns_all(self):
        logger = AuditLogger()
        logger.log("run-A", "ingestion", "ingest_source")
        logger.log("run-B", "ingestion", "ingest_source")
        logger.log("run-C", "ingestion", "ingest_source")

        all_events = logger.get_events()
        assert len(all_events) == 3

    def test_event_count_correct(self):
        logger = AuditLogger()
        logger.log("run-1", "ingestion", "ingest_source")
        logger.log("run-1", "schema_validation", "validate_schema")
        logger.log("run-1", "policy_enforcement", "enforce_policies")

        assert logger.event_count("run-1") == 3

    def test_event_count_without_run_id(self):
        logger = AuditLogger()
        for i in range(5):
            logger.log(f"run-{i}", "ingestion", "ingest_source")
        assert logger.event_count() == 5

    def test_events_ordered_by_timestamp(self):
        logger = AuditLogger()
        logger.log("run-1", "stage_1", "action_1")
        logger.log("run-1", "stage_2", "action_2")
        logger.log("run-1", "stage_3", "action_3")

        events = logger.get_events("run-1")
        assert len(events) == 3
        timestamps = [e.timestamp for e in events]
        assert timestamps == sorted(timestamps)

    def test_multiple_events_same_run_id(self):
        logger = AuditLogger()
        stages = ["ingestion", "schema_validation", "policy_enforcement",
                  "trust_scoring", "lineage", "pipeline"]
        for stage in stages:
            logger.log("run-X", stage, "action")

        events = logger.get_events("run-X")
        assert len(events) == 6

    def test_event_count_zero_for_unknown_run(self):
        logger = AuditLogger()
        logger.log("run-1", "ingestion", "ingest_source")
        assert logger.event_count("nonexistent-run") == 0

    def test_events_from_different_runs_isolated(self):
        logger = AuditLogger()
        logger.log("run-1", "ingestion", "ingest_source")
        logger.log("run-1", "schema_validation", "validate_schema")
        logger.log("run-2", "ingestion", "ingest_source")

        assert logger.event_count("run-1") == 2
        assert logger.event_count("run-2") == 1
