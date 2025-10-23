# Prisma Validate - SQL Query Validator

Validate SQL queries against your Prisma schema to catch errors before runtime.

## Problem

When using Prisma on the frontend but raw SQL queries in backend services (Python, Go, etc.), it's easy to introduce bugs:

- **Prisma Client Python is no longer maintained** (deprecated as of 2024)
- Table names get out of sync (e.g., `apply_jobs` vs `jobs`)
- Column names don't match (e.g., `jobType` vs `job_type`)
- Schema changes break SQL queries in unexpected places
- Errors only surface at runtime in production

## Why This Tool?

**Prisma Client Python is deprecated and unmaintained.** If you're using Prisma for your frontend/TypeScript and raw SQL in Python backends, you need a way to keep them in sync. This tool bridges that gap by validating your Python SQL queries against your Prisma schema at development time.

## Solution

This tool uses Prisma's official Data Model Meta Format (DMMF) to validate SQL queries against your schema at development time - no runtime dependencies, no deprecated clients.

## What Gets Validated

### ✅ Validated
- **Table names** - catches `apply_jobs` vs `jobs` mismatches
- **Column names** - catches `jobType` vs `job_type` mismatches
- **Column references in**:
  - `SELECT` clauses
  - `WHERE` conditions
  - `JOIN` conditions
  - `ORDER BY` clauses
  - `GROUP BY` clauses
  - Aggregate functions (`COUNT`, `SUM`, etc.)
  - Subqueries
- **Prisma mappings** - respects `@map` and `@@map` directives
- **SQL syntax errors** - catches some syntax errors (keyword typos, missing closing parens, unclosed strings)

### ❌ Not Validated
- **Data types** - Type mismatches (e.g., inserting string into integer column)
- **Constraints** - NOT NULL, FOREIGN KEY, UNIQUE, CHECK constraints
- **Column names in `INSERT`/`UPDATE` SET clauses** - SQLGlot's `qualify()` function doesn't validate these (by design, it only qualifies column references in SELECT/WHERE/JOIN)
- **Runtime values** - Cannot validate actual data values
- **Database-specific functions** - Custom functions, stored procedures
- **All syntax errors** - Catches major syntax errors (typos, unclosed strings) but not all (missing commas, etc.)

**Why the INSERT/UPDATE limitation is acceptable:**
- Most schema mismatch bugs occur in complex `SELECT` queries with JOINs (which ARE validated)
- `INSERT`/`UPDATE` column errors are typically caught quickly in unit/integration tests
- The tool focuses on the 80% case: catching table/column name mismatches in read queries
- You can still validate that `INSERT`/`UPDATE` reference the correct **tables**

## Supported Databases

Works with **any SQL dialect** supported by SQLGlot:

| Database | Dialect | Auto-detected from Prisma | Example |
|----------|---------|---------------------------|---------|
| **PostgreSQL** | `postgres` | ✅ Yes (default) | `datasource db { provider = "postgresql" }` |
| **MySQL** | `mysql` | ✅ Yes | `datasource db { provider = "mysql" }` |
| **SQLite** | `sqlite` | ✅ Yes | `datasource db { provider = "sqlite" }` |
| **SQL Server** | `tsql` | ✅ Yes | `datasource db { provider = "sqlserver" }` |
| **CockroachDB** | `postgres` | ✅ Yes | `datasource db { provider = "cockroachdb" }` |
| **MariaDB** | `mysql` | ✅ Yes (via MySQL) | Use `mysql` dialect |
| **BigQuery** | `bigquery` | ⚠️ Manual | Pass `dialect="bigquery"` |
| **Snowflake** | `snowflake` | ⚠️ Manual | Pass `dialect="snowflake"` |
| **Redshift** | `redshift` | ⚠️ Manual | Pass `dialect="redshift"` |

**Dialect auto-detection:** Use `detect_dialect_from_schema("prisma/schema.prisma")` to automatically detect the correct SQL dialect from your Prisma provider. See example above.

## Features

- ✅ Validates SQL queries against Prisma schema
- ✅ No runtime dependencies (development/CI only)
- ✅ No need for deprecated Prisma Client Python
- ✅ Supports all major SQL dialects
- ✅ Respects Prisma's `@map` and `@@map` directives
- ✅ Zero runtime overhead - validation happens at build time
- ✅ Based on official Prisma DMMF format
- ✅ Works with any programming language (Python, Go, Rust, etc.)

## Installation

This is a **development-time tool** for validation. **Two simple steps:**

### Step 1: Install @prisma/internals
The tool needs this to read your Prisma schema:

```bash
npm install --save-dev @prisma/internals
```

### Step 2: Add pre-commit hook
Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/alexanderhupfer/prisma-validate
    rev: v0.3.0
    hooks:
      - id: prisma-validate
```

**That's it!** The hook will auto-detect your schema location and validate marked SQL queries.

**Note:** This tool is only used during development, pre-commit hooks, and CI/CD. It has zero runtime overhead and should not be installed in production.

## Quick Start

### Using CLI

Mark SQL queries you want to validate with a SQL comment:

```python
cursor.execute("""
    -- prisma-validate
    SELECT id, status FROM jobs WHERE id = %s
""", (job_id,))
```

Or use block comments:

```python
cursor.execute("""
    /* prisma-validate */
    SELECT id, status FROM jobs WHERE id = %s
""", (job_id,))
```

Run validation:

```bash
# Auto-detects schema location
prisma-validate backend/tasks/*.py

# Or specify schema path explicitly
prisma-validate --schema-path prisma/schema.prisma backend/**/*.py
```

### Using as Python Library

You can also import and use programmatically:

```python
from prisma_validate import load_dmmf, convert_dmmf_to_sqlglot, validate_query

# Load from DMMF JSON (if you have one pre-generated)
dmmf = load_dmmf('prisma-dmmf.json')
schema = convert_dmmf_to_sqlglot(dmmf)

# Validate a query
query = "SELECT id, status FROM jobs WHERE id = %s"
errors = validate_query(query, schema)

if errors:
    print("Query validation failed:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Query is valid!")
```

### Auto-Detect SQL Dialect

The validator automatically detects the correct SQL dialect from your Prisma schema:

```python
from prisma_validate import detect_dialect_from_schema, validate_query

# Auto-detect from schema.prisma
dialect = detect_dialect_from_schema("prisma/schema.prisma")

# Use detected dialect (no need to hardcode!)
errors = validate_query(query, schema, dialect=dialect)
```

**Supported auto-detection:**
- `provider = "postgresql"` → `postgres`
- `provider = "mysql"` → `mysql`
- `provider = "sqlite"` → `sqlite`
- `provider = "sqlserver"` → `tsql`
- `provider = "cockroachdb"` → `postgres`

### Manually Specify Dialect

You can also specify dialects manually:

```python
# MySQL
errors = validate_query(query, schema, dialect="mysql")

# SQL Server
errors = validate_query(query, schema, dialect="tsql")

# BigQuery (not auto-detected)
errors = validate_query(query, schema, dialect="bigquery")
```

### Use strict mode for CI/CD

```python
from prisma_validate import validate_query_strict, ValidationError

try:
    # Raises ValidationError if invalid
    validate_query_strict(
        "SELECT id FROM apply_jobs WHERE id = %s",  # Wrong table name!
        schema
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
    exit(1)
```

## Real-World Example

This tool was built to catch an actual production bug. Here's what happened:

**Prisma Schema:**
```prisma
model Job {
  id        Int      @id @default(autoincrement())
  status    String
  progress  Int

  @@map("jobs")  // Maps to "jobs" table
}
```

**Buggy Python Code:**
```python
# This query used the wrong table name!
cursor.execute("SELECT * FROM apply_jobs WHERE id = %s", (job_id,))
# Error: relation "apply_jobs" does not exist
```

**How this tool catches it:**
```python
from prisma_validate import validate_query

schema = convert_dmmf_to_sqlglot(load_dmmf('prisma-dmmf.json'))

# Buggy query
errors = validate_query("SELECT * FROM apply_jobs WHERE id = %s", schema)
print(errors)
# ['Table "apply_jobs" not found in schema. Did you mean "jobs"?']

# Fixed query
errors = validate_query("SELECT * FROM jobs WHERE id = %s", schema)
print(errors)
# [] - Valid!
```

## Integration Options

### Pre-commit Hook (Recommended)

The easiest way is to reference the GitHub repository directly:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/alexanderhupfer/prisma-validate
    rev: v0.3.0
    hooks:
      - id: prisma-validate
        # Optional: specify schema path if not in standard location
        # args: ['--schema-path=path/to/schema.prisma']
```

Then install the hooks:

```bash
pre-commit install
```

### Custom Schema Location

If your schema is in a non-standard location:

```yaml
repos:
  - repo: https://github.com/alexanderhupfer/prisma-validate
    rev: v0.3.0
    hooks:
      - id: prisma-validate
        args: ['--schema-path=custom/path/schema.prisma']
```

### CI/CD Pipeline

```yaml
# .github/workflows/validate-sql.yml
name: Validate SQL

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install @prisma/internals
        run: npm install --save-dev @prisma/internals

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install prisma-validate
        run: pip install git+https://github.com/alexanderhupfer/prisma-validate.git@v0.3.0

      - name: Validate SQL queries
        run: prisma-validate backend/**/*.py
```

### Pytest Integration

```python
# test_sql_queries.py
import pytest
from prisma_validate import load_dmmf, convert_dmmf_to_sqlglot, validate_query_strict

@pytest.fixture(scope="module")
def schema():
    dmmf = load_dmmf('prisma-dmmf.json')
    return convert_dmmf_to_sqlglot(dmmf)

def test_job_queries(schema):
    """Test that all job-related queries are valid."""
    queries = [
        "SELECT id, status FROM jobs WHERE id = %s",
        "UPDATE jobs SET status = %s WHERE id = %s",
        "INSERT INTO jobs (status, progress) VALUES (%s, %s)",
    ]

    for query in queries:
        validate_query_strict(query, schema)  # Raises if invalid
```

## CLI Reference

### Basic Usage

```bash
# Validate specific files
prisma-validate file1.py file2.py

# Validate with glob patterns
prisma-validate backend/tasks/*.py

# Specify custom schema location
prisma-validate --schema-path prisma/schema.prisma backend/**/*.py
```

### Options

- `files`: Python files to validate (required, supports multiple files)
- `--schema-path PATH`: Path to schema.prisma (optional, auto-detects if not provided)

### Schema Auto-Detection

If `--schema-path` is not provided, searches these locations in order:
1. `./prisma/schema.prisma`
2. `./frontend/prisma/schema.prisma`
3. `./backend/prisma/schema.prisma`
4. `../prisma/schema.prisma`

### Exit Codes

- `0`: All queries valid
- `1`: Validation errors found or setup error

## API Reference

### `load_dmmf(path: str | Path) -> Dict`
Load DMMF from JSON file.

### `convert_dmmf_to_sqlglot(dmmf: Dict) -> Dict[str, Dict[str, str]]`
Convert Prisma DMMF to SQLGlot schema format.

Returns:
```python
{
    "table_name": {
        "column_name": "SQL_TYPE",
        ...
    },
    ...
}
```

### `validate_query(query: str, schema: Dict, dialect: str = "postgres") -> List[str]`
Validate SQL query against schema.

Args:
- `query`: SQL query string (may contain `%s` placeholders)
- `schema`: SQLGlot schema from `convert_dmmf_to_sqlglot()`
- `dialect`: SQL dialect (default: "postgres")

Returns: List of error messages (empty if valid)

### `validate_query_strict(query: str, schema: Dict, dialect: str = "postgres") -> None`
Validate SQL query, raising `ValidationError` if invalid.

Raises: `ValidationError` with details if query is invalid

## Supported Features

- Table validation (respects `@@map()`)
- Column validation (respects `@map()`)
- SQL dialects: PostgreSQL, MySQL, SQLite, BigQuery, etc.
- Query types: SELECT, INSERT, UPDATE, DELETE
- Joins and subqueries
- Parameter placeholders (`%s`, `:param`, `?`, etc.)

## Limitations

- Relations are not validated (only scalar fields)
- Complex computed columns may not be supported
- Database-specific functions are not validated
- Views and materialized views are not supported yet

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run examples
uv run python examples/1_basic_validation.py
uv run python examples/2_catch_apply_jobs_error.py
```

## How it Works

1. Prisma schema → DMMF (using `@prisma/internals`)
2. DMMF → SQLGlot schema (Python dict with table/column mappings)
3. SQLGlot validates SQL queries against schema
4. Reports table/column mismatches before runtime

## Why DMMF?

We chose Prisma's DMMF as the source of truth because:

- Official Prisma format - won't break with Prisma updates
- Includes all mappings (`@map`, `@@map`)
- Already used internally by Prisma Client
- No need to parse Prisma schema ourselves
- Can be generated as part of build process

## License

MIT

## Contributing

This is a proof-of-concept. Contributions welcome!

- Add support for more SQL features
- Improve error messages
- Add more test coverage
- Support for views and computed columns
