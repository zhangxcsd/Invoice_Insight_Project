"""Parallel execution helpers and worker sizing utilities."""

from __future__ import annotations

import multiprocessing
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable, Optional, TypeVar, Union

from vat_audit_pipeline.core import models


T = TypeVar("T")
R = TypeVar("R")


def map_concurrent(fn: Callable[[T], R], items: Iterable[T], max_workers: int = 4) -> list[R]:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(fn, items))


def calculate_optimal_workers(
    excel_files: list[str],
    configured_workers: Optional[Union[int, str]],
    disk_busy_percent: Optional[float] = None,
    io_threshold: float = 75,
    reduce_factor: float = 0.5,
    min_workers: int = 1,
) -> int:
    if configured_workers is None or (isinstance(configured_workers, str) and str(configured_workers).lower() == "auto"):
        target = max(1, multiprocessing.cpu_count() - 1)
    else:
        try:
            target = int(configured_workers)
        except Exception:
            target = max(1, multiprocessing.cpu_count() - 1)
    if excel_files:
        target = min(target, len(excel_files))

    if disk_busy_percent is not None and disk_busy_percent >= io_threshold:
        reduced = max(min_workers, int(target * reduce_factor))
        target = reduced

    return max(1, target)


def measure_disk_busy_percent(sample_seconds: float = 0.25) -> Optional[float]:
    try:
        import psutil

        io1 = psutil.disk_io_counters()
        if not io1:
            return None
        time.sleep(sample_seconds)
        io2 = psutil.disk_io_counters()
        if not io2:
            return None

        def _busy_delta(obj1, obj2):
            if hasattr(obj1, "busy_time") and hasattr(obj2, "busy_time"):
                return obj2.busy_time - obj1.busy_time
            if hasattr(obj1, "read_time") and hasattr(obj2, "read_time") and hasattr(obj1, "write_time") and hasattr(obj2, "write_time"):
                return (obj2.read_time - obj1.read_time) + (obj2.write_time - obj1.write_time)
            return None

        delta_ms = _busy_delta(io1, io2)
        if delta_ms is None:
            return None
        busy_pct = (delta_ms / (sample_seconds * 1000)) * 100
        return max(0.0, min(100.0, busy_pct))
    except Exception:
        return None