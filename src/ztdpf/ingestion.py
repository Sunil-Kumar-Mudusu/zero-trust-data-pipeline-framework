"""Secure data ingestion with SHA-256 checksum and UUID run ID."""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import PipelineConfig
from .exceptions import IngestionError


@dataclass
class IngestionResult:
    """Immutable record produced by a single ingestion run."""

    run_id: str
    source_name: str
    source_path: str
    row_count: int
    column_count: int
    columns: list[str]
    checksum: str
    ingested_at: datetime
    inferred_dtypes: dict[str, str]
    warnings: list[str] = field(default_factory=list)


def ingest(
    source_path: str,
    config: PipelineConfig,
) -> tuple[IngestionResult, pd.DataFrame]:
    """
    Read a data source, compute its SHA-256 checksum, and return an
    IngestionResult alongside the loaded DataFrame.

    Raises:
        IngestionError: if the file is missing, empty, or cannot be parsed.
    """
    path = Path(source_path)
    if not path.exists():
        raise IngestionError(f"Source file not found: {source_path}")

    raw_bytes = path.read_bytes()
    if not raw_bytes.strip():
        raise IngestionError(f"Source file is empty: {source_path}")

    checksum = hashlib.sha256(raw_bytes).hexdigest()

    cfg = config.ingestion
    try:
        if cfg.source_type == "csv":
            df = pd.read_csv(
                source_path,
                delimiter=cfg.delimiter,
                encoding=cfg.encoding,
            )
        elif cfg.source_type == "json":
            df = pd.read_json(source_path, encoding=cfg.encoding)
        elif cfg.source_type == "jsonl":
            df = pd.read_json(source_path, lines=True, encoding=cfg.encoding)
        else:
            raise IngestionError(f"Unsupported source type: {cfg.source_type}")
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError(f"Failed to read source file: {exc}") from exc

    if df.empty:
        raise IngestionError("Source file contains no data rows.")

    warnings: list[str] = []
    null_cols = [c for c in df.columns if df[c].isnull().any()]
    if null_cols:
        warnings.append(f"Null values detected in: {', '.join(null_cols)}")

    result = IngestionResult(
        run_id=str(uuid.uuid4()),
        source_name=path.stem,
        source_path=str(path.resolve()),
        row_count=len(df),
        column_count=len(df.columns),
        columns=list(df.columns),
        checksum=checksum,
        ingested_at=datetime.now(timezone.utc),
        inferred_dtypes={c: str(df[c].dtype) for c in df.columns},
        warnings=warnings,
    )
    return result, df
