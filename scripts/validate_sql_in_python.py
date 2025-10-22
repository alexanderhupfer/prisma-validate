#!/usr/bin/env python3
"""
Pre-commit hook: Extract and validate SQL queries from Python files.

Usage:
    python scripts/validate_sql_in_python.py file1.py file2.py ...

Exit codes:
    0 - All SQL queries are valid
    1 - Invalid SQL queries found
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prisma_validate import load_dmmf, convert_dmmf_to_sqlglot, validate_query


def extract_sql_queries(file_path: Path) -> List[Tuple[str, int]]:
    """
    Extract SQL queries from Python file that are marked for validation.

    Only extracts queries preceded by validation marker comments:
    - # prisma-validate
    - # validate-sql

    Example:
        # prisma-validate
        cursor.execute("SELECT id FROM jobs WHERE id = %s", (job_id,))

    Returns:
        List of (query, line_number) tuples
    """
    queries = []

    try:
        content = file_path.read_text()
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return queries

    lines = content.split('\n')

    # Track if previous line had a validation marker
    validate_next = False
    validation_markers = ['# prisma-validate', '# validate-sql']

    # Pattern 1: cursor.execute("...") or cursor.execute('...')
    # Handles: cursor.execute("SELECT ...", ...)
    execute_pattern = re.compile(
        r'cursor\.execute\s*\(\s*["\'](.+?)["\']',
        re.IGNORECASE
    )

    # Pattern 2: Multi-line SQL in triple quotes or regular strings
    # Look for SQL keywords at the start, but skip docstrings
    sql_keywords = ['SELECT', 'UPDATE', 'INSERT', 'DELETE', 'WITH']
    in_triple_quote = False
    triple_quote_query = []
    triple_quote_start_line = 0
    quote_char = None
    is_docstring = False

    for i, line in enumerate(lines, start=1):
        # Check if this line has a validation marker
        stripped = line.strip()
        if any(stripped.startswith(marker) for marker in validation_markers):
            validate_next = True
            continue

        # Only extract queries if marked for validation
        if not validate_next:
            continue

        # Check for execute patterns
        match = execute_pattern.search(line)
        if match:
            query = match.group(1)
            # Clean up the query
            query = query.strip()
            if any(query.upper().startswith(kw) for kw in sql_keywords):
                queries.append((query, i))
                validate_next = False  # Reset after finding query
                continue

        # Check for triple-quote SQL blocks (only if marked)
        # Starting a triple-quote block
        if not in_triple_quote:
            if ('"""' in stripped or "'''" in stripped):
                quote_char = '"""' if '"""' in stripped else "'''"

                # Detect if this is a docstring (appears right after def, class, or at module level)
                # Check previous non-empty lines for function/class definitions
                is_docstring = False
                for j in range(i-2, max(0, i-10), -1):
                    prev_line = lines[j].strip()
                    if not prev_line:
                        continue
                    # Check if we're right after a function/class definition
                    if prev_line.endswith('):') or prev_line.endswith('->') or prev_line.startswith('class '):
                        is_docstring = True
                        break
                    # If we hit code that's not part of a definition, stop
                    if not prev_line.endswith(',') and not prev_line.endswith('('):
                        break
                # Also check if at module start
                if i <= 5:
                    is_docstring = True

                # Check if it starts and ends on same line
                if stripped.count(quote_char) == 2:
                    # Single line triple quote
                    if not is_docstring:
                        content_match = re.search(rf'{quote_char}(.+?){quote_char}', stripped)
                        if content_match:
                            sql_content = content_match.group(1).strip()
                            if any(sql_content.upper().startswith(kw) for kw in sql_keywords):
                                queries.append((sql_content, i))
                                validate_next = False  # Reset after finding query
                else:
                    # Multi-line triple quote starting
                    if not is_docstring:
                        in_triple_quote = True
                        triple_quote_start_line = i
                        # Get content after opening quotes
                        after_quote = stripped.split(quote_char, 1)[1]
                        if after_quote:
                            triple_quote_query.append(after_quote)
        else:
            # Inside a triple-quote block
            if quote_char in line:
                # Ending the triple-quote block
                before_quote = line.split(quote_char)[0]
                if before_quote:
                    triple_quote_query.append(before_quote)

                full_query = '\n'.join(triple_quote_query).strip()
                if any(full_query.upper().startswith(kw) for kw in sql_keywords):
                    queries.append((full_query, triple_quote_start_line))
                    validate_next = False  # Reset after finding query

                # Reset
                in_triple_quote = False
                triple_quote_query = []
                triple_quote_start_line = 0
            else:
                triple_quote_query.append(line)

    return queries


def validate_file(file_path: Path, schema) -> Tuple[bool, List[str]]:
    """
    Validate all SQL queries in a Python file.

    Returns:
        (is_valid, error_messages)
    """
    queries = extract_sql_queries(file_path)

    if not queries:
        return True, []

    errors = []
    is_valid = True

    for query, line_num in queries:
        validation_errors = validate_query(query, schema)
        if validation_errors:
            is_valid = False
            errors.append(f"\n{file_path}:{line_num}")
            errors.append(f"  Query: {query[:80]}...")
            for error in validation_errors:
                errors.append(f"  ❌ {error}")

    return is_valid, errors


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_sql_in_python.py <file1.py> [file2.py ...]")
        sys.exit(1)

    # Load schema
    dmmf_path = Path(__file__).parent.parent / "tests/fixtures/sample.dmmf.json"

    # Allow override via environment variable
    import os
    if os.getenv("PRISMA_DMMF_PATH"):
        dmmf_path = Path(os.getenv("PRISMA_DMMF_PATH"))

    if not dmmf_path.exists():
        print(f"Error: DMMF file not found at {dmmf_path}")
        print("Set PRISMA_DMMF_PATH environment variable to specify location")
        sys.exit(1)

    print(f"Loading schema from {dmmf_path}")
    dmmf = load_dmmf(dmmf_path)
    schema = convert_dmmf_to_sqlglot(dmmf)
    print(f"Schema loaded with {len(schema)} tables")
    print()

    # Validate each file
    all_valid = True
    total_queries = 0

    for file_arg in sys.argv[1:]:
        file_path = Path(file_arg)

        if not file_path.exists():
            print(f"Warning: {file_path} does not exist, skipping")
            continue

        if not file_path.suffix == '.py':
            continue

        queries = extract_sql_queries(file_path)
        total_queries += len(queries)

        if queries:
            print(f"Validating {file_path} ({len(queries)} queries)")

        is_valid, errors = validate_file(file_path, schema)

        if not is_valid:
            all_valid = False
            for error in errors:
                print(error)

    print()
    print("=" * 70)
    if all_valid:
        print(f"✅ All SQL queries valid ({total_queries} queries checked)")
        print("=" * 70)
        sys.exit(0)
    else:
        print(f"❌ Invalid SQL queries found")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
