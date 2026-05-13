"""End-to-end zero-trust pipeline orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import PipelineConfig
from .ingestion import ingest, IngestionResult
from .schema_validator import validate_schema, SchemaReport
from .policy_engine import enforce_policies, PolicyReport
from .trust_score import calculate_trust, TrustReport
from .lineage_tracker import LineageTracker, LineageRecord
from .audit_logger import AuditLogger
from .metadata_store import MetadataStore
from .exceptions import ZTDPFError


@dataclass
class PipelineRunResult:
    """Summary of a completed pipeline run."""

    run_id: str
    pipeline_name: str
    source_name: str
    source_row_count: int
    output_row_count: int
    schema_score: float
    trust_score: float
    trust_level: str
    audit_event_count: int
    warnings: list[str]
    status: str
    lineage_id: str = ""
    errors: list[str] = field(default_factory=list)


def load_config(config_path: str) -> PipelineConfig:
    """Load and parse a YAML pipeline configuration file."""
    with open(config_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return PipelineConfig(**raw)


def run_pipeline(source_path: str, config_path: str) -> PipelineRunResult:
    """
    Execute the full zero-trust pipeline against *source_path*.

    Pipeline stages:
      1. Ingestion         — checksum, UUID run_id
      2. Schema validation — column presence, dtype, null-rate, range
      3. Policy enforcement — sensitive detection, masking, row filters
      4. Trust scoring     — weighted composite score
      5. Lineage recording — source/output schema mapping
      6. Metadata persist  — SQLite catalog update

    Returns:
        PipelineRunResult with status PASS / WARNING / FAIL.
    """
    config = load_config(config_path)
    audit = AuditLogger(config.storage.audit_db)
    lineage = LineageTracker(config.storage.lineage_db)
    store = MetadataStore(config.storage.metadata_db)

    # 1. Ingestion
    ingestion_result, df = ingest(source_path, config)
    audit.log(
        ingestion_result.run_id,
        "ingestion",
        "ingest_source",
        detail=f"rows={ingestion_result.row_count},cols={ingestion_result.column_count}",
    )

    # 2. Schema validation
    schema_report = validate_schema(df, config)
    audit.log(
        ingestion_result.run_id,
        "schema_validation",
        "validate_schema",
        status="success" if schema_report.is_valid else "warning",
        detail=f"score={schema_report.schema_score},missing={schema_report.missing_columns}",
    )

    # 3. Policy enforcement
    policy_report, df_out = enforce_policies(df, config)
    audit.log(
        ingestion_result.run_id,
        "policy_enforcement",
        "enforce_policies",
        status="success" if policy_report.is_compliant else "violation",
        detail=(
            f"sensitive_cols={len(policy_report.sensitive_columns_detected)},"
            f"violations={len(policy_report.violations)}"
        ),
    )

    # 4. Trust score
    trust_report = calculate_trust(schema_report, policy_report, df_out, config)
    audit.log(
        ingestion_result.run_id,
        "trust_scoring",
        "calculate_trust",
        detail=f"overall={trust_report.overall_trust},level={trust_report.trust_level}",
    )

    # 5. Lineage recording
    lineage_record = lineage.record(
        ingestion_result,
        schema_report,
        policy_report,
        list(df_out.columns),
        len(df_out),
    )
    audit.log(
        ingestion_result.run_id,
        "lineage",
        "record_lineage",
        detail=f"lineage_id={lineage_record.lineage_id}",
    )

    # 6. Persist metadata
    store.save_ingestion(ingestion_result.run_id, ingestion_result)
    store.save_schema(ingestion_result.run_id, schema_report)
    store.save_policy(ingestion_result.run_id, policy_report)
    store.save_trust(ingestion_result.run_id, trust_report)

    # Aggregate warnings
    warnings: list[str] = list(ingestion_result.warnings) + list(policy_report.violations)
    if schema_report.null_rate_violations:
        warnings.append(
            f"Null-rate violations in columns: {schema_report.null_rate_violations}"
        )

    if not trust_report.passes_threshold:
        status = "FAIL"
    elif warnings:
        status = "WARNING"
    else:
        status = "PASS"

    store.save_run(ingestion_result.run_id, config.pipeline_name, trust_report, status)
    audit.log(
        ingestion_result.run_id,
        "pipeline",
        "run_complete",
        detail=f"status={status},trust={trust_report.overall_trust}",
    )

    return PipelineRunResult(
        run_id=ingestion_result.run_id,
        pipeline_name=config.pipeline_name,
        source_name=ingestion_result.source_name,
        source_row_count=ingestion_result.row_count,
        output_row_count=len(df_out),
        schema_score=schema_report.schema_score,
        trust_score=trust_report.overall_trust,
        trust_level=trust_report.trust_level,
        audit_event_count=audit.event_count(ingestion_result.run_id),
        warnings=warnings,
        status=status,
        lineage_id=lineage_record.lineage_id,
    )
