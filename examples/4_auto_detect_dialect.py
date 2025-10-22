#!/usr/bin/env python3
"""
Example 4: Auto-detecting SQL dialect from Prisma schema

Demonstrates how to automatically detect the correct SQL dialect
based on the database provider in your schema.prisma file.
"""

import sys
from pathlib import Path

# Add src to path for examples
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prisma_validate import (
    load_dmmf,
    convert_dmmf_to_sqlglot,
    validate_query,
    detect_dialect_from_schema
)

print("=" * 70)
print("AUTO-DETECTING SQL DIALECT FROM PRISMA SCHEMA")
print("=" * 70)
print()

# Example: Detect dialect from schema file
schema_path = Path(__file__).parent.parent / "tests/fixtures/sample.prisma"

if schema_path.exists():
    dialect = detect_dialect_from_schema(schema_path)
    print(f"✅ Detected dialect from schema: '{dialect}'")
    print(f"   Schema file: {schema_path}")
else:
    print(f"⚠️  Schema file not found, using default: 'postgres'")
    dialect = "postgres"

print()

# Load the DMMF
dmmf_path = Path(__file__).parent.parent / "tests/fixtures/sample.dmmf.json"
dmmf = load_dmmf(dmmf_path)
schema = convert_dmmf_to_sqlglot(dmmf)

print("=" * 70)
print("VALIDATING QUERIES WITH AUTO-DETECTED DIALECT")
print("=" * 70)
print()

# PostgreSQL-style query (with %s placeholder)
if dialect == "postgres":
    query = "SELECT id, status FROM jobs WHERE id = %s"
    errors = validate_query(query, schema, dialect=dialect)
    print(f"PostgreSQL query: {query}")
    print(f"Validation: {'✅ Valid' if not errors else '❌ Invalid'}")
    print()

# MySQL-style query (with ? placeholder)
elif dialect == "mysql":
    query = "SELECT id, status FROM jobs WHERE id = ?"
    errors = validate_query(query, schema, dialect=dialect)
    print(f"MySQL query: {query}")
    print(f"Validation: {'✅ Valid' if not errors else '❌ Invalid'}")
    print()

# SQLite-style query
elif dialect == "sqlite":
    query = "SELECT id, status FROM jobs WHERE id = ?"
    errors = validate_query(query, schema, dialect=dialect)
    print(f"SQLite query: {query}")
    print(f"Validation: {'✅ Valid' if not errors else '❌ Invalid'}")
    print()

print("=" * 70)
print("PROVIDER MAPPINGS")
print("=" * 70)
print()
print("Prisma Provider → SQLGlot Dialect:")
print("  postgresql    → postgres")
print("  mysql         → mysql")
print("  sqlite        → sqlite")
print("  sqlserver     → tsql")
print("  cockroachdb   → postgres")
print()

print("=" * 70)
print("USAGE IN YOUR CODE")
print("=" * 70)
print()
print("from prisma_validate import detect_dialect_from_schema, validate_query")
print()
print("# Auto-detect dialect")
print("dialect = detect_dialect_from_schema('prisma/schema.prisma')")
print()
print("# Use detected dialect for validation")
print("errors = validate_query(query, schema, dialect=dialect)")
print()

print("=" * 70)
print("BENEFITS")
print("=" * 70)
print()
print("✅ No need to manually specify dialect")
print("✅ Automatically stays in sync with your Prisma config")
print("✅ Works across different database providers")
print("✅ Defaults to 'postgres' if detection fails")
print()
print("=" * 70)
