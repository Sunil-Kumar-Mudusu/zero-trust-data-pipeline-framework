# Architecture: Zero-Trust Data Pipeline Framework

## Overview

The Zero-Trust Data Pipeline Framework implements a six-stage pipeline that applies
zero-trust security principles to every data flow. Rather than implicitly trusting
any data at any stage, the framework enforces continuous verification, least-privilege
access, and complete auditability throughout the processing lifecycle.

---

## Core Principle

Traditional data pipelines assume that data arriving from a trusted source can be
passed through downstream stages without re-verification. The zero-trust model
rejects this assumption: **no data element is trusted until it has been verified,
validated, and cleared by policy at every stage.**

---

## The Six-Stage Pipeline

### Stage 1 — Ingestion (`ztdpf.ingestion`)

**Purpose:** Securely ingest a data source and produce a tamper-evident record.

**Mechanism:**
- A unique `run_id` (UUID4) is assigned to each pipeline execution
- A SHA-256 checksum is computed over the raw file bytes before parsing
- Source type is validated (`csv`, `json`, `jsonl`)
- Null-column warnings are emitted for transparency
- An `IngestionResult` dataclass captures all provenance metadata

**Zero-Trust Relevance:** The checksum binds the pipeline run to a specific, known
version of the source file. Any downstream tampering or re-ingestion of a different
file will produce a different checksum, breaking the chain of trust.

---

### Stage 2 — Schema Validation (`ztdpf.schema_validator`)

**Purpose:** Verify that every arriving dataset conforms to the declared contract.

**Mechanism:**
- Required column presence is checked first; missing columns are flagged
- Per-column dtype matching (string/integer/float/boolean/date)
- Null-rate enforcement: columns exceeding `max_null_rate` are flagged as violations
- Range checks: `min_value` and `max_value` constraints on numeric columns
- Allowed-value constraints for categorical columns
- A `schema_score` (0–100) quantifies contract compliance

**Zero-Trust Relevance:** Schema validation implements the "never trust, always verify"
principle. Even data from a known, checksummed source may have drifted in structure.
Explicit validation gates every column on explicit expectations.

---

### Stage 3 — Policy Enforcement (`ztdpf.policy_engine`)

**Purpose:** Apply zero-trust access policies to columns and rows.

**Mechanism:**
- **Sensitive column detection**: Automatic detection via column name matching
  (against a built-in dictionary of 30+ sensitive field names) and value-level
  scanning using regex patterns for SSNs, emails, phone numbers, and credit cards
- **Access decisions**: Each sensitive column receives a decision:
  - `PERMIT` — column is cleared for downstream use
  - `MASK` — column values are masked using a configured pattern
  - `DENY` — access to this column is denied; a policy violation is raised
- **Masking patterns**: `email` (local-part truncation + domain preserving),
  `last4` (reveal last 4 characters only), or a default `***MASKED***`
- **Row-level filters**: Configurable row filters using operators
  (`eq`, `ne`, `in`, `notin`, `notnull`, `isnull`) remove non-qualifying rows
- Violations are collected in `PolicyReport.violations`

**Zero-Trust Relevance:** This stage implements micro-segmentation and least-privilege
access. Every column must be explicitly permitted or masked; sensitive data is never
passed through unchecked.

---

### Stage 4 — Trust Scoring (`ztdpf.trust_score`)

**Purpose:** Compute a quantitative trust score for the processed dataset.

**Mechanism:**

The overall trust score is a weighted sum of three dimensions:

```
overall_trust = schema_trust × schema_weight
              + policy_trust × policy_weight
              + integrity_trust × integrity_weight
```

Default weights (configurable):
- Schema weight:    0.35
- Policy weight:    0.40
- Integrity weight: 0.25

**Schema trust** = `schema_score` from Stage 2 (0–100)

**Policy trust** = 100 if compliant; else max(0, 100 – violations × 25)

**Integrity trust** = composite of:
- Completeness: penalises null cells (up to 200% penalty rate)
- Uniqueness: penalises duplicate rows (up to 200% penalty rate)
- Weighted 60/40 in favour of completeness

**Trust levels:**
| Score    | Level    |
|----------|----------|
| ≥ 90     | HIGH     |
| 75–89    | MEDIUM   |
| 60–74    | LOW      |
| < 60     | CRITICAL |

**Zero-Trust Relevance:** Continuous verification is implemented by computing trust
at every run, not assuming it from prior runs. The trust score gates pipeline
acceptance through `min_trust_score`.

---

### Stage 5 — Lineage Tracking (`ztdpf.lineage_tracker`)

**Purpose:** Create an immutable record linking the source schema to the output schema
with all policies that were applied.

**Mechanism:**
- Source columns, output columns, source checksum, row counts, and all policy
  access decisions are persisted to a SQLite table
- Each lineage record has a unique `lineage_id` (UUID4)
- Records can be retrieved by `lineage_id` or queried by `run_id`

**Zero-Trust Relevance:** Lineage is the audit proof that every transformation was
authorised and recorded. It supports compliance investigations, incident response,
and continuous auditing.

---

### Stage 6 — Audit Logging & Metadata Persistence

#### Audit Logger (`ztdpf.audit_logger`)

**Purpose:** Write-once event log capturing one event per pipeline stage.

**Mechanism:**
- Each stage emits an `AuditEvent` with `event_id`, `run_id`, `stage`, `action`,
  `status`, `detail`, and `timestamp`
- Events are appended to a SQLite table using `INSERT` (not `INSERT OR REPLACE`)
  to preserve immutability
- At least six events are emitted per pipeline run (one per stage)

#### Metadata Store (`ztdpf.metadata_store`)

**Purpose:** Queryable catalog of all pipeline run outcomes.

**Mechanism:**
- Five tables: `pipeline_runs`, `ingestion_results`, `schema_results`,
  `policy_results`, `trust_results`
- `list_runs()` returns runs ordered most-recent-first
- All JSON-serialisable fields (lists, dicts) are stored as JSON strings

---

## Data Flow

```
 [CSV / JSON File]
        │
        ▼
 ┌──────────────────────────────────────────┐
 │ Stage 1: Ingestion                       │
 │  SHA-256 checksum + UUID run_id          │
 │  → IngestionResult + DataFrame           │
 └──────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────┐
 │ Stage 2: Schema Validation               │
 │  Required cols + dtype + null + range    │
 │  → SchemaReport (schema_score 0–100)     │
 └──────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────┐
 │ Stage 3: Policy Enforcement              │
 │  Sensitive detection + masking + filters │
 │  → PolicyReport + masked DataFrame       │
 └──────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────┐
 │ Stage 4: Trust Scoring                   │
 │  Weighted composite: schema+policy+data  │
 │  → TrustReport (trust_level, passes?)    │
 └──────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────┐
 │ Stage 5: Lineage Recording               │
 │  Source schema → policies → output schema│
 │  → LineageRecord                         │
 └──────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────┐
 │ Stage 6: Audit + Metadata Persistence    │
 │  AuditLogger: 6+ events per run          │
 │  MetadataStore: 5-table SQLite catalog   │
 └──────────────────────────────────────────┘
        │
        ▼
 PipelineRunResult
   run_id / pipeline_name / trust_score
   trust_level / status / audit_event_count
   lineage_id / warnings / errors
```

---

## Configuration

All behaviour is driven by `PipelineConfig` (Pydantic v2), loaded from YAML:

```
PipelineConfig
├── IngestionConfig    -- source_type, delimiter, encoding
├── SchemaConfig       -- required_columns, column_schemas, max_null_rate
│   └── ColumnSchema   -- name, dtype, nullable, allowed_values, min/max_value
├── PolicyConfig       -- sensitive_columns, row_filters, deny_if_sensitive_unmasked
│   ├── SensitiveColumnPolicy  -- column, action, mask_pattern
│   └── RowFilterPolicy        -- column, operator, value
├── TrustConfig        -- schema_weight, policy_weight, integrity_weight, min_trust_score
└── StorageConfig      -- metadata_db, lineage_db, audit_db
```

---

## Technology Choices

| Component       | Technology         | Rationale                                    |
|-----------------|--------------------|----------------------------------------------|
| Data processing | pandas 2.x         | Industry-standard tabular data processing    |
| Configuration   | Pydantic v2        | Runtime validation, IDE support, YAML-native |
| Configuration   | PyYAML 6.x         | Human-readable pipeline definition           |
| Persistence     | SQLite (stdlib)    | Zero-dependency, embeddable, ACID-compliant  |
| Identifiers     | uuid (stdlib)      | Collision-resistant run/event/lineage IDs    |
| Testing         | pytest 7.x         | Industry-standard Python test framework      |

---

## Security Properties

1. **Tamper evidence** — SHA-256 checksum prevents silent source substitution
2. **Sensitive data protection** — Automatic PII detection and masking
3. **Access control** — Explicit PERMIT/MASK/DENY per sensitive column
4. **Row-level security** — Configurable row filters remove non-qualifying data
5. **Immutable audit trail** — Write-once events with timestamps and run IDs
6. **Quantified trust** — Every run produces a numeric trust score for governance
7. **Full lineage** — Source-to-output mapping with cryptographic binding

---

*For the conceptual model, see `docs/zero_trust_model.md`.
For the article mapping, see `docs/article_mapping.md`.*
