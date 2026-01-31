"""Helper functions and dataclasses for sheet processing.

This module is the canonical implementation. The legacy module
`utils.sheet_processing` re-exports symbols from here for compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

import pandas as pd


@dataclass
class PipelineSettings:
    """集中所有运行时设置，避免全局变量散落。

    此对象通过依赖注入传递给 worker 和辅助函数，提高可测试性和参数清晰度。
    """

    business_tag: str = "VAT_INV"
    input_dir: str = "Source_Data"
    database_dir: str = "Database"
    output_dir: str = "Outputs"
    debug_mode: bool = False

    enable_parallel: bool = True
    worker_count: Any = "auto"  # str or int

    csv_chunk_size: int = 10000
    stream_chunk_size: int = 50000
    stream_chunk_dynamic: bool = True
    stream_chunk_memory_percent: float = 0.1

    memory_threshold_percent: int = 80
    stream_switch_threshold_percent: int = 75
    large_file_streaming_mb: int = 100

    io_throttle_enabled: bool = True
    io_throttle_busy_percent: int = 75
    io_throttle_reduce_factor: float = 0.5
    io_throttle_min_workers: int = 1

    max_failure_samples: int = 100
    tax_text_to_zero: bool = True

    config: Optional[Any] = None

    @classmethod
    def from_config(cls, config_obj: Any) -> "PipelineSettings":
        """从 config_manager 对象构建 PipelineSettings。"""

        settings = cls()

        try:
            settings.business_tag = config_obj.business_tag
            settings.input_dir = config_obj.input_dir
            settings.database_dir = config_obj.database_dir
            settings.output_dir = config_obj.output_dir
            settings.debug_mode = config_obj.debug_enabled

            settings.enable_parallel = config_obj.parallel_enabled
            settings.worker_count = config_obj.worker_count

            settings.csv_chunk_size = config_obj.csv_chunk_size
            settings.stream_chunk_size = config_obj.stream_chunk_size

            mem_mon = config_obj.get("performance", "memory_monitoring", default={})
            if isinstance(mem_mon, dict):
                settings.memory_threshold_percent = mem_mon.get("memory_threshold_percent", 80)
                settings.stream_switch_threshold_percent = mem_mon.get("stream_switch_threshold_percent", 75)
                settings.large_file_streaming_mb = mem_mon.get("large_file_streaming_mb", 100)
                settings.stream_chunk_dynamic = mem_mon.get("enabled", True)

            io_throttle = config_obj.get("performance", "io_throttle", default={})
            if isinstance(io_throttle, dict):
                settings.io_throttle_enabled = io_throttle.get("enabled", True)
                settings.io_throttle_busy_percent = io_throttle.get("busy_threshold_percent", 75)
                settings.io_throttle_reduce_factor = io_throttle.get("reduce_factor", 0.5)
                settings.io_throttle_min_workers = io_throttle.get("min_workers", 1)

            settings.max_failure_samples = config_obj.max_failure_samples
            settings.tax_text_to_zero = config_obj.tax_text_to_zero

            settings.config = config_obj
        except Exception as e:
            import logging

            logger = logging.getLogger("vat_audit")
            logger.warning(f"从 config 对象构建 PipelineSettings 时失败，使用默认值: {e}")

        return settings

    def get_database_path(self, base_dir: str) -> str:
        """获取数据库文件完整路径。"""

        import os

        db_dir = os.path.join(base_dir, self.database_dir)
        return os.path.join(db_dir, f"{self.business_tag}_Audit_Repo.db")


@dataclass
class SheetProcessingContext:
    """Context for processing a single sheet within a file."""

    file_path: str
    file_name: str
    sheet_name: str
    process_time: str
    use_streaming: bool
    use_queue: Optional[Any]
    use_csv_fallback: bool
    temp_dir: str
    settings: PipelineSettings


@dataclass
class SheetTypeMapping:
    """Mapping of sheet name -> (target_table, target_columns, classification)."""

    sheet_type: str
    target_table: str
    target_columns: list
    classification: str
    table_prefix: str
    extract_keys: bool = False


def get_sheet_handler(
    sheet_name: str,
    meta: dict,
    detail_columns: list,
    header_columns: list,
    summary_columns: list,
    special_columns: dict,
    business_tag: str,
) -> Optional[SheetTypeMapping]:
    """根据 sheet 名和 meta 信息，返回对应的处理策略。"""

    if sheet_name in meta.get("special_sheets", {}):
        suffix = meta["special_sheets"][sheet_name]
        target_cols = special_columns.get(suffix, [])
        return SheetTypeMapping(
            sheet_type=f"special_{suffix.lower()}",
            target_table=f"ODS_{business_tag}_SPECIAL_{suffix}",
            target_columns=target_cols,
            classification=f"special_{suffix.lower()}",
            table_prefix=f"{suffix}__",
        )

    if sheet_name in meta.get("summary_sheets", []):
        return SheetTypeMapping(
            sheet_type="summary",
            target_table=f"ODS_{business_tag}_DETAIL",
            target_columns=summary_columns,
            classification="summary",
            table_prefix="DETAIL__",
            extract_keys=True,
        )

    if sheet_name in meta.get("detail_sheets", []):
        return SheetTypeMapping(
            sheet_type="detail",
            target_table=f"ODS_{business_tag}_TEMP_TRANSIT",
            target_columns=detail_columns,
            classification="detail",
            table_prefix="TEMP_TRANSIT__",
        )

    if sheet_name in meta.get("header_sheets", []):
        return SheetTypeMapping(
            sheet_type="header",
            target_table=f"ODS_{business_tag}_HEADER",
            target_columns=header_columns,
            classification="header",
            table_prefix="HEADER__",
        )

    return None


def normalize_sheet_dataframe(
    df: pd.DataFrame,
    sheet_name: str,
    file_name: str,
    process_time: str,
    target_columns: list,
    cast_fn,
    cast_stats: list,
    cast_failures: list,
    errors: list,
    extract_year: bool = True,
) -> Tuple[pd.DataFrame, int]:
    """规范化一个 DataFrame：类型化、添加审计列、重新索引、提取年份。"""

    try:
        df = cast_fn(df, file_name, sheet_name, cast_stats, cast_failures)
    except Exception as e:
        errors.append(
            {
                "file": file_name,
                "sheet": sheet_name,
                "stage": "cast",
                "error_type": type(e).__name__,
                "message": str(e),
            }
        )
        raise

    df["AUDIT_SRC_FILE"] = file_name
    df["AUDIT_IMPORT_TIME"] = process_time

    if extract_year and "开票日期" in df.columns:
        df["开票年份"] = df["开票日期"].astype(str).str[:4]
    else:
        df["开票年份"] = None

    df = df.reindex(columns=list(target_columns))

    return df, len(df)


def write_to_csv_or_queue(
    df: pd.DataFrame,
    target_table: str,
    temp_csv_path: str,
    queue_obj: Optional[Any],
    use_csv_fallback: bool,
    queue_timeout: float = 5.0,
) -> Tuple[bool, str]:
    """尝试写入 DataFrame 到队列，失败则回退到 CSV。"""

    if queue_obj is None or use_csv_fallback:
        df.to_csv(temp_csv_path, index=False, encoding="utf-8-sig")
        return False, f"写入 CSV: {temp_csv_path}"

    try:
        queue_obj.put((target_table, df), timeout=queue_timeout)
        return True, f"入队成功: {target_table}"
    except Exception as e:
        df.to_csv(temp_csv_path, index=False, encoding="utf-8-sig")
        return False, f"队列失败，回退到 CSV: {temp_csv_path} ({e})"


__all__ = [
    "PipelineSettings",
    "SheetProcessingContext",
    "SheetTypeMapping",
    "get_sheet_handler",
    "normalize_sheet_dataframe",
    "write_to_csv_or_queue",
]
