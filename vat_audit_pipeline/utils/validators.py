"""Validation and error reporting helpers."""

from __future__ import annotations

import json
import os
from functools import wraps
from typing import Dict, List, Optional, Tuple

import pandas as pd

from vat_audit_pipeline.core import models
from vat_audit_pipeline.utils.file_handlers import format_timestamp_for_filename, save_dataframe_to_csv
from vat_audit_pipeline.utils.logging import _progress


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_config(func):
    """Decorator to ensure a config object is present and minimally valid.

    This is intentionally lightweight and works with either:
    - a bound method (expects `self.config`), or
    - a function receiving `config=` kwarg.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        config = kwargs.get("config")
        if config is None and args:
            config = getattr(args[0], "config", None)
        if not config:
            raise ValueError("配置未加载")

        for attr in ("input_dir", "database_dir", "output_dir"):
            if getattr(config, attr, None) in (None, ""):
                raise ValueError(f"缺少必要配置: {attr}")

        return func(*args, **kwargs)

    return wrapper


def validate_input_file(file_path: str, max_file_mb: float) -> Tuple[bool, str]:
    if not os.path.isfile(file_path):
        return False, "not a file"
    fname = os.path.basename(file_path)
    if fname.startswith("~$"):
        return False, "temporary excel lock file"
    if not fname.lower().endswith((".xls", ".xlsx", ".xlsm")):
        return False, "unsupported extension"
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if max_file_mb and size_mb > max_file_mb:
            return False, f"file too large ({size_mb:.1f}MB > {max_file_mb}MB limit)"
    except Exception:
        return False, "size check failed"
    return True, "ok"


def suggest_remedy_for_error(error_type: Optional[str], message: Optional[str] = None) -> str:
    mapping = {
        "FileNotFoundError": "检查文件路径是否正确并存在（确认文件名和目录）。",
        "PermissionError": "检查该文件/目录的读写权限或是否被其他进程锁定。",
        "MemoryError": "数据量可能过大，考虑增加内存/使用流式处理或减小 chunk 大小。",
        "ValueError": "数据格式错误或类型不匹配，请检查字段值及格式。",
        "KeyError": "缺少预期列，检查源表头是否包含必要字段。",
        "UnicodeDecodeError": "文件编码不匹配，尝试以 UTF-8/GBK 打开或检查文件来源。",
        "OSError": "操作系统级错误，请检查路径、权限和磁盘空间。",
        "TimeoutError": "操作超时，重试或增大超时设置。",
        "InvalidFileException": "Excel文件可能已损坏或格式不正确，请检查文件是否可以正常打开。",
        "InvalidFileFormatException": "Excel文件格式不正确或已损坏，请验证文件完整性。",
        "FileLockedException": "文件被其他程序锁定，请关闭Excel应用程序或其他可能使用该文件的程序。",
    }
    if not error_type:
        return ""
    suggestion = mapping.get(error_type, "")
    if not suggestion and message:
        msg = str(message)
        if "permission" in msg.lower():
            suggestion = mapping.get("PermissionError")
        elif "not found" in msg.lower():
            suggestion = mapping.get("FileNotFoundError")
        elif "invalid file" in msg.lower() or "corrupt" in msg.lower():
            suggestion = mapping.get("InvalidFileException")
        elif "lock" in msg.lower() or "access denied" in msg.lower():
            suggestion = mapping.get("FileLockedException")
    return suggestion or ""


def write_error_logs(
    error_logs: List[Dict],
    process_time: str,
    output_dir: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    if not error_logs:
        return None, None
    output_dir = output_dir or os.path.join(os.getcwd(), "Outputs")
    enriched = []
    for e in error_logs:
        e2 = dict(e)
        if "suggestion" not in e2 or not e2.get("suggestion"):
            e2["suggestion"] = suggest_remedy_for_error(e2.get("error_type"), e2.get("message"))
        enriched.append(e2)
    err_df = pd.DataFrame(enriched)
    basefn = f"{models.ERROR_LOG_PREFIX}_{format_timestamp_for_filename(process_time)}"
    csv_path = os.path.join(output_dir, f"{basefn}.csv")
    json_path = os.path.join(output_dir, f"{basefn}.json")
    os.makedirs(output_dir, exist_ok=True)
    save_dataframe_to_csv(err_df, csv_path)
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(enriched, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    _progress(f"导出结构化错误日志: {csv_path} & {json_path} (共 {len(enriched)} 条记录)")
    return csv_path, json_path