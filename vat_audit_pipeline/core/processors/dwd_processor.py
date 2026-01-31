"""DWD 层处理器 - 数据去重与台账生成模块

=== DWD 层职责（Data Warehouse Detail）===
DWD 层是数据仓库的"明细层"，负责对 ODS 层的原始数据进行清洗、去重、规范化，
生成按年度分表的发票台账，为后续的分析和应用提供干净、可靠的数据基础。

**核心目标：**
- 数据去重：识别并处理重复的发票记录（源内去重）
- 数据规范化：统一日期、金额、税率等格式
- 分年度存储：按年份生成 LEDGER_*_YYYY_* 表，便于查询和维护
- 审计追踪：保留所有去重记录的捕获时间，支持后续审计

=== 处理流程 ===

**1. 数据去重（Deduplication）**
   ```
   输入：ODS_*_DETAIL / ODS_*_HEADER 表
   输出：去重后的明细数据 + 重复记录清单
   
   去重规则（detail 表）：
   - 主键：发票代码 + 发票号码 + 开票日期
   - 策略：保留首次出现的记录（keep="first"）
   - 记录：所有重复记录写入 duplicates_detail.csv
   
   去重规则（header 表）：
   - 主键：发票代码 + 发票号码
   - 策略：保留首次出现的记录
   - 记录：所有重复记录写入 duplicates_header.csv
   ```

**2. 按年度分表（Yearly Partitioning）**
   ```
   输入：去重后的 ODS 数据
   输出：LEDGER_*_YYYY_INVOICE_DETAIL / LEDGER_*_YYYY_INVOICE_HEADER
   
   分表逻辑：
   - 从 ODS 表中提取所有不重复的年份（year 字段）
   - 为每个年份创建独立的 LEDGER 表
   - 每个表只包含该年度的发票数据
   
   优势：
   - 查询性能：单表数据量小，查询更快
   - 维护便利：可独立备份、归档某一年度的数据
   - 扩展灵活：新年度自动创建新表，不影响旧数据
   ```

**3. 数据规范化（Normalization）**
   - **税率标准化**：将"13%"、"13.00%"、"0.13" 统一为数值 13
   - **金额格式化**：去除千分位逗号，保留两位小数
   - **日期标准化**：统一为 YYYY-MM-DD 格式
   - **空值处理**：空字符串、"无"、"NULL" 统一为 NULL
   - **字段选择**：只保留业务必需的字段（detail_cols_needed）

**4. 去重报告（Duplication Report）**
   - 生成 duplicates_detail.csv：明细层重复记录
   - 生成 duplicates_header.csv：表头层重复记录
   - 每条重复记录添加 `dedup_capture_time` 字段标记发现时间
   - 支持人工审核：判断是否为真重复还是数据更新

=== 关键设计决策 ===

**1. 为什么保留重复记录？**
   - 审计需求：需要追溯哪些发票重复导入了
   - 人工复核：有些"重复"可能是发票冲红、更正等正常业务
   - 问题排查：帮助识别数据源的质量问题

**2. 为什么按年度分表？**
   - 性能优化：单表数据量控制在合理范围
   - 历史归档：旧年度数据可移至冷存储
   - 查询便利：大部分查询都是针对特定年度
   - 维护简化：可独立重建某一年度的表

**3. 为什么不做业务校验？**
   - 职责分离：DWD 层只负责数据清洗，业务校验在 ADS 层
   - 灵活扩展：业务规则变化时只需修改 ADS 层
   - 可重用性：DWD 层数据可供多种分析场景使用

=== 去重规则详解 ===

**Detail 表去重键：**
- 发票代码（invoice_code）
- 发票号码（invoice_number）
- 开票日期（invoice_date）

**Header 表去重键：**
- 发票代码（invoice_code）
- 发票号码（invoice_number）

**为什么 Detail 要加开票日期？**
- Detail 表可能包含同一发票的多条明细（多行商品）
- 仅用代码+号码无法区分是否为真重复
- 加上开票日期后，可确保同一发票的多条明细都被保留

=== 典型使用场景 ===
```python
# 场景 1：处理 DWD 层（去重并生成台账）
from vat_audit_pipeline.processors.dwd_processor import process_dwd

ledger_rows, dup_detail, dup_header = process_dwd(
    conn=db_conn,
    runtime=runtime_context,
    process_time='2024-01-15 10:30:00',
    logger=my_logger
)

print(f"生成台账：{len(ledger_rows)} 个年度")
print(f"发现重复（detail）：{sum(len(df) for df in dup_detail)} 条")
print(f"发现重复（header）：{sum(len(df) for df in dup_header)} 条")

# 场景 2：查看某年度台账
df_2024 = pd.read_sql("SELECT * FROM LEDGER_PURCHASE_2024_INVOICE_DETAIL", conn)
print(f"2024年进项发票：{len(df_2024)} 条")

# 场景 3：审查重复记录
if dup_detail:
    df_all_dups = pd.concat(dup_detail, ignore_index=True)
    df_all_dups.to_csv("duplicates_detail.csv", index=False, encoding='utf-8-sig')
```

=== 维护建议 ===
1. **调整去重规则**：修改 DETAIL_DEDUP_COLS / HEADER_DEDUP_COLS 配置
2. **新增规范化规则**：在数据规范化阶段添加自定义转换
3. **处理重复记录**：定期审查 duplicates_*.csv，识别数据质量问题
4. **性能优化**：对 LEDGER 表的常用查询字段建立索引
5. **数据归档**：定期将旧年度表导出并移至冷存储
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from vat_audit_pipeline.core import models
from vat_audit_pipeline.core.models import RuntimeContext
from vat_audit_pipeline.utils.file_handlers import add_dedup_capture_time
from vat_audit_pipeline.utils.logging import _progress
from vat_audit_pipeline.utils.validators import write_error_logs


def _normalize_invoice_year(year_value: Any) -> Optional[str]:
    """
    标准化发票年份为整数字符串形式。
    
    处理混合的年份格式（例如 '2023', '2023.0', 2023, 2023.0）。
    
    Args:
        year_value: 任意格式的年份值
    
    Returns:
        标准化后的年份字符串（纯整数，如 '2023'），或 None 如果无效
    """
    if year_value is None or year_value == '':
        return None
    
    try:
        # 转换为字符串并去除首尾空格
        year_str = str(year_value).strip()
        
        # 处理浮点数字符串（如 '2023.0' → '2023'）
        if '.' in year_str:
            year_float = float(year_str)
            year_int = int(year_float)
            year_str = str(year_int)
        
        # 验证是否为有效的年份数字
        if year_str.isdigit() and len(year_str) == 4:
            return year_str
        
        return None
    except (ValueError, TypeError, AttributeError):
        return None


def process_dwd(conn: sqlite3.Connection, runtime: RuntimeContext, process_time: str, logger) -> Tuple[List[Dict[str, Any]], List[pd.DataFrame], List[pd.DataFrame]]:
    logger.info("正在从 ODS_*_DETAIL 与 ODS_*_HEADER 生成按年度的发票台账（源内去重）...")
    ledger_rows: List[Dict[str, Any]] = []
    duplicates_detail: List[pd.DataFrame] = []
    duplicates_header: List[pd.DataFrame] = []
    try:
        yrs = pd.read_sql(
            f"SELECT DISTINCT {models.INVOICE_YEAR_COL} as y FROM ODS_{runtime.business_tag}_DETAIL WHERE {models.INVOICE_YEAR_COL} IS NOT NULL ORDER BY y",
            conn,
        )["y"].dropna().tolist()
    except Exception:
        yrs = []

    detail_cols_needed = models.DETAIL_COLS_NEEDED
    detail_dedup_subset = models.DETAIL_DEDUP_COLS
    if yrs:
        _progress(f"开始生成明细台账：共 {len(yrs)} 个年度需要处理。")
    for i, yr in enumerate(yrs, start=1):
        # 标准化年份格式（处理 '2023.0' 之类的混合格式）
        normalized_yr = _normalize_invoice_year(yr)
        if not normalized_yr:
            continue
        _progress(f"[{i}/{len(yrs)}] 生成 {normalized_yr} 年度 发票明细台账（源内去重）...")
        # 注意：使用原始的 yr 来查询，这样可以查到所有格式的数据（'2023' 和 '2023.0'）
        # 然后在创建表时使用标准化的 normalized_yr
        df = pd.read_sql(
            f"SELECT * FROM ODS_{runtime.business_tag}_DETAIL WHERE {models.INVOICE_YEAR_COL}=? ORDER BY rowid",
            conn,
            params=(yr,),
        )
        rows_before = len(df)
        dedup_keys = [c for c in detail_dedup_subset if c in df.columns]
        mask_dup = df.duplicated(subset=dedup_keys, keep="first") if dedup_keys else df.duplicated(keep="first")
        df_dedup = df[~mask_dup].copy()
        df_dups = df[mask_dup].copy()
        rows_after = len(df_dedup)
        rows_dropped = rows_before - rows_after
        if not df_dups.empty:
            df_dups = add_dedup_capture_time(df_dups, process_time)
            duplicates_detail.append(df_dups)
        cols_present = [c for c in detail_cols_needed if c in df_dedup.columns]
        df_out = df_dedup[cols_present].copy()
        df_out.to_sql(f"ODS_VAT_INV_DETAIL_FULL_{normalized_yr}", conn, if_exists="replace", index=False)
        ledger_rows.append(
            {
                "type": "detail",
                "year": normalized_yr,
                "rows_before": rows_before,
                "rows_after": rows_after,
                "rows_dropped": rows_dropped,
                "cols": ",".join(cols_present),
            }
        )

    try:
        yrs_hdr = pd.read_sql(
            f"SELECT DISTINCT {models.INVOICE_YEAR_COL} as y FROM ODS_{runtime.business_tag}_HEADER WHERE {models.INVOICE_YEAR_COL} IS NOT NULL ORDER BY y",
            conn,
        )["y"].dropna().tolist()
    except Exception:
        yrs_hdr = []

    header_cols_needed = models.HEADER_COLS_NEEDED
    header_dedup_subset = models.HEADER_DEDUP_COLS
    if yrs_hdr:
        _progress(f"开始生成表头台账：共 {len(yrs_hdr)} 个年度需要处理。")
    for i, yr in enumerate(yrs_hdr, start=1):
        # 标准化年份格式（处理 '2023.0' 之类的混合格式）
        normalized_yr = _normalize_invoice_year(yr)
        if not normalized_yr:
            continue
        _progress(f"[{i}/{len(yrs_hdr)}] 生成 {normalized_yr} 年度 发票信息台账（源内去重）...")
        # 使用原始的 yr 来查询，这样可以查到所有格式的数据（'2023' 和 '2023.0'）
        # 然后在创建表时使用标准化的 normalized_yr
        df = pd.read_sql(
            f"SELECT * FROM ODS_{runtime.business_tag}_HEADER WHERE {models.INVOICE_YEAR_COL}=? ORDER BY rowid",
            conn,
            params=(yr,),
        )
        rows_before = len(df)
        dedup_keys = [c for c in header_dedup_subset if c in df.columns]
        mask_dup = df.duplicated(subset=dedup_keys, keep="first") if dedup_keys else df.duplicated(keep="first")
        df_dedup = df[~mask_dup].copy()
        df_dups = df[mask_dup].copy()
        rows_after = len(df_dedup)
        rows_dropped = rows_before - rows_after
        if not df_dups.empty:
            df_dups = add_dedup_capture_time(df_dups, process_time)
            duplicates_header.append(df_dups)
        cols_present = [c for c in header_cols_needed if c in df_dedup.columns]
        df_out = df_dedup[cols_present].copy()
        df_out.to_sql(f"ODS_VAT_INV_HEADER_FULL_{normalized_yr}", conn, if_exists="replace", index=False)
        ledger_rows.append(
            {
                "type": "header",
                "year": normalized_yr,
                "rows_before": rows_before,
                "rows_after": rows_after,
                "rows_dropped": rows_dropped,
                "cols": ",".join(cols_present),
            }
        )

    cursor = conn.cursor()
    
    # 收集所有已创建的年份（从 ledger_rows 获取实际创建的表对应的年份）
    created_years_detail = [row["year"] for row in ledger_rows if row["type"] == "detail"]
    created_years_header = [row["year"] for row in ledger_rows if row["type"] == "header"]
    
    for yr in created_years_detail:
        try:
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS idx_ods_vat_inv_detail_full_{yr}_code_no ON ODS_VAT_INV_DETAIL_FULL_{yr}({models.INVOICE_CODE_COL}, {models.INVOICE_NUMBER_COL})"
            )
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS idx_ods_vat_inv_detail_full_{yr}_num ON ODS_VAT_INV_DETAIL_FULL_{yr}({models.ETICKET_NUMBER_COL})"
            )
        except Exception:
            pass
    for yr in created_years_header:
        try:
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS idx_ods_vat_inv_header_full_{yr}_code_no ON ODS_VAT_INV_HEADER_FULL_{yr}({models.INVOICE_CODE_COL}, {models.INVOICE_NUMBER_COL})"
            )
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS idx_ods_vat_inv_header_full_{yr}_num ON ODS_VAT_INV_HEADER_FULL_{yr}({models.ETICKET_NUMBER_COL})"
            )
        except Exception:
            pass

    return ledger_rows, duplicates_detail, duplicates_header


def export_duplicates(runtime: RuntimeContext, duplicates_detail: List[pd.DataFrame], duplicates_header: List[pd.DataFrame], process_time: str, output_dir: str, logger) -> Dict[str, Optional[str]]:
    if duplicates_detail:
        df_dup_detail = pd.concat(duplicates_detail, ignore_index=True)
        if models.AUDIT_IMPORT_TIME_COL not in df_dup_detail.columns:
            df_dup_detail[models.AUDIT_IMPORT_TIME_COL] = process_time
        detail_out_xlsx = os.path.join(output_dir, "发票明细台账重复导入的数据清单.xlsx")
        try:
            df_dup_detail.to_excel(detail_out_xlsx, index=False)
            logger.info(f"导出重复明细到 Excel: {detail_out_xlsx}")
        except Exception as e:
            detail_out_csv = detail_out_xlsx.replace(".xlsx", ".csv")
            df_dup_detail.to_csv(detail_out_csv, index=False, encoding=models.CSV_ENCODING)
            logger.warning(f"导出重复明细 Excel 失败，已导出为 CSV: {detail_out_csv} ({e})")
    else:
        logger.info("未发现明细台账内被去重的记录。")

    if duplicates_header:
        df_dup_header = pd.concat(duplicates_header, ignore_index=True)
        if models.AUDIT_IMPORT_TIME_COL not in df_dup_header.columns:
            df_dup_header[models.AUDIT_IMPORT_TIME_COL] = process_time
        header_out_xlsx = os.path.join(output_dir, "发票信息台账重复导入的数据清单.xlsx")
        try:
            df_dup_header.to_excel(header_out_xlsx, index=False)
            logger.info(f"导出重复表头到 Excel: {header_out_xlsx}")
        except Exception as e:
            header_out_csv = header_out_xlsx.replace(".xlsx", ".csv")
            df_dup_header.to_csv(header_out_csv, index=False, encoding=models.CSV_ENCODING)
            logger.warning(f"导出重复表头 Excel 失败，已导出为 CSV: {header_out_csv} ({e})")
    else:
        logger.info("未发现发票信息台账内被去重的记录。")

    return {
        "detail_xlsx": os.path.join(output_dir, "发票明细台账重复导入的数据清单.xlsx") if duplicates_detail else None,
        "header_xlsx": os.path.join(output_dir, "发票信息台账重复导入的数据清单.xlsx") if duplicates_header else None,
    }