"""Context managers to reduce global state during processing."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Optional

from vat_audit_pipeline.utils.database import connect_sqlite


@dataclass
class ProcessingContext:
    """Holds shared resources (e.g., DB connection) for a pipeline run."""

    db_path: str
    config: Optional[Any] = None
    conn: sqlite3.Connection | None = None

    def __enter__(self) -> "ProcessingContext":
        self.conn = connect_sqlite(self.db_path)
        self._apply_pragmas()
        return self

    def _apply_pragmas(self) -> None:
        if not self.conn:
            return

        journal_mode = "WAL"
        synchronous = "NORMAL"

        if self.config and hasattr(self.config, "get"):
            journal_mode = str(self.config.get("database", "journal_mode", default=journal_mode))
            synchronous = str(self.config.get("database", "synchronous", default=synchronous))

        try:
            self.conn.execute(f"PRAGMA journal_mode={journal_mode}")
        except Exception:
            pass
        try:
            self.conn.execute(f"PRAGMA synchronous={synchronous}")
        except Exception:
            pass

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        self.conn = None
