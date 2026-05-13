# Verification Checklist

Use this checklist to verify a pipeline run meets zero-trust quality standards.

---

## Stage 1 — Ingestion

- [ ] `IngestionResult.run_id` is a valid UUID4
- [ ] `IngestionResult.checksum` is a 64-character SHA-256 hex string
- [ ] `IngestionResult.row_count` matches the number of rows in the source file
- [ ] `IngestionResult.column_count` matches the number of columns in the source file
- [ ] `IngestionResult.source_name` matches the stem of the source file path
- [ ] `IngestionResult.ingested_at` is a timezone-aware datetime
- [ ] `IngestionResult.inferred_dtypes` is populated for all columns
- [ ] `IngestionResult.warnings` is reviewed for null-value advisories

---

## Stage 2 — Schema Validation

- [ ] `SchemaReport.missing_columns == []` (all required columns present)
- [ ] `SchemaReport.null_rate_violations == []` (all columns within null threshold)
- [ ] `SchemaReport.schema_score >= 80` (acceptable schema quality)
- [ ] `SchemaReport.is_valid == True`
- [ ] All `ColumnReport.dtype_match == True` for configured columns
- [ ] All `ColumnReport.range_violation == False`
- [ ] All `ColumnReport.allowed_value_violation == False`
- [ ] All `ColumnReport.null_violation == False` for non-nullable columns

---

## Stage 3 — Policy Enforcement

- [ ] `PolicyReport.sensitive_columns_detected` matches expected PII columns
- [ ] All expected sensitive columns have `AccessDecision.decision == "MASK"` or `"PERMIT"`
- [ ] No `AccessDecision.decision == "DENY"` entries (unless intentionally blocked)
- [ ] `PolicyReport.violations == []`
- [ ] `PolicyReport.is_compliant == True`
- [ ] `PolicyReport.policies_checked` equals the number of configured sensitive_columns + row_filters
- [ ] Row filter reduced the row count as expected

---

## Stage 4 — Trust Scoring

- [ ] `TrustReport.schema_trust >= 80`
- [ ] `TrustReport.policy_trust == 100` (full policy compliance)
- [ ] `TrustReport.integrity_trust >= 70`
- [ ] `TrustReport.overall_trust >= 80`
- [ ] `TrustReport.trust_level in ("HIGH", "MEDIUM")`
- [ ] `TrustReport.passes_threshold == True`

---

## Stage 5 — Lineage

- [ ] `LineageRecord.lineage_id` is a valid UUID4
- [ ] `LineageRecord.source_checksum` matches `IngestionResult.checksum`
- [ ] `LineageRecord.source_columns` matches `IngestionResult.columns`
- [ ] `LineageRecord.output_columns` reflects post-masking column list
- [ ] `LineageRecord.policies_applied` is non-empty when sensitive columns were detected
- [ ] `LineageRecord.source_row_count` matches `IngestionResult.row_count`
- [ ] `LineageRecord.output_row_count <= source_row_count` (filtering may reduce rows)
- [ ] `LineageRecord.recorded_at` is a timezone-aware datetime

---

## Stage 6 — Audit and Metadata

- [ ] `AuditLogger.event_count(run_id) >= 6` (one event per pipeline stage)
- [ ] Audit events cover stages: `ingestion`, `schema_validation`, `policy_enforcement`,
      `trust_scoring`, `lineage`, `pipeline`
- [ ] All audit events have a valid UUID4 `event_id`
- [ ] All audit events reference the correct `run_id`
- [ ] `MetadataStore.get_run(run_id)` is not None
- [ ] `MetadataStore.get_schema_result(run_id)` is not None
- [ ] `MetadataStore.get_trust_result(run_id)` is not None

---

## Pipeline Run Result

- [ ] `PipelineRunResult.run_id` is a valid UUID4
- [ ] `PipelineRunResult.trust_score` is between 0.0 and 100.0
- [ ] `PipelineRunResult.trust_level in ("HIGH", "MEDIUM", "LOW", "CRITICAL")`
- [ ] `PipelineRunResult.status in ("PASS", "WARNING", "FAIL")`
- [ ] `PipelineRunResult.audit_event_count >= 6`
- [ ] `PipelineRunResult.lineage_id` is a non-empty valid UUID4
- [ ] `PipelineRunResult.schema_score >= 0.0`

---

## Recommended Thresholds for Production Promotion

| Metric                      | Minimum for PASS |
|-----------------------------|-----------------|
| `SchemaReport.schema_score` | ≥ 80            |
| `TrustReport.policy_trust`  | = 100           |
| `TrustReport.overall_trust` | ≥ 80            |
| `TrustReport.trust_level`   | HIGH or MEDIUM  |
| Audit event count           | ≥ 6             |
| Policy violations           | 0               |
| Missing required columns    | 0               |

---

## Test Coverage

- [ ] All 8 modules have dedicated test files
- [ ] `pytest -q` exits with 0 failures
- [ ] Total test count ≥ 120
- [ ] `python examples/sample_pipeline.py` completes without error
- [ ] Sample pipeline reports trust level HIGH or MEDIUM
