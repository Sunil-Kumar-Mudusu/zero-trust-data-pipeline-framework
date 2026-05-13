# Zero-Trust Model for Data Pipelines

## What Is Zero-Trust?

Zero-trust is a security model built on the principle that no entity — user, device,
service, or data — should be inherently trusted. Trust must be explicitly granted and
continuously re-verified at every point of access.

Originally developed for network security, zero-trust is equally applicable to data
engineering. In data pipelines, the untrusted entity is not a user or a device but
the data itself: every record, column, and row must earn its right to proceed through
the pipeline.

---

## The Five Zero-Trust Principles Applied to Data

### 1. Never Trust, Always Verify

**In network security:** No network segment is implicitly trusted. Every connection
is verified regardless of origin.

**In data pipelines:** No data file is implicitly trusted regardless of its declared
source. The `ingestion` stage computes a SHA-256 checksum over raw bytes before
parsing, binding the run identity to a specific version of the source. Schema
validation then independently verifies column presence, dtypes, and constraints
without assuming the source system is trustworthy.

**Framework implementation:**
- `IngestionResult.checksum` — cryptographic binding to source content
- `validate_schema()` — independent, explicit contract verification

---

### 2. Least Privilege

**In network security:** Users and services are granted only the minimum access
needed to perform their function.

**In data pipelines:** Each downstream stage receives only the data it needs, with
sensitive fields either masked or removed. The `PERMIT/MASK/DENY` access decision
system ensures no sensitive column passes to the output without explicit clearance.
Row-level filters further restrict the data surface to only qualifying records.

**Framework implementation:**
- `PolicyConfig.sensitive_columns` — per-column access decisions
- `AccessDecision.decision` — PERMIT / MASK / DENY
- `RowFilterPolicy` — row-level data reduction

---

### 3. Assume Breach

**In network security:** Design systems as though a breach has already occurred.
Lateral movement must be contained.

**In data pipelines:** Assume any incoming dataset may contain embedded sensitive
data (PII, financial identifiers, health records) even if not expected. Automatic
sensitive-data detection scans both column names and column values before any
downstream processing occurs.

**Framework implementation:**
- `_detect_sensitive_columns()` — dual-layer: name dict + value regex scan
- `deny_if_sensitive_unmasked` — default-deny posture for unrecognised sensitive columns
- Built-in detection for: SSN, email, phone, credit card, salary, medical records,
  account numbers, passwords, IP addresses, and more

---

### 4. Continuous Verification

**In network security:** Trust is not a one-time grant. Sessions are re-verified
continuously.

**In data pipelines:** Trust is not granted at ingestion and assumed to persist.
Every pipeline run computes a fresh `TrustReport` from three independent dimensions:
schema integrity, policy compliance, and data integrity. A dataset that passed
yesterday may fail today if its structure or content has drifted.

The `min_trust_score` threshold provides an automated continuous verification gate:
every run must earn a sufficient trust score to proceed.

**Framework implementation:**
- `calculate_trust()` — per-run weighted trust computation
- `TrustReport.passes_threshold` — automated governance gate
- `TrustReport.trust_level` — HIGH / MEDIUM / LOW / CRITICAL classification

---

### 5. Micro-Segmentation

**In network security:** Networks are divided into small segments so that a
compromised segment cannot access others.

**In data pipelines:** Data is segmented at the column level. Each column is
independently evaluated and assigned an access decision. Sensitive columns are
isolated from the output through masking or denial. Row-level filters provide an
additional dimension of segmentation, ensuring that only qualifying subsets of
data proceed downstream.

**Framework implementation:**
- `AccessDecision` — per-column isolation and decision
- `_mask_value()` — in-place column transformation at cell level
- `RowFilterPolicy` — row-level segmentation

---

## Trust Score Dimensions

The framework quantifies zero-trust compliance through three measurable dimensions:

```
┌─────────────────────────────────────────────────────────┐
│                  TRUST SCORE (0–100)                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Schema Trust (35%)                                     │
│  ├── Required column presence                           │
│  ├── Per-column dtype compliance                        │
│  ├── Null-rate within threshold                         │
│  ├── Value range adherence                              │
│  └── Allowed-value compliance                           │
│                                                         │
│  Policy Trust (40%)                                     │
│  ├── Sensitive column detection completeness            │
│  ├── Access decision enforcement                        │
│  └── Policy violation count (−25 per violation)        │
│                                                         │
│  Data Integrity Trust (25%)                             │
│  ├── Completeness (null-cell rate)                      │
│  └── Uniqueness (duplicate-row rate)                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Trust Levels

| Score Range | Trust Level | Interpretation                                      |
|-------------|-------------|-----------------------------------------------------|
| 90–100      | HIGH        | Dataset meets all quality and policy standards      |
| 75–89       | MEDIUM      | Minor issues; acceptable with documented exceptions |
| 60–74       | LOW         | Significant concerns; human review recommended      |
| 0–59        | CRITICAL    | Pipeline should be halted; immediate remediation    |

---

## Audit and Lineage as Trust Infrastructure

Zero-trust is not only about blocking bad data — it is equally about proving that
good data was handled correctly. The framework implements this through:

**Immutable audit trail:** Every stage emits a write-once `AuditEvent` recording
what was done, when, and with what outcome. This supports compliance review,
incident investigation, and regulatory audit.

**Lineage records:** Every pipeline run produces a `LineageRecord` that maps the
source schema (with its SHA-256 checksum) through all applied policies to the output
schema. This provides cryptographically verifiable provenance.

**Metadata catalog:** All run outcomes are queryable through the `MetadataStore`,
enabling trend analysis, trust-score governance reporting, and SLA monitoring.

---

## Summary

The zero-trust data pipeline model treats security and quality not as checkpoint
gates but as continuous, quantified properties. By applying never-trust, least-
privilege, assume-breach, continuous-verification, and micro-segmentation at every
stage of the data lifecycle, the framework ensures that every record that reaches a
downstream AI system or analytics layer has earned its presence there.
