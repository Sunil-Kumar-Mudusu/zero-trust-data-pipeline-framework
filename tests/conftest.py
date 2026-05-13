"""Shared fixtures for the ZTDPF test suite."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from ztdpf.config import (
    PipelineConfig,
    IngestionConfig,
    SchemaConfig,
    ColumnSchema,
    PolicyConfig,
    SensitiveColumnPolicy,
    RowFilterPolicy,
    TrustConfig,
    StorageConfig,
)
from ztdpf.ingestion import IngestionResult
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helper: minimal PipelineConfig
# ---------------------------------------------------------------------------

def make_config(
    pipeline_name: str = "test_pipeline",
    source_type: str = "csv",
    required_columns: list[str] | None = None,
    column_schemas: list[ColumnSchema] | None = None,
    sensitive_columns: list[SensitiveColumnPolicy] | None = None,
    row_filters: list[RowFilterPolicy] | None = None,
    deny_if_sensitive_unmasked: bool = True,
    min_trust_score: float = 60.0,
) -> PipelineConfig:
    return PipelineConfig(
        pipeline_name=pipeline_name,
        ingestion=IngestionConfig(source_type=source_type),
        schema=SchemaConfig(
            required_columns=required_columns or [],
            column_schemas=column_schemas or [],
        ),
        policy=PolicyConfig(
            sensitive_columns=sensitive_columns or [],
            row_filters=row_filters or [],
            deny_if_sensitive_unmasked=deny_if_sensitive_unmasked,
        ),
        trust=TrustConfig(min_trust_score=min_trust_score),
        storage=StorageConfig(
            metadata_db=":memory:",
            lineage_db=":memory:",
            audit_db=":memory:",
        ),
    )


@pytest.fixture
def basic_config() -> PipelineConfig:
    return make_config()


@pytest.fixture
def sample_csv(tmp_path: Path) -> str:
    """Write a standard 20-row CSV and return its path."""
    csv_content = (
        "transaction_id,customer_name,email,age,amount,currency,status,account_number\n"
        "TXN-001,Alice Johnson,alice@example.com,34,250.00,USD,completed,ACC-88421\n"
        "TXN-002,Bob Martinez,bob@techcorp.io,28,1050.75,EUR,completed,ACC-33017\n"
        "TXN-003,Carol White,carol@webmail.net,45,89.99,GBP,completed,ACC-55234\n"
        "TXN-004,David Lee,david@example.com,52,3200.00,USD,completed,ACC-72109\n"
        "TXN-005,Eva Chen,eva@startup.io,31,175.50,EUR,failed,ACC-61845\n"
        "TXN-006,Frank Brown,frank@mailbox.org,67,420.00,GBP,completed,ACC-94312\n"
        "TXN-007,Grace Kim,grace@example.com,23,99.00,USD,completed,ACC-11789\n"
        "TXN-008,Henry Davis,henry@enterprise.net,41,560.25,EUR,completed,ACC-28654\n"
        "TXN-009,Irene Lopez,irene@webmail.net,38,1800.00,GBP,completed,ACC-47001\n"
        "TXN-010,James Wilson,james@example.com,,325.00,USD,completed,ACC-83567\n"
        "TXN-011,Karen Hall,karen@techcorp.io,55,640.80,EUR,completed,ACC-19234\n"
        "TXN-012,Liam Scott,liam@startup.io,29,215.00,GBP,completed,ACC-36781\n"
        "TXN-013,Mia Adams,mia@example.com,44,4750.00,USD,completed,ACC-52098\n"
        "TXN-014,Noah Baker,noah@mailbox.org,36,88.40,EUR,completed,ACC-74563\n"
        "TXN-015,Olivia Turner,olivia@webmail.net,60,1100.00,GBP,failed,ACC-90127\n"
        "TXN-016,Peter Harris,peter@enterprise.net,47,780.60,USD,completed,ACC-23890\n"
        "TXN-017,Quinn Foster,quinn@example.com,33,390.00,EUR,completed,ACC-41256\n"
        "TXN-018,Rachel Young,rachel@techcorp.io,26,155.75,GBP,completed,ACC-68034\n"
        "TXN-019,Samuel Clark,samuel@startup.io,58,2900.00,USD,completed,ACC-15672\n"
        "TXN-020,Tina Lewis,tina@example.com,39,475.20,EUR,completed,ACC-87345\n"
    )
    p = tmp_path / "sample_input.csv"
    p.write_text(csv_content, encoding="utf-8")
    return str(p)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Return a small, clean DataFrame without sensitive columns."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Carol", "David", "Eva"],
            "amount": [100.0, 200.0, 300.0, 400.0, 500.0],
            "currency": ["USD", "EUR", "GBP", "USD", "EUR"],
            "status": ["completed", "completed", "completed", "completed", "completed"],
        }
    )


@pytest.fixture
def sensitive_df() -> pd.DataFrame:
    """Return a DataFrame containing sensitive columns."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "email": [
                "user1@example.com",
                "user2@domain.org",
                "user3@mail.net",
            ],
            "account_number": ["ACC-12345", "ACC-67890", "ACC-11111"],
            "amount": [100.0, 200.0, 300.0],
        }
    )


@pytest.fixture
def mock_ingestion_result() -> IngestionResult:
    return IngestionResult(
        run_id="test-run-id-0000",
        source_name="test_source",
        source_path="/tmp/test_source.csv",
        row_count=20,
        column_count=8,
        columns=["transaction_id", "customer_name", "email", "age",
                 "amount", "currency", "status", "account_number"],
        checksum="abc123" * 10 + "abcd",
        ingested_at=datetime.now(timezone.utc),
        inferred_dtypes={
            "transaction_id": "object",
            "customer_name": "object",
            "email": "object",
            "age": "float64",
            "amount": "float64",
            "currency": "object",
            "status": "object",
            "account_number": "object",
        },
        warnings=[],
    )
