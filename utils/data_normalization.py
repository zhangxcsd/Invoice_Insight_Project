"""Legacy compatibility shim.

The canonical implementation lives in `vat_audit_pipeline.utils.normalization`.
This module re-exports the public symbols for older import paths.
"""

from vat_audit_pipeline.utils.normalization import (  # noqa: F401
    cast_and_record,
    normalize_excel_date_col,
    normalize_numeric_col,
    normalize_tax_rate_col,
)

__all__ = [
    "normalize_excel_date_col",
    "normalize_numeric_col",
    "normalize_tax_rate_col",
    "cast_and_record",
]
