"""Tests for automatic SQL dialect detection from Prisma schema."""

from pathlib import Path
import pytest
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prisma_validate import detect_dialect_from_schema


def test_detect_postgresql():
    """Test detection of PostgreSQL provider."""
    schema_content = """
    datasource db {
      provider = "postgresql"
      url      = env("DATABASE_URL")
    }

    model User {
      id Int @id
    }
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.prisma', delete=False) as f:
        f.write(schema_content)
        temp_path = f.name

    try:
        dialect = detect_dialect_from_schema(temp_path)
        assert dialect == "postgres"
    finally:
        Path(temp_path).unlink()


def test_detect_mysql():
    """Test detection of MySQL provider."""
    schema_content = """
    datasource db {
      provider = "mysql"
      url      = env("DATABASE_URL")
    }
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.prisma', delete=False) as f:
        f.write(schema_content)
        temp_path = f.name

    try:
        dialect = detect_dialect_from_schema(temp_path)
        assert dialect == "mysql"
    finally:
        Path(temp_path).unlink()


def test_detect_sqlite():
    """Test detection of SQLite provider."""
    schema_content = """
    datasource db {
      provider = "sqlite"
      url      = "file:./dev.db"
    }
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.prisma', delete=False) as f:
        f.write(schema_content)
        temp_path = f.name

    try:
        dialect = detect_dialect_from_schema(temp_path)
        assert dialect == "sqlite"
    finally:
        Path(temp_path).unlink()


def test_detect_sqlserver():
    """Test detection of SQL Server provider."""
    schema_content = """
    datasource db {
      provider = "sqlserver"
      url      = env("DATABASE_URL")
    }
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.prisma', delete=False) as f:
        f.write(schema_content)
        temp_path = f.name

    try:
        dialect = detect_dialect_from_schema(temp_path)
        assert dialect == "tsql"
    finally:
        Path(temp_path).unlink()


def test_detect_cockroachdb():
    """Test detection of CockroachDB provider (uses postgres dialect)."""
    schema_content = """
    datasource db {
      provider = "cockroachdb"
      url      = env("DATABASE_URL")
    }
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.prisma', delete=False) as f:
        f.write(schema_content)
        temp_path = f.name

    try:
        dialect = detect_dialect_from_schema(temp_path)
        assert dialect == "postgres"  # CockroachDB uses PostgreSQL dialect
    finally:
        Path(temp_path).unlink()


def test_provider_without_quotes():
    """Test detection when provider is specified without quotes."""
    schema_content = """
    datasource db {
      provider = mysql
      url      = env("DATABASE_URL")
    }
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.prisma', delete=False) as f:
        f.write(schema_content)
        temp_path = f.name

    try:
        dialect = detect_dialect_from_schema(temp_path)
        assert dialect == "mysql"
    finally:
        Path(temp_path).unlink()


def test_default_to_postgres_on_error():
    """Test that it defaults to postgres when file not found."""
    dialect = detect_dialect_from_schema("/nonexistent/path/schema.prisma")
    assert dialect == "postgres"


def test_default_to_postgres_unknown_provider():
    """Test that unknown providers default to postgres."""
    schema_content = """
    datasource db {
      provider = "unknowndb"
      url      = env("DATABASE_URL")
    }
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.prisma', delete=False) as f:
        f.write(schema_content)
        temp_path = f.name

    try:
        dialect = detect_dialect_from_schema(temp_path)
        assert dialect == "postgres"  # Defaults to postgres
    finally:
        Path(temp_path).unlink()


def test_multiline_datasource():
    """Test detection with multiline datasource block."""
    schema_content = """
    generator client {
      provider = "prisma-client-js"
    }

    datasource db {
      provider     = "postgresql"
      url          = env("DATABASE_URL")
      shadowDatabaseUrl = env("SHADOW_DATABASE_URL")
    }

    model User {
      id   Int    @id
      name String
    }
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.prisma', delete=False) as f:
        f.write(schema_content)
        temp_path = f.name

    try:
        dialect = detect_dialect_from_schema(temp_path)
        assert dialect == "postgres"
    finally:
        Path(temp_path).unlink()
