"""Test what validation features SQLGlot supports."""

from pathlib import Path
import pytest
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prisma_validate import (
    load_dmmf,
    convert_dmmf_to_sqlglot,
    validate_query,
)


@pytest.fixture
def schema():
    """Load schema from test fixtures."""
    dmmf_path = Path(__file__).parent / "fixtures/sample.dmmf.json"
    dmmf = load_dmmf(dmmf_path)
    return convert_dmmf_to_sqlglot(dmmf)


def test_validates_table_existence(schema):
    """SQLGlot validates that referenced tables exist."""
    # Valid
    assert len(validate_query("SELECT id FROM jobs", schema)) == 0

    # Invalid - table doesn't exist
    errors = validate_query("SELECT id FROM nonexistent_table", schema)
    assert len(errors) > 0
    assert "nonexistent_table" in errors[0].lower()


def test_validates_column_existence(schema):
    """SQLGlot validates that referenced columns exist in the table."""
    # Valid
    assert len(validate_query("SELECT id, status FROM jobs", schema)) == 0

    # Invalid - column doesn't exist
    errors = validate_query("SELECT nonexistent_column FROM jobs", schema)
    assert len(errors) > 0


def test_validates_joins(schema):
    """SQLGlot validates table and column references in JOINs."""
    # Valid self-join
    query = "SELECT j1.id FROM jobs j1 JOIN jobs j2 ON j1.id = j2.id"
    assert len(validate_query(query, schema)) == 0

    # Invalid - wrong table in join
    query = "SELECT j1.id FROM jobs j1 JOIN fake_table j2 ON j1.id = j2.id"
    errors = validate_query(query, schema)
    assert len(errors) > 0


def test_validates_where_clause(schema):
    """SQLGlot validates column references in WHERE clauses."""
    # Valid
    query = "SELECT id FROM jobs WHERE status = 'pending'"
    assert len(validate_query(query, schema)) == 0

    # Invalid - column doesn't exist
    query = "SELECT id FROM jobs WHERE fake_column = 'value'"
    errors = validate_query(query, schema)
    assert len(errors) > 0


def test_validates_aggregate_functions(schema):
    """SQLGlot validates column references in aggregate functions."""
    # Valid
    query = "SELECT COUNT(id), SUM(progress) FROM jobs"
    assert len(validate_query(query, schema)) == 0

    # Invalid - column doesn't exist
    query = "SELECT COUNT(fake_column) FROM jobs"
    errors = validate_query(query, schema)
    assert len(errors) > 0


def test_validates_group_by(schema):
    """SQLGlot validates column references in GROUP BY."""
    # Valid
    query = "SELECT status, COUNT(*) FROM jobs GROUP BY status"
    assert len(validate_query(query, schema)) == 0

    # Invalid - column doesn't exist
    query = "SELECT status, COUNT(*) FROM jobs GROUP BY fake_column"
    errors = validate_query(query, schema)
    assert len(errors) > 0


def test_validates_order_by(schema):
    """SQLGlot validates column references in ORDER BY."""
    # Valid
    query = "SELECT id FROM jobs ORDER BY created_at DESC"
    assert len(validate_query(query, schema)) == 0

    # Invalid - column doesn't exist
    query = "SELECT id FROM jobs ORDER BY fake_column"
    errors = validate_query(query, schema)
    assert len(errors) > 0


def test_validates_subqueries(schema):
    """SQLGlot validates table/column references in subqueries."""
    # Valid
    query = """
        SELECT id FROM jobs
        WHERE status IN (SELECT DISTINCT status FROM jobs WHERE progress > 50)
    """
    assert len(validate_query(query, schema)) == 0

    # Invalid - wrong table in subquery
    query = "SELECT id FROM jobs WHERE status IN (SELECT status FROM fake_table)"
    errors = validate_query(query, schema)
    assert len(errors) > 0


def test_insert_table_validation(schema):
    """SQLGlot validates table names in INSERT statements."""
    # Valid
    query = "INSERT INTO jobs (status, progress) VALUES ('pending', 0)"
    assert len(validate_query(query, schema)) == 0

    # Invalid - table doesn't exist
    query = "INSERT INTO fake_table (status) VALUES ('value')"
    errors = validate_query(query, schema)
    assert len(errors) > 0


def test_update_table_validation(schema):
    """SQLGlot validates table names in UPDATE statements."""
    # Valid
    query = "UPDATE jobs SET status = 'completed', progress = 100 WHERE id = 1"
    assert len(validate_query(query, schema)) == 0

    # Invalid - table doesn't exist
    query = "UPDATE fake_table SET status = 'value' WHERE id = 1"
    errors = validate_query(query, schema)
    assert len(errors) > 0


def test_sql_syntax_validation(schema):
    """SQLGlot catches severe SQL syntax errors."""
    # Valid syntax
    assert len(validate_query("SELECT id FROM jobs", schema)) == 0

    # Invalid syntax - completely malformed
    errors = validate_query("SELECTT id FROMM jobs", schema)
    assert len(errors) > 0


def test_different_dialects(schema):
    """Test validation with different SQL dialects."""
    # PostgreSQL (default)
    query = "SELECT id FROM jobs WHERE id = %s"
    assert len(validate_query(query, schema, dialect="postgres")) == 0

    # MySQL
    query = "SELECT id FROM jobs WHERE id = ?"
    assert len(validate_query(query, schema, dialect="mysql")) == 0

    # SQLite
    assert len(validate_query(query, schema, dialect="sqlite")) == 0


def test_does_not_validate_types():
    """SQLGlot does NOT validate data types in our current setup."""
    # This is a limitation - we only validate structure, not types
    # Type validation would require more complex schema information
    pass


def test_does_not_validate_constraints():
    """SQLGlot does NOT validate constraints (NOT NULL, FOREIGN KEY, etc.)."""
    # This is a limitation - constraint validation requires runtime info
    pass
