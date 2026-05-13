"""Schema validation with per-column dtype, null-rate, range, and allowed-value checks."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .config import PipelineConfig
from .exceptions import SchemaValidationError

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ColumnReport:
    """Validation result for a single column."""

    name: str
    dtype_match: bool
    null_rate: float
    null_violation: bool
    range_violation: bool
    allowed_value_violation: bool


@dataclass
class SchemaReport:
    """Aggregate result of schema validation for one pipeline run."""

    missing_columns: list[str]
    column_reports: list[ColumnReport]
    null_rate_violations: list[str]
    schema_score: float
    is_valid: bool


# ---------------------------------------------------------------------------
# Dtype mapping
# ---------------------------------------------------------------------------

_DTYPE_MAP: dict[str, tuple[str, ...]] = {
    "integer": ("int64", "int32", "int16", "int8", "Int64", "Int32", "uint8",
                "uint16", "uint32", "uint64"),
    "float": ("float64", "float32", "Float64", "Float32"),
    "string": ("object", "string", "str"),
    "boolean": ("bool", "boolean"),
    "date": ("datetime64[ns]", "datetime64[us]", "datetime64[ms]"),
}


def validate_schema(df: pd.DataFrame, config: PipelineConfig) -> SchemaReport:
    """
    Validate *df* against the schema constraints in *config*.

    Returns a SchemaReport with a schema_score (0–100) and a boolean
    is_valid flag.  Does not raise; all findings are reported.
    """
    cfg = config.schema

    # 1. Required column presence
    missing = [c for c in cfg.required_columns if c not in df.columns]

    col_reports: list[ColumnReport] = []
    null_violations: list[str] = []

    # 2. Per-column checks
    for col_schema in cfg.column_schemas:
        if col_schema.name not in df.columns:
            continue

        series = df[col_schema.name]

        # dtype check
        expected_dtypes = _DTYPE_MAP.get(col_schema.dtype, ())
        dtype_match = str(series.dtype) in expected_dtypes

        # null-rate check
        null_rate = float(series.isnull().mean())
        null_violation = not col_schema.nullable and null_rate > 0
        if null_rate > cfg.max_null_rate:
            null_violations.append(col_schema.name)

        # range check
        range_violation = False
        if col_schema.min_value is not None:
            try:
                numeric = pd.to_numeric(series, errors="coerce").dropna()
                if numeric.lt(col_schema.min_value).any():
                    range_violation = True
            except Exception:
                pass
        if col_schema.max_value is not None:
            try:
                numeric = pd.to_numeric(series, errors="coerce").dropna()
                if numeric.gt(col_schema.max_value).any():
                    range_violation = True
            except Exception:
                pass

        # allowed-values check
        allowed_violation = False
        if col_schema.allowed_values is not None:
            bad = series.dropna()[~series.dropna().isin(col_schema.allowed_values)]
            allowed_violation = len(bad) > 0

        col_reports.append(
            ColumnReport(
                name=col_schema.name,
                dtype_match=dtype_match,
                null_rate=null_rate,
                null_violation=null_violation,
                range_violation=range_violation,
                allowed_value_violation=allowed_violation,
            )
        )

    # 3. Compute schema score
    total_checks = len(cfg.required_columns) + len(cfg.column_schemas) * 3
    if total_checks == 0:
        schema_score = 100.0
    else:
        failures = (
            len(missing)
            + sum(1 for r in col_reports if not r.dtype_match)
            + len(null_violations)
            + sum(1 for r in col_reports if r.range_violation or r.allowed_value_violation)
        )
        schema_score = max(0.0, 100.0 - (failures / total_checks) * 100)

    is_valid = len(missing) == 0 and len(null_violations) == 0

    return SchemaReport(
        missing_columns=missing,
        column_reports=col_reports,
        null_rate_violations=null_violations,
        schema_score=round(schema_score, 2),
        is_valid=is_valid,
    )
