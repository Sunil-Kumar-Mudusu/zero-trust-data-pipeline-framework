"""Tests for ztdpf.ingestion."""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

import pandas as pd
import pytest

from ztdpf.config import PipelineConfig, IngestionConfig, StorageConfig
from ztdpf.exceptions import IngestionError
from ztdpf.ingestion import ingest, IngestionResult
from tests.conftest import make_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _csv_config(source_type: str = "csv") -> PipelineConfig:
    return make_config(source_type=source_type)


def _write_csv(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestIngestBasics:
    def test_returns_tuple(self, sample_csv, basic_config):
        result = ingest(sample_csv, basic_config)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_result_is_ingestion_result(self, sample_csv, basic_config):
        ir, df = ingest(sample_csv, basic_config)
        assert isinstance(ir, IngestionResult)

    def test_dataframe_returned(self, sample_csv, basic_config):
        ir, df = ingest(sample_csv, basic_config)
        assert isinstance(df, pd.DataFrame)

    def test_run_id_is_valid_uuid(self, sample_csv, basic_config):
        ir, _ = ingest(sample_csv, basic_config)
        parsed = uuid.UUID(ir.run_id)
        assert str(parsed) == ir.run_id

    def test_checksum_is_64_char_hex(self, sample_csv, basic_config):
        ir, _ = ingest(sample_csv, basic_config)
        assert len(ir.checksum) == 64
        assert all(c in "0123456789abcdef" for c in ir.checksum)

    def test_checksum_is_deterministic(self, sample_csv, basic_config):
        ir1, _ = ingest(sample_csv, basic_config)
        ir2, _ = ingest(sample_csv, basic_config)
        assert ir1.checksum == ir2.checksum

    def test_checksum_matches_sha256(self, sample_csv, basic_config):
        expected = hashlib.sha256(Path(sample_csv).read_bytes()).hexdigest()
        ir, _ = ingest(sample_csv, basic_config)
        assert ir.checksum == expected

    def test_row_count_correct(self, sample_csv, basic_config):
        ir, df = ingest(sample_csv, basic_config)
        assert ir.row_count == len(df)
        assert ir.row_count == 20

    def test_column_count_correct(self, sample_csv, basic_config):
        ir, df = ingest(sample_csv, basic_config)
        assert ir.column_count == len(df.columns)
        assert ir.column_count == 8

    def test_columns_list_correct(self, sample_csv, basic_config):
        ir, df = ingest(sample_csv, basic_config)
        assert ir.columns == list(df.columns)

    def test_source_name_is_stem(self, sample_csv, basic_config):
        ir, _ = ingest(sample_csv, basic_config)
        assert ir.source_name == "sample_input"

    def test_inferred_dtypes_populated(self, sample_csv, basic_config):
        ir, df = ingest(sample_csv, basic_config)
        assert len(ir.inferred_dtypes) == len(df.columns)
        for col in df.columns:
            assert col in ir.inferred_dtypes

    def test_null_warning_issued(self, sample_csv, basic_config):
        # sample_csv has null age in row 10
        ir, _ = ingest(sample_csv, basic_config)
        assert len(ir.warnings) >= 1
        assert any("age" in w for w in ir.warnings)

    def test_no_warnings_for_clean_data(self, tmp_path, basic_config):
        p = tmp_path / "clean.csv"
        p.write_text("id,name\n1,Alice\n2,Bob\n", encoding="utf-8")
        ir, _ = ingest(str(p), basic_config)
        assert ir.warnings == []


class TestIngestErrors:
    def test_missing_file_raises_ingestion_error(self, basic_config):
        with pytest.raises(IngestionError, match="not found"):
            ingest("/nonexistent/path/data.csv", basic_config)

    def test_empty_file_raises_ingestion_error(self, tmp_path, basic_config):
        p = tmp_path / "empty.csv"
        p.write_bytes(b"")
        with pytest.raises(IngestionError):
            ingest(str(p), basic_config)

    def test_whitespace_only_file_raises(self, tmp_path, basic_config):
        p = tmp_path / "blank.csv"
        p.write_text("   \n  \n", encoding="utf-8")
        with pytest.raises(IngestionError):
            ingest(str(p), basic_config)

    def test_unsupported_source_type_raises(self, sample_csv):
        cfg = make_config(source_type="parquet")
        with pytest.raises(IngestionError, match="Unsupported"):
            ingest(sample_csv, cfg)

    def test_header_only_csv_raises(self, tmp_path, basic_config):
        p = tmp_path / "header_only.csv"
        p.write_text("col_a,col_b\n", encoding="utf-8")
        with pytest.raises(IngestionError, match="no data rows"):
            ingest(str(p), basic_config)


class TestIngestJsonSource:
    def test_json_source_works(self, tmp_path):
        data = [
            {"id": 1, "name": "Alice", "amount": 100.0},
            {"id": 2, "name": "Bob", "amount": 200.0},
        ]
        p = tmp_path / "data.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cfg = make_config(source_type="json")
        ir, df = ingest(str(p), cfg)
        assert ir.row_count == 2
        assert set(df.columns) == {"id", "name", "amount"}

    def test_jsonl_source_works(self, tmp_path):
        p = tmp_path / "data.jsonl"
        p.write_text(
            '{"id": 1, "val": 10}\n{"id": 2, "val": 20}\n',
            encoding="utf-8",
        )
        cfg = make_config(source_type="jsonl")
        ir, df = ingest(str(p), cfg)
        assert ir.row_count == 2

    def test_run_ids_are_unique(self, sample_csv, basic_config):
        ir1, _ = ingest(sample_csv, basic_config)
        ir2, _ = ingest(sample_csv, basic_config)
        assert ir1.run_id != ir2.run_id
