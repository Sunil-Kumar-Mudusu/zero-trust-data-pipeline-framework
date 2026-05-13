"""Pipeline configuration models using Pydantic v2."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    """Per-column schema constraints."""

    name: str
    dtype: str  # "string" | "integer" | "float" | "date" | "boolean"
    nullable: bool = True
    allowed_values: Optional[list] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class SchemaConfig(BaseModel):
    """Schema validation configuration."""

    required_columns: list[str] = []
    column_schemas: list[ColumnSchema] = []
    max_null_rate: float = 0.2


class SensitiveColumnPolicy(BaseModel):
    """Policy for a single sensitive column."""

    column: str
    action: str  # "mask" | "block" | "allow"
    mask_pattern: Optional[str] = None  # e.g. "email", "last4"


class RowFilterPolicy(BaseModel):
    """Row-level filter policy."""

    column: str
    operator: str  # "eq" | "ne" | "in" | "notin" | "notnull" | "isnull"
    value: object = None


class PolicyConfig(BaseModel):
    """Zero-trust policy configuration."""

    sensitive_columns: list[SensitiveColumnPolicy] = []
    row_filters: list[RowFilterPolicy] = []
    deny_if_sensitive_unmasked: bool = True
    sensitive_patterns: list[str] = []  # regex patterns for auto-detection


class TrustConfig(BaseModel):
    """Trust score weighting and threshold configuration."""

    schema_weight: float = 0.35
    policy_weight: float = 0.40
    integrity_weight: float = 0.25
    min_trust_score: float = 60.0


class IngestionConfig(BaseModel):
    """Data source ingestion configuration."""

    source_type: str = "csv"  # "csv" | "json" | "jsonl"
    delimiter: str = ","
    encoding: str = "utf-8"


class StorageConfig(BaseModel):
    """Persistence backend configuration."""

    metadata_db: str = "metadata.db"
    lineage_db: str = "lineage.db"
    audit_db: str = "audit.db"


class PipelineConfig(BaseModel):
    """Root pipeline configuration."""

    pipeline_name: str
    version: str = "1.0"
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    schema: SchemaConfig = Field(default_factory=SchemaConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    trust: TrustConfig = Field(default_factory=TrustConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
