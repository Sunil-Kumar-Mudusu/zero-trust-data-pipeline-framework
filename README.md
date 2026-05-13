# Zero-Trust Data Pipeline Framework

A production-style reference implementation of the zero-trust data pipeline
architecture described in:

> Mudusu, S. K., & Gentyala, S. (2026). Zero-Trust Data Pipelines for AI Systems:
> A Framework for Secure, Verifiable, and Auditable Data Engineering.
> *JRTCSE — Journal of Research Trends in Computer Science and Engineering*, Vol. 14, Issue 2.
> https://jrtcse.com/index.php/home/article/view/JRTCSE.2026.14.2.2/JRTCSE.2026.14.2.2

> This framework was formalized as a GitHub reference implementation during
> March–April 2026 based on the published article.

---

## What this demonstrates

- Secure CSV/JSON ingestion with SHA-256 checksum and UUID run ID
- Schema validation with per-column dtype, null-rate, and range checks
- Zero-trust policy enforcement: sensitive column detection, row-level filters, access decisions
- Data masking for sensitive fields (PII, financial, health data)
- Immutable audit event trail (one event per pipeline stage)
- Full data lineage: source schema → policies applied → output schema
- Trust scoring (0–100) across three dimensions: schema integrity, policy compliance, data integrity
- SQLite-backed metadata catalog with full run history
- 120+ pytest tests across all eight modules

---

## Architecture overview

```
Data Source (CSV / JSON)
        |
        v
  Ingestion          -- SHA-256 checksum, UUID run ID, encoding check
        |
        v
  Schema Validator   -- column presence, dtype, null rate, range checks
        |
        v
  Policy Engine      -- sensitive column detection, access decisions, masking
        |
        v
  Trust Score        -- schema trust + policy trust + integrity trust → 0–100
        |
        v
  Lineage Tracker    -- source schema, policies applied, output schema
        |
        v
  Audit Logger  +  Metadata Store  -- SQLite-backed persistence
        |
        v
  PipelineRunResult
    trust_score / trust_level / status / run_id
```

See `docs/architecture.md` and `docs/article_mapping.md` for full details.

---

## Installation

**Requirements:** Python 3.11+

```bash
git clone https://github.com/Sunil-Kumar-Mudusu/zero-trust-data-pipeline-framework.git
cd zero-trust-data-pipeline-framework

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

---

## Quick start

```bash
python examples/sample_pipeline.py
```

---

## Example output

```
================================================================
  Zero-Trust Data Pipeline Framework - Pipeline Execution
================================================================

[1] Data Ingestion
    run_id        : <uuid>
    source        : sample_input
    rows loaded   : 20
    columns       : 8
    checksum      : <sha256>

[2] Schema Validation
    schema score  : 100.0
    missing cols  : 0
    null violations: 0
    status        : VALID

[3] Policy Enforcement
    policies checked : 4
    violations       : 0
    sensitive cols   : 2
    access decision  : PERMIT
    status           : COMPLIANT

[4] Trust Score
    schema trust   : 100.0
    policy trust   : 100.0
    integrity trust: 95.0
    overall trust  : 98.5/100
    trust level    : HIGH

[5] Lineage Recorded
    lineage_id    : <uuid>

================================================================
  PIPELINE SUMMARY
================================================================
  Run ID          : <uuid>
  Pipeline        : sample_zero_trust_pipeline
  Source          : sample_input (20 rows)
  Trust score     : 98.5/100
  Trust level     : HIGH
  Audit events    : 6
  Status          : PASS
================================================================
```

Full output in `docs/test_results.md`.

---

## Tests

```bash
pytest -q
```

**120+ tests — 0 failures** across all eight modules.

---

## Pipeline configuration

Edit `examples/zero_trust_policies.yaml` to configure:
- Source format and encoding
- Required columns and per-column schema constraints
- Zero-trust policies (sensitive columns, row filters, masking rules)
- Trust score thresholds
- SQLite database paths

---

## Verification checklist

- [ ] `SchemaReport.is_valid == True`
- [ ] `PolicyReport.is_compliant == True`
- [ ] `TrustReport.overall_trust >= 80`
- [ ] `PipelineRunResult.trust_level in ("HIGH", "MEDIUM")`
- [ ] `PipelineRunResult.audit_event_count >= 6`
- [ ] Lineage record present for the run

---

## License

MIT License - see `LICENSE`.

---

## Citation

Mudusu, S. K., & Gentyala, S. (2026). Zero-Trust Data Pipelines for AI Systems:
A Framework for Secure, Verifiable, and Auditable Data Engineering.
*JRTCSE*, Vol. 14, Issue 2.
https://jrtcse.com/index.php/home/article/view/JRTCSE.2026.14.2.2/JRTCSE.2026.14.2.2
