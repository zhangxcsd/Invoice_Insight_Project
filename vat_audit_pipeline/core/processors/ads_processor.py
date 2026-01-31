"""ADS 层处理器 - 应用层分析与异常检测模块

=== ADS 层职责（Application Data Store）===
ADS 层是数据仓库的"应用层"，负责在 DWD 层干净数据的基础上进行业务分析、
异常检测、统计汇总等高级处理，生成面向具体业务场景的分析结果。

**核心目标：**
- 异常检测：识别不符合业务规则的发票数据
- 业务分析：生成统计报告、趋势分析等
- 数据聚合：按维度汇总数据供快速查询
- 规则引擎：支持灵活配置的业务校验规则

=== 处理流程 ===

**1. 税率异常检测（Tax Rate Anomaly Detection）**
   ```
   输入：DWD_*_YYYY_STND 表（所有年度）
   输出：ADS_*_TAX_ANOMALY 表
   
   检测规则：
   - 数值型税率：不在 [0, 3, 6, 9, 13] 集合中
   - 字符型税率：不在 ['0', '3', '6', '9', '13', '0%', '免税', '不征税', '免征'] 集合中
   
   业务背景：
   - 中国增值税税率：13%（基本税率）、9%（农产品等）、6%（服务业）、3%（小规模）、0%（出口）
   - 异常场景：录入错误（如"1.3"误写为"130"）、非标准表述、税率变更滞后等
   ```

**2. 多年度数据聚合（Multi-Year Aggregation）**
   ```
   策略：UNION ALL 所有年度的 DWD 表
   
   SELECT * FROM DWD_PURCHASE_2022_STND
   UNION ALL
   SELECT * FROM DWD_PURCHASE_2023_STND
   UNION ALL
   SELECT * FROM DWD_PURCHASE_2024_STND
   
   目的：
   - 跨年度分析：如多年趋势对比
   - 全局异常：如同一供应商在不同年度的税率不一致
   ```

=== 当前实现的分析模型 ===

**1. 税率异常模型（ADS_*_TAX_ANOMALY）**
   - **检测逻辑**：识别不符合标准税率的发票
   - **应用场景**：
     * 审计抽查：优先审查异常税率的发票
     * 质量监控：识别数据录入错误
     * 风险预警：发现可能的虚开发票（非标准税率）
   - **输出字段**：继承 DWD 表的所有字段
   - **使用示例**：
     ```sql
     -- 查看所有税率异常的发票
     SELECT 发票代码, 发票号码, 税率, 税额, 开票日期 
     FROM ADS_PURCHASE_TAX_ANOMALY
     ORDER BY 税额 DESC;
     
     -- 按供应商统计异常数量
     SELECT 销方名称, COUNT(*) as 异常数量, SUM(税额) as 异常税额
     FROM ADS_PURCHASE_TAX_ANOMALY
     GROUP BY 销方名称
     ORDER BY 异常数量 DESC;
     ```

=== 扩展方向（待实现）===

**2. 金额异常模型（ADS_*_AMOUNT_ANOMALY）**
   - 检测规则：
     * 税额 ≠ 金额 × 税率（允许小数精度误差）
     * 价税合计 ≠ 金额 + 税额
     * 负数金额（冲红以外的场景）
   - 应用场景：识别计算错误、数据篡改

**3. 供应商异常模型（ADS_*_VENDOR_ANOMALY）**
   - 检测规则：
     * 同一供应商在不同年度税率不一致
     * 供应商名称相似度检测（识别拆分发票）
     * 新增供应商首次交易金额过大
   - 应用场景：供应商风险评估、虚开发票识别

**4. 时间序列异常（ADS_*_TIME_ANOMALY）**
   - 检测规则：
     * 开票日期早于业务发生日期
     * 集中在月末、季末、年末的发票
     * 发票号码不连续（可能存在作废）
   - 应用场景：识别虚开发票的时间特征

**5. 关联交易分析（ADS_*_RELATED_PARTY）**
   - 检测规则：
     * 购销双方为关联企业
     * 交易价格显著偏离市场价
   - 应用场景：关联交易定价审计

=== 关键设计决策 ===

**1. 为什么 ADS 层只做聚合和标记？**
   - 保持原子性：不修改 DWD 数据，只生成分析视图
   - 可追溯性：异常记录可回溯到 DWD 层查看完整信息
   - 灵活性：业务规则变化时，只需重建 ADS 表

**2. 为什么使用 SQL 而非 Python？**
   - 性能：数据库引擎对大批量聚合优化更好
   - 可维护：SQL 更直观，业务人员也能理解
   - 可重用：分析逻辑可独立于 Python 代码
   - 可调试：可直接在数据库工具中验证 SQL

**3. 为什么不做实时检测？**
   - 批处理特性：发票数据通常按批次导入
   - 性能考虑：实时检测会拖慢导入速度
   - 业务需求：审计通常是事后分析，不需要实时

=== 典型使用场景 ===

    # 场景 1：生成 ADS 分析模型
    from vat_audit_pipeline.processors.ads_processor import process_ads
    
    process_ads(conn=db_conn, runtime=runtime_context, logger=my_logger)
    print("ADS 分析模型生成完成")
    
    # 场景 2：查询税率异常
    df_anomaly = pd.read_sql(
        "SELECT * FROM ADS_PURCHASE_TAX_ANOMALY WHERE 税额 > 10000",
        conn
    )
    print(f"高金额税率异常：{len(df_anomaly)} 条")
    
    # 场景 3：生成审计报告
    summary = pd.read_sql('''
        SELECT 
            税率,
            COUNT(*) as 发票数量,
            SUM(金额) as 总金额,
            SUM(税额) as 总税额
        FROM ADS_PURCHASE_TAX_ANOMALY
        GROUP BY 税率
        ORDER BY 总税额 DESC
    ''', conn)
    summary.to_excel("税率异常汇总.xlsx", index=False)

=== 性能优化建议 ===
1. **索引优化**：在 DWD 表的 tax_rate、year 等字段建立索引
2. **增量处理**：仅处理新增年度的数据，避免全量重建
3. **分区表**：对于超大规模数据，考虑按年度分区
4. **物化视图**：对于频繁查询的聚合结果，考虑创建物化视图

=== 维护建议 ===
1. **新增检测规则**：在 process_ads() 中添加新的 CREATE TABLE AS 语句
2. **调整阈值**：根据实际业务调整异常检测的阈值
3. **定期审查**：定期查看 ADS 表，评估规则的有效性
4. **导出报告**：将 ADS 结果导出为 Excel，供业务人员审查
5. **规则文档化**：将每条检测规则的业务含义记录在文档中
"""

from __future__ import annotations

import sqlite3
from typing import List

from vat_audit_pipeline.core.models import RuntimeContext


def process_ads(conn: sqlite3.Connection, runtime: RuntimeContext, logger) -> None:
    logger.info("正在运行审计专题模型...")
    try:
        years = [r[0].split("_")[-2] for r in conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'DWD_%_STND'").fetchall()]
        all_dwd_tables: List[str] = [f"DWD_{runtime.business_tag}_{yr}_STND" for yr in years if str(yr).isdigit()]
        union_query = " UNION ALL ".join([f"SELECT * FROM {t}" for t in all_dwd_tables])
        if union_query:
            cursor = conn.cursor()
            cursor.execute(
                f"CREATE TABLE IF NOT EXISTS ADS_{runtime.business_tag}_TAX_ANOMALY AS SELECT * FROM ({union_query}) "
                "WHERE (税率_数值 IS NOT NULL AND 税率_数值 NOT IN (13, 9, 6, 3, 0)) "
                "OR (税率_数值 IS NULL AND 税率 NOT IN ('13','9','6','3','0','0%','0.00%','0.0%','免税','不征税','免征'));"
            )
    except Exception as e:
        logger.warning(f"生成 ADS 模型失败: {e}")