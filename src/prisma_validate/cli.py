#!/usr/bin/env python3
"""
Command-line interface for prisma-validate.

Usage:
    prisma-validate file1.py file2.py ...
    prisma-validate --schema-path prisma/schema.prisma backend/**/*.py
"""

import sys
import json
import subprocess
import argparse
import re
from pathlib import Path
from typing import List, Tuple, Optional

from prisma_validate import (
    convert_dmmf_to_sqlglot,
    validate_query,
    detect_dialect_from_schema,
)


def find_schema() -> Optional[Path]:
    """
    Auto-detect Prisma schema location.

    Searches common locations in order:
    1. ./prisma/schema.prisma
    2. ./frontend/prisma/schema.prisma
    3. ./backend/prisma/schema.prisma
    4. ../prisma/schema.prisma

    Returns:
        Path to schema.prisma if found, None otherwise
    """
    search_paths = [
        Path("prisma/schema.prisma"),
        Path("frontend/prisma/schema.prisma"),
        Path("backend/prisma/schema.prisma"),
        Path("../prisma/schema.prisma"),
    ]

    for path in search_paths:
        if path.exists():
            return path.resolve()

    return None


def generate_dmmf(schema_path: Path) -> dict:
    """
    Generate DMMF from Prisma schema using Node.js.

    Args:
        schema_path: Path to schema.prisma file

    Returns:
        DMMF dictionary

    Raises:
        SystemExit: If DMMF generation fails
    """
    generate_script = """
const { getDMMF } = require('@prisma/internals');
const fs = require('fs');

const schema = fs.readFileSync(process.argv[1], 'utf-8');
getDMMF({ datamodel: schema }).then(dmmf => {
    console.log(JSON.stringify(dmmf));
}).catch(err => {
    console.error('Failed to generate DMMF:', err);
    process.exit(1);
});
"""

    try:
        result = subprocess.run(
            ['node', '-e', generate_script, str(schema_path.resolve())],
            cwd=str(schema_path.parent),  # Run from schema directory
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        if "Cannot find module '@prisma/internals'" in e.stderr:
            print("❌ Error: @prisma/internals not found", file=sys.stderr)
            print("", file=sys.stderr)
            print("To generate DMMF, install @prisma/internals in your Node.js project:", file=sys.stderr)
            print("  npm install --save-dev @prisma/internals", file=sys.stderr)
            print("", file=sys.stderr)
            print("Then run:", file=sys.stderr)
            print("  prisma-validate <files>", file=sys.stderr)
            print("", file=sys.stderr)
            print("Learn more: https://github.com/alexanderhupfer/prisma-validate#setup", file=sys.stderr)
        else:
            print(f"❌ Error generating DMMF: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing DMMF JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Error: Node.js not found", file=sys.stderr)
        print("Please install Node.js: https://nodejs.org/", file=sys.stderr)
        sys.exit(1)


def extract_sql_queries(file_path: Path) -> List[Tuple[str, int]]:
    """
    Extract SQL queries marked with SQL comments.

    Looks for SQL queries containing:
    - -- prisma-validate (SQL line comment)
    - /* prisma-validate */ (SQL block comment)

    Args:
        file_path: Path to Python file

    Returns:
        List of (query, line_number) tuples
    """
    queries = []
    sql_markers = ['-- prisma-validate', '/* prisma-validate */']

    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"⚠️  Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return queries

    # Find all cursor.execute() calls with triple-quoted strings
    # Pattern: cursor.execute(""" ... """, ...)
    triple_quote_pattern = r'cursor\.execute\s*\(\s*"""(.*?)"""\s*[,\)]'
    for match in re.finditer(triple_quote_pattern, content, re.DOTALL):
        query = match.group(1).strip()
        # Check if query contains validation marker
        if any(marker in query for marker in sql_markers):
            # Find line number
            line_num = content[:match.start()].count('\n') + 1
            # Remove the marker from the query for validation
            clean_query = query
            for marker in sql_markers:
                clean_query = clean_query.replace(marker, '').strip()
            queries.append((clean_query, line_num))

    # Also check single-quoted triple strings
    single_quote_pattern = r"cursor\.execute\s*\(\s*'''(.*?)'''\s*[,\)]"
    for match in re.finditer(single_quote_pattern, content, re.DOTALL):
        query = match.group(1).strip()
        if any(marker in query for marker in sql_markers):
            line_num = content[:match.start()].count('\n') + 1
            clean_query = query
            for marker in sql_markers:
                clean_query = clean_query.replace(marker, '').strip()
            queries.append((clean_query, line_num))

    # Also check single-line string queries
    single_line_pattern = r'cursor\.execute\s*\(\s*["\']([^"\']+)["\']\s*[,\)]'
    for match in re.finditer(single_line_pattern, content):
        query = match.group(1).strip()
        if any(marker in query for marker in sql_markers):
            line_num = content[:match.start()].count('\n') + 1
            clean_query = query
            for marker in sql_markers:
                clean_query = clean_query.replace(marker, '').strip()
            queries.append((clean_query, line_num))

    return queries


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Validate SQL queries against Prisma schema',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  prisma-validate backend/tasks/*.py
  prisma-validate --schema-path prisma/schema.prisma file.py

Mark queries for validation with SQL comments:
  cursor.execute(\"\"\"
      -- prisma-validate
      SELECT * FROM jobs WHERE id = %s
  \"\"\", (id,))
        """
    )

    parser.add_argument(
        'files',
        nargs='+',
        help='Python files to validate'
    )

    parser.add_argument(
        '--schema-path',
        type=Path,
        help='Path to schema.prisma (auto-detected if not provided)'
    )

    args = parser.parse_args()

    # Find or validate schema path
    if args.schema_path:
        schema_path = args.schema_path
        if not schema_path.exists():
            print(f"❌ Error: Schema not found at {schema_path}", file=sys.stderr)
            sys.exit(1)
    else:
        schema_path = find_schema()
        if not schema_path:
            print("❌ Error: Could not find schema.prisma", file=sys.stderr)
            print("", file=sys.stderr)
            print("Searched:", file=sys.stderr)
            print("  - prisma/schema.prisma", file=sys.stderr)
            print("  - frontend/prisma/schema.prisma", file=sys.stderr)
            print("  - backend/prisma/schema.prisma", file=sys.stderr)
            print("  - ../prisma/schema.prisma", file=sys.stderr)
            print("", file=sys.stderr)
            print("Use --schema-path to specify location explicitly", file=sys.stderr)
            sys.exit(1)

    print(f"🔍 Generating DMMF from {schema_path}...")

    # Generate DMMF and create schema
    dmmf = generate_dmmf(schema_path)
    schema = convert_dmmf_to_sqlglot(dmmf)

    # Detect SQL dialect
    dialect = detect_dialect_from_schema(schema_path)
    print(f"📝 Using SQL dialect: {dialect}")
    print()

    # Validate all files
    total_errors = 0
    files_checked = 0

    for file_path_str in args.files:
        file_path = Path(file_path_str)

        if not file_path.exists():
            print(f"⚠️  Warning: File not found: {file_path}", file=sys.stderr)
            continue

        if not file_path.suffix == '.py':
            continue

        queries = extract_sql_queries(file_path)

        if not queries:
            continue

        files_checked += 1
        print(f"📄 {file_path} ({len(queries)} marked queries)")

        for query, line_num in queries:
            errors = validate_query(query, schema, dialect=dialect)

            if errors:
                total_errors += len(errors)
                # Truncate long queries for display
                display_query = query[:60] + "..." if len(query) > 60 else query
                print(f"  ❌ Line {line_num}: {display_query}")
                for error in errors:
                    print(f"     → {error}")
            else:
                print(f"  ✅ Line {line_num}: Valid")

        print()

    # Summary and exit
    if files_checked == 0:
        print("✅ No Python files with marked queries found")
        sys.exit(0)

    if total_errors > 0:
        print(f"❌ Validation failed with {total_errors} error(s)")
        sys.exit(1)
    else:
        print("✅ All marked SQL queries are valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
