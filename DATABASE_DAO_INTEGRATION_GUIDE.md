"""
数据库抽象层集成示例

本文件展示如何在 VAT_Invoice_Processor.py 中逐步整合 DAO 层。
注意：这是示例代码，实际集成需要同步更新 VAT_Invoice_Processor.py。
"""

# 示例 1: 使用 DatabaseConnection 替代直接的 sqlite3 操作
# =========================================================

# 【之前的代码】
# import sqlite3
# conn = sqlite3.connect(database_path)
# cursor = conn.cursor()
# cursor.execute('PRAGMA journal_mode=WAL')
# cursor.execute(f"SELECT * FROM ODS_{BUSINESS_TAG}_DETAIL WHERE 开票年份={yr}")
# rows = cursor.fetchall()

# 【整合后的代码】
from vat_audit_pipeline.utils.database import DatabaseConnection, ODSDetailDAO

db = DatabaseConnection(database_path)
db.pragma_optimize(mode='wal')

# 使用 DAO 层查询
ods_detail_dao = ODSDetailDAO(db, business_tag='PURCHASE')
years = ods_detail_dao.get_distinct_years()
for year in years:
    detail_rows = ods_detail_dao.find_by_year(year)
    print(f"Year {year}: {len(detail_rows)} 条记录")

db.close()


# 示例 2: 事务管理
# ===============

# 【之前的代码】
# cursor.execute('BEGIN IMMEDIATE')
# try:
#     cursor.execute("INSERT INTO table VALUES (?, ?)", (val1, val2))
#     conn.commit()
# except Exception as e:
#     conn.rollback()

# 【整合后的代码】
db = DatabaseConnection(database_path)
try:
    with db.transaction():
        result = db.execute_insert(
            "INSERT INTO ODS_PURCHASE_DETAIL (发票代码, 发票号码, 金额) VALUES (?, ?, ?)",
            ('2023001', '001', 100.00)
        )
        if result.is_success():
            print(f"✓ 插入 {result.rowcount} 条记录")
except Exception as e:
    print(f"✗ 事务失败: {e}")
finally:
    db.close()


# 示例 3: 参数化查询避免 SQL 注入
# ==============================

# 【有 SQL 注入风险的代码】
# user_input = "'; DROP TABLE users; --"
# cursor.execute(f"SELECT * FROM table WHERE name = '{user_input}'")

# 【安全的参数化查询】
db = DatabaseConnection(database_path)

# 直接使用 DatabaseConnection
user_input = "'; DROP TABLE users; --"
result = db.execute_select(
    "SELECT * FROM ODS_PURCHASE_DETAIL WHERE 发票代码=?",
    (user_input,)  # 参数通过元组传入，不在 SQL 字符串中
)

# 或者使用 DAO
ods_detail_dao = ODSDetailDAO(db, 'PURCHASE')
invoice = ods_detail_dao.find_by_invoice('2023001', '001')

db.close()


# 示例 4: 复杂查询与错误处理
# =========================

from vat_audit_pipeline.utils.database import DatabaseConnection, QueryResult

db = DatabaseConnection(database_path)

# 查询带条件和排序
result = db.execute_select(
    """SELECT * FROM ODS_PURCHASE_DETAIL 
       WHERE 金额 > ? AND 开票年份 = ?
       ORDER BY 开票日期 DESC
       LIMIT 100""",
    (1000, '2023')
)

if result.is_success():
    print(f"查询成功，{result.rowcount} 条记录，耗时 {result.execution_time_ms:.2f}ms")
    for row_dict in result.to_dict_list():
        print(f"  - 发票: {row_dict['发票代码']}/{row_dict['发票号码']}, 金额: {row_dict['金额']}")
else:
    print(f"✗ 查询失败: {result.error}")

db.close()


# 示例 5: 创建和管理表索引
# =======================

db = DatabaseConnection(database_path)
ods_detail_dao = ODSDetailDAO(db, 'PURCHASE')

# 创建单列索引
result = ods_detail_dao.create_index(
    "idx_ods_purchase_detail_invoice_code",
    ["发票代码"]
)
print(f"索引创建: {result.is_success()}")

# 创建复合索引
result = ods_detail_dao.create_index(
    "idx_ods_purchase_detail_code_number",
    ["发票代码", "发票号码"]
)
print(f"复合索引创建: {result.is_success()}")

db.close()


# 示例 6: 与 process_dwd 函数整合
# ==============================

def process_dwd_with_dao(db_path: str, business_tag: str, process_time: str):
    """使用 DAO 层重写 process_dwd 函数（简化版）。"""
    from vat_audit_pipeline.utils.database import DatabaseConnection, ODSDetailDAO, ODSHeaderDAO, LedgerDAO
    
    db = DatabaseConnection(db_path)
    
    try:
        # 获取所有年份
        ods_detail_dao = ODSDetailDAO(db, business_tag)
        years = ods_detail_dao.get_distinct_years()
        
        for year in years:
            if not (year and str(year).isdigit()):
                continue
            
            print(f"处理 {year} 年度明细...")
            
            # 查询该年份所有明细
            details = ods_detail_dao.find_by_year(year)
            
            # 使用 DataFrame 进行去重（保持原有逻辑）
            import pandas as pd
            df = pd.DataFrame([dict(row) for row in details])
            dedup_cols = ['发票代码', '发票号码', '开票日期', '金额']
            df_dedup = df.drop_duplicates(subset=dedup_cols, keep='first')
            
            # 写入 LEDGER 表
            ledger_dao = LedgerDAO(db, business_tag, year, 'detail')
            # 注意：to_sql 仍由 pandas 处理，DAO 也提供了 insert 方法
            df_dedup.to_sql(ledger_dao.table_name, db.connect(), if_exists='replace', index=False)
            
            print(f"  ✓ {year} 年明细: {len(details)} -> {len(df_dedup)} 条")
        
        # 对表头执行相同操作
        ods_header_dao = ODSHeaderDAO(db, business_tag)
        years_hdr = ods_header_dao.get_distinct_years()
        
        for year in years_hdr:
            if not (year and str(year).isdigit()):
                continue
            
            print(f"处理 {year} 年度表头...")
            headers = ods_header_dao.find_by_year(year)
            
            import pandas as pd
            df = pd.DataFrame([dict(row) for row in headers])
            dedup_cols = ['发票代码', '发票号码']
            df_dedup = df.drop_duplicates(subset=dedup_cols, keep='first')
            
            ledger_dao = LedgerDAO(db, business_tag, year, 'header')
            df_dedup.to_sql(ledger_dao.table_name, db.connect(), if_exists='replace', index=False)
            
            print(f"  ✓ {year} 年表头: {len(headers)} -> {len(df_dedup)} 条")
    
    finally:
        db.close()


# 示例 7: 批量数据导入（使用事务）
# ==============================

def batch_import_with_transaction(db_path: str, business_tag: str, records: list):
    """
    使用事务和 DAO 批量导入数据。
    
    Args:
        db_path: 数据库路径
        business_tag: 业务标签
        records: 列表，每个元素是 (发票代码, 发票号码, 金额, ...) 元组
    """
    from vat_audit_pipeline.utils.database import DatabaseConnection, ODSDetailDAO
    
    db = DatabaseConnection(db_path)
    ods_detail_dao = ODSDetailDAO(db, business_tag)
    
    try:
        with db.transaction():
            # 批量插入
            columns = ['发票代码', '发票号码', '金额']  # 示例列
            result = ods_detail_dao.insert(columns, records)
            
            if result.is_success():
                print(f"✓ 批量导入成功: {result.rowcount} 条记录")
            else:
                print(f"✗ 导入失败: {result.error}")
    except Exception as e:
        print(f"✗ 事务异常: {e}")
    finally:
        db.close()


# 示例 8: 异常处理与日志
# ======================

import logging
from vat_audit_pipeline.utils.database import DatabaseConnection, DatabaseConnectionError, DatabaseQueryError

logger = logging.getLogger(__name__)

db = None
try:
    db = DatabaseConnection("/path/to/vat_audit.sqlite")
    
    # 执行查询
    result = db.execute_select("SELECT COUNT(*) FROM ODS_PURCHASE_DETAIL")
    
    if result.is_success():
        count = result.rows[0][0] if result.rows else 0
        logger.info(f"表中共有 {count} 条记录")
    else:
        logger.error(f"查询失败: {result.error}")

except DatabaseConnectionError as e:
    logger.error(f"连接失败: {e}")
except DatabaseQueryError as e:
    logger.error(f"查询异常: {e}")
except Exception as e:
    logger.error(f"未知异常: {e}")
finally:
    if db:
        db.close()


# 集成检查清单
# ============

"""
在 VAT_Invoice_Processor.py 中集成 DAO 层的分步骤：

[ ] 1. 导入 DAO 类
    from vat_audit_pipeline.utils.database import DatabaseConnection, ODSDetailDAO, ODSHeaderDAO, LedgerDAO

[ ] 2. 在 VATAuditPipeline.__init__ 中初始化数据库连接
    self.db = DatabaseConnection(self.settings.database_dir + '/vat_audit.sqlite')
    self.db.pragma_optimize(mode='wal')

[ ] 3. 用 DAO 替代 _prepare_ods_tables 中的直接 sqlite3 操作
    self.ods_detail_dao = ODSDetailDAO(self.db, self.business_tag)
    self.ods_detail_dao.drop_table()  # 清空表

[ ] 4. 用 DAO 替代 process_dwd 中的查询操作
    years = self.ods_detail_dao.get_distinct_years()
    for year in years:
        details = self.ods_detail_dao.find_by_year(year)

[ ] 5. 用 db.transaction() 替代手动 BEGIN/COMMIT/ROLLBACK
    with self.db.transaction():
        self.ods_detail_dao.insert(columns, values)

[ ] 6. 使用参数化查询（确保所有用户输入通过 params 传入）
    result = self.db.execute_select(
        "SELECT * FROM table WHERE 发票代码=?",
        (invoice_code,)
    )

[ ] 7. 测试各 DAO 方法，确保查询正确且性能满足预期
    pytest tests/test_dao.py -v

[ ] 8. 更新错误处理，捕获 DatabaseQueryError, DatabaseConnectionError
    try:
        result = self.db.execute_select(...)
    except DatabaseQueryError as e:
        logger.error(f"查询失败: {e}")

[ ] 9. 在 __exit__ 或主函数最后调用 db.close()
    finally:
        if self.db:
            self.db.close()

[ ] 10. 验证 SQL 注入防护，使用 grep 检查所有 cursor.execute() 是否使用了参数化
    grep -n "execute(f\"" VAT_Invoice_Processor.py  # 应返回空结果
"""
