# Pre-commit Hook Integration Guide

This guide shows how to integrate opt-in SQL validation into your development workflow.

## Overview

**Opt-in validation with comment markers:**
- Only validates SQL queries marked with `# prisma-validate` or `# validate-sql`
- Ignores queries to other databases (BigQuery, analytics, etc.)
- Two validation modes:
  - **Python file changed**: Validates marked queries in that file
  - **Prisma schema changed**: Validates ALL marked queries in codebase

## Quick Start

### 1. Mark Your SQL Queries

Add a validation marker comment before queries that go to your Prisma-managed PostgreSQL database:

```python
# prisma-validate
cursor.execute("SELECT id, status FROM jobs WHERE id = %s", (job_id,))
```

**Multi-line queries:**
```python
# prisma-validate
query = """
    UPDATE jobs
    SET status = %s, progress = %s
    WHERE id = %s
"""
cursor.execute(query, values)
```

**What NOT to mark:**
```python
# BigQuery - don't mark
bigquery_client.query("SELECT * FROM analytics.sales")

# Other database - don't mark
analytics_db.execute("SELECT * FROM external_table")
```

### 2. Install Pre-commit Hook

**Option A: Using pre-commit framework (Recommended)**

```bash
# Install pre-commit
pip install pre-commit
# or
uv add --dev pre-commit

# Copy configuration to project root
cp prisma-validate/.pre-commit-config.yaml .pre-commit-config.yaml

# Install the git hook
pre-commit install
```

**Option B: Manual git hook**

```bash
cp prisma-validate/scripts/pre-commit-hook.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### 3. Test It

```bash
# Run on all files
pre-commit run --all-files

# Or test manually
cd prisma-validate
uv run python scripts/validate_sql_in_python.py ../backend/tasks/your_file.py
```

## How It Works

### Scenario 1: Changing a Python File

You modify `backend/tasks/apply_changes.py`:

```python
def process_job(job_id):
    # prisma-validate
    cursor.execute("SELECT id FROM apply_jobs WHERE id = %s", (job_id,))
                                    ^^^^^^^^^^
                                    Typo - should be "jobs"
```

**When you commit:**
```bash
git add backend/tasks/apply_changes.py
git commit -m "Process jobs"
```

**Hook runs:**
```
🔍 Validating SQL queries against Prisma schema...
📊 Generating DMMF from Prisma schema...
✅ DMMF generated

📝 Checking changed Python files for marked queries:
  - backend/tasks/apply_changes.py

backend/tasks/apply_changes.py:15
  Query: SELECT id FROM apply_jobs WHERE id = %s
  ❌ Table "apply_jobs" not found in schema

❌ Invalid SQL queries found
```

**Commit is blocked** - fix the typo and try again!

### Scenario 2: Changing Prisma Schema

You modify the Prisma schema:

```prisma
model Job {
  id        Int      @id @default(autoincrement())
  status    String
  - oldField  String  // Removed this field

  @@map("jobs")
}
```

**When you commit:**
```bash
git add frontend/prisma/schema.prisma
git commit -m "Remove oldField from Job model"
```

**Hook runs:**
```
🔍 Validating SQL queries against Prisma schema...
📊 Generating DMMF from Prisma schema...
✅ DMMF generated

⚠️  Prisma schema changed - validating ALL marked queries in codebase

📝 Checking ALL files with marked queries:
  - backend/tasks/apply_changes.py
  - backend/tasks/create_job.py
  - backend/services/job_service.py

backend/tasks/legacy_code.py:45
  Query: SELECT oldField FROM jobs WHERE id = %s
  ❌ Column "oldField" not found in table "jobs"

❌ Invalid SQL queries found
```

**Commit is blocked** - you need to update all queries that reference the removed field!

This catches **breaking schema changes** before they reach production.

## Usage Examples

### ✅ Correct Usage

```python
# Query to Prisma PostgreSQL database - MARK IT
# prisma-validate
cursor.execute("SELECT id FROM jobs WHERE status = %s", ('pending',))

# Query to BigQuery - DON'T MARK
bigquery_client.query("""
    SELECT product_id, SUM(revenue)
    FROM analytics.sales
    GROUP BY product_id
""")

# Query to another PostgreSQL database - DON'T MARK
other_db_cursor.execute("SELECT * FROM external_table")

# Multiple marked queries in one function
def update_job_status(job_id, status):
    # prisma-validate
    cursor.execute("UPDATE jobs SET status = %s WHERE id = %s", (status, job_id))

    # prisma-validate
    cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
```

### Validation Markers

Both markers work the same way:
- `# prisma-validate` (recommended)
- `# validate-sql` (alias)

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/validate-sql.yml`:

```yaml
name: Validate SQL Queries

on:
  pull_request:
    paths:
      - '**.py'
      - 'frontend/prisma/schema.prisma'

jobs:
  validate-sql:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install Prisma
        run: |
          cd frontend
          npm install @prisma/internals

      - name: Generate DMMF
        run: |
          cd frontend
          npx tsx << 'EOF'
          import { getDMMF } from '@prisma/internals';
          import { readFileSync, writeFileSync } from 'fs';

          const schema = readFileSync('./prisma/schema.prisma', 'utf-8');
          getDMMF({ datamodel: schema }).then(dmmf => {
            writeFileSync('../prisma-validate/.dmmf.json', JSON.stringify(dmmf, null, 2));
          });
          EOF

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install uv
        run: pip install uv

      - name: Find files with validation markers
        id: find-files
        run: |
          FILES=$(grep -rl "# prisma-validate\|# validate-sql" backend/ || echo "")
          echo "files=$FILES" >> $GITHUB_OUTPUT

      - name: Validate SQL queries
        if: steps.find-files.outputs.files != ''
        run: |
          cd prisma-validate
          PRISMA_DMMF_PATH=".dmmf.json" \
            uv run python scripts/validate_sql_in_python.py \
            ${{ steps.find-files.outputs.files }}
```

## Configuration

### Environment Variables

- `PRISMA_DMMF_PATH`: Path to DMMF JSON file (default: `tests/fixtures/sample.dmmf.json`)

### Skipping Validation

Emergency commits without validation:

```bash
# Skip all hooks
git commit --no-verify -m "Emergency hotfix"

# Skip specific hook (pre-commit framework)
SKIP=validate-sql-queries git commit -m "WIP"
```

## Advanced Usage

### Find All Marked Queries

```bash
# Find all files with markers
grep -r "# prisma-validate" backend/

# Count marked queries
grep -r "# prisma-validate" backend/ | wc -l
```

### Validate Specific Directory

```bash
cd prisma-validate

# Only validate tasks
find ../backend/tasks -name "*.py" -exec \
  uv run python scripts/validate_sql_in_python.py {} +

# Only validate services
find ../backend/services -name "*.py" -exec \
  uv run python scripts/validate_sql_in_python.py {} +
```

### IDE Integration

#### VS Code

Create `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Validate SQL in current file",
      "type": "shell",
      "command": "cd prisma-validate && PRISMA_DMMF_PATH=tests/fixtures/sample.dmmf.json uv run python scripts/validate_sql_in_python.py ${file}",
      "problemMatcher": [],
      "presentation": {
        "reveal": "always"
      }
    }
  ]
}
```

#### PyCharm External Tool

1. Settings → Tools → External Tools → Add
2. Configure:
   - Name: `Validate SQL`
   - Program: `uv`
   - Arguments: `run python scripts/validate_sql_in_python.py $FilePath$`
   - Working directory: `$ProjectFileDir$/prisma-validate`

## Migration Strategy

### Gradual Adoption

You don't need to mark all queries at once:

**Week 1**: Mark queries in critical files
```python
# backend/tasks/apply_changes_to_shopify.py
# prisma-validate
cursor.execute("SELECT id FROM jobs WHERE id = %s")
```

**Week 2**: Mark queries in new code
- New features automatically get markers
- Old code gets marked as you touch it

**Week 3**: Mark remaining queries
```bash
# Find all cursor.execute calls
grep -rn "cursor.execute" backend/ | grep -v "# prisma-validate"
```

### Team Onboarding

**Add to code review checklist:**
- [ ] New SQL queries have `# prisma-validate` marker (if they query Prisma DB)
- [ ] Non-Prisma queries are NOT marked

**Document in team wiki:**
- When to use markers
- How to run validation locally
- What to do when validation fails

## Troubleshooting

### Hook doesn't find marked queries

```bash
# Check if markers exist
grep -r "# prisma-validate" backend/

# Test extraction manually
cd prisma-validate
uv run python scripts/validate_sql_in_python.py ../backend/tasks/your_file.py
```

### False positives

If valid SQL is flagged as invalid:

1. **Check table/column names match Prisma schema**
   ```prisma
   model Job {
     jobType String @map("job_type")  // Use "job_type" in SQL, not "jobType"
     @@map("jobs")  // Use "jobs" in SQL, not "Job"
   }
   ```

2. **Verify DMMF is up to date**
   ```bash
   # Regenerate DMMF
   cd frontend
   npx tsx -e "import { getDMMF } from '@prisma/internals'; ..."
   ```

### Hook is slow

Pre-commit hook generates DMMF every time. To speed up:

**Option 1**: Cache DMMF in CI only
```yaml
# GitHub Actions
- uses: actions/cache@v3
  with:
    path: prisma-validate/.dmmf.json
    key: dmmf-${{ hashFiles('frontend/prisma/schema.prisma') }}
```

**Option 2**: Run in CI only (skip pre-commit hook)
```bash
# Uninstall hook locally
pre-commit uninstall

# Rely on CI for validation
```

## Best Practices

### 1. Mark New Queries Immediately

When writing new code:
```python
def create_job():
    # prisma-validate  ← Add this first
    cursor.execute("INSERT INTO jobs (status) VALUES (%s)", ('pending',))
```

### 2. Update Schema First

When changing database schema:
1. Update Prisma schema
2. Commit (validation runs on all marked queries)
3. Fix any broken queries
4. Deploy

### 3. Use Descriptive Markers

Add context to help future developers:
```python
# prisma-validate - checks job status for reporting
cursor.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
```

### 4. Don't Over-Mark

Only mark queries to Prisma database:
```python
# ✅ Prisma PostgreSQL - MARK IT
# prisma-validate
cursor.execute("SELECT id FROM jobs WHERE id = %s")

# ❌ BigQuery - DON'T MARK
bigquery_client.query("SELECT * FROM analytics.sales")

# ❌ DuckDB - DON'T MARK
duckdb_cursor.execute("SELECT * FROM local_cache")
```

## Summary

### Key Benefits

✅ **Opt-in**: Only validates marked queries
✅ **Selective**: Ignores non-Prisma databases
✅ **Comprehensive**: Validates entire codebase when schema changes
✅ **Fast**: Only checks marked queries
✅ **Safe**: Catches bugs before production

### Quick Reference

```python
# Mark queries to Prisma database
# prisma-validate
cursor.execute("SELECT id FROM jobs WHERE id = %s")

# Don't mark other databases
bigquery_client.query("SELECT * FROM analytics.sales")
```

### Two Validation Modes

| Change Type | Validates | Example |
|------------|-----------|---------|
| Python file | Marked queries in that file | `backend/tasks/process.py` |
| Prisma schema | ALL marked queries in codebase | All files with `# prisma-validate` |

This ensures schema changes don't break existing queries!
