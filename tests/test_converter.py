"""Tests for DMMF to SQLGlot schema conversion."""

import json
from pathlib import Path
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prisma_validate.converter import (
    load_dmmf,
    convert_dmmf_to_sqlglot,
    prisma_type_to_sql,
)


def test_load_dmmf():
    """Test loading DMMF from JSON file."""
    dmmf_path = Path(__file__).parent / "fixtures/sample.dmmf.json"
    dmmf = load_dmmf(dmmf_path)

    assert "datamodel" in dmmf
    assert "models" in dmmf["datamodel"]
    assert len(dmmf["datamodel"]["models"]) > 0


def test_prisma_type_to_sql():
    """Test Prisma type to SQL type conversion."""
    assert prisma_type_to_sql("String") == "TEXT"
    assert prisma_type_to_sql("Int") == "INTEGER"
    assert prisma_type_to_sql("BigInt") == "BIGINT"
    assert prisma_type_to_sql("Float") == "DOUBLE PRECISION"
    assert prisma_type_to_sql("Boolean") == "BOOLEAN"
    assert prisma_type_to_sql("DateTime") == "TIMESTAMP"
    assert prisma_type_to_sql("Json") == "JSONB"
    assert prisma_type_to_sql("Unknown") == "TEXT"  # Default fallback


def test_convert_dmmf_to_sqlglot():
    """Test DMMF to SQLGlot schema conversion."""
    dmmf_path = Path(__file__).parent / "fixtures/sample.dmmf.json"
    dmmf = load_dmmf(dmmf_path)
    schema = convert_dmmf_to_sqlglot(dmmf)

    # Should have 'jobs' table (from @@map directive)
    assert "jobs" in schema
    assert isinstance(schema["jobs"], dict)

    # Check key columns exist with correct types
    job_table = schema["jobs"]
    assert job_table["id"] == "INTEGER"
    assert job_table["job_type"] == "TEXT"  # Mapped from jobType
    assert job_table["status"] == "TEXT"
    assert job_table["progress"] == "INTEGER"
    assert job_table["errors"] == "JSONB"
    assert job_table["created_at"] == "TIMESTAMP"
    assert job_table["diff_gcs_path"] == "TEXT"


def test_field_mapping():
    """Test that @map directives are respected."""
    dmmf_path = Path(__file__).parent / "fixtures/sample.dmmf.json"
    dmmf = load_dmmf(dmmf_path)
    schema = convert_dmmf_to_sqlglot(dmmf)

    job_table = schema["jobs"]

    # These should use the mapped database column names, not Prisma field names
    assert "job_type" in job_table  # Not "jobType"
    assert "session_id" in job_table  # Not "sessionId"
    assert "chat_session_id" in job_table  # Not "chatSessionId"
    assert "batch_job_name" in job_table  # Not "batchJobName"
    assert "current_step" in job_table  # Not "currentStep"
    assert "created_at" in job_table  # Not "createdAt"
    assert "completed_at" in job_table  # Not "completedAt"
    assert "total_changes" in job_table  # Not "totalChanges"
    assert "applied_changes" in job_table  # Not "appliedChanges"
    assert "diff_gcs_path" in job_table  # Not "diffGcsPath"
    assert "total_tasks" in job_table  # Not "totalTasks"
    assert "completed_tasks" in job_table  # Not "completedTasks"
