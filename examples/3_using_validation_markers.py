#!/usr/bin/env python3
"""
Example 3: Using validation markers in your code

Demonstrates how to mark SQL queries for validation.
Only queries with markers will be validated against Prisma schema.
"""


def example_prisma_database():
    """
    Queries that go to the Prisma-managed PostgreSQL database
    should be marked with # prisma-validate
    """

    # prisma-validate
    cursor.execute("SELECT id, status FROM jobs WHERE id = %s", (job_id,))

    # prisma-validate
    query = """
        UPDATE jobs
        SET status = %s, progress = %s
        WHERE id = %s
    """
    cursor.execute(query, ('completed', 100, job_id))


def example_other_database():
    """
    Queries to other databases (BigQuery, analytics DB, etc.)
    should NOT be marked - they won't be validated
    """

    # This query goes to BigQuery - not validated
    bigquery_client.query("""
        SELECT product_id, SUM(quantity)
        FROM analytics.sales
        WHERE date >= '2024-01-01'
        GROUP BY product_id
    """)

    # This query goes to a third-party API - not validated
    analytics_db.execute("SELECT * FROM external_table")


def example_validation_alias():
    """
    You can also use # validate-sql as an alias
    """

    # validate-sql
    cursor.execute("INSERT INTO jobs (status) VALUES (%s)", ('pending',))


def example_invalid_query():
    """
    This demonstrates what happens when validation fails
    """

    # prisma-validate
    # This will FAIL validation - table name is wrong!
    cursor.execute("SELECT id FROM apply_jobs WHERE id = %s", (job_id,))
    #                               ^^^^^^^^^^
    #                               Should be "jobs"


def example_no_marker():
    """
    Without a marker, the query is not validated.
    Useful for queries to non-Prisma databases.
    """

    # No marker - this query won't be validated even though it's invalid
    cursor.execute("SELECT * FROM fake_table WHERE id = %s", (1,))


# Benefits of opt-in validation:
#
# ✅ Only validates queries to Prisma-managed database
# ✅ Ignores queries to BigQuery, analytics DBs, etc.
# ✅ Explicit - you control what gets validated
# ✅ Safe - won't break queries to other systems
# ✅ Fast - only validates marked queries
#
# When to use markers:
# - ✓ Queries using cursor.execute() to PostgreSQL (Prisma DB)
# - ✓ Raw SQL that interacts with Prisma models
# - ✗ BigQuery queries
# - ✗ Analytics database queries
# - ✗ Third-party API queries
# - ✗ DuckDB/local queries


if __name__ == "__main__":
    print("=" * 70)
    print("VALIDATION MARKER EXAMPLES")
    print("=" * 70)
    print()
    print("This file shows how to use validation markers:")
    print()
    print("  # prisma-validate")
    print("  cursor.execute('SELECT id FROM jobs WHERE id = %s')")
    print()
    print("Markers can be used with:")
    print("  - Single-line queries: cursor.execute('SELECT ...')")
    print("  - Multi-line queries in triple quotes")
    print("  - Any SQL that goes to the Prisma-managed PostgreSQL database")
    print()
    print("=" * 70)
