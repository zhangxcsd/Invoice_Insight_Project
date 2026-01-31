"""Legacy compatibility shim.

The canonical implementation lives in `vat_audit_pipeline.utils.logging`.
This module re-exports the public symbols for older import paths.
"""

from vat_audit_pipeline.utils.logging import (  # noqa: F401
    MemoryMonitor,
    PerformanceTimer,
    ProgressLogger,
    QueueStatistics,
    _debug_var,
    _progress,
    create_progress_bar,
    logger,
)

__all__ = [
    "logger",
    "ProgressLogger",
    "_progress",
    "_debug_var",
    "create_progress_bar",
    "PerformanceTimer",
    "MemoryMonitor",
    "QueueStatistics",
]
