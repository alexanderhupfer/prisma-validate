"""
Prisma SQLGlot - Validate SQL queries against Prisma schema
"""

from .converter import convert_dmmf_to_sqlglot, load_dmmf, detect_dialect_from_schema
from .validator import validate_query, validate_query_strict, ValidationError

__version__ = "0.1.0"
__all__ = [
    "convert_dmmf_to_sqlglot",
    "load_dmmf",
    "detect_dialect_from_schema",
    "validate_query",
    "validate_query_strict",
    "ValidationError",
]
