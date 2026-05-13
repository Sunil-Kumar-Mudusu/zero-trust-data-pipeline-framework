"""Tests for ztdpf.policy_engine."""
from __future__ import annotations

import pandas as pd
import pytest

from ztdpf.config import (
    SensitiveColumnPolicy,
    RowFilterPolicy,
    PolicyConfig,
)
from ztdpf.policy_engine import (
    enforce_policies,
    PolicyReport,
    AccessDecision,
    _mask_value,
)
from tests.conftest import make_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _policy_config(
    sensitive_columns: list[SensitiveColumnPolicy] | None = None,
    row_filters: list[RowFilterPolicy] | None = None,
    deny_if_sensitive_unmasked: bool = True,
) -> "PipelineConfig":
    return make_config(
        sensitive_columns=sensitive_columns or [],
        row_filters=row_filters or [],
        deny_if_sensitive_unmasked=deny_if_sensitive_unmasked,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSensitiveColumnDetection:
    def test_email_column_auto_detected(self, sensitive_df):
        cfg = _policy_config(deny_if_sensitive_unmasked=True)
        report, _ = enforce_policies(sensitive_df, cfg)
        assert "email" in report.sensitive_columns_detected

    def test_account_number_auto_detected(self, sensitive_df):
        cfg = _policy_config(deny_if_sensitive_unmasked=True)
        report, _ = enforce_policies(sensitive_df, cfg)
        assert "account_number" in report.sensitive_columns_detected

    def test_plain_df_no_sensitive_columns(self, sample_df):
        cfg = _policy_config(deny_if_sensitive_unmasked=False)
        report, _ = enforce_policies(sample_df, cfg)
        assert report.sensitive_columns_detected == []

    def test_value_based_detection_email_content(self):
        df = pd.DataFrame({"contact": ["alice@example.com", "bob@domain.org"]})
        cfg = _policy_config(deny_if_sensitive_unmasked=True)
        report, _ = enforce_policies(df, cfg)
        assert "contact" in report.sensitive_columns_detected

    def test_ssn_column_name_detected(self):
        df = pd.DataFrame({"ssn": ["123-45-6789", "987-65-4321"]})
        cfg = _policy_config()
        report, _ = enforce_policies(df, cfg)
        assert "ssn" in report.sensitive_columns_detected

    def test_password_column_name_detected(self):
        df = pd.DataFrame({"password": ["secret1", "secret2"]})
        cfg = _policy_config()
        report, _ = enforce_policies(df, cfg)
        assert "password" in report.sensitive_columns_detected


class TestMaskingBehavior:
    def test_email_masked_with_stars(self, sensitive_df):
        cfg = _policy_config(
            sensitive_columns=[
                SensitiveColumnPolicy(column="email", action="mask", mask_pattern="email")
            ]
        )
        _, df_out = enforce_policies(sensitive_df, cfg)
        for val in df_out["email"].dropna():
            assert "***@" in val

    def test_account_number_last4_masked(self, sensitive_df):
        cfg = _policy_config(
            sensitive_columns=[
                SensitiveColumnPolicy(column="account_number", action="mask", mask_pattern="last4")
            ]
        )
        _, df_out = enforce_policies(sensitive_df, cfg)
        for val in df_out["account_number"].dropna():
            assert val.startswith("****")

    def test_masked_email_preserves_domain(self):
        val = _mask_value("alice@example.com", "email")
        assert "@" in val
        assert "example.com" in val

    def test_masked_last4_shows_last4(self):
        val = _mask_value("ACC-12345", "last4")
        assert val.endswith("2345")
        assert val.startswith("****")

    def test_default_mask_pattern(self):
        val = _mask_value("sensitive", None)
        assert val == "***MASKED***"

    def test_auto_mask_applied_when_deny_if_unmasked(self, sensitive_df):
        cfg = _policy_config(deny_if_sensitive_unmasked=True)
        _, df_out = enforce_policies(sensitive_df, cfg)
        # email should be masked
        for val in df_out["email"].dropna():
            assert "@" not in val or "***" in val


class TestAccessDecisions:
    def test_mask_decision_recorded(self, sensitive_df):
        cfg = _policy_config(
            sensitive_columns=[
                SensitiveColumnPolicy(column="email", action="mask", mask_pattern="email")
            ]
        )
        report, _ = enforce_policies(sensitive_df, cfg)
        decisions = {d.column: d.decision for d in report.access_decisions}
        assert decisions.get("email") == "MASK"

    def test_permit_decision_when_not_deny_unmasked(self):
        df = pd.DataFrame({"email": ["a@b.com"]})
        cfg = _policy_config(
            sensitive_columns=[
                SensitiveColumnPolicy(column="email", action="allow")
            ],
            deny_if_sensitive_unmasked=False,
        )
        report, _ = enforce_policies(df, cfg)
        decisions = {d.column: d.decision for d in report.access_decisions}
        assert decisions.get("email") == "PERMIT"

    def test_deny_action_records_violation(self):
        df = pd.DataFrame({"salary": [50000, 60000]})
        cfg = _policy_config(
            sensitive_columns=[
                SensitiveColumnPolicy(column="salary", action="deny")
            ]
        )
        report, _ = enforce_policies(df, cfg)
        assert len(report.violations) >= 1
        decisions = {d.column: d.decision for d in report.access_decisions}
        assert decisions.get("salary") == "DENY"


class TestRowFilters:
    def test_ne_filter_removes_rows(self):
        df = pd.DataFrame({"status": ["completed", "failed", "completed", "failed"]})
        cfg = _policy_config(
            row_filters=[RowFilterPolicy(column="status", operator="ne", value="failed")]
        )
        _, df_out = enforce_policies(df, cfg)
        assert "failed" not in df_out["status"].values
        assert len(df_out) == 2

    def test_eq_filter_keeps_matching_rows(self):
        df = pd.DataFrame({"currency": ["USD", "EUR", "USD", "GBP"]})
        cfg = _policy_config(
            row_filters=[RowFilterPolicy(column="currency", operator="eq", value="USD")]
        )
        _, df_out = enforce_policies(df, cfg)
        assert all(df_out["currency"] == "USD")
        assert len(df_out) == 2

    def test_in_filter_works(self):
        df = pd.DataFrame({"currency": ["USD", "EUR", "GBP", "JPY"]})
        cfg = _policy_config(
            row_filters=[RowFilterPolicy(column="currency", operator="in", value=["USD", "EUR"])]
        )
        _, df_out = enforce_policies(df, cfg)
        assert set(df_out["currency"]) == {"USD", "EUR"}

    def test_notin_filter_works(self):
        df = pd.DataFrame({"status": ["completed", "failed", "pending"]})
        cfg = _policy_config(
            row_filters=[RowFilterPolicy(column="status", operator="notin", value=["failed", "pending"])]
        )
        _, df_out = enforce_policies(df, cfg)
        assert list(df_out["status"]) == ["completed"]

    def test_notnull_filter_removes_nulls(self):
        df = pd.DataFrame({"age": [25, None, 30, None, 40]})
        cfg = _policy_config(
            row_filters=[RowFilterPolicy(column="age", operator="notnull")]
        )
        _, df_out = enforce_policies(df, cfg)
        assert df_out["age"].notna().all()
        assert len(df_out) == 3


class TestComplianceStatus:
    def test_compliant_when_no_violations(self, sample_df):
        cfg = _policy_config(deny_if_sensitive_unmasked=False)
        report, _ = enforce_policies(sample_df, cfg)
        assert report.is_compliant is True
        assert report.violations == []

    def test_non_compliant_when_deny_violated(self):
        df = pd.DataFrame({"salary": [50000]})
        cfg = _policy_config(
            sensitive_columns=[SensitiveColumnPolicy(column="salary", action="deny")]
        )
        report, _ = enforce_policies(df, cfg)
        assert report.is_compliant is False

    def test_policies_checked_count(self, sensitive_df):
        cfg = _policy_config(
            sensitive_columns=[
                SensitiveColumnPolicy(column="email", action="mask", mask_pattern="email"),
                SensitiveColumnPolicy(column="account_number", action="mask", mask_pattern="last4"),
            ],
            row_filters=[
                RowFilterPolicy(column="amount", operator="notnull"),
            ],
        )
        report, _ = enforce_policies(sensitive_df, cfg)
        assert report.policies_checked == 3  # 2 sensitive + 1 filter
