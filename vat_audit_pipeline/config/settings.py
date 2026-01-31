"""Configuration helpers and defaults for the pipeline package."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
from typing import Any, Optional

import yaml

from .validators import validate_app_settings, validate_pipeline_config


@dataclass
class AppSettings:
    """Application-level defaults that should rarely change."""

    default_max_file_mb: float = 500.0


@dataclass
class PipelineSettings:
    """Runtime tunables for the VAT pipeline."""

    business_tag: str = "VAT_INV"
    base_dir: Optional[Path] = None
    input_dir: Optional[str] = None
    database_dir: Optional[str] = None
    output_dir: Optional[str] = None
    parallel_enabled: bool = True
    worker_count: Optional[int] = None
    csv_chunk_size: int = 10000
    stream_chunk_size: int = 50000
    stream_chunk_dynamic: bool = True
    stream_chunk_memory_percent: float = 0.1

    memory_monitoring_enabled: bool = True
    memory_threshold_percent: float = 80
    stream_switch_threshold_percent: float = 75
    large_file_streaming_mb: float = 100

    io_throttle_enabled: bool = True
    io_busy_threshold_percent: float = 75
    io_reduce_factor: float = 0.5
    io_min_workers: int = 1

    max_failure_samples: int = 100
    tax_text_to_zero: bool = True
    debug_enabled: bool = False

    def resolve_paths(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.input_dir = self.input_dir or os.path.join(base_dir, "Source_Data")
        self.database_dir = self.database_dir or os.path.join(base_dir, "Database")
        self.output_dir = self.output_dir or os.path.join(base_dir, "Outputs")

    def resolve_workers(self) -> None:
        if self.worker_count is None:
            import multiprocessing

            self.worker_count = max(1, multiprocessing.cpu_count() - 1)

    def validate_identifier(self) -> None:
        if not isinstance(self.business_tag, str) or not re.match(r"^[A-Za-z0-9_]+$", self.business_tag):
            raise ValueError(f"非法业务标识: {self.business_tag}")


def load_yaml_settings(path: str | Path) -> dict:
    """Load a YAML file into a dictionary (empty dict if missing)."""

    config_path = Path(path)
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_pipeline_settings(config: Any, base_dir: Path) -> PipelineSettings:
    """Construct PipelineSettings from config_manager config object."""

    settings = PipelineSettings()
    if config:
        settings.business_tag = getattr(config, "business_tag", settings.business_tag)
        settings.input_dir = getattr(config, "input_dir", settings.input_dir)
        settings.database_dir = getattr(config, "database_dir", settings.database_dir)
        settings.output_dir = getattr(config, "output_dir", settings.output_dir)
        settings.parallel_enabled = getattr(config, "parallel_enabled", settings.parallel_enabled)
        settings.worker_count = getattr(config, "worker_count", settings.worker_count)
        settings.csv_chunk_size = getattr(config, "csv_chunk_size", settings.csv_chunk_size)
        settings.stream_chunk_size = getattr(config, "stream_chunk_size", settings.stream_chunk_size)
        if hasattr(config, "get"):
            settings.stream_chunk_dynamic = bool(config.get("performance", "stream_chunk_dynamic", default=settings.stream_chunk_dynamic))
            settings.stream_chunk_memory_percent = float(
                config.get("performance", "stream_chunk_memory_percent", default=settings.stream_chunk_memory_percent)
            )

            settings.memory_monitoring_enabled = bool(
                config.get("performance", "memory_monitoring", "enabled", default=settings.memory_monitoring_enabled)
            )
            settings.memory_threshold_percent = float(
                config.get("performance", "memory_monitoring", "memory_threshold_percent", default=settings.memory_threshold_percent)
            )
            settings.stream_switch_threshold_percent = float(
                config.get(
                    "performance",
                    "memory_monitoring",
                    "stream_switch_threshold_percent",
                    default=settings.stream_switch_threshold_percent,
                )
            )
            settings.large_file_streaming_mb = float(
                config.get("performance", "memory_monitoring", "large_file_streaming_mb", default=settings.large_file_streaming_mb)
            )

            settings.io_throttle_enabled = bool(
                config.get("performance", "io_throttle", "enabled", default=settings.io_throttle_enabled)
            )
            settings.io_busy_threshold_percent = float(
                config.get("performance", "io_throttle", "busy_threshold_percent", default=settings.io_busy_threshold_percent)
            )
            settings.io_reduce_factor = float(
                config.get("performance", "io_throttle", "reduce_factor", default=settings.io_reduce_factor)
            )
            settings.io_min_workers = int(
                config.get("performance", "io_throttle", "min_workers", default=settings.io_min_workers)
            )
        settings.max_failure_samples = getattr(config, "max_failure_samples", settings.max_failure_samples)
        settings.tax_text_to_zero = getattr(config, "tax_text_to_zero", settings.tax_text_to_zero)
        settings.debug_enabled = getattr(config, "debug_enabled", settings.debug_enabled)

    settings.validate_identifier()
    settings.resolve_paths(base_dir)
    settings.resolve_workers()
    validate_pipeline_config(settings)
    return settings


def load_app_settings() -> AppSettings:
    """Return validated AppSettings instance."""

    app = AppSettings()
    validate_app_settings(app)
    return app