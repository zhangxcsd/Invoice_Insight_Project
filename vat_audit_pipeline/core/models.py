"""Shared data models and constants for the VAT audit pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    import pandas as pd


# Audit tracking columns
AUDIT_SRC_FILE_COL = "AUDIT_SRC_FILE"
AUDIT_IMPORT_TIME_COL = "AUDIT_IMPORT_TIME"
DEDUP_CAPTURE_TIME_COL = "DEDUP_CAPTURE_TIME"
INVOICE_YEAR_COL = "开票年份"

# Invoice key fields
INVOICE_CODE_COL = "发票代码"
INVOICE_NUMBER_COL = "发票号码"
ETICKET_NUMBER_COL = "数电发票号码"
INVOICE_DATE_COL = "开票日期"
INVOICE_KEY_COLS = [INVOICE_CODE_COL, INVOICE_NUMBER_COL, ETICKET_NUMBER_COL]

# Detail/header columns required for downstream exports
DETAIL_COLS_NEEDED = [
    INVOICE_CODE_COL,
    INVOICE_NUMBER_COL,
    ETICKET_NUMBER_COL,
    "销方识别号",
    "销方名称",
    "购方识别号",
    "购买方名称",
    INVOICE_DATE_COL,
    "税收分类编码",
    "特定业务类型",
    "货物或应税劳务名称",
    "规格型号",
    "单位",
    "数量",
    "单价",
    "金额",
    "税率",
    "税率_数值",
    "税额",
    "价税合计",
    "发票来源",
    "发票票种",
    "发票状态",
    "是否正数发票",
    "发票风险等级",
    "开票人",
    "备注",
]

HEADER_COLS_NEEDED = [
    INVOICE_CODE_COL,
    INVOICE_NUMBER_COL,
    ETICKET_NUMBER_COL,
    "销方识别号",
    "销方名称",
    "购方识别号",
    "购买方名称",
    INVOICE_DATE_COL,
    "金额",
    "税率",
    "税率_数值",
    "税额",
    "价税合计",
    "发票来源",
    "发票票种",
    "发票状态",
    "是否正数发票",
    "发票风险等级",
    "开票人",
    "备注",
]

# Dedup subsets
DETAIL_DEDUP_COLS = [
    INVOICE_CODE_COL,
    INVOICE_NUMBER_COL,
    ETICKET_NUMBER_COL,
    INVOICE_DATE_COL,
    "货物或应税劳务名称",
    "数量",
    "单价",
    "金额",
    "税额",
    "发票票种",
    "发票状态",
    "开票人",
    "备注",
]
HEADER_DEDUP_COLS = [INVOICE_CODE_COL, INVOICE_NUMBER_COL, ETICKET_NUMBER_COL]

# File handling defaults
CSV_ENCODING = "utf-8-sig"
TEMP_FILE_PREFIX = "tmp_imports"
FILE_SPLIT_DELIMITER = "__"
DEFAULT_CSV_CHUNK_SIZE = 1000
DEFAULT_STREAM_CHUNK_SIZE = 10000
STREAM_FETCH_SIZE = 500

# Output manifest prefixes
MANIFEST_PREFIX = "ods_sheet_manifest"
CAST_STATS_PREFIX = "ods_type_cast_manifest"
CAST_FAILURES_PREFIX = "ods_type_cast_failures"
ERROR_LOG_PREFIX = "process_error_logs"
IMPORT_SUMMARY_PREFIX = "ods_import_summary"
LEDGER_MANIFEST_PREFIX = "invoice_ledgers_manifest"

# Logging defaults
LOG_TO_FILE = True
LOG_FILE_NAME = "vat_audit.log"
LOG_LEVEL = "INFO"
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 5


@dataclass
class DataFile:
    path: Path
    metadata: dict[str, Any] | None = None


@dataclass
class RuntimeContext:
    """Resolved runtime configuration shared across processors."""

    business_tag: str
    base_dir: Path
    input_dir: Path
    db_dir: Path
    output_dir: Path
    db_path: Path
    enable_parallel_import: bool
    worker_count: int
    csv_chunk_size: int
    stream_chunk_size: int
    max_failure_sample_per_col: int
    tax_text_to_zero: bool
    debug_mode: bool = False


@dataclass
class InvoiceRecord:
    """Optional typed representation for a single invoice row.

    This is an additive model intended for downstream extensions and tests.
    The pipeline core still primarily operates on pandas DataFrames.
    """

    invoice_code: Optional[str] = None
    invoice_number: Optional[str] = None
    eticket_number: Optional[str] = None
    invoice_date: Any | None = None
    amount: Optional[float] = None
    tax_rate: Optional[float] = None

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "InvoiceRecord":
        return cls(
            invoice_code=row.get(INVOICE_CODE_COL),
            invoice_number=row.get(INVOICE_NUMBER_COL),
            eticket_number=row.get(ETICKET_NUMBER_COL),
            invoice_date=row.get(INVOICE_DATE_COL),
            amount=row.get("金额"),
            tax_rate=row.get("税率_数值", row.get("税率")),
        )

    @classmethod
    def from_dataframe_row(cls, df_row: Any) -> "InvoiceRecord":
        """Best-effort conversion from a pandas Series-like row."""

        try:
            mapping = df_row.to_dict()
        except Exception:
            mapping = dict(df_row) if df_row is not None else {}
        return cls.from_mapping(mapping)


@dataclass
class ProcessingResult:
    """Standard wrapper for processor stage results."""

    success: bool
    data: "pd.DataFrame | None" = None
    metadata: dict[str, Any] | None = None
    errors: list[dict[str, Any]] | None = None
    stats: dict[str, Any] | None = None