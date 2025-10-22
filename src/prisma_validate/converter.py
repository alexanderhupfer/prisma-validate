"""
Convert Prisma DMMF (Data Model Meta Format) to SQLGlot schema format.

DMMF is Prisma's internal representation of the schema as an AST.
SQLGlot uses a dict format: {table_name: {column_name: sql_type}}
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional


def load_dmmf(file_path: str | Path) -> Dict[str, Any]:
    """Load DMMF JSON from file."""
    with open(file_path) as f:
        return json.load(f)


def prisma_type_to_sql(prisma_type: str) -> str:
    """
    Convert Prisma scalar type to SQL type.

    Prisma types: String, Int, BigInt, Float, Decimal, Boolean, DateTime, Json, Bytes
    """
    type_map = {
        "String": "TEXT",
        "Int": "INTEGER",
        "BigInt": "BIGINT",
        "Float": "DOUBLE PRECISION",
        "Decimal": "DECIMAL",
        "Boolean": "BOOLEAN",
        "DateTime": "TIMESTAMP",
        "Json": "JSONB",
        "Bytes": "BYTEA",
    }
    return type_map.get(prisma_type, "TEXT")


def convert_dmmf_to_sqlglot(dmmf: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    Convert Prisma DMMF to SQLGlot schema format.

    Args:
        dmmf: Prisma DMMF (from getDMMF() or loaded from JSON)

    Returns:
        SQLGlot schema dict: {table_name: {column_name: sql_type}}

    Example:
        {
            "job": {
                "id": "INTEGER",
                "job_type": "TEXT",
                "status": "TEXT",
                "progress": "INTEGER",
                "diff_gcs_path": "TEXT"
            }
        }
    """
    schema: Dict[str, Dict[str, str]] = {}

    models = dmmf.get("datamodel", {}).get("models", [])

    for model in models:
        # Get table name (use dbName if specified, otherwise use model name)
        table_name = model.get("dbName") or model["name"]
        table_name = table_name.lower()

        schema[table_name] = {}

        for field in model.get("fields", []):
            # Skip relation fields (they don't map to columns)
            if field.get("kind") == "object":
                continue

            # Get column name (use dbName if specified, otherwise use field name)
            column_name = field.get("dbName") or field["name"]

            # Get SQL type
            prisma_type = field.get("type", "String")
            sql_type = prisma_type_to_sql(prisma_type)

            schema[table_name][column_name] = sql_type

    return schema


def detect_dialect_from_schema(schema_path: str | Path) -> str:
    """
    Auto-detect SQL dialect from Prisma schema file.

    Reads the schema.prisma file and extracts the datasource provider.

    Args:
        schema_path: Path to schema.prisma file

    Returns:
        SQLGlot dialect string (postgres, mysql, sqlite, tsql, etc.)

    Example:
        >>> detect_dialect_from_schema("prisma/schema.prisma")
        'postgres'
    """
    # Mapping from Prisma provider names to SQLGlot dialects
    provider_to_dialect = {
        "postgresql": "postgres",
        "postgres": "postgres",
        "mysql": "mysql",
        "sqlite": "sqlite",
        "sqlserver": "tsql",
        "cockroachdb": "postgres",  # CockroachDB uses PostgreSQL dialect
        "mongodb": "postgres",  # MongoDB connector still uses SQL-like queries
    }

    try:
        with open(schema_path, 'r') as f:
            content = f.read()

        # Look for: datasource db { provider = "postgresql" }
        # Pattern matches provider with optional quotes
        pattern = r'datasource\s+\w+\s*\{[^}]*provider\s*=\s*["\']?(\w+)["\']?'
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)

        if match:
            provider = match.group(1).lower()
            dialect = provider_to_dialect.get(provider, "postgres")
            return dialect

    except (FileNotFoundError, IOError):
        pass

    # Default to postgres if can't detect
    return "postgres"
