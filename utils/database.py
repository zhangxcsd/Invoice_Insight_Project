"""Legacy database shim.

The canonical implementation lives in `vat_audit_pipeline.utils.database`.
This module is kept for backward compatibility with the historical import path
`utils.database`.
"""

from __future__ import annotations

from vat_audit_pipeline.utils.database import (  # noqa: F401
    DAOBase,
    DatabaseConnection,
    DatabaseConnectionError,
    DatabaseQueryError,
    LedgerDAO,
    OADSAnalyticsDAO,
    ODSDetailDAO,
    ODSHeaderDAO,
    QueryResult,
    SQLInjectionError,
    connect_sqlite,
)

__all__ = [
    "connect_sqlite",
    "QueryResult",
    "DatabaseConnection",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "SQLInjectionError",
    "DAOBase",
    "ODSDetailDAO",
    "ODSHeaderDAO",
    "LedgerDAO",
    "OADSAnalyticsDAO",
]
