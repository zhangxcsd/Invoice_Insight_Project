"""Legacy error handling shim.

The canonical implementation lives in `vat_audit_pipeline.utils.error_handling`.
This module is kept for backward compatibility with the historical import path
`utils.error_handling`.
"""

from __future__ import annotations

from vat_audit_pipeline.utils.error_handling import (  # noqa: F401
    ConfigError,
    DataEncodingError,
    DataError,
    DataTypeError,
    DataValidationError,
    DatabaseConnectionError,
    DatabaseError,
    DatabaseQueryError,
    DatabaseTransactionError,
    ErrorCategory,
    ErrorCollector,
    ErrorLevel,
    ErrorStatistics,
    ExcelError,
    ExcelParseError,
    ExcelSheetError,
    FileError,
    FileNotFoundError_,
    FileReadError,
    FileWriteError,
    MemoryError_,
    PermissionError_,
    VATAuditException,
    convert_exception_to_vat_error,
)

__all__ = [
    "ErrorLevel",
    "ErrorCategory",
    "VATAuditException",
    "ErrorStatistics",
    "ErrorCollector",
    "FileError",
    "FileReadError",
    "FileWriteError",
    "FileNotFoundError_",
    "PermissionError_",
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "DatabaseTransactionError",
    "DataError",
    "DataValidationError",
    "DataEncodingError",
    "DataTypeError",
    "ExcelError",
    "ExcelParseError",
    "ExcelSheetError",
    "ConfigError",
    "MemoryError_",
    "convert_exception_to_vat_error",
]
