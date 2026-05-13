# Article-to-Implementation Mapping

> This framework was formalized as a GitHub reference implementation during
> March–April 2026 based on the published article.

## Source Publication

**Title:** Zero-Trust Data Pipelines for AI Systems: A Framework for Secure, Verifiable, and Auditable Data Engineering

**Authors:** Mudusu, S. K., & Gentyala, S.

**Journal:** JRTCSE — Journal of Research Trends in Computer Science and Engineering

**Volume/Issue:** Vol. 14, Issue 2, 2026

**URL:** https://jrtcse.com/index.php/home/article/view/JRTCSE.2026.14.2.2/JRTCSE.2026.14.2.2

---

## Concept-to-Module Mapping

### 1. Zero-Trust Security Model for Data Pipelines

**Paper concept:** Apply zero-trust principles ("never trust, always verify") to
every stage of a data pipeline rather than only at network perimeters.

**Implementation:** `src/ztdpf/policy_engine.py`

The `enforce_policies()` function implements never-trust-by-default: every column
in the arriving DataFrame is checked against both name-based and value-based
sensitivity rules. No column is permitted downstream without explicit evaluation.
The `deny_if_sensitive_unmasked` configuration flag enforces this default-deny posture.

---

### 2. Cryptographic Data Provenance

**Paper concept:** Bind each pipeline run to a specific version of the source data
using cryptographic hashing to prevent silent substitution attacks.

**Implementation:** `src/ztdpf/ingestion.py` — `ingest()`

SHA-256 is computed over raw file bytes before parsing. The `IngestionResult`
dataclass carries both the `checksum` and a UUID4 `run_id` that propagates through
all downstream stages, creating a verifiable chain of custody.

---

### 3. Schema Contract Enforcement

**Paper concept:** Treat the schema as a formal contract that arriving data must
satisfy. Violations should be quantified rather than silently ignored.

**Implementation:** `src/ztdpf/schema_validator.py` — `validate_schema()`

The `SchemaConfig` declares required columns, per-column dtypes, null-rate limits,
value ranges, and allowed values. The `SchemaReport` quantifies compliance as a
`schema_score` (0–100) and carries specific violation lists for governance reporting.

---

### 4. Automated PII and Sensitive Data Detection

**Paper concept:** Sensitive data should be detected automatically using both
structural (column name) and content-level (value pattern) signals, not solely
through manual annotation.

**Implementation:** `src/ztdpf/policy_engine.py` — `_detect_sensitive_columns()`

Two detection mechanisms are combined:
- **Name-based:** A built-in dictionary of 30+ sensitive field names (SSN, email,
  password, salary, medical record, etc.)
- **Value-based:** Regex pattern scanning on string column values for emails, SSNs,
  phone numbers, and credit card patterns

This dual-layer approach mirrors the paper's recommendation for defence-in-depth
sensitive data discovery.

---

### 5. Tiered Access Control (PERMIT / MASK / DENY)

**Paper concept:** Access decisions for sensitive columns should be tiered rather
than binary, allowing masked access as a middle ground between full access and
complete denial.

**Implementation:** `src/ztdpf/policy_engine.py` — `enforce_policies()`

Each sensitive column receives an `AccessDecision` with decision `PERMIT`, `MASK`,
or `DENY`. The masking sub-system supports configurable patterns (`email`, `last4`,
or default full masking), implementing the principle of least-privilege data exposure.

---

### 6. Row-Level Security

**Paper concept:** Access control in data pipelines must extend to individual rows,
not only columns. Certain rows may be excluded based on access policy.

**Implementation:** `src/ztdpf/policy_engine.py` — `RowFilterPolicy`

The `enforce_policies()` function applies row-level filters after column masking.
Supported operators: `eq`, `ne`, `in`, `notin`, `notnull`, `isnull`. This enables
policies such as "exclude all rows with status=failed" or "only process rows with
non-null account_number."

---

### 7. Quantified Trust Scoring

**Paper concept:** Pipeline trustworthiness should be expressed as a quantitative
metric combining multiple dimensions of quality and policy compliance, enabling
threshold-based automated governance decisions.

**Implementation:** `src/ztdpf/trust_score.py` — `calculate_trust()`

The three-dimensional trust score:
- **Schema trust** (weight 0.35): schema contract compliance score
- **Policy trust** (weight 0.40): zero-trust policy compliance
- **Data integrity trust** (weight 0.25): completeness and uniqueness

The overall score (0–100) maps to trust levels (HIGH/MEDIUM/LOW/CRITICAL) and
is compared against `min_trust_score` to produce a binary pass/fail gate.

---

### 8. Immutable Audit Trail

**Paper concept:** Every operation on data must be recorded in an append-only,
tamper-evident log that supports compliance review and incident response.

**Implementation:** `src/ztdpf/audit_logger.py` — `AuditLogger`

The `log()` method appends `AuditEvent` records using SQLite `INSERT` (not
`INSERT OR REPLACE`) to preserve immutability. Each event carries a unique
`event_id`, `run_id`, `stage`, `action`, `status`, `detail`, and `timestamp`.
The pipeline runner emits at least six events per run (one per stage).

---

### 9. Data Lineage Recording

**Paper concept:** The complete transformation history of a dataset — from source
schema through applied policies to output schema — must be recorded and queryable
for compliance and provenance investigations.

**Implementation:** `src/ztdpf/lineage_tracker.py` — `LineageTracker`

Each `LineageRecord` captures:
- Source path and SHA-256 checksum
- Source and output column lists
- All policy access decisions applied
- Source and output row counts
- Cryptographically unique `lineage_id` (UUID4)

This creates an immutable, queryable lineage graph for every pipeline run.

---

### 10. SQLite-Backed Metadata Catalog

**Paper concept:** Pipeline metadata must be persisted in a queryable catalog to
enable run-history analysis, trend monitoring, and trust-score governance.

**Implementation:** `src/ztdpf/metadata_store.py` — `MetadataStore`

A five-table SQLite schema persists ingestion, schema, policy, trust, and
run-level metadata. The `list_runs()` method enables most-recent-first querying
of run history, supporting operational dashboards and governance reporting.

---

### 11. Pipeline Orchestration

**Paper concept:** The zero-trust stages should be composed into a single, coherent
pipeline that propagates the run identity and enforces stage ordering.

**Implementation:** `src/ztdpf/pipeline_runner.py` — `run_pipeline()`

The runner composes all six stages in sequence, propagating the `run_id` from
ingestion through audit logging. The `PipelineRunResult` provides a single
structured object capturing every governance-relevant metric from the run.

---

## Implementation Coverage Summary

| Paper Concept                          | Module                  | Key Function/Class           |
|----------------------------------------|-------------------------|------------------------------|
| Cryptographic provenance               | `ingestion`             | `ingest()`, SHA-256 checksum |
| Schema contract enforcement            | `schema_validator`      | `validate_schema()`          |
| Automated sensitive data detection     | `policy_engine`         | `_detect_sensitive_columns()` |
| Tiered access control (PERMIT/MASK/DENY)| `policy_engine`        | `enforce_policies()`         |
| Row-level security                     | `policy_engine`         | `RowFilterPolicy`            |
| Quantified trust scoring               | `trust_score`           | `calculate_trust()`          |
| Immutable audit trail                  | `audit_logger`          | `AuditLogger`                |
| Data lineage recording                 | `lineage_tracker`       | `LineageTracker`             |
| Metadata catalog                       | `metadata_store`        | `MetadataStore`              |
| Configuration model                    | `config`                | `PipelineConfig`             |
| Pipeline orchestration                 | `pipeline_runner`       | `run_pipeline()`             |
