# Example 5: Using the CLI Tool

The `prisma-validate` CLI provides a convenient way to validate SQL queries without writing custom scripts.

## Basic Usage

### Validate specific files

```bash
prisma-validate backend/tasks/my_task.py
```

### Validate multiple files

```bash
prisma-validate backend/tasks/file1.py backend/tasks/file2.py
```

### Validate with glob patterns

```bash
# All Python files in tasks directory
prisma-validate backend/tasks/*.py

# All Python files recursively
prisma-validate backend/**/*.py
```

## Custom Schema Location

If your Prisma schema is not in a standard location:

```bash
prisma-validate --schema-path custom/path/schema.prisma backend/**/*.py
```

## Schema Auto-Detection

By default, the CLI searches these locations automatically:
1. `./prisma/schema.prisma`
2. `./frontend/prisma/schema.prisma`
3. `./backend/prisma/schema.prisma`
4. `../prisma/schema.prisma`

## Marking Queries for Validation

Add a SQL comment inside the query you want to validate:

```python
# In your Python file (e.g., backend/tasks/my_task.py):

cursor.execute("""
    -- prisma-validate
    SELECT id, status FROM jobs WHERE id = %s
""", (job_id,))

# This query won't be validated (no marker):
bigquery_client.query("SELECT * FROM analytics.sales")

# This will be validated (using block comment):
cursor.execute("""
    /* prisma-validate */
    SELECT j.id, j.status, j.progress
    FROM jobs j
    WHERE j.id = %s
""", (job_id,))
```

**Language-agnostic**: SQL comments work in any language (Python, Go, Rust, Java, etc.)!

## Output Format

### Successful Validation

```
🔍 Generating DMMF from frontend/prisma/schema.prisma...
📝 Using SQL dialect: postgres

📄 backend/tasks/my_task.py (2 marked queries)
  ✅ Line 45: Valid
  ✅ Line 67: Valid

✅ All marked SQL queries are valid!
```

### Failed Validation

```
🔍 Generating DMMF from frontend/prisma/schema.prisma...
📝 Using SQL dialect: postgres

📄 backend/tasks/my_task.py (2 marked queries)
  ✅ Line 45: Valid
  ❌ Line 67: SELECT id FROM apply_jobs WHERE id = %s...
     → Table "apply_jobs" not found in schema

❌ Validation failed with 1 error(s)
```

## Exit Codes

The CLI exits with:
- `0` if all queries are valid
- `1` if validation fails or there's a setup error

This makes it easy to use in CI/CD pipelines:

```bash
# In CI/CD script
prisma-validate backend/**/*.py
if [ $? -ne 0 ]; then
    echo "SQL validation failed!"
    exit 1
fi
```

## Integration with Pre-commit

The recommended way to use the CLI is through pre-commit hooks:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/alexanderhupfer/prisma-validate
    rev: v0.3.0
    hooks:
      - id: prisma-validate
```

This automatically validates marked SQL queries on every commit!

## Requirements

The CLI requires:
1. **Node.js** - To run Prisma's DMMF generator
2. **@prisma/internals** - Installed in your Node.js project:
   ```bash
   npm install --save-dev @prisma/internals
   ```

## Error Messages

### @prisma/internals Not Found

```
❌ Error: @prisma/internals not found

To generate DMMF, install @prisma/internals in your Node.js project:
  npm install --save-dev @prisma/internals

Then run:
  prisma-validate <files>

Learn more: https://github.com/alexanderhupfer/prisma-validate#setup
```

**Solution:** Install the package in your Node.js project (where package.json is).

### Schema Not Found

```
❌ Error: Could not find schema.prisma

Searched:
  - prisma/schema.prisma
  - frontend/prisma/schema.prisma
  - backend/prisma/schema.prisma
  - ../prisma/schema.prisma

Use --schema-path to specify location explicitly
```

**Solution:** Either move your schema to a standard location or use `--schema-path`.

### Node.js Not Found

```
❌ Error: Node.js not found
Please install Node.js: https://nodejs.org/
```

**Solution:** Install Node.js from https://nodejs.org/

## Tips

1. **Use validation markers liberally** - Only mark queries that go to the Prisma database
2. **Skip analytics queries** - Don't mark queries to BigQuery, DuckDB, etc.
3. **Validate often** - Run locally before committing, or use pre-commit hooks
4. **Check CI/CD** - Add validation to your pipeline to catch schema drift

## Complete Example

```python
# backend/tasks/process_jobs.py
import psycopg2
from connections.database import get_connection

def update_job_status(job_id: int, status: str):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Validate this query against Prisma schema
        cursor.execute("""
            -- prisma-validate
            UPDATE jobs
            SET status = %s, updated_at = NOW()
            WHERE id = %s
        """, (status, job_id))

        conn.commit()

    finally:
        cursor.close()
        conn.close()

def get_analytics_data():
    # Don't validate this - it goes to BigQuery, not Prisma DB
    from google.cloud import bigquery
    client = bigquery.Client()

    query = """
        SELECT user_id, COUNT(*) as action_count
        FROM analytics.user_actions
        GROUP BY user_id
    """

    return client.query(query).result()
```

Run validation:

```bash
prisma-validate backend/tasks/process_jobs.py
```

Output:

```
🔍 Generating DMMF from frontend/prisma/schema.prisma...
📝 Using SQL dialect: postgres

📄 backend/tasks/process_jobs.py (1 marked queries)
  ✅ Line 11: Valid

✅ All marked SQL queries are valid!
```
