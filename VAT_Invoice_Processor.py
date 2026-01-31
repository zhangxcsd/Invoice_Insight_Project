"""增值税发票审计系统 - 兼容性门面模块

=== 业务背景 ===
本系统用于处理和审计企业的增值税发票数据，主要应用场景包括：
1. 进项发票与销项发票的批量导入和清洗
2. 发票数据的去重、规范化和质量检查
3. 发票台账的按年分层构建（支持多年份数据）
4. 异常发票的识别和报告（如税率异常、金额异常等）

数据来源：通常从税务系统导出的 Excel 文件（.xlsx/.xls），包含：
  - 发票明细表（detail）：商品/服务级别的行项目
  - 发票表头表（header）：发票级别的汇总信息
  - 汇总表（summary）：统计汇总数据
  - 特殊表（special）：其他自定义业务表

=== 架构演进 ===
历史版本：单体脚本（~2000行），所有逻辑在一个文件中
当前版本：模块化架构，核心逻辑重构到 `vat_audit_pipeline` 包中

本模块作用：
- 向后兼容层：保持旧脚本/测试的导入路径不变
- 统一入口：将所有执行委托给新的包架构
- 平滑迁移：允许逐步从旧代码迁移到新架构

历史实现已归档至：`归档-20260103/VAT_Invoice_Processor.py`

=== 设计理念 ===
1. **数据分层**：采用ODS→DWD→DIM→DWS→DM→ADS/RPT 架构，明晰责权分离
   各层定位 + 表命名 + 核心表设计：
o	ODS 层：原始明细层，存储未加工的原始发票数据，命名要体现年份、表类型、层，比如 ODS_VAT_INV_2022_HEADER（2022 发票头表）、ODS_VAT_INV_2022_DETAIL（2022 发票明细表），2023 同理，注意用户笔误（2023 的明细表写成了 2022，要注意但不用指错，按用户给的来）。
o	DWD 层：明细层，清洗后的标准化明细数据，整合头表和明细表，命名 DWD_VAT_INV_CLEANED（全量清洗后的发票明细表），核心是标准化字段，处理脏数据。
o	DIM 层：维度层，存储维度数据，比如企业维度（省属企业维度表）、商品品类维度、时间维度，命名 DIM_ENTERPRISE（企业维度）、DIM_GOODS_CATEGORY（商品品类维度）、DIM_TIME（时间维度）。
o	DWS 层：汇总层，按维度汇总的中间数据，比如按企业 + 年月汇总进销数据，按销方 + 日期汇总发票基础数据，命名 DWS_VAT_INV_INOUT_SUMMARY（进销汇总表）、DWS_VAT_INV_SERIAL_BASE（连号基础汇总表）。
o	DM 层：集市层，专门针对两个模型的疑点计算表，命名 DM_VAT_INV_SERIAL_SPLIT（连号发票拆分模型表）、DM_VAT_INV_INOUT_IMBALANCE（进销倒挂模型表），核心是标记疑点、风险等级。
o	ADS/RPT 层：应用 / 报表层，为 PowerBI 可视化准备的宽表，命名 ADS_VAT_INV_AUDIT_SUSPECT（审计疑点汇总宽表），整合两个模型的疑点，方便可视化。


2. **批量处理**：支持多文件并行处理，适应大规模发票数据
   - 可配置的工作进程数（worker_count）
   - 智能的内存和磁盘IO优化

3. **容错机制**：
   - 单个文件失败不影响整体流程
   - 详细的错误日志和诊断信息
   - 自动重试和降级策略

4. **可追溯性**：
   - 每条数据记录来源文件和导入时间
   - 完整的处理日志和审计轨迹
   - 去重时保留所有版本的捕获时间

=== 使用示例 ===
命令行方式：
    python VAT_Invoice_Processor.py
    python -m vat_audit_pipeline.main --input Source_Data --verbose

编程方式：
    from VAT_Invoice_Processor import VATAuditPipeline
    pipeline = VATAuditPipeline()
    pipeline.run()

=== 配置说明 ===
支持 YAML 配置文件（config.yaml）或使用默认值：
  - business_tag: 业务标签（用于表名前缀）
  - input_dir: 输入目录（Excel 文件所在位置）
  - output_dir: 输出目录（日志、报告、清单）
  - database_dir: 数据库目录（SQLite 文件存放位置）
  - parallel_enabled: 是否启用并行处理
  - worker_count: 并行工作进程数

详细配置项参见：README.md 和 config_default.yaml
"""

from __future__ import annotations

import atexit
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from vat_audit_pipeline.config.settings import AppSettings, PipelineSettings
from vat_audit_pipeline.config.validators import validate_app_settings, validate_pipeline_config
from vat_audit_pipeline.core import models
from vat_audit_pipeline.core.models import RuntimeContext
from vat_audit_pipeline.core.pipeline import VATAuditPipeline
from vat_audit_pipeline.core.processors.ods_processor import process_file_worker as _process_file_worker_new
from vat_audit_pipeline.main import main
from vat_audit_pipeline.utils.file_handlers import cleanup_old_temp_files as _cleanup_old_temp_files
from vat_audit_pipeline.utils.file_handlers import cleanup_temp_files
from vat_audit_pipeline.utils.validators import write_error_logs

from vat_audit_pipeline.utils.normalization import (
    cast_and_record,
    normalize_excel_date_col,
    normalize_numeric_col,
    normalize_tax_rate_col,
)
from vat_audit_pipeline.utils.encoding import detect_encoding, read_csv_with_encoding_detection
from vat_audit_pipeline.utils.logging import ProgressLogger, _debug_var, create_progress_bar


def _is_running_under_pytest() -> bool:
    """检测是否在 pytest 测试环境中运行。
    
    用途：在测试环境中使用单独的日志文件（vat_audit_pytest.log），
         避免与正常运行时的日志文件冲突。
    """
    return ("pytest" in sys.modules) or bool(os.environ.get("PYTEST_CURRENT_TEST"))


def _resolve_base_dir() -> Path:
    """根据运行模式解析根目录，兼容 PyInstaller 冻结后的可执行文件。

    - frozen 模式下（PyInstaller），返回可执行文件所在目录，确保 Source_Data/Outputs/Database
      等目录与 .exe 同级，便于分发和读写。
    - 源码模式下，返回当前文件所在目录。
    """

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


# 项目根目录和输出目录配置
# BASE_DIR: 项目根目录，所有相对路径的基准点
# OUTPUT_DIR: 输出目录，存放日志文件、处理报告、清单文件等
BASE_DIR = _resolve_base_dir()
for _dir_name in ("Outputs", "Source_Data", "Database"):
    os.makedirs(BASE_DIR / _dir_name, exist_ok=True)
OUTPUT_DIR = str(BASE_DIR / "Outputs")


try:
    from config_manager import get_config

    config = get_config()
except Exception:
    config = None

ENABLE_DEBUG = bool(getattr(config, "debug_enabled", False)) if config is not None else False

# Legacy compatibility exports (used by scripts/test_import.py and older tooling)
try:
    ENABLE_PARALLEL_IMPORT = bool(getattr(config, "parallel_enabled", False)) if config is not None else False
except Exception:
    ENABLE_PARALLEL_IMPORT = False

try:
    WORKER_COUNT = int(getattr(config, "worker_count", 1)) if config is not None else 1
except Exception:
    WORKER_COUNT = 1


def _build_legacy_logger() -> Tuple[logging.Logger, str]:
    logger_name = "vat_audit_legacy"
    legacy_logger = logging.getLogger(logger_name)
    legacy_logger.propagate = False

    level = logging.DEBUG if ENABLE_DEBUG else logging.INFO
    legacy_logger.setLevel(level)

    # Avoid duplicating handlers on repeated imports (pytest collection).
    if legacy_logger.handlers:
        log_file = getattr(legacy_logger, "_legacy_log_file", None)
        if isinstance(log_file, str):
            return legacy_logger, log_file

    log_filename = "vat_audit_pytest.log" if _is_running_under_pytest() else models.LOG_FILE_NAME
    log_path = str(Path(OUTPUT_DIR) / log_filename)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=models.LOG_MAX_BYTES,
        backupCount=models.LOG_BACKUP_COUNT,
        encoding="utf-8",
        delay=True,
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    legacy_logger.addHandler(stream_handler)
    legacy_logger.addHandler(file_handler)

    setattr(legacy_logger, "_legacy_log_file", log_path)
    return legacy_logger, log_path


logger, LOG_FILE = _build_legacy_logger()


_CURRENT_TEMP_DIR: Optional[str] = None


def cleanup_old_temp_files(max_age_hours: int = 24) -> None:
    """Legacy wrapper: clean old worker temp dirs under Outputs/tmp_imports."""

    base_dir = str(Path(OUTPUT_DIR) / models.TEMP_FILE_PREFIX)
    _cleanup_old_temp_files(base_dir, max_age_hours=max_age_hours)


def register_cleanup() -> None:
    """在程序退出时注册当前临时目录的清理处理器。

    为了兼容旧测试，这里不要求显式传入 temp dir；运行时若设置了
    `_CURRENT_TEMP_DIR`，退出时会自动清理。
    """

    def _cleanup() -> None:
        if _CURRENT_TEMP_DIR and os.path.exists(_CURRENT_TEMP_DIR):
            cleanup_temp_files(_CURRENT_TEMP_DIR)

    atexit.register(_cleanup)


def _build_runtime_for_legacy_worker(temp_dir_root: str) -> RuntimeContext:
    base_dir = BASE_DIR
    input_dir = base_dir / "Source_Data"
    db_dir = base_dir / "Database"
    output_dir = Path(OUTPUT_DIR)
    db_path = db_dir / "vat_audit.db"

    return RuntimeContext(
        business_tag=getattr(config, "business_tag", "VAT") if config is not None else "VAT",
        base_dir=base_dir,
        input_dir=input_dir,
        db_dir=db_dir,
        output_dir=output_dir,
        db_path=db_path,
        enable_parallel_import=False,
        worker_count=1,
        csv_chunk_size=models.DEFAULT_CSV_CHUNK_SIZE,
        stream_chunk_size=models.DEFAULT_STREAM_CHUNK_SIZE,
        max_failure_sample_per_col=50,
        tax_text_to_zero=True,
        debug_mode=ENABLE_DEBUG,
    )


def process_file_worker(args) -> Dict[str, Any]:
    """Compatibility adapter for legacy worker signature.

    Old tests pass an 8-tuple:
        (file, meta, temp_dir_root, process_time, detail_cols, header_cols, summary_cols, special_cols)

    New worker expects a 12-tuple:
        (runtime, config, tax_text_to_zero, file, meta, temp_dir_root, process_time,
         detail_cols, header_cols, summary_cols, special_cols, stream_chunk_size)
    """

    if not isinstance(args, tuple):
        return _process_file_worker_new(args)

    if len(args) == 12:
        return _process_file_worker_new(args)

    if len(args) != 8:
        raise ValueError(f"Unsupported legacy worker args length: {len(args)}")

    (
        file,
        meta,
        temp_dir_root,
        process_time,
        detail_columns,
        header_columns,
        summary_columns,
        special_columns,
    ) = args

    runtime = _build_runtime_for_legacy_worker(str(temp_dir_root))
    global _CURRENT_TEMP_DIR
    _CURRENT_TEMP_DIR = str(temp_dir_root)

    tax_text_to_zero = True
    try:
        if config is not None and hasattr(config, "get"):
            tax_text_to_zero = bool(config.get("processing", "tax_text_to_zero", default=True))
    except Exception:
        tax_text_to_zero = True

    new_args = (
        runtime,
        config,
        tax_text_to_zero,
        str(file),
        meta,
        str(temp_dir_root),
        process_time,
        detail_columns,
        header_columns,
        summary_columns,
        special_columns,
        runtime.stream_chunk_size,
    )
    return _process_file_worker_new(new_args)


def run_vat_audit_pipeline() -> None:
    """旧版兼容性包装器，供某些脚本使用。"""

    VATAuditPipeline().run()


if __name__ == "__main__":
    main()
