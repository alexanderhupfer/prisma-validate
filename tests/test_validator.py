"""Tests for SQL query validation."""

from pathlib import Path
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prisma_validate import (
    load_dmmf,
    convert_dmmf_to_sqlglot,
    validate_query,
    ValidationError,
)
from prisma_validate.validator import validate_query_strict


@pytest.fixture
def schema():
    """Load schema from test fixtures."""
    dmmf_path = Path(__file__).parent / "fixtures/sample.dmmf.json"
    dmmf = load_dmmf(dmmf_path)
    return convert_dmmf_to_sqlglot(dmmf)


def test_valid_query_simple(schema):
    """Test validation of simple valid query."""
    query = "SELECT id FROM jobs WHERE id = %s"
    errors = validate_query(query, schema)
    assert len(errors) == 0


def test_valid_query_multiple_columns(schema):
    """Test validation with multiple columns."""
    query = "SELECT id, status, progress FROM jobs WHERE status = %s"
    errors = validate_query(query, schema)
    assert len(errors) == 0


def test_valid_query_with_join(schema):
    """Test self-join query."""
    query = "SELECT j1.id FROM jobs j1 JOIN jobs j2 ON j1.id = j2.id"
    errors = validate_query(query, schema)
    assert len(errors) == 0


def test_invalid_table_name(schema):
    """Test that invalid table names are caught."""
    query = "SELECT id FROM apply_jobs WHERE id = %s"
    errors = validate_query(query, schema)

    assert len(errors) > 0
    # Should mention the table not being found
    assert any("apply_jobs" in err.lower() or "not found" in err.lower() for err in errors)


def test_invalid_column_name(schema):
    """Test that invalid column names are caught."""
    query = "SELECT invalid_column FROM jobs WHERE id = %s"
    errors = validate_query(query, schema)

    assert len(errors) > 0


def test_update_query_valid(schema):
    """Test UPDATE query validation."""
    query = "UPDATE jobs SET status = %s, progress = %s WHERE id = %s"
    errors = validate_query(query, schema)
    assert len(errors) == 0


def test_update_query_invalid_table(schema):
    """Test UPDATE with invalid table."""
    query = "UPDATE apply_jobs SET status = %s WHERE id = %s"
    errors = validate_query(query, schema)
    assert len(errors) > 0


def test_insert_query_valid(schema):
    """Test INSERT query validation."""
    query = "INSERT INTO jobs (job_type, status, progress) VALUES (%s, %s, %s)"
    errors = validate_query(query, schema)
    assert len(errors) == 0


def test_delete_query_valid(schema):
    """Test DELETE query validation."""
    query = "DELETE FROM jobs WHERE id = %s"
    errors = validate_query(query, schema)
    assert len(errors) == 0


def test_validate_query_strict_raises_on_error(schema):
    """Test that strict validation raises exception."""
    query = "SELECT id FROM fake_table WHERE id = %s"

    with pytest.raises(ValidationError) as exc_info:
        validate_query_strict(query, schema)

    assert "validation failed" in str(exc_info.value).lower()


def test_validate_query_strict_passes_on_valid(schema):
    """Test that strict validation passes for valid query."""
    query = "SELECT id FROM jobs WHERE id = %s"

    # Should not raise
    validate_query_strict(query, schema)


def test_catches_apply_jobs_bug(schema):
    """
    Test that the actual bug we fixed would have been caught.

    The bug: backend Python code used 'apply_jobs' table name,
    but Prisma schema defined it as 'jobs' (via @@map("jobs"))
    """
    # This was the buggy query from apply_changes_to_shopify.py:152
    buggy_query = "SELECT diff_gcs_path FROM apply_jobs WHERE id = %s"
    errors = validate_query(buggy_query, schema)

    # Should detect that 'apply_jobs' doesn't exist
    assert len(errors) > 0
    assert any("apply_jobs" in err.lower() for err in errors)

    # The correct query should pass (using 'jobs' not 'apply_jobs')
    correct_query = "SELECT diff_gcs_path FROM jobs WHERE id = %s"
    errors = validate_query(correct_query, schema)
    assert len(errors) == 0


def test_mixed_quoting_auto_fix(schema):
    """
    Test that mixed quoted/unquoted identifiers are auto-fixed.

    PostgreSQL case rules:
    - Unquoted identifiers are lowercased (email -> email)
    - Quoted identifiers preserve case ("firstName" -> firstName)

    Before auto-fix: SQLGlot validation would fail with mixed quoting
    After auto-fix: All identifiers are quoted consistently
    """
    # Query with mixed quoting (like email_utils.py:80)
    mixed_query = """
        SELECT shop, "firstName", "lastName"
        FROM "Session"
        WHERE shop = %s
          AND "isOnline" = true
    """
    errors = validate_query(mixed_query, schema)

    # Should pass due to auto-fix (quotes all identifiers)
    assert len(errors) == 0


def test_all_quoted_identifiers(schema):
    """Test that queries with all quoted identifiers work correctly."""
    query = """
        SELECT "shop", "firstName", "lastName"
        FROM "Session"
        WHERE "shop" = %s
    """
    errors = validate_query(query, schema)
    assert len(errors) == 0


def test_all_unquoted_identifiers(schema):
    """Test that queries with all unquoted identifiers work correctly."""
    # Note: Lowercase columns like 'id', 'shop', 'state' work unquoted
    query = """
        SELECT id, shop, state
        FROM "Session"
        WHERE shop = %s
    """
    errors = validate_query(query, schema)
    assert len(errors) == 0


def test_mixed_quoting_in_where_clause(schema):
    """Test mixed quoting in WHERE clause with complex conditions."""
    query = """
        SELECT "firstName"
        FROM "Session"
        WHERE shop = %s
          AND "isOnline" = true
          AND "firstName" IS NOT NULL
    """
    errors = validate_query(query, schema)
    assert len(errors) == 0


def test_mixed_quoting_in_order_by(schema):
    """Test mixed quoting in ORDER BY clause."""
    query = """
        SELECT shop, "firstName"
        FROM "Session"
        WHERE shop = %s
        ORDER BY "firstName", shop
    """
    errors = validate_query(query, schema)
    assert len(errors) == 0


def test_mixed_quoting_with_joins(schema):
    """Test mixed quoting in JOIN conditions."""
    query = """
        SELECT s1.shop, s1."firstName", s2."lastName"
        FROM "Session" s1
        JOIN "Session" s2 ON s1.shop = s2.shop
        WHERE s1."isOnline" = true
    """
    errors = validate_query(query, schema)
    assert len(errors) == 0
