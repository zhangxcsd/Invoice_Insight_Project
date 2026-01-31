"""增值税审计流水线 - 核心编排模块

=== 模块职责 ===
本模块负责协调整个增值税发票审计流程的执行，从原始 Excel 文件到最终的数据库和报告输出。
这是从原有单体脚本 VAT_Invoice_Processor.py 中提取出的核心流水线逻辑。

=== 处理流程（Pipeline Steps）===
1. **扫描阶段**（Scan Phase）
   - 扫描输入目录下的所有 Excel 文件
   - 读取每个文件的工作表元数据（sheet names, columns）
   - 根据配置识别不同类型的工作表（detail/header/summary/special）
   - 生成文件清单（manifest）供后续处理使用

2. **ODS 层处理**（Operational Data Store）
   - 将 Excel 数据原样导入到临时表 ODS_*_TEMP_TRANSIT
   - 支持并行处理多个文件以提升性能
   - 按工作表类型分别导入到不同的 ODS 表：
     * ODS_*_DETAIL：发票明细数据
     * ODS_*_HEADER：发票表头数据
     * ODS_*_SUMMARY：汇总统计数据
     * ODS_*_SPECIAL_*：特殊业务表
   - 添加审计字段（来源文件、导入时间、年份等）
   - 记录数据类型转换统计和失败情况

3. **DWD 层处理**（Data Warehouse Detail）
   - 数据去重：识别并处理重复的发票记录
   - 数据规范化：统一日期格式、金额格式、税率格式等
   - 按年份分表：将数据分配到 LEDGER_*_YYYY_* 表
   - 记录去重情况：保留所有版本的捕获时间供审计
   - 输出去重报告：detail 和 header 层的重复记录清单

4. **ADS 层处理**（Application Data Store）
   - 异常检测：识别税率异常、金额异常、日期异常等
   - 业务分析：生成统计报告、趋势分析等
   - 数据聚合：按维度汇总数据供查询使用

5. **清理阶段**（Cleanup Phase）
   - 删除临时表 ODS_*_TEMP_TRANSIT
   - 清理临时文件和中间结果
   - 生成资源使用报告（内存、CPU、磁盘IO）

=== 关键设计决策 ===

**1. 为什么使用 SQLite？**
   - 零配置：无需额外安装数据库服务
   - 文件化：便于备份和迁移
   - 足够性能：对于百万级发票数据，SQLite 性能充足
   - 事务支持：保证数据一致性

**2. 为什么分层（ODS/DWD/ADS）？**
   - 可追溯：ODS 保留原始数据，便于问题排查
   - 可维护：每层职责清晰，便于独立优化
   - 可扩展：新增分析需求只需修改 ADS 层
   - 可回滚：数据处理失败可从上一层重新开始

**3. 为什么支持并行处理？**
   - 性能：多文件并行导入可显著提升速度
   - 资源利用：充分利用多核 CPU
   - 可配置：根据硬件条件调整 worker_count
   - 安全：每个 worker 独立处理，失败不影响其他

**4. 为什么需要临时表？**
   - 原子性：确保批量导入要么全成功，要么全失败
   - 性能：先导入临时表，再批量插入正式表
   - 灵活性：可在临时表上执行额外的数据清洗

=== 错误处理策略 ===
- 文件级容错：单个文件失败不中断整体流程
- 记录级容错：单条记录解析失败不影响其他记录
- 详细日志：记录每个阶段的成功/失败情况
- 错误报告：生成 error_logs.csv 供人工审查

=== 性能优化 ===
- 流式处理：大文件使用 openpyxl 只读模式，避免内存溢出
- 批量插入：使用 executemany 减少数据库往返
- 索引优化：在关键字段（发票代码、发票号码）上建立索引
- 并行处理：根据 CPU 核心数和磁盘 IO 自动调整并行度
- 内存监控：实时监控内存使用，自动降级为流式处理

=== 维护建议 ===
1. 新增数据源：在 ODS 处理器中添加新的工作表识别逻辑
2. 新增校验：在 DWD 或 ADS 层添加校验规则
3. 性能调优：调整 worker_count、batch_size 等参数
4. 错误排查：查看 vat_audit.log 和 error_logs.csv
5. 数据恢复：从 ODS 层重新执行 DWD/ADS 处理
"""

from __future__ import annotations

import glob
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from vat_audit_pipeline.config.settings import AppSettings, build_pipeline_settings, load_app_settings
from vat_audit_pipeline.core import models
from vat_audit_pipeline.core.models import RuntimeContext
from vat_audit_pipeline.core.context import ProcessingContext
from vat_audit_pipeline.core.processors.ads_processor import process_ads
from vat_audit_pipeline.core.processors.dwd_processor import export_duplicates, process_dwd
from vat_audit_pipeline.core.processors.ods_processor import (
    process_ods,
    read_excel_with_engine,
    should_use_streaming_for_file,
)
from vat_audit_pipeline.utils.file_handlers import cleanup_temp_files, generate_manifest_filename, save_dataframe_to_csv
from vat_audit_pipeline.utils.monitoring import ResourceMonitor, write_resource_report
from vat_audit_pipeline.utils.validators import validate_input_file, write_error_logs
from vat_audit_pipeline.utils.logging import MemoryMonitor, PerformanceTimer, _debug_var, _progress


def build_logger(base_dir: Path, output_dir: Path, debug: bool = False) -> logging.Logger:
    logger = logging.getLogger("vat_audit")
    if logger.handlers:
        return logger
    level = logging.DEBUG if debug else getattr(logging, models.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    if models.LOG_TO_FILE:
        log_path = output_dir / models.LOG_FILE_NAME
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(log_path, maxBytes=models.LOG_MAX_BYTES, backupCount=models.LOG_BACKUP_COUNT, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


class VATAuditPipeline:
    def __init__(self, config_path: str | None = None, input_dir: str | None = None, verbose: bool = False) -> None:
        self.process_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.base_dir = Path(__file__).resolve().parent.parent
        self.app_settings: AppSettings = load_app_settings()
        self.config_path = config_path
        self.cli_input_dir = input_dir
        self.verbose = verbose

        self.config = self._load_external_config()
        self.settings = build_pipeline_settings(self.config, self.base_dir)

        if self.cli_input_dir:
            self.settings.input_dir = self.cli_input_dir
        if self.verbose:
            self.settings.debug_enabled = True

        self.runtime = RuntimeContext(
            business_tag=self.settings.business_tag,
            base_dir=self.base_dir,
            input_dir=Path(self.settings.input_dir),
            db_dir=Path(self.settings.database_dir),
            output_dir=Path(self.settings.output_dir),
            db_path=Path(self.settings.database_dir) / f"{self.settings.business_tag}_Audit_Repo.db",
            enable_parallel_import=self.settings.parallel_enabled,
            worker_count=self.settings.worker_count or 1,
            csv_chunk_size=self.settings.csv_chunk_size,
            stream_chunk_size=self.settings.stream_chunk_size,
            max_failure_sample_per_col=self.settings.max_failure_samples,
            tax_text_to_zero=self.settings.tax_text_to_zero,
            debug_mode=self.settings.debug_enabled,
        )

        self.logger = build_logger(self.base_dir, self.runtime.output_dir, debug=self.runtime.debug_mode)
        self.logger.info("✅ 从config.yaml加载配置成功")

        for d in [self.runtime.db_dir, self.runtime.output_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.excel_files: List[str] = []
        self.skipped_files: List[tuple[str, str]] = []
        self.files_meta: Dict[str, Any] = {}
        self.file_columns: Dict[str, List[str]] = {}
        self.sheet_manifest: List[Dict[str, Any]] = []
        self.error_logs: List[Dict[str, Any]] = []
        self.temp_root: Optional[str] = None
        self.conn: Optional[sqlite3.Connection] = None

        try:
            import psutil

            available_mem_mb = psutil.virtual_memory().available / (1024 * 1024)
            dynamic_stream_chunk = max(5000, min(100000, int(available_mem_mb * 0.1 * 1024)))
            self.logger.info(
                f"系统配置 - 工作进程数: {self.runtime.worker_count}, CSV块大小: {self.runtime.csv_chunk_size}, "
                f"流式块大小: {self.runtime.stream_chunk_size}(默认) / {dynamic_stream_chunk:,}(动态), 可用内存: {available_mem_mb:.0f}MB"
            )
        except ImportError:
            self.logger.info(
                f"系统配置 - 工作进程数: {self.runtime.worker_count}, CSV块大小: {self.runtime.csv_chunk_size}, 流式块大小: {self.runtime.stream_chunk_size}"
            )

    def _load_external_config(self):
        try:
            from config_manager import get_config_with_overrides

            # 构建覆盖项：支持GUI传入的目录与业务标签（通过环境变量）
            overrides = {}
            # CLI 输入目录
            if self.cli_input_dir:
                overrides.setdefault("paths", {})["input_dir"] = self.cli_input_dir
            # 环境覆盖（由GUI设置）
            env_business_tag = os.environ.get("VAT_BUSINESS_TAG")
            env_input_dir = os.environ.get("VAT_INPUT_DIR")
            env_output_dir = os.environ.get("VAT_OUTPUT_DIR")
            env_database_dir = os.environ.get("VAT_DATABASE_DIR")
            if env_business_tag:
                overrides.setdefault("business", {})["tag"] = env_business_tag
            if env_input_dir:
                overrides.setdefault("paths", {})["input_dir"] = env_input_dir
            if env_output_dir:
                overrides.setdefault("paths", {})["output_dir"] = env_output_dir
            if env_database_dir:
                overrides.setdefault("paths", {})["database_dir"] = env_database_dir

            cfg = get_config_with_overrides(config_path=self.config_path, overrides=overrides or None)
            return cfg
        except Exception as e:
            raise

    def scan_excel_files(self) -> List[str]:
        self.logger.info(f"正在扫描Excel文件：{self.runtime.input_dir}")
        if not self.runtime.input_dir.exists():
            self.logger.error(f"输入目录不存在: {self.runtime.input_dir}")
            return []

        candidate_files = glob.glob(str(self.runtime.input_dir / "**" / "*.xls*"), recursive=True)

        max_file_mb = self.app_settings.default_max_file_mb
        if self.config and hasattr(self.config, "get"):
            try:
                max_file_mb = self.config.get("inputs", "max_file_mb", default=max_file_mb)
                if isinstance(max_file_mb, str):
                    max_file_mb = float(max_file_mb)
            except Exception:
                max_file_mb = self.app_settings.default_max_file_mb

        valid_files = []
        skipped_files = []
        for f in candidate_files:
            ok, reason = validate_input_file(f, max_file_mb)
            if ok:
                valid_files.append(f)
            else:
                skipped_files.append((f, reason))

        self.excel_files = valid_files
        self.skipped_files = skipped_files

        self.logger.info(f"发现 {len(candidate_files)} 个Excel文件，已通过校验 {len(valid_files)} 个，跳过 {len(skipped_files)} 个")
        if skipped_files:
            for f, why in skipped_files:
                self.logger.warning(f"跳过文件 {f}: {why}")

        return self.excel_files

    def scan_excel_metadata(self) -> Dict[str, Any]:
        self.logger.info("开始扫描Excel文件元数据...")

        DETAIL_RE = re.compile(r"发票基础信息|.*明细.*", re.I)
        SUMMARY_RE = re.compile(r"信息汇总", re.I)
        HEADER_RE = re.compile(r"发票基础信息|发票基础(?:信息|表)?\d*", re.I)

        SPECIAL_SHEETS = [
            (re.compile(r"铁路(电子)?客票|铁路电子发票", re.I), "RAILWAY"),
            (re.compile(r"建筑服务", re.I), "BUILDING_SERVICE"),
            (re.compile(r"不动产租赁|不动产租赁经营服务", re.I), "REAL_ESTATE_RENTAL"),
            (re.compile(r"机动车销售统一发票", re.I), "VEHICLE"),
            (re.compile(r"货物运输服务", re.I), "CARGO_TRANSPORT"),
            (re.compile(r"过路过桥费", re.I), "TOLL"),
        ]

        self.files_meta = {}
        self.file_columns = {}
        self.scan_failed_files: List[str] = []

        for file in self.excel_files:
            fname = os.path.basename(file)
            try:
                engine = "xlrd" if str(file).lower().endswith(".xls") else None
                xl = pd.ExcelFile(file, engine=engine)
                cols = set()
                sheet_info: Dict[str, List[str]] = {}
                detail_sheets: List[str] = []
                header_sheets: List[str] = []
                summary_sheets: List[str] = []
                special_sheets: Dict[str, str] = {}

                for sheet in xl.sheet_names:
                    try:
                        raw_cols = read_excel_with_engine(file, sheet_name=sheet, nrows=0).columns.tolist()
                        header_cols = [str(c) for c in raw_cols]
                        sheet_info[sheet] = header_cols
                        cols.update(header_cols)

                        matched = False
                        for pat, suffix in SPECIAL_SHEETS:
                            if pat.search(sheet):
                                special_sheets[sheet] = suffix
                                matched = True
                                break

                        if matched:
                            continue

                        if SUMMARY_RE.search(sheet):
                            summary_sheets.append(sheet)
                        elif HEADER_RE.search(sheet):
                            header_sheets.append(sheet)
                        elif DETAIL_RE.search(sheet):
                            detail_sheets.append(sheet)
                    except Exception as e:
                        self.logger.warning(f"读取工作表 {sheet} 表头失败 {fname}: {e}")
                        continue

                self.files_meta[fname] = {
                    "sheet_info": sheet_info,
                    "detail_sheets": detail_sheets,
                    "header_sheets": header_sheets,
                    "summary_sheets": summary_sheets,
                    "special_sheets": special_sheets,
                }
                self.file_columns[fname] = sorted([str(c) for c in cols])
            except Exception as e:
                self.logger.warning(f"读取失败（列扫描） {fname}: {e}")
                self.files_meta[fname] = None
                self.scan_failed_files.append(fname)

        success_count = sum(1 for m in self.files_meta.values() if m is not None)
        self.logger.info(f"元数据扫描完成：{len(self.files_meta)} 个文件，成功 {success_count} 个")
        if self.scan_failed_files:
            failed_list = ";".join(sorted(self.scan_failed_files))
            self.logger.warning(f"元数据扫描失败 {len(self.scan_failed_files)} 个：{failed_list}")
        return self.files_meta

    def clean_temp_files(self) -> None:
        if self.temp_root and os.path.exists(self.temp_root):
            cleanup_temp_files(self.temp_root)
        self.temp_root = None

    def init_database(self) -> sqlite3.Connection:
        self.logger.info(f"初始化数据库: {self.runtime.db_path}")
        try:
            self.conn = sqlite3.connect(self.runtime.db_path)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.logger.info("数据库连接成功，已启用WAL模式")
        except Exception as e:
            self.logger.error(f"无法连接到数据库 {self.runtime.db_path}: {e}")
            raise
        return self.conn

    def run(self) -> None:
        self.logger.info(f"\n{'='*60}\n>>> 【增值税发票审计流程】启动于 {datetime.now()}\n{'='*60}")
        profiler_enabled = False
        if self.config and hasattr(self.config, "get"):
            profiler_enabled = bool(self.config.get("features", "performance_profiling", default=False))
        profiler_enabled = profiler_enabled or bool(self.runtime.debug_mode)

        resource_monitor = ResourceMonitor() if profiler_enabled else None
        if resource_monitor:
            resource_monitor.sample_memory()
            resource_monitor.sample_cpu()
        try:
            self.scan_excel_files()
            if not self.excel_files:
                self.logger.warning("未发现Excel文件，流程终止")
                return

            self.scan_excel_metadata()
            if resource_monitor:
                resource_monitor.sample_memory()
                resource_monitor.sample_cpu()

            # 仅处理元数据扫描成功的文件，失败的在后续汇总中体现
            processing_files = [f for f in self.excel_files if self.files_meta.get(os.path.basename(f))]
            if not processing_files:
                self.logger.error("元数据扫描全部失败，流程终止")
                return

            # 获取数据库连接（不使用 with 语句，避免过早关闭）
            self._processing_context = ProcessingContext(str(self.runtime.db_path), config=self.config)
            self._processing_context.__enter__()
            self.conn = self._processing_context.conn
            cursor = self.conn.cursor()
            process_time = self.process_time

            try:
                cursor.execute(f"DROP TABLE IF EXISTS ODS_{self.runtime.business_tag}_TEMP_TRANSIT")
                self.conn.commit()
            except Exception as e:
                self.logger.error(f"删除旧表失败: {e}")
                self._processing_context.__exit__(None, None, None)
                return

            detail_columns = set()
            header_columns = set()
            summary_columns = set()
            special_columns: Dict[str, set] = {}
            for fname, meta in self.files_meta.items():
                if not meta:
                    continue
                for s in meta.get("detail_sheets", []):
                    detail_columns.update(meta["sheet_info"].get(s, []))
                for s in meta.get("header_sheets", []):
                    header_columns.update(meta["sheet_info"].get(s, []))
                for s in meta.get("summary_sheets", []):
                    summary_columns.update(meta["sheet_info"].get(s, []))
                for s, suffix in meta.get("special_sheets", {}).items():
                    special_columns.setdefault(suffix, set()).update(meta["sheet_info"].get(s, []))

            for cols in (detail_columns, header_columns, summary_columns):
                cols.update([models.AUDIT_SRC_FILE_COL, models.AUDIT_IMPORT_TIME_COL, models.INVOICE_YEAR_COL, "税率_数值"])
            for suffix in special_columns:
                special_columns[suffix].update([models.AUDIT_SRC_FILE_COL, models.AUDIT_IMPORT_TIME_COL, models.INVOICE_YEAR_COL])

            ods_result = process_ods(
                self.runtime,
                self.logger,
                processing_files,
                self.files_meta,
                list(detail_columns),
                list(header_columns),
                list(summary_columns),
                {k: list(v) for k, v in special_columns.items()},
                process_time,
                self.config,
                self.conn,
            )

            if resource_monitor:
                resource_monitor.sample_memory()
                resource_monitor.sample_cpu()

            sheet_manifest = ods_result.get("sheet_manifest", [])
            processed_files = ods_result.get("processed_files", set())
            read_failed_files = ods_result.get("read_failed_files", [])
            cast_stats = ods_result.get("cast_stats", [])
            cast_failures = ods_result.get("cast_failures", [])
            error_logs = ods_result.get("error_logs", [])
            self.temp_root = ods_result.get("temp_root")
            self.sheet_manifest = sheet_manifest

            scan_failed_files = [f for f, m in self.files_meta.items() if m is None]
            total_files = len(self.files_meta)
            summary = {
                "total_files": total_files,
                "processed_files": len(processed_files),
                "scan_failed_files": ";".join(scan_failed_files),
                "read_failed_files": ";".join(read_failed_files),
                "process_time": process_time,
            }
            try:
                summary_df = pd.DataFrame([summary])
                summary_path = self.runtime.output_dir / generate_manifest_filename(models.IMPORT_SUMMARY_PREFIX, process_time)
                save_dataframe_to_csv(summary_df, summary_path)
                self.logger.info(f"导入汇总已导出: {summary_path}")
            except Exception as e:
                self.logger.error(f"写入汇总失败: {e}")

            if error_logs:
                write_error_logs(error_logs, process_time, output_dir=str(self.runtime.output_dir))

            ledger_rows, duplicates_detail, duplicates_header = process_dwd(self.conn, self.runtime, process_time, self.logger)
            export_duplicates(self.runtime, duplicates_detail, duplicates_header, process_time, str(self.runtime.output_dir), self.logger)
            process_ads(self.conn, self.runtime, self.logger)

            if resource_monitor:
                resource_monitor.sample_memory()
                resource_monitor.sample_cpu()

            try:
                cursor.execute(f"DROP TABLE IF EXISTS ODS_{self.runtime.business_tag}_TEMP_TRANSIT")
                self.conn.commit()
            except Exception as e:
                self.logger.warning(f"删除临时表失败: {e}")
            self.logger.info(f"\n[{datetime.now()}] >>> 流程圆满完成！DB文件在 Database 文件夹中。")

        except Exception as e:
            self.logger.error(f"流水线执行失败: {e}")
            import traceback

            traceback.print_exc()
        finally:
            if resource_monitor:
                try:
                    report = resource_monitor.generate_report()
                    report["process_time"] = self.process_time
                    report["business_tag"] = self.runtime.business_tag
                    report["worker_count"] = self.runtime.worker_count
                    report_path = self.runtime.output_dir / f"resource_report_{process_time.replace(':','-').replace(' ','_')}.json"
                    write_resource_report(report, report_path)
                    self.logger.info(f"资源监控报告已导出: {report_path}")
                except Exception:
                    pass

            # 确保关闭数据库连接
            if hasattr(self, 'conn') and self.conn:
                try:
                    if hasattr(self, '_processing_context'):
                        self._processing_context.__exit__(None, None, None)
                    self.conn = None
                    self.logger.info("数据库连接已关闭")
                except Exception as e:
                    self.logger.warning(f"关闭数据库连接时出错: {e}")
            self.clean_temp_files()