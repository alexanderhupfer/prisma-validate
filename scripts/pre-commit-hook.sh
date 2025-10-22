#!/bin/bash
# Pre-commit hook to validate SQL queries in Python files
#
# This script:
# 1. Generates fresh DMMF from Prisma schema
# 2. If Prisma schema changed: validates ALL marked queries in codebase
# 3. If only Python files changed: validates marked queries in those files
# 4. Fails the commit if invalid SQL is found

set -e

echo "🔍 Validating SQL queries against Prisma schema..."
echo

# Check if we're in the bulk-ai project root
if [ ! -f "frontend/prisma/schema.prisma" ]; then
    echo "Error: Could not find frontend/prisma/schema.prisma"
    echo "This hook should run from the bulk-ai project root"
    exit 1
fi

# Step 1: Generate DMMF from Prisma schema
echo "📊 Generating DMMF from Prisma schema..."
cd frontend
npx tsx << 'EOF'
import { getDMMF } from '@prisma/internals';
import { readFileSync, writeFileSync } from 'fs';

const schema = readFileSync('./prisma/schema.prisma', 'utf-8');
getDMMF({ datamodel: schema }).then(dmmf => {
  writeFileSync('../prisma-validate/.dmmf.json', JSON.stringify(dmmf, null, 2));
  console.log('✅ DMMF generated');
});
EOF
cd ..

# Step 2: Check what files changed
SCHEMA_CHANGED=$(git diff --cached --name-only --diff-filter=ACM | grep 'prisma/schema.prisma' || true)
PYTHON_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)

if [ -n "$SCHEMA_CHANGED" ]; then
    echo
    echo "⚠️  Prisma schema changed - validating ALL marked queries in codebase"
    echo

    # Find all Python files with validation markers
    ALL_MARKED_FILES=$(grep -rl "# prisma-validate\|# validate-sql" backend/ 2>/dev/null || true)

    if [ -z "$ALL_MARKED_FILES" ]; then
        echo "No Python files with validation markers found"
        rm -f prisma-validate/.dmmf.json
        exit 0
    fi

    echo "📝 Checking ALL files with marked queries:"
    echo "$ALL_MARKED_FILES" | sed 's/^/  - /'
    echo

    # Run validation on all marked files
    cd prisma-validate
    PRISMA_DMMF_PATH=".dmmf.json" uv run python scripts/validate_sql_in_python.py $ALL_MARKED_FILES

elif [ -n "$PYTHON_FILES" ]; then
    echo
    echo "📝 Checking changed Python files for marked queries:"
    echo "$PYTHON_FILES" | sed 's/^/  - /'
    echo

    # Run validation only on changed files
    cd prisma-validate
    PRISMA_DMMF_PATH=".dmmf.json" uv run python scripts/validate_sql_in_python.py $PYTHON_FILES

else
    echo "No Python files or Prisma schema to validate"
    rm -f prisma-validate/.dmmf.json
    exit 0
fi

# Cleanup
rm -f .dmmf.json

echo
echo "✅ SQL validation passed!"
