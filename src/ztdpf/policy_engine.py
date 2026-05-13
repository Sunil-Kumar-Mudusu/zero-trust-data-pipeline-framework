"""Zero-trust policy enforcement: sensitive column detection, access decisions, masking."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from .config import PipelineConfig, SensitiveColumnPolicy
from .exceptions import PolicyViolationError

# ---------------------------------------------------------------------------
# Built-in sensitive patterns (value-level scanning)
# ---------------------------------------------------------------------------

_SENSITIVE_VALUE_PATTERNS: dict[str, re.Pattern] = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
}

# Column names that are considered sensitive regardless of content
_SENSITIVE_COL_NAMES: frozenset[str] = frozenset(
    {
        "ssn", "social_security", "social_security_number",
        "email", "email_address",
        "phone", "phone_number", "mobile", "cell",
        "credit_card", "card_number", "cvv",
        "password", "passwd", "secret", "token",
        "dob", "date_of_birth", "birthdate",
        "ip_address", "ip",
        "salary", "income", "wage",
        "medical_record", "diagnosis", "patient_id",
        "account_number", "routing_number",
    }
)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class AccessDecision:
    """Access control decision for a single column."""

    column: str
    decision: str  # "PERMIT" | "MASK" | "DENY"
    reason: str


@dataclass
class PolicyReport:
    """Aggregate result of policy enforcement for one pipeline run."""

    policies_checked: int
    violations: list[str]
    sensitive_columns_detected: list[str]
    access_decisions: list[AccessDecision]
    is_compliant: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_sensitive_columns(
    df: pd.DataFrame, config: PipelineConfig
) -> list[str]:
    """Return an ordered, deduplicated list of sensitive column names."""
    detected: list[str] = []

    for col in df.columns:
        # Name-based detection
        if col.lower() in _SENSITIVE_COL_NAMES:
            detected.append(col)
            continue

        # Config-supplied regex patterns against column name
        name_matched = False
        for pattern in config.policy.sensitive_patterns:
            if re.search(pattern, col, re.IGNORECASE):
                detected.append(col)
                name_matched = True
                break
        if name_matched:
            continue

        # Value-based detection on string columns
        if str(df[col].dtype) in ("object", "str", "string"):
            sample = df[col].dropna().astype(str).head(50)
            for _pat_name, pat in _SENSITIVE_VALUE_PATTERNS.items():
                if sample.str.contains(pat.pattern, regex=True).any():
                    detected.append(col)
                    break

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for item in detected:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _mask_value(val: str, pattern: Optional[str]) -> str:
    """Apply a masking pattern to a string value."""
    if pattern is None:
        return "***MASKED***"
    if pattern == "email":
        parts = str(val).split("@")
        if len(parts) == 2:
            local = parts[0]
            return (local[:2] + "***@" + parts[1]) if len(local) >= 2 else "***@" + parts[1]
        return "***@***.***"
    if pattern == "last4":
        s = re.sub(r"[\s\-]", "", str(val))
        return ("****" + s[-4:]) if len(s) >= 4 else "****"
    return "***MASKED***"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def enforce_policies(
    df: pd.DataFrame,
    config: PipelineConfig,
) -> tuple[PolicyReport, pd.DataFrame]:
    """
    Apply all zero-trust policies to *df*.

    Returns:
        (PolicyReport, masked/filtered DataFrame)

    Does not raise; violations are captured in PolicyReport.violations and
    is_compliant is set to False when any denial or unhandled violation occurs.
    """
    cfg = config.policy
    violations: list[str] = []
    decisions: list[AccessDecision] = []
    df_out = df.copy()

    # Auto-detect sensitive columns
    auto_detected = _detect_sensitive_columns(df, config)

    # Build explicit policy lookup
    policy_map: dict[str, SensitiveColumnPolicy] = {
        p.column: p for p in cfg.sensitive_columns
    }

    # ---- Process auto-detected columns ----
    for col in auto_detected:
        if col not in df_out.columns:
            continue
        pol = policy_map.get(col)
        if pol is not None:
            action = pol.action
        elif cfg.deny_if_sensitive_unmasked:
            action = "mask"
        else:
            action = "allow"

        if action in ("deny", "block"):
            violations.append(
                f"Column '{col}' is sensitive and access is denied by policy."
            )
            decisions.append(
                AccessDecision(col, "DENY", "sensitive column — denied by policy")
            )
        elif action == "mask":
            mask_pat = pol.mask_pattern if pol else None
            df_out[col] = df_out[col].apply(
                lambda v, mp=mask_pat: _mask_value(str(v), mp) if pd.notna(v) else v
            )
            decisions.append(
                AccessDecision(col, "MASK", "sensitive column — masked by policy")
            )
        else:
            decisions.append(
                AccessDecision(col, "PERMIT", "sensitive column — permitted by policy")
            )

    # ---- Process explicitly configured columns not auto-detected ----
    for col, pol in policy_map.items():
        if col in auto_detected:
            continue
        if col not in df_out.columns:
            continue
        if pol.action in ("deny", "block"):
            violations.append(
                f"Column '{col}' denied by explicit policy."
            )
            decisions.append(
                AccessDecision(col, "DENY", "explicit deny policy")
            )
        elif pol.action == "mask":
            df_out[col] = df_out[col].apply(
                lambda v, mp=pol.mask_pattern: _mask_value(str(v), mp) if pd.notna(v) else v
            )
            decisions.append(
                AccessDecision(col, "MASK", "explicit mask policy")
            )

    # ---- Apply row filters ----
    for rf in cfg.row_filters:
        if rf.column not in df_out.columns:
            continue
        col_series = df_out[rf.column]
        if rf.operator == "eq":
            df_out = df_out[col_series == rf.value]
        elif rf.operator == "ne":
            df_out = df_out[col_series != rf.value]
        elif rf.operator == "in":
            df_out = df_out[col_series.isin(rf.value)]
        elif rf.operator == "notin":
            df_out = df_out[~col_series.isin(rf.value)]
        elif rf.operator == "notnull":
            df_out = df_out[col_series.notna()]
        elif rf.operator == "isnull":
            df_out = df_out[col_series.isna()]

    is_compliant = len(violations) == 0

    return (
        PolicyReport(
            policies_checked=len(cfg.sensitive_columns) + len(cfg.row_filters),
            violations=violations,
            sensitive_columns_detected=auto_detected,
            access_decisions=decisions,
            is_compliant=is_compliant,
        ),
        df_out,
    )
