"""File and path helpers used across the pipeline."""

from __future__ import annotations

import atexit
import multiprocessing
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from vat_audit_pipeline.core import models


def list_files(root: str | Path, patterns: Iterable[str]) -> list[Path]:
    root_path = Path(root)
    files: list[Path] = []
    for pattern in patterns:
        files.extend(root_path.glob(pattern))
    return sorted(files)


def format_timestamp_for_filename(timestamp: str) -> str:
    return timestamp.replace(":", "-").replace(" ", "_")


def generate_manifest_filename(prefix: str, timestamp: str) -> str:
    formatted_time = format_timestamp_for_filename(timestamp)
    return f"{prefix}_{formatted_time}.csv"


def add_audit_columns(df: pd.DataFrame, source_file: str, import_time: str) -> pd.DataFrame:
    df[models.AUDIT_SRC_FILE_COL] = source_file
    df[models.AUDIT_IMPORT_TIME_COL] = import_time
    return df


def add_invoice_year_column(df: pd.DataFrame) -> pd.DataFrame:
    if models.INVOICE_DATE_COL in df.columns:
        df[models.INVOICE_YEAR_COL] = df[models.INVOICE_DATE_COL].astype(str).str[:4]
    else:
        df[models.INVOICE_YEAR_COL] = None
    return df


def select_invoice_key_columns(df: pd.DataFrame) -> List[str]:
    return [col for col in models.INVOICE_KEY_COLS if col in df.columns]


def add_dedup_capture_time(df: pd.DataFrame, capture_time: str) -> pd.DataFrame:
    if models.AUDIT_IMPORT_TIME_COL not in df.columns:
        df[models.AUDIT_IMPORT_TIME_COL] = None
    df[models.DEDUP_CAPTURE_TIME_COL] = capture_time
    return df


def save_dataframe_to_csv(df: pd.DataFrame, output_path: str) -> None:
    df.to_csv(output_path, index=False, encoding=models.CSV_ENCODING)


def filter_dataframe_columns(df: pd.DataFrame, target_columns: List[str]) -> pd.DataFrame:
    return df.reindex(columns=list(target_columns))


def ensure_audit_import_time_column(df: pd.DataFrame, default_time: str) -> pd.DataFrame:
    if models.AUDIT_IMPORT_TIME_COL not in df.columns:
        df[models.AUDIT_IMPORT_TIME_COL] = default_time
    return df


def ensure_worker_temp_dir(temp_root: str) -> str:
    os.makedirs(temp_root, exist_ok=True)
    worker_dir = os.path.join(temp_root, f"worker_{multiprocessing.current_process().pid}")
    os.makedirs(worker_dir, exist_ok=True)
    return worker_dir


def cleanup_temp_files(path: str) -> None:
    if path and os.path.exists(path):
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass


def cleanup_old_temp_files(base_dir: Optional[str], max_age_hours: int = 24) -> None:
    if not base_dir or not os.path.exists(base_dir):
        return
    cutoff = datetime.now().timestamp() - max_age_hours * 3600
    for name in os.listdir(base_dir):
        full_path = os.path.join(base_dir, name)
        try:
            if os.path.isdir(full_path) and os.path.getmtime(full_path) < cutoff:
                shutil.rmtree(full_path, ignore_errors=True)
        except Exception:
            continue


def register_cleanup(current_temp_dir: str) -> None:
    def _cleanup():
        if current_temp_dir and os.path.exists(current_temp_dir):
            cleanup_temp_files(current_temp_dir)

    atexit.register(_cleanup)