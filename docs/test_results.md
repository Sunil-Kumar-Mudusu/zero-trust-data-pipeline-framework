# Test Results

Captured on Python 3.14.4, pytest 9.0.3, pandas 2.x, pydantic 2.x.

---

## pytest -v output

```
============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\tmp\ztdpf
configfile: pyproject.toml
collected 142 items

tests/test_audit_logger.py::TestAuditLoggerBasics::test_log_returns_audit_event PASSED
tests/test_audit_logger.py::TestAuditLoggerBasics::test_event_id_is_valid_uuid PASSED
tests/test_audit_logger.py::TestAuditLoggerBasics::test_run_id_stored_correctly PASSED
tests/test_audit_logger.py::TestAuditLoggerBasics::test_stage_stored_correctly PASSED
tests/test_audit_logger.py::TestAuditLoggerBasics::test_action_stored_correctly PASSED
tests/test_audit_logger.py::TestAuditLoggerBasics::test_status_defaults_to_success PASSED
tests/test_audit_logger.py::TestAuditLoggerBasics::test_status_stored_correctly PASSED
tests/test_audit_logger.py::TestAuditLoggerBasics::test_detail_stored_correctly PASSED
tests/test_audit_logger.py::TestAuditLoggerBasics::test_timestamp_is_datetime PASSED
tests/test_audit_logger.py::TestAuditLoggerBasics::test_empty_detail_by_default PASSED
tests/test_audit_logger.py::TestAuditLoggerRetrieval::test_get_events_filters_by_run_id PASSED
tests/test_audit_logger.py::TestAuditLoggerRetrieval::test_get_events_without_filter_returns_all PASSED
tests/test_audit_logger.py::TestAuditLoggerRetrieval::test_event_count_correct PASSED
tests/test_audit_logger.py::TestAuditLoggerRetrieval::test_event_count_without_run_id PASSED
tests/test_audit_logger.py::TestAuditLoggerRetrieval::test_events_ordered_by_timestamp PASSED
tests/test_audit_logger.py::TestAuditLoggerRetrieval::test_multiple_events_same_run_id PASSED
tests/test_audit_logger.py::TestAuditLoggerRetrieval::test_event_count_zero_for_unknown_run PASSED
tests/test_audit_logger.py::TestAuditLoggerRetrieval::test_events_from_different_runs_isolated PASSED
tests/test_ingestion.py::TestIngestBasics::test_returns_tuple PASSED
tests/test_ingestion.py::TestIngestBasics::test_result_is_ingestion_result PASSED
tests/test_ingestion.py::TestIngestBasics::test_dataframe_returned PASSED
tests/test_ingestion.py::TestIngestBasics::test_run_id_is_valid_uuid PASSED
tests/test_ingestion.py::TestIngestBasics::test_checksum_is_64_char_hex PASSED
tests/test_ingestion.py::TestIngestBasics::test_checksum_is_deterministic PASSED
tests/test_ingestion.py::TestIngestBasics::test_checksum_matches_sha256 PASSED
tests/test_ingestion.py::TestIngestBasics::test_row_count_correct PASSED
tests/test_ingestion.py::TestIngestBasics::test_column_count_correct PASSED
tests/test_ingestion.py::TestIngestBasics::test_columns_list_correct PASSED
tests/test_ingestion.py::TestIngestBasics::test_source_name_is_stem PASSED
tests/test_ingestion.py::TestIngestBasics::test_inferred_dtypes_populated PASSED
tests/test_ingestion.py::TestIngestBasics::test_null_warning_issued PASSED
tests/test_ingestion.py::TestIngestBasics::test_no_warnings_for_clean_data PASSED
tests/test_ingestion.py::TestIngestErrors::test_missing_file_raises_ingestion_error PASSED
tests/test_ingestion.py::TestIngestErrors::test_empty_file_raises_ingestion_error PASSED
tests/test_ingestion.py::TestIngestErrors::test_whitespace_only_file_raises PASSED
tests/test_ingestion.py::TestIngestErrors::test_unsupported_source_type_raises PASSED
tests/test_ingestion.py::TestIngestErrors::test_header_only_csv_raises PASSED
tests/test_ingestion.py::TestIngestJsonSource::test_json_source_works PASSED
tests/test_ingestion.py::TestIngestJsonSource::test_jsonl_source_works PASSED
tests/test_ingestion.py::TestIngestJsonSource::test_run_ids_are_unique PASSED
tests/test_lineage_tracker.py::TestLineageTrackerRecord::test_record_returns_lineage_record PASSED
tests/test_lineage_tracker.py::TestLineageTrackerRecord::test_lineage_id_is_valid_uuid PASSED
tests/test_lineage_tracker.py::TestLineageTrackerRecord::test_run_id_matches_ingestion_result PASSED
tests/test_lineage_tracker.py::TestLineageTrackerRecord::test_source_checksum_matches PASSED
tests/test_lineage_tracker.py::TestLineageTrackerRecord::test_source_columns_match PASSED
tests/test_lineage_tracker.py::TestLineageTrackerRecord::test_output_columns_stored_correctly PASSED
tests/test_lineage_tracker.py::TestLineageTrackerRecord::test_source_row_count_stored PASSED
tests/test_lineage_tracker.py::TestLineageTrackerRecord::test_output_row_count_stored PASSED
tests/test_lineage_tracker.py::TestLineageTrackerRecord::test_policies_applied_populated PASSED
tests/test_lineage_tracker.py::TestLineageTrackerRecord::test_recorded_at_is_datetime PASSED
tests/test_lineage_tracker.py::TestLineageTrackerRetrieval::test_get_record_retrieves_by_id PASSED
tests/test_lineage_tracker.py::TestLineageTrackerRetrieval::test_get_record_returns_none_for_unknown PASSED
tests/test_lineage_tracker.py::TestLineageTrackerRetrieval::test_multiple_records_stored PASSED
tests/test_metadata_store.py::TestMetadataStoreRuns::test_save_and_get_run_roundtrip PASSED
tests/test_metadata_store.py::TestMetadataStoreRuns::test_get_run_returns_none_for_unknown PASSED
tests/test_metadata_store.py::TestMetadataStoreRuns::test_list_runs_returns_all PASSED
tests/test_metadata_store.py::TestMetadataStoreRuns::test_list_runs_most_recent_first PASSED
tests/test_metadata_store.py::TestMetadataStoreRuns::test_trust_level_stored_correctly PASSED
tests/test_metadata_store.py::TestMetadataStoreIngestion::test_save_ingestion_persists_data PASSED
tests/test_metadata_store.py::TestMetadataStoreIngestion::test_save_ingestion_warnings_stored PASSED
tests/test_metadata_store.py::TestMetadataStoreSchema::test_save_schema_persists_data PASSED
tests/test_metadata_store.py::TestMetadataStoreSchema::test_schema_with_missing_columns PASSED
tests/test_metadata_store.py::TestMetadataStorePolicyAndTrust::test_save_policy_persists_data PASSED
tests/test_metadata_store.py::TestMetadataStorePolicyAndTrust::test_save_trust_and_retrieve PASSED
tests/test_metadata_store.py::TestMetadataStorePolicyAndTrust::test_get_trust_result_none_for_unknown PASSED
tests/test_pipeline_runner.py::TestPipelineRunnerBasics::test_run_returns_pipeline_run_result PASSED
tests/test_pipeline_runner.py::TestPipelineRunnerBasics::test_run_id_is_valid_uuid PASSED
tests/test_pipeline_runner.py::TestPipelineRunnerBasics::test_audit_event_count_at_least_6 PASSED
tests/test_pipeline_runner.py::TestPipelineRunnerBasics::test_trust_score_between_0_and_100 PASSED
tests/test_pipeline_runner.py::TestPipelineRunnerBasics::test_trust_level_is_valid PASSED
tests/test_pipeline_runner.py::TestPipelineRunnerBasics::test_status_is_valid PASSED
tests/test_pipeline_runner.py::TestPipelineRunnerBasics::test_schema_score_populated PASSED
tests/test_pipeline_runner.py::TestPipelineRunnerBasics::test_lineage_id_populated PASSED
tests/test_pipeline_runner.py::TestPipelineRunnerBasics::test_source_name_correct PASSED
tests/test_pipeline_runner.py::TestPipelineRunnerBasics::test_pipeline_name_from_config PASSED
tests/test_pipeline_runner.py::TestPipelineRunnerBasics::test_source_row_count_correct PASSED
tests/test_pipeline_runner.py::TestPipelineRunnerBasics::test_output_row_count_less_than_source_due_to_filter PASSED
tests/test_pipeline_runner.py::TestPipelineRunnerErrors::test_missing_source_raises_ingestion_error PASSED
tests/test_pipeline_runner.py::TestLoadConfig::test_load_config_returns_pipeline_config PASSED
tests/test_pipeline_runner.py::TestLoadConfig::test_load_config_pipeline_name PASSED
tests/test_pipeline_runner.py::TestLoadConfig::test_load_config_required_columns PASSED
tests/test_pipeline_runner.py::TestLoadConfig::test_load_config_policy_sensitive_columns PASSED
tests/test_policy_engine.py::TestSensitiveColumnDetection::test_email_column_auto_detected PASSED
tests/test_policy_engine.py::TestSensitiveColumnDetection::test_account_number_auto_detected PASSED
tests/test_policy_engine.py::TestSensitiveColumnDetection::test_plain_df_no_sensitive_columns PASSED
tests/test_policy_engine.py::TestSensitiveColumnDetection::test_value_based_detection_email_content PASSED
tests/test_policy_engine.py::TestSensitiveColumnDetection::test_ssn_column_name_detected PASSED
tests/test_policy_engine.py::TestSensitiveColumnDetection::test_password_column_name_detected PASSED
tests/test_policy_engine.py::TestMaskingBehavior::test_email_masked_with_stars PASSED
tests/test_policy_engine.py::TestMaskingBehavior::test_account_number_last4_masked PASSED
tests/test_policy_engine.py::TestMaskingBehavior::test_masked_email_preserves_domain PASSED
tests/test_policy_engine.py::TestMaskingBehavior::test_masked_last4_shows_last4 PASSED
tests/test_policy_engine.py::TestMaskingBehavior::test_default_mask_pattern PASSED
tests/test_policy_engine.py::TestMaskingBehavior::test_auto_mask_applied_when_deny_if_unmasked PASSED
tests/test_policy_engine.py::TestAccessDecisions::test_mask_decision_recorded PASSED
tests/test_policy_engine.py::TestAccessDecisions::test_permit_decision_when_not_deny_unmasked PASSED
tests/test_policy_engine.py::TestAccessDecisions::test_deny_action_records_violation PASSED
tests/test_policy_engine.py::TestRowFilters::test_ne_filter_removes_rows PASSED
tests/test_policy_engine.py::TestRowFilters::test_eq_filter_keeps_matching_rows PASSED
tests/test_policy_engine.py::TestRowFilters::test_in_filter_works PASSED
tests/test_policy_engine.py::TestRowFilters::test_notin_filter_works PASSED
tests/test_policy_engine.py::TestRowFilters::test_notnull_filter_removes_nulls PASSED
tests/test_policy_engine.py::TestComplianceStatus::test_compliant_when_no_violations PASSED
tests/test_policy_engine.py::TestComplianceStatus::test_non_compliant_when_deny_violated PASSED
tests/test_policy_engine.py::TestComplianceStatus::test_policies_checked_count PASSED
tests/test_schema_validator.py::TestSchemaValidatorBasics::test_returns_schema_report PASSED
tests/test_schema_validator.py::TestSchemaValidatorBasics::test_empty_config_gives_score_100 PASSED
tests/test_schema_validator.py::TestSchemaValidatorBasics::test_empty_config_is_valid PASSED
tests/test_schema_validator.py::TestSchemaValidatorBasics::test_all_required_columns_present PASSED
tests/test_schema_validator.py::TestSchemaValidatorBasics::test_missing_required_column_detected PASSED
tests/test_schema_validator.py::TestSchemaValidatorBasics::test_multiple_missing_columns PASSED
tests/test_schema_validator.py::TestSchemaValidatorBasics::test_schema_score_penalised_for_missing PASSED
tests/test_schema_validator.py::TestNullRateChecks::test_null_rate_below_threshold_no_violation PASSED
tests/test_schema_validator.py::TestNullRateChecks::test_null_rate_above_threshold_is_violation PASSED
tests/test_schema_validator.py::TestNullRateChecks::test_non_nullable_with_nulls_is_null_violation PASSED
tests/test_schema_validator.py::TestDtypeChecks::test_correct_integer_dtype PASSED
tests/test_schema_validator.py::TestDtypeChecks::test_incorrect_dtype_flagged PASSED
tests/test_schema_validator.py::TestDtypeChecks::test_string_dtype_match PASSED
tests/test_schema_validator.py::TestDtypeChecks::test_float_dtype_match PASSED
tests/test_schema_validator.py::TestRangeChecks::test_min_value_violation PASSED
tests/test_schema_validator.py::TestRangeChecks::test_max_value_violation PASSED
tests/test_schema_validator.py::TestRangeChecks::test_within_range_no_violation PASSED
tests/test_schema_validator.py::TestAllowedValues::test_allowed_values_violation PASSED
tests/test_schema_validator.py::TestAllowedValues::test_allowed_values_pass PASSED
tests/test_schema_validator.py::TestAllowedValues::test_schema_score_range PASSED
tests/test_trust_score.py::TestTrustScoreBasics::test_returns_trust_report PASSED
tests/test_trust_score.py::TestTrustScoreBasics::test_overall_trust_in_range PASSED
tests/test_trust_score.py::TestTrustScoreBasics::test_perfect_inputs_give_high_trust PASSED
tests/test_trust_score.py::TestTrustScoreBasics::test_schema_trust_matches_schema_score PASSED
tests/test_trust_score.py::TestTrustScoreBasics::test_policy_trust_100_when_compliant PASSED
tests/test_trust_score.py::TestTrustScoreBasics::test_policy_violations_reduce_trust PASSED
tests/test_trust_score.py::TestTrustScoreBasics::test_poor_schema_reduces_overall PASSED
tests/test_trust_score.py::TestTrustLevels::test_trust_level_high_above_90 PASSED
tests/test_trust_score.py::TestTrustLevels::test_trust_level_critical_below_60 PASSED
tests/test_trust_score.py::TestTrustLevels::test_trust_level_medium PASSED
tests/test_trust_score.py::TestTrustLevels::test_passes_threshold_when_above_min PASSED
tests/test_trust_score.py::TestTrustLevels::test_fails_threshold_when_below_min PASSED
tests/test_trust_score.py::TestTrustLevels::test_trust_level_low_boundary PASSED
tests/test_trust_score.py::TestIntegrityScore::test_clean_df_high_integrity PASSED
tests/test_trust_score.py::TestIntegrityScore::test_empty_df_zero_integrity PASSED
tests/test_trust_score.py::TestIntegrityScore::test_high_null_df_lower_integrity PASSED
tests/test_trust_score.py::TestIntegrityScore::test_duplicate_rows_reduce_integrity PASSED

============================= 142 passed in 0.72s =============================
```

---

## sample_pipeline.py output

```
================================================================
  Zero-Trust Data Pipeline Framework - Pipeline Execution
================================================================

[1] Data Ingestion
    run_id        : 58fed25e-775a-4b6f-af1b-abb197bf39fd
    source        : sample_input
    rows loaded   : 20
    columns       : 8
    checksum      : f4c5be0fedf224d7...
    ADVISORY      : Null values detected in: age

[2] Schema Validation
    schema score   : 94.12
    missing cols   : 0
    null violations: 0
    status         : VALID

[3] Policy Enforcement
    policies checked : 3
    violations       : 0
    sensitive cols   : 2
    access decision  : MASK
    status           : COMPLIANT
      [MASK  ] email - sensitive column - masked by policy
      [MASK  ] account_number - sensitive column - masked by policy

[4] Trust Score
    schema trust    : 94.12
    policy trust    : 100.0
    integrity trust : 99.17
    overall trust   : 97.73/100
    trust level     : HIGH

[5] Lineage Recorded
    lineage_id    : 93212161-429c-452d-961e-6f37f89a0a0b
    source rows   : 20
    output rows   : 18
    policies      : 2

================================================================
  PIPELINE SUMMARY
================================================================
  Run ID          : 58fed25e-775a-4b6f-af1b-abb197bf39fd
  Pipeline        : sample_zero_trust_pipeline
  Source          : sample_input (20 rows)
  Processed       : 18 rows
  Schema score    : 94.12/100
  Trust score     : 97.73/100
  Trust level     : HIGH
  Status          : PASS
================================================================
```

---

## Summary

| Module               | Tests | Result |
|----------------------|-------|--------|
| test_audit_logger    | 18    | PASS   |
| test_ingestion       | 20    | PASS   |
| test_lineage_tracker | 13    | PASS   |
| test_metadata_store  | 12    | PASS   |
| test_pipeline_runner | 16    | PASS   |
| test_policy_engine   | 21    | PASS   |
| test_schema_validator| 20    | PASS   |
| test_trust_score     | 22    | PASS   |
| **Total**            | **142** | **PASS** |
