"""Tests for ztdpf.pipeline_runner."""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
import yaml

from ztdpf.pipeline_runner import run_pipeline, load_config, PipelineRunResult
from ztdpf.config import PipelineConfig
from ztdpf.exceptions import IngestionError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_POLICY_YAML = """\
pipeline_name: test_pipeline
version: "1.0"

ingestion:
  source_type: csv
  delimiter: ","
  encoding: utf-8

schema:
  required_columns:
    - transaction_id
    - amount
    - status
  column_schemas:
    - name: amount
      dtype: float
      nullable: false
      min_value: 0.0
    - name: status
      dtype: string
      nullable: false
  max_null_rate: 0.3

policy:
  sensitive_columns:
    - column: email
      action: mask
      mask_pattern: email
    - column: account_number
      action: mask
      mask_pattern: last4
  row_filters:
    - column: status
      operator: "ne"
      value: "failed"
  deny_if_sensitive_unmasked: true
  sensitive_patterns: []

trust:
  schema_weight: 0.35
  policy_weight: 0.40
  integrity_weight: 0.25
  min_trust_score: 60.0

storage:
  metadata_db: ":memory:"
  lineage_db: ":memory:"
  audit_db: ":memory:"
"""


@pytest.fixture
def config_file(tmp_path: Path) -> str:
    p = tmp_path / "pipeline_config.yaml"
    p.write_text(_POLICY_YAML, encoding="utf-8")
    return str(p)


@pytest.fixture
def csv_source(tmp_path: Path) -> str:
    content = (
        "transaction_id,customer_name,email,age,amount,currency,status,account_number\n"
        "TXN-001,Alice,alice@example.com,34,250.00,USD,completed,ACC-88421\n"
        "TXN-002,Bob,bob@corp.io,28,1050.75,EUR,completed,ACC-33017\n"
        "TXN-003,Carol,carol@mail.net,45,89.99,GBP,completed,ACC-55234\n"
        "TXN-004,David,david@example.com,52,3200.00,USD,completed,ACC-72109\n"
        "TXN-005,Eva,eva@startup.io,31,175.50,EUR,failed,ACC-61845\n"
        "TXN-006,Frank,frank@org.net,67,420.00,GBP,completed,ACC-94312\n"
        "TXN-007,Grace,grace@example.com,23,99.00,USD,completed,ACC-11789\n"
        "TXN-008,Henry,henry@corp.io,41,560.25,EUR,completed,ACC-28654\n"
        "TXN-009,Irene,irene@mail.net,38,1800.00,GBP,completed,ACC-47001\n"
        "TXN-010,James,james@example.com,29,325.00,USD,completed,ACC-83567\n"
    )
    p = tmp_path / "test_input.csv"
    p.write_text(content, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPipelineRunnerBasics:
    def test_run_returns_pipeline_run_result(self, csv_source, config_file):
        result = run_pipeline(csv_source, config_file)
        assert isinstance(result, PipelineRunResult)

    def test_run_id_is_valid_uuid(self, csv_source, config_file):
        result = run_pipeline(csv_source, config_file)
        parsed = uuid.UUID(result.run_id)
        assert str(parsed) == result.run_id

    def test_audit_event_count_at_least_6(self, csv_source, config_file):
        result = run_pipeline(csv_source, config_file)
        assert result.audit_event_count >= 6

    def test_trust_score_between_0_and_100(self, csv_source, config_file):
        result = run_pipeline(csv_source, config_file)
        assert 0.0 <= result.trust_score <= 100.0

    def test_trust_level_is_valid(self, csv_source, config_file):
        result = run_pipeline(csv_source, config_file)
        assert result.trust_level in ("HIGH", "MEDIUM", "LOW", "CRITICAL")

    def test_status_is_valid(self, csv_source, config_file):
        result = run_pipeline(csv_source, config_file)
        assert result.status in ("PASS", "WARNING", "FAIL")

    def test_schema_score_populated(self, csv_source, config_file):
        result = run_pipeline(csv_source, config_file)
        assert result.schema_score is not None
        assert 0.0 <= result.schema_score <= 100.0

    def test_lineage_id_populated(self, csv_source, config_file):
        result = run_pipeline(csv_source, config_file)
        assert result.lineage_id != ""
        parsed = uuid.UUID(result.lineage_id)
        assert str(parsed) == result.lineage_id

    def test_source_name_correct(self, csv_source, config_file):
        result = run_pipeline(csv_source, config_file)
        assert result.source_name == "test_input"

    def test_pipeline_name_from_config(self, csv_source, config_file):
        result = run_pipeline(csv_source, config_file)
        assert result.pipeline_name == "test_pipeline"

    def test_source_row_count_correct(self, csv_source, config_file):
        result = run_pipeline(csv_source, config_file)
        assert result.source_row_count == 10

    def test_output_row_count_less_than_source_due_to_filter(self, csv_source, config_file):
        result = run_pipeline(csv_source, config_file)
        # Row filter removes "failed" rows (1 in this data)
        assert result.output_row_count < result.source_row_count


class TestPipelineRunnerErrors:
    def test_missing_source_raises_ingestion_error(self, config_file):
        with pytest.raises(IngestionError, match="not found"):
            run_pipeline("/nonexistent/data.csv", config_file)


class TestLoadConfig:
    def test_load_config_returns_pipeline_config(self, config_file):
        cfg = load_config(config_file)
        assert isinstance(cfg, PipelineConfig)

    def test_load_config_pipeline_name(self, config_file):
        cfg = load_config(config_file)
        assert cfg.pipeline_name == "test_pipeline"

    def test_load_config_required_columns(self, config_file):
        cfg = load_config(config_file)
        assert "transaction_id" in cfg.schema.required_columns

    def test_load_config_policy_sensitive_columns(self, config_file):
        cfg = load_config(config_file)
        col_names = [p.column for p in cfg.policy.sensitive_columns]
        assert "email" in col_names
        assert "account_number" in col_names
