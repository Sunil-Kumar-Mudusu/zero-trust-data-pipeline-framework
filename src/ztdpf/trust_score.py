"""Trust scoring (0–100) combining schema integrity, policy compliance, and data integrity."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import PipelineConfig
from .schema_validator import SchemaReport
from .policy_engine import PolicyReport


@dataclass
class TrustReport:
    """Composite trust assessment for a single pipeline run."""

    schema_trust: float
    policy_trust: float
    integrity_trust: float
    overall_trust: float
    trust_level: str  # "HIGH" | "MEDIUM" | "LOW" | "CRITICAL"
    passes_threshold: bool


def _integrity_score(df: pd.DataFrame) -> float:
    """
    Compute a data-integrity sub-score (0–100) based on:
      - Completeness: penalises null cells
      - Uniqueness:   penalises duplicate rows
    """
    if df.empty:
        return 0.0

    total_cells = df.shape[0] * df.shape[1]
    null_cells = int(df.isnull().sum().sum())
    null_rate = null_cells / total_cells if total_cells > 0 else 0.0
    # Penalise more steeply for high null rates
    completeness = max(0.0, 100.0 - null_rate * 200)

    dup_rate = df.duplicated().sum() / len(df) if len(df) > 0 else 0.0
    uniqueness = max(0.0, 100.0 - dup_rate * 200)

    return round(completeness * 0.6 + uniqueness * 0.4, 2)


def calculate_trust(
    schema_report: SchemaReport,
    policy_report: PolicyReport,
    df: pd.DataFrame,
    config: PipelineConfig,
) -> TrustReport:
    """
    Calculate a weighted composite trust score and derive a trust level.

    Weights are drawn from config.trust:
      - schema_weight   (default 0.35)
      - policy_weight   (default 0.40)
      - integrity_weight (default 0.25)
    """
    cfg = config.trust

    schema_trust = schema_report.schema_score
    policy_trust = (
        100.0
        if policy_report.is_compliant
        else max(0.0, 100.0 - len(policy_report.violations) * 25.0)
    )
    integrity_trust = _integrity_score(df)

    overall = (
        schema_trust * cfg.schema_weight
        + policy_trust * cfg.policy_weight
        + integrity_trust * cfg.integrity_weight
    )
    overall = round(min(100.0, max(0.0, overall)), 2)

    if overall >= 90:
        level = "HIGH"
    elif overall >= 75:
        level = "MEDIUM"
    elif overall >= 60:
        level = "LOW"
    else:
        level = "CRITICAL"

    return TrustReport(
        schema_trust=round(schema_trust, 2),
        policy_trust=round(policy_trust, 2),
        integrity_trust=integrity_trust,
        overall_trust=overall,
        trust_level=level,
        passes_threshold=overall >= cfg.min_trust_score,
    )
