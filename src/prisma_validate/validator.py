"""
Validate SQL queries against Prisma-derived schema using SQLGlot.
"""

from typing import Dict, List
import sqlglot
from sqlglot.optimizer.qualify import qualify


class ValidationError(Exception):
    """Raised when SQL query validation fails."""

    pass


def validate_query(
    query: str, schema: Dict[str, Dict[str, str]], dialect: str = "postgres"
) -> List[str]:
    """
    Validate SQL query against schema.

    Validates:
    - Table existence
    - Column names in SELECT, WHERE, JOIN, ORDER BY, GROUP BY
    - Column references in aggregate functions and subqueries
    - Some SQL syntax errors (keyword typos, unclosed strings, missing parens)

    Limitations (by design):
    - Does NOT validate column names in INSERT column lists
    - Does NOT validate column names in UPDATE SET clauses
    - Does NOT validate data types or constraints
    - Does NOT catch all syntax errors (e.g., missing commas are often tolerated)

    This is because SQLGlot's qualify() function is designed to resolve
    and qualify column references (not validate DML column lists).
    Most critical bugs occur in complex SELECT queries anyway.

    Args:
        query: SQL query string (may contain placeholders like %s)
        schema: SQLGlot schema dict from convert_dmmf_to_sqlglot()
        dialect: SQL dialect (default: postgres)

    Returns:
        List of validation error messages (empty if valid)

    Example:
        >>> schema = {"job": {"id": "INTEGER", "status": "TEXT"}}
        >>> validate_query("SELECT id FROM job", schema)
        []
        >>> validate_query("SELECT id FROM apply_jobs", schema)
        ['Table "apply_jobs" not found']
    """
    errors = []

    try:
        # Replace parameter placeholders to avoid parse errors
        # %s → :param (named parameter style SQLGlot understands)
        normalized_query = query.replace("%s", ":param")

        # Parse the query
        ast = sqlglot.parse_one(normalized_query, dialect=dialect)

        # Extract table names from the query
        referenced_tables = set()
        for table in ast.find_all(sqlglot.exp.Table):
            table_name = table.name.lower()
            referenced_tables.add(table_name)

        # Check if all referenced tables exist in schema
        for table_name in referenced_tables:
            if table_name not in schema:
                errors.append(f'Table "{table_name}" not found in schema')

        # Only run qualify if tables exist (to validate columns)
        if not errors:
            try:
                qualify(ast, schema=schema, dialect=dialect)
            except Exception as e:
                # Extract meaningful error message
                error_msg = str(e)
                if "not found" in error_msg.lower() or "unknown" in error_msg.lower():
                    errors.append(error_msg)
                else:
                    errors.append(f"Schema validation error: {error_msg}")

    except sqlglot.errors.ParseError as e:
        errors.append(f"SQL syntax error: {e}")
    except Exception as e:
        errors.append(f"Validation error: {e}")

    return errors


def validate_query_strict(
    query: str, schema: Dict[str, Dict[str, str]], dialect: str = "postgres"
) -> None:
    """
    Validate SQL query, raising ValidationError if invalid.

    Args:
        query: SQL query string
        schema: SQLGlot schema dict
        dialect: SQL dialect

    Raises:
        ValidationError: If query is invalid

    Example:
        >>> schema = {"job": {"id": "INTEGER"}}
        >>> validate_query_strict("SELECT id FROM job", schema)  # OK
        >>> validate_query_strict("SELECT id FROM fake_table", schema)
        ValidationError: Table "fake_table" not found
    """
    errors = validate_query(query, schema, dialect)
    if errors:
        raise ValidationError(f"Query validation failed: {'; '.join(errors)}")
