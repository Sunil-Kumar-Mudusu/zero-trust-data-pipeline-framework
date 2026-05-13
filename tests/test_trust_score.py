"""Tests for ztdpf.trust_score."""
from __future__ import annotations

import pandas as pd
import pytest

from ztdpf.schema_validator import SchemaReport, ColumnReport
from ztdpf.policy_engine import PolicyReport, AccessDecision
from ztdpf.trust_score import calculate_trust, TrustReport, _integrity_score
from tests.conftest import make_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _perfect_schema_report() -> SchemaReport:
    return SchemaReport(
        missing_columns=[],
        column_reports=[],
        null_rate_violations=[],
        schema_score=100.0,
        is_valid=True,
    )


def _poor_schema_report() -> SchemaReport:
    return SchemaReport(
        missing_columns=["col_a", "col_b"],
        column_reports=[],
        null_rate_violations=["col_c"],
        schema_score=40.0,
        is_valid=False,
    )


def _compliant_policy_report() -> PolicyReport:
    return PolicyReport(
        policies_checked=2,
        violations=[],
        sensitive_columns_detected=[],
        access_decisions=[],
        is_compliant=True,
    )


def _violated_policy_report(violations: int = 2) -> PolicyReport:
    return PolicyReport(
        policies_checked=4,
        violations=[f"violation_{i}" for i in range(violations)],
        sensitive_columns_detected=["email"],
        access_decisions=[],
        is_compliant=False,
    )


def _clean_df() -> pd.DataFrame:
    return pd.DataFrame(
        {"a": [1, 2, 3, 4, 5], "b": [10.0, 20.0, 30.0, 40.0, 50.0]}
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTrustScoreBasics:
    def test_returns_trust_report(self, basic_config):
        report = calculate_trust(
            _perfect_schema_report(), _compliant_policy_report(), _clean_df(), basic_config
        )
        assert isinstance(report, TrustReport)

    def test_overall_trust_in_range(self, basic_config):
        report = calculate_trust(
            _perfect_schema_report(), _compliant_policy_report(), _clean_df(), basic_config
        )
        assert 0.0 <= report.overall_trust <= 100.0

    def test_perfect_inputs_give_high_trust(self, basic_config):
        report = calculate_trust(
            _perfect_schema_report(), _compliant_policy_report(), _clean_df(), basic_config
        )
        assert report.overall_trust >= 90.0

    def test_schema_trust_matches_schema_score(self, basic_config):
        schema = _perfect_schema_report()
        report = calculate_trust(schema, _compliant_policy_report(), _clean_df(), basic_config)
        assert report.schema_trust == schema.schema_score

    def test_policy_trust_100_when_compliant(self, basic_config):
        report = calculate_trust(
            _perfect_schema_report(), _compliant_policy_report(), _clean_df(), basic_config
        )
        assert report.policy_trust == 100.0

    def test_policy_violations_reduce_trust(self, basic_config):
        report = calculate_trust(
            _perfect_schema_report(), _violated_policy_report(2), _clean_df(), basic_config
        )
        assert report.policy_trust < 100.0

    def test_poor_schema_reduces_overall(self, basic_config):
        report = calculate_trust(
            _poor_schema_report(), _compliant_policy_report(), _clean_df(), basic_config
        )
        assert report.overall_trust < 80.0


class TestTrustLevels:
    def test_trust_level_high_above_90(self, basic_config):
        report = calculate_trust(
            _perfect_schema_report(), _compliant_policy_report(), _clean_df(), basic_config
        )
        assert report.trust_level == "HIGH"

    def test_trust_level_critical_below_60(self):
        cfg = make_config(min_trust_score=60.0)
        schema = SchemaReport([], [], [], 10.0, False)
        policy = _violated_policy_report(4)
        df = pd.DataFrame({"a": [None, None, None]})
        report = calculate_trust(schema, policy, df, cfg)
        assert report.trust_level == "CRITICAL"

    def test_trust_level_medium(self):
        cfg = make_config()
        schema = SchemaReport([], [], [], 75.0, True)
        policy = _compliant_policy_report()
        df = _clean_df()
        report = calculate_trust(schema, policy, df, cfg)
        # Overall = 75*0.35 + 100*0.40 + integrity*0.25
        # Should be in MEDIUM or HIGH range
        assert report.trust_level in ("MEDIUM", "HIGH")

    def test_passes_threshold_when_above_min(self, basic_config):
        report = calculate_trust(
            _perfect_schema_report(), _compliant_policy_report(), _clean_df(), basic_config
        )
        assert report.passes_threshold is True

    def test_fails_threshold_when_below_min(self):
        cfg = make_config(min_trust_score=95.0)
        schema = SchemaReport([], [], [], 40.0, False)
        policy = _violated_policy_report(3)
        df = pd.DataFrame({"a": [None] * 10})
        report = calculate_trust(schema, policy, df, cfg)
        assert report.passes_threshold is False

    def test_trust_level_low_boundary(self):
        cfg = make_config(min_trust_score=50.0)
        schema = SchemaReport([], [], [], 60.0, True)
        policy = PolicyReport(2, ["v1"], [], [], False)
        df = _clean_df()
        report = calculate_trust(schema, policy, df, cfg)
        assert report.trust_level in ("LOW", "MEDIUM", "HIGH")


class TestIntegrityScore:
    def test_clean_df_high_integrity(self):
        df = _clean_df()
        score = _integrity_score(df)
        assert score > 80.0

    def test_empty_df_zero_integrity(self):
        df = pd.DataFrame()
        score = _integrity_score(df)
        assert score == 0.0

    def test_high_null_df_lower_integrity(self):
        df = pd.DataFrame({"a": [None] * 8 + [1, 2]})
        clean_score = _integrity_score(_clean_df())
        null_score = _integrity_score(df)
        assert null_score < clean_score

    def test_duplicate_rows_reduce_integrity(self):
        clean = _clean_df()
        duped = pd.concat([clean, clean, clean], ignore_index=True)
        clean_score = _integrity_score(clean)
        dup_score = _integrity_score(duped)
        assert dup_score <= clean_score
