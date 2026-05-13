# Policy Model

## Overview

The policy engine (`ztdpf.policy_engine`) is the enforcement layer of the zero-trust
framework. It evaluates every column in the arriving dataset against zero-trust policies
and produces a `PolicyReport` with access decisions for each sensitive column.

---

## Policy Types

### 1. Sensitive Column Policies

Sensitive column policies declare how specific columns should be handled.

**Configuration:**
```yaml
policy:
  sensitive_columns:
    - column: email
      action: mask
      mask_pattern: email
    - column: ssn
      action: deny
    - column: customer_id
      action: allow
```

**Actions:**

| Action   | Effect                                          |
|----------|-------------------------------------------------|
| `mask`   | Column values are transformed using the mask pattern |
| `deny`   | Access is denied; a policy violation is recorded |
| `allow`  | Column is explicitly permitted downstream       |
| `block`  | Alias for `deny`                                |

---

### 2. Row Filter Policies

Row filter policies remove rows that do not meet access criteria.

**Configuration:**
```yaml
policy:
  row_filters:
    - column: status
      operator: "ne"
      value: "failed"
    - column: age
      operator: "notnull"
```

**Supported Operators:**

| Operator  | Description                                  |
|-----------|----------------------------------------------|
| `eq`      | Keep rows where column equals value          |
| `ne`      | Keep rows where column does not equal value  |
| `in`      | Keep rows where column is in value list      |
| `notin`   | Keep rows where column is not in value list  |
| `notnull` | Keep rows where column is not null           |
| `isnull`  | Keep rows where column is null               |

---

## Sensitive Column Detection

The policy engine automatically detects sensitive columns through two mechanisms:

### Name-Based Detection

Columns whose names (case-insensitive) match any entry in the built-in sensitive
name dictionary are flagged. The dictionary includes:

| Category        | Column Names                                                   |
|-----------------|----------------------------------------------------------------|
| Identity        | ssn, social_security, social_security_number                  |
| Contact         | email, email_address, phone, phone_number, mobile, cell       |
| Financial       | credit_card, card_number, cvv, salary, income, wage, account_number, routing_number |
| Credentials     | password, passwd, secret, token                                |
| Health          | dob, date_of_birth, birthdate, medical_record, diagnosis, patient_id |
| Network         | ip_address, ip                                                 |

### Value-Based Detection

String columns are scanned (first 50 rows) for value patterns matching:

| Pattern      | Regex Description                          |
|--------------|--------------------------------------------|
| SSN          | `\d{3}-\d{2}-\d{4}`                       |
| Email        | Standard email address pattern             |
| Phone        | US/international phone number patterns     |
| Credit card  | 13–16 consecutive digit sequences          |

### Custom Patterns

Additional regex patterns can be supplied via `sensitive_patterns`:
```yaml
policy:
  sensitive_patterns:
    - ".*_token$"
    - ".*_secret$"
```

---

## Access Decisions

Each sensitive column that passes through the policy engine receives an `AccessDecision`:

```python
@dataclass
class AccessDecision:
    column: str
    decision: str  # "PERMIT" | "MASK" | "DENY"
    reason: str
```

Decision logic:

```
For each auto-detected sensitive column:
    if column has explicit policy:
        apply that policy's action
    elif deny_if_sensitive_unmasked is True:
        action = "mask"   ← default-deny posture
    else:
        action = "allow"
```

---

## Masking Patterns

### `email` pattern
- Format: `{first2chars}***@{domain}`
- Example: `alice@example.com` → `al***@example.com`

### `last4` pattern
- Format: `****{last4digits}`
- Example: `ACC-12345` → `****2345`

### Default (no pattern)
- Format: `***MASKED***`
- Applied when no `mask_pattern` is configured

---

## Policy Compliance

A pipeline run is considered **compliant** when:
- No `DENY` decisions were triggered
- No sensitive column passed through unmasked when `deny_if_sensitive_unmasked = True`

Non-compliance is recorded in `PolicyReport.violations` as human-readable strings.
Each violation reduces the `policy_trust` score by 25 points (floored at 0).

---

## Policy Trust Score

```
policy_trust = 100.0                         if is_compliant
             = max(0, 100 - violations × 25) if not compliant
```

| Violations | Policy Trust |
|------------|-------------|
| 0          | 100.0       |
| 1          | 75.0        |
| 2          | 50.0        |
| 3          | 25.0        |
| 4+         | 0.0         |

---

## Configuration Reference

```yaml
policy:
  sensitive_columns:          # list of SensitiveColumnPolicy
    - column: <name>          # column name
      action: mask|deny|allow # access action
      mask_pattern: email|last4|null  # optional masking pattern

  row_filters:                # list of RowFilterPolicy
    - column: <name>
      operator: eq|ne|in|notin|notnull|isnull
      value: <scalar or list>

  deny_if_sensitive_unmasked: true   # default-deny posture
  sensitive_patterns: []             # additional regex patterns
```

---

## Example PolicyReport

```python
PolicyReport(
    policies_checked=4,        # 2 sensitive_columns + 2 row_filters
    violations=[],
    sensitive_columns_detected=["email", "account_number"],
    access_decisions=[
        AccessDecision("email", "MASK", "sensitive column — masked by policy"),
        AccessDecision("account_number", "MASK", "sensitive column — masked by policy"),
    ],
    is_compliant=True,
)
```
