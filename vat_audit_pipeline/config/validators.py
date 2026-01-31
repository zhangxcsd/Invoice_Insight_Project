"""Validation helpers for configuration objects."""

from __future__ import annotations

from typing import Iterable


def validate_app_settings(settings) -> None:
    errors = []
    if settings.default_max_file_mb < 10:
        errors.append(
            f"default_max_file_mb 必须 >= 10，当前值: {settings.default_max_file_mb}MB（过小会拒绝大多数正常文件）"
        )
    if errors:
        error_msg = "应用配置参数校验失败：\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)


def validate_pipeline_config(settings) -> None:
    errors = []
    if settings.worker_count is not None and settings.worker_count < 1:
        errors.append(f"worker_count 必须 >= 1，当前值: {settings.worker_count}")
    if settings.csv_chunk_size < 100:
        errors.append(f"csv_chunk_size 必须 >= 100，当前值: {settings.csv_chunk_size}")
    if settings.stream_chunk_size < 1000:
        errors.append(f"stream_chunk_size 必须 >= 1000，当前值: {settings.stream_chunk_size}")
    if hasattr(settings, "stream_chunk_memory_percent"):
        try:
            v = float(settings.stream_chunk_memory_percent)
            if not (0 < v <= 1):
                errors.append(f"stream_chunk_memory_percent 必须在 (0, 1]，当前值: {settings.stream_chunk_memory_percent}")
        except Exception:
            errors.append(f"stream_chunk_memory_percent 非法值: {settings.stream_chunk_memory_percent}")

    for key in ("memory_threshold_percent", "stream_switch_threshold_percent", "io_busy_threshold_percent"):
        if hasattr(settings, key):
            try:
                v = float(getattr(settings, key))
                if not (0 < v <= 100):
                    errors.append(f"{key} 必须在 (0, 100]，当前值: {getattr(settings, key)}")
            except Exception:
                errors.append(f"{key} 非法值: {getattr(settings, key)}")

    for key in ("large_file_streaming_mb",):
        if hasattr(settings, key):
            try:
                v = float(getattr(settings, key))
                if v <= 0:
                    errors.append(f"{key} 必须为正数，当前值: {getattr(settings, key)}")
            except Exception:
                errors.append(f"{key} 非法值: {getattr(settings, key)}")

    if hasattr(settings, "io_reduce_factor"):
        try:
            v = float(settings.io_reduce_factor)
            if not (0 < v <= 1):
                errors.append(f"io_reduce_factor 必须在 (0, 1]，当前值: {settings.io_reduce_factor}")
        except Exception:
            errors.append(f"io_reduce_factor 非法值: {settings.io_reduce_factor}")

    if hasattr(settings, "io_min_workers"):
        try:
            v = int(settings.io_min_workers)
            if v < 1:
                errors.append(f"io_min_workers 必须 >= 1，当前值: {settings.io_min_workers}")
        except Exception:
            errors.append(f"io_min_workers 非法值: {settings.io_min_workers}")
    if settings.max_failure_samples < 1:
        errors.append(f"max_failure_samples 必须 >= 1，当前值: {settings.max_failure_samples}")
    if errors:
        error_msg = "配置参数校验失败：\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)


def validate_required_keys(cfg, required: Iterable[str]) -> None:
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")