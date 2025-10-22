#!/usr/bin/env python3
"""
Example 1: Basic SQL query validation

Demonstrates:
- Loading DMMF from JSON
- Converting to SQLGlot schema
- Validating SQL queries
"""

import sys
from pathlib import Path

# Add src to path for examples
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prisma_validate import load_dmmf, convert_dmmf_to_sqlglot, validate_query

# Load DMMF from test fixtures
dmmf_path = Path(__file__).parent.parent / "tests/fixtures/sample.dmmf.json"
dmmf = load_dmmf(dmmf_path)

# Convert to SQLGlot schema
schema = convert_dmmf_to_sqlglot(dmmf)

print("=" * 60)
print("SQLGlot Schema Generated from Prisma DMMF")
print("=" * 60)
print(f"Tables: {list(schema.keys())}")
print(f"\nColumns in 'jobs' table:")
for column, sql_type in schema["jobs"].items():
    print(f"  {column:20} {sql_type}")

print("\n" + "=" * 60)
print("Validating SQL Queries")
print("=" * 60)

# Test 1: Valid query
query1 = "SELECT diff_gcs_path FROM jobs WHERE id = %s"
errors1 = validate_query(query1, schema)
print(f"\n✅ Query: {query1}")
print(f"   Valid: {len(errors1) == 0}")
if errors1:
    for error in errors1:
        print(f"   Error: {error}")

# Test 2: Valid query with multiple columns
query2 = "SELECT id, status, progress FROM jobs WHERE status = %s"
errors2 = validate_query(query2, schema)
print(f"\n✅ Query: {query2}")
print(f"   Valid: {len(errors2) == 0}")

# Test 3: Invalid column name
query3 = "SELECT invalid_column FROM jobs WHERE id = %s"
errors3 = validate_query(query3, schema)
print(f"\n❌ Query: {query3}")
print(f"   Valid: {len(errors3) == 0}")
if errors3:
    for error in errors3:
        print(f"   Error: {error}")

# Test 4: Invalid table name
query4 = "SELECT id FROM fake_table WHERE id = %s"
errors4 = validate_query(query4, schema)
print(f"\n❌ Query: {query4}")
print(f"   Valid: {len(errors4) == 0}")
if errors4:
    for error in errors4:
        print(f"   Error: {error}")

print("\n" + "=" * 60)
