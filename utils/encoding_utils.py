"""Legacy compatibility shim.

The canonical implementation lives in `vat_audit_pipeline.utils.encoding`.
This module re-exports the public symbols for older import paths.
"""

from vat_audit_pipeline.utils.encoding import (  # noqa: F401
    detect_encoding,
    read_csv_with_encoding_detection,
)

__all__ = [
    "detect_encoding",
    "read_csv_with_encoding_detection",
]
