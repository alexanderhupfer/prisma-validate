#!/usr/bin/env python3
"""
Example 2: Catching the apply_jobs bug

Demonstrates how this tool would have caught the actual bug we just fixed:
- Backend Python code referenced "apply_jobs" table
- But Prisma schema defines the table as "job" (via @@map)
- This validation would catch it before runtime!
"""

import sys
from pathlib import Path

# Add src to path for examples
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prisma_validate import load_dmmf, convert_dmmf_to_sqlglot, validate_query

# Load DMMF
dmmf_path = Path(__file__).parent.parent / "tests/fixtures/sample.dmmf.json"
dmmf = load_dmmf(dmmf_path)
schema = convert_dmmf_to_sqlglot(dmmf)

print("=" * 70)
print("REPRODUCING THE BUG: apply_jobs → job")
print("=" * 70)
print("\nContext:")
print("- Frontend Prisma schema defined: model Job { @@map('jobs') }")
print("- Backend Python had legacy references to 'apply_jobs' table")
print("- Runtime error: 'relation apply_jobs does not exist'")
print("\nHow this tool would have prevented it:")
print()

# This was the buggy query from apply_changes_to_shopify.py line 152
buggy_query = """
    SELECT diff_gcs_path FROM apply_jobs WHERE id = %s
"""

print(f"❌ BUGGY QUERY (from apply_changes_to_shopify.py:152):")
print(f"   {buggy_query.strip()}")
print()

errors = validate_query(buggy_query, schema)
if errors:
    print("🔍 Validation would have caught this!")
    for error in errors:
        print(f"   Error: {error}")
else:
    print("   ⚠️  No errors detected (unexpected!)")

print()

# The correct query after fix
correct_query = """
    SELECT diff_gcs_path FROM jobs WHERE id = %s
"""

print(f"✅ FIXED QUERY:")
print(f"   {correct_query.strip()}")
print()

errors = validate_query(correct_query, schema)
if errors:
    print("   ❌ Validation failed (unexpected):")
    for error in errors:
        print(f"      {error}")
else:
    print("   ✅ Validation passed!")

print()
print("=" * 70)
print("CONCLUSION")
print("=" * 70)
print("If this validation was in pre-commit hooks or CI:")
print("✅ Would catch table name mismatches before deployment")
print("✅ Would prevent runtime 'relation does not exist' errors")
print("✅ Would ensure Python queries stay in sync with Prisma schema")
print("=" * 70)
