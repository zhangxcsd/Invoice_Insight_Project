"""Logging utilities for the package.

This module is the canonical implementation. The legacy module
`utils.logging_utils` re-exports symbols from here for compatibility.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pandas as pd
from tqdm import tqdm

logger = logging.getLogger("vat_audit")


class ProgressLogger:
    """Simple progress helper that can optionally back tqdm."""

    def __init__(self, total: int, desc: str = "处理中", use_tqdm: bool = False):
        self.total = total
        self.desc = desc
        self.current = 0
        # 检查是否在 GUI 环境中运行，如果是则禁用 tqdm
        import os
        tqdm_disabled = os.environ.get('TQDM_DISABLE', '0') == '1'
        self.use_tqdm = use_tqdm and total is not None and total > 0 and not tqdm_disabled
        self.pbar = None
        if self.use_tqdm:
            self.pbar = tqdm(total=total, desc=desc, unit="items", ncols=100, disable=False)

    def update(self, n: int = 1, msg: Optional[str] = None):
        self.current += n
        if msg:
            if self.use_tqdm:
                self.pbar.write(msg)
            else:
                logger.info(msg)
        if self.use_tqdm:
            self.pbar.update(n)

    def set_description(self, desc: str):
        if self.use_tqdm:
            self.pbar.set_description(desc)
        self.desc = desc

    def close(self):
        if self.use_tqdm and self.pbar:
            self.pbar.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _progress(msg: str):
    """Lightweight progress logger; flushes handlers when possible."""

    logger.info(msg)
    for h in logger.handlers:
        try:
            if hasattr(h, "flush"):
                h.flush()
        except Exception:
            pass


def _debug_var(name, value, prefix: str = ""):
    """Debug-print variable summaries when DEBUG is enabled."""

    if not logger.isEnabledFor(logging.DEBUG):
        return
    if isinstance(value, (list, tuple, set)):
        logger.debug(
            f"{prefix}[DEBUG] {name}: length={len(value)}, head={list(value)[:3]}{'...' if len(value) > 3 else ''}"
        )
    elif isinstance(value, dict):
        keys = list(value.keys())
        logger.debug(f"{prefix}[DEBUG] {name}: length={len(value)}, keys={keys[:5]}{'...' if len(keys) > 5 else ''}")
    elif isinstance(value, pd.DataFrame):
        logger.debug(f"{prefix}[DEBUG] {name}: shape={value.shape}, cols={list(value.columns)}")
    else:
        logger.debug(f"{prefix}[DEBUG] {name}={value}")


def create_progress_bar(total: int, desc: str = "处理中"):
    if total is None or total <= 0:
        return None
    # 在 GUI 模式下不使用 tqdm（通过环境变量检测）
    import os
    use_tqdm = os.environ.get('TQDM_DISABLE', '0') != '1'
    return ProgressLogger(total=total, desc=desc, use_tqdm=use_tqdm)


class PerformanceTimer:
    """Context timer for performance logging."""

    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.elapsed_seconds = None

    def __enter__(self):
        self.start_time = datetime.now()
        return self

    def __exit__(self, *args):
        self.end_time = datetime.now()
        self.elapsed_seconds = (self.end_time - self.start_time).total_seconds()

    def get_elapsed(self) -> float:
        if self.elapsed_seconds is not None:
            return self.elapsed_seconds
        if self.start_time is not None:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0

    def log(self, level: str = "info"):
        msg = f"⏱️  {self.name}: {self.get_elapsed():.2f}s"
        getattr(logger, level)(msg)
        return msg


class MemoryMonitor:
    """Lightweight process memory tracker."""

    def __init__(self):
        self.initial_mb = None
        self.peak_mb = None
        self.final_mb = None
        self.stream_triggered = False
        self.stream_trigger_count = 0

    def start(self):
        try:
            import psutil

            p = psutil.Process()
            self.initial_mb = p.memory_info().rss / (1024 * 1024)
        except Exception:
            pass

    def update_peak(self):
        try:
            import psutil

            p = psutil.Process()
            current_mb = p.memory_info().rss / (1024 * 1024)
            if self.peak_mb is None or current_mb > self.peak_mb:
                self.peak_mb = current_mb
        except Exception:
            pass

    def end(self):
        try:
            import psutil

            p = psutil.Process()
            self.final_mb = p.memory_info().rss / (1024 * 1024)
        except Exception:
            pass

    def log(self):
        parts = []
        if self.initial_mb is not None:
            parts.append(f"初始: {self.initial_mb:.0f}MB")
        if self.peak_mb is not None:
            parts.append(f"峰值: {self.peak_mb:.0f}MB")
        if self.final_mb is not None:
            parts.append(f"最终: {self.final_mb:.0f}MB")
        if parts:
            msg = f"📊 内存统计: {' | '.join(parts)}"
            logger.info(msg)
            return msg
        return ""

    def get_memory_utilization_percent(self) -> float:
        try:
            import psutil

            total = psutil.virtual_memory().total / (1024 * 1024)
            current = psutil.Process().memory_info().rss / (1024 * 1024)
            return (current / total) * 100 if total > 0 else 0
        except Exception:
            return 0.0

    def get_available_memory_percent(self) -> float:
        try:
            import psutil

            vm = psutil.virtual_memory()
            total_mb = vm.total / (1024 * 1024)
            available_mb = vm.available / (1024 * 1024)
            return (available_mb / total_mb) * 100 if total_mb > 0 else 0
        except Exception:
            return 0.0

    def should_trigger_streaming(self, threshold_percent: int = 75) -> bool:
        try:
            import psutil

            system_memory_percent = psutil.virtual_memory().percent
            if system_memory_percent >= threshold_percent:
                self.stream_triggered = True
                self.stream_trigger_count += 1
                return True
            return False
        except Exception:
            return False

    def check_should_stream_for_file(self, file_size_mb: float, memory_threshold_mb: float = None) -> bool:
        try:
            import psutil

            available_mb = psutil.virtual_memory().available / (1024 * 1024)
            if file_size_mb > available_mb * 0.5:
                return True
            if psutil.virtual_memory().percent > 80:
                return True
            return False
        except Exception:
            return False

    def get_statistics(self):
        return {
            "initial_mb": self.initial_mb,
            "peak_mb": self.peak_mb,
            "final_mb": self.final_mb,
            "current_utilization_percent": self.get_memory_utilization_percent(),
            "available_memory_percent": self.get_available_memory_percent(),
        }


class QueueStatistics:
    """Queue accounting helper for parallel import."""

    def __init__(self):
        self.dataframes_queued = 0
        self.dataframes_consumed = 0
        self.queue_timeouts = 0
        self.queue_max_depth = 0
        self.csv_fallbacks = 0

    def log(self):
        msg = (
            "📈 队列统计: 入队"
            f"{self.dataframes_queued} | 消费{self.dataframes_consumed} | 超时{self.queue_timeouts} | "
            f"最大深度{self.queue_max_depth} | CSV回退{self.csv_fallbacks}"
        )
        logger.info(msg)
        return msg
