"""Legacy compatibility shim.

The canonical implementation lives in `vat_audit_pipeline.utils.sheet_processing`.
This module re-exports the public symbols for older import paths.
"""

from vat_audit_pipeline.utils.sheet_processing import (  # noqa: F401
    PipelineSettings,
    SheetProcessingContext,
    SheetTypeMapping,
    get_sheet_handler,
    normalize_sheet_dataframe,
    write_to_csv_or_queue,
)

__all__ = [
    "PipelineSettings",
    "SheetProcessingContext",
    "SheetTypeMapping",
    "get_sheet_handler",
    "normalize_sheet_dataframe",
    "write_to_csv_or_queue",
]


