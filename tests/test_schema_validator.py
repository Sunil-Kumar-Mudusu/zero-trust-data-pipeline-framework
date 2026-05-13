"""Tests for ztdpf.schema_validator."""
from __future__ import annotations

import pandas as pd
import pytest

from ztdpf.config import ColumnSchema, SchemaConfig
from ztdpf.schema_validator import validate_schema, SchemaReport, ColumnReport
from tests.conftest import make_config


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def _config_with_schema(
    required: list[str] | None = None,
    col_schemas: list[ColumnSchema] | None = None,
    max_null_rate: float = 0.2,
):
    cfg = make_config(
        required_columns=required or [],
        column_schemas=col_schemas or [],
    )
    cfg.schema.max_null_rate = max_null_rate
    return cfg


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSchemaValidatorBasics:
    def test_returns_schema_report(self, sample_df, basic_config):
        report = validate_schema(sample_df, basic_config)
        assert isinstance(report, SchemaReport)

    def test_empty_config_gives_score_100(self, sample_df, basic_config):
        report = validate_schema(sample_df, basic_config)
        assert report.schema_score == 100.0

    def test_empty_config_is_valid(self, sample_df, basic_config):
        report = validate_schema(sample_df, basic_config)
        assert report.is_valid is True

    def test_all_required_columns_present(self, sample_df):
        cfg = _config_with_schema(required=["id", "name", "amount"])
        report = validate_schema(sample_df, cfg)
        assert report.missing_columns == []
        assert report.is_valid is True

    def test_missing_required_column_detected(self, sample_df):
        cfg = _config_with_schema(required=["id", "nonexistent_column"])
        report = validate_schema(sample_df, cfg)
        assert "nonexistent_column" in report.missing_columns
        assert report.is_valid is False

    def test_multiple_missing_columns(self, sample_df):
        cfg = _config_with_schema(required=["id", "foo", "bar", "baz"])
        report = validate_schema(sample_df, cfg)
        assert len(report.missing_columns) == 3

    def test_schema_score_penalised_for_missing(self, sample_df):
        cfg = _config_with_schema(required=["id", "nonexistent"])
        report = validate_schema(sample_df, cfg)
        assert report.schema_score < 100.0


class TestNullRateChecks:
    def test_null_rate_below_threshold_no_violation(self, tmp_path):
        df = pd.DataFrame({"col": [1, 2, None, 4, 5, 6, 7, 8, 9, 10]})
        cfg = _config_with_schema(
            col_schemas=[ColumnSchema(name="col", dtype="integer", nullable=True)],
            max_null_rate=0.2,
        )
        report = validate_schema(df, cfg)
        assert "col" not in report.null_rate_violations

    def test_null_rate_above_threshold_is_violation(self):
        df = pd.DataFrame({"col": [1, None, None, None, 5]})
        cfg = _config_with_schema(
            col_schemas=[ColumnSchema(name="col", dtype="integer", nullable=True)],
            max_null_rate=0.2,
        )
        report = validate_schema(df, cfg)
        assert "col" in report.null_rate_violations
        assert report.is_valid is False

    def test_non_nullable_with_nulls_is_null_violation(self):
        df = pd.DataFrame({"name": ["Alice", None, "Carol"]})
        cfg = _config_with_schema(
            col_schemas=[ColumnSchema(name="name", dtype="string", nullable=False)],
            max_null_rate=0.5,
        )
        report = validate_schema(df, cfg)
        cr = next(r for r in report.column_reports if r.name == "name")
        assert cr.null_violation is True


class TestDtypeChecks:
    def test_correct_integer_dtype(self):
        df = pd.DataFrame({"count": [1, 2, 3]})
        cfg = _config_with_schema(
            col_schemas=[ColumnSchema(name="count", dtype="integer")]
        )
        report = validate_schema(df, cfg)
        cr = report.column_reports[0]
        assert cr.dtype_match is True

    def test_incorrect_dtype_flagged(self):
        df = pd.DataFrame({"count": ["a", "b", "c"]})
        cfg = _config_with_schema(
            col_schemas=[ColumnSchema(name="count", dtype="integer")]
        )
        report = validate_schema(df, cfg)
        cr = report.column_reports[0]
        assert cr.dtype_match is False

    def test_string_dtype_match(self):
        df = pd.DataFrame({"label": ["foo", "bar"]})
        cfg = _config_with_schema(
            col_schemas=[ColumnSchema(name="label", dtype="string")]
        )
        report = validate_schema(df, cfg)
        assert report.column_reports[0].dtype_match is True

    def test_float_dtype_match(self):
        df = pd.DataFrame({"price": [1.0, 2.5, 3.9]})
        cfg = _config_with_schema(
            col_schemas=[ColumnSchema(name="price", dtype="float")]
        )
        report = validate_schema(df, cfg)
        assert report.column_reports[0].dtype_match is True


class TestRangeChecks:
    def test_min_value_violation(self):
        df = pd.DataFrame({"age": [25, 17, 30]})  # 17 < 18
        cfg = _config_with_schema(
            col_schemas=[ColumnSchema(name="age", dtype="integer", min_value=18)]
        )
        report = validate_schema(df, cfg)
        cr = report.column_reports[0]
        assert cr.range_violation is True

    def test_max_value_violation(self):
        df = pd.DataFrame({"age": [25, 130, 30]})  # 130 > 120
        cfg = _config_with_schema(
            col_schemas=[ColumnSchema(name="age", dtype="integer", max_value=120)]
        )
        report = validate_schema(df, cfg)
        cr = report.column_reports[0]
        assert cr.range_violation is True

    def test_within_range_no_violation(self):
        df = pd.DataFrame({"age": [25, 40, 30]})
        cfg = _config_with_schema(
            col_schemas=[ColumnSchema(name="age", dtype="integer", min_value=18, max_value=120)]
        )
        report = validate_schema(df, cfg)
        cr = report.column_reports[0]
        assert cr.range_violation is False


class TestAllowedValues:
    def test_allowed_values_violation(self):
        df = pd.DataFrame({"currency": ["USD", "JPY", "GBP"]})  # JPY not allowed
        cfg = _config_with_schema(
            col_schemas=[
                ColumnSchema(name="currency", dtype="string",
                             allowed_values=["USD", "EUR", "GBP"])
            ]
        )
        report = validate_schema(df, cfg)
        cr = report.column_reports[0]
        assert cr.allowed_value_violation is True

    def test_allowed_values_pass(self):
        df = pd.DataFrame({"currency": ["USD", "EUR", "GBP"]})
        cfg = _config_with_schema(
            col_schemas=[
                ColumnSchema(name="currency", dtype="string",
                             allowed_values=["USD", "EUR", "GBP"])
            ]
        )
        report = validate_schema(df, cfg)
        cr = report.column_reports[0]
        assert cr.allowed_value_violation is False

    def test_schema_score_range(self, sample_df, basic_config):
        report = validate_schema(sample_df, basic_config)
        assert 0.0 <= report.schema_score <= 100.0
