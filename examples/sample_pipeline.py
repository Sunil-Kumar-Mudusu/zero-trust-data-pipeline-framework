"""End-to-end zero-trust pipeline demonstration."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ztdpf.pipeline_runner import load_config
from ztdpf.ingestion import ingest
from ztdpf.schema_validator import validate_schema
from ztdpf.policy_engine import enforce_policies
from ztdpf.trust_score import calculate_trust
from ztdpf.lineage_tracker import LineageTracker

CONFIG = str(Path(__file__).parent / "zero_trust_policies.yaml")
SOURCE = str(Path(__file__).parent / "sample_input.csv")


def main() -> None:
    print("=" * 64)
    print("  Zero-Trust Data Pipeline Framework - Pipeline Execution")
    print("=" * 64)

    config = load_config(CONFIG)
    ingestion_result, df = ingest(SOURCE, config)
    schema_report = validate_schema(df, config)
    policy_report, df_out = enforce_policies(df, config)
    trust_report = calculate_trust(schema_report, policy_report, df_out, config)

    # ---- Stage 1: Ingestion ----
    print(f"\n[1] Data Ingestion")
    print(f"    run_id        : {ingestion_result.run_id}")
    print(f"    source        : {ingestion_result.source_name}")
    print(f"    rows loaded   : {ingestion_result.row_count}")
    print(f"    columns       : {ingestion_result.column_count}")
    print(f"    checksum      : {ingestion_result.checksum[:16]}...")
    for w in ingestion_result.warnings:
        print(f"    ADVISORY      : {w}")

    # ---- Stage 2: Schema Validation ----
    print(f"\n[2] Schema Validation")
    print(f"    schema score   : {schema_report.schema_score}")
    print(f"    missing cols   : {len(schema_report.missing_columns)}")
    print(f"    null violations: {len(schema_report.null_rate_violations)}")
    print(f"    status         : {'VALID' if schema_report.is_valid else 'INVALID'}")
    if schema_report.missing_columns:
        print(f"    missing        : {schema_report.missing_columns}")

    # ---- Stage 3: Policy Enforcement ----
    print(f"\n[3] Policy Enforcement")
    print(f"    policies checked : {policy_report.policies_checked}")
    print(f"    violations       : {len(policy_report.violations)}")
    print(f"    sensitive cols   : {len(policy_report.sensitive_columns_detected)}")
    decisions = {d.decision for d in policy_report.access_decisions}
    if "DENY" in decisions:
        overall_decision = "DENY"
    elif "MASK" in decisions:
        overall_decision = "MASK"
    else:
        overall_decision = "PERMIT"
    print(f"    access decision  : {overall_decision}")
    print(f"    status           : {'COMPLIANT' if policy_report.is_compliant else 'VIOLATION'}")
    for dec in policy_report.access_decisions:
        print(f"      [{dec.decision:6s}] {dec.column} - {dec.reason}")

    # ---- Stage 4: Trust Score ----
    print(f"\n[4] Trust Score")
    print(f"    schema trust    : {trust_report.schema_trust}")
    print(f"    policy trust    : {trust_report.policy_trust}")
    print(f"    integrity trust : {trust_report.integrity_trust}")
    print(f"    overall trust   : {trust_report.overall_trust}/100")
    print(f"    trust level     : {trust_report.trust_level}")

    # ---- Stage 5: Lineage ----
    lt = LineageTracker()
    lr = lt.record(
        ingestion_result, schema_report, policy_report,
        list(df_out.columns), len(df_out),
    )
    print(f"\n[5] Lineage Recorded")
    print(f"    lineage_id    : {lr.lineage_id}")
    print(f"    source rows   : {lr.source_row_count}")
    print(f"    output rows   : {lr.output_row_count}")
    print(f"    policies      : {len(lr.policies_applied)}")

    # ---- Summary ----
    status = "PASS" if trust_report.passes_threshold else "FAIL"
    print(f"\n{'=' * 64}")
    print(f"  PIPELINE SUMMARY")
    print(f"{'=' * 64}")
    print(f"  Run ID          : {ingestion_result.run_id}")
    print(f"  Pipeline        : {config.pipeline_name}")
    print(f"  Source          : {ingestion_result.source_name} ({ingestion_result.row_count} rows)")
    print(f"  Processed       : {len(df_out)} rows")
    print(f"  Schema score    : {schema_report.schema_score}/100")
    print(f"  Trust score     : {trust_report.overall_trust}/100")
    print(f"  Trust level     : {trust_report.trust_level}")
    print(f"  Status          : {status}")
    print(f"{'=' * 64}")


if __name__ == "__main__":
    main()
