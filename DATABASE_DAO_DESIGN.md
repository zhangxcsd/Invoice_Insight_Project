"""
数据库抽象层（DAO）设计文档

本文档阐述数据库抽象层的架构、设计原则、安全机制和逐步集成策略。
"""

# ============================================================================
# 1. 概述
# ============================================================================

"""
问题背景：
- 当前代码直接使用 sqlite3 库，存在 SQL 注入风险
- 例如：cursor.execute(f"SELECT * FROM ODS_{BUSINESS_TAG}_DETAIL WHERE 开票年份={yr}")
  其中 yr 如果来自用户输入，未经验证则可能导致 SQL 注入
- 全局变量（BUSINESS_TAG 等）分散在代码各处，难以测试和维护

解决方案：
1. **参数化查询（Parameterized Queries）**：所有用户输入通过 params 元组传入，不在 SQL 字符串中拼接
2. **轻量级 DAO 层**：无需 ORM（SQLAlchemy），简单直接的 Data Access Object 接口
3. **事务管理**：统一的 BEGIN/COMMIT/ROLLBACK 管理，避免嵌套问题
4. **依赖注入**：DAO 通过构造函数接收 database_path，不读取全局变量
5. **日志追踪**：所有 SQL 操作自动记录执行时间、结果、异常

设计特点：
- 最小依赖：仅使用 Python 标准库 sqlite3，无需额外安装
- 易于测试：可注入模拟数据库，单元测试覆盖完整
- 逐步集成：可与现有代码共存，逐步迁移而不强行全量重构
- 性能优化：支持 WAL 模式、事务优化等
"""


# ============================================================================
# 2. 核心类设计
# ============================================================================

"""
2.1 DatabaseConnection（数据库连接管理器）
────────────────────────────────────────────

职责：
  - 建立和关闭数据库连接
  - 提供参数化查询接口（execute_select/insert/update/delete）
  - 管理事务生命周期
  - 记录执行时间和异常日志

关键方法：
  - connect(): 建立连接（单例模式，复用）
  - close(): 关闭连接
  - transaction(): 上下文管理器，自动 BEGIN/COMMIT/ROLLBACK
  - execute_select(query, params): 参数化 SELECT
  - execute_insert(query, params): 参数化 INSERT
  - execute_update(query, params): 参数化 UPDATE
  - execute_delete(query, params): 参数化 DELETE
  - pragma_optimize(mode): 性能优化（WAL 等）

参数化查询示例：
  
  # ❌ 危险（SQL 注入风险）
  cursor.execute(f"SELECT * FROM table WHERE year={user_input}")
  
  # ✅ 安全（参数化查询）
  result = db.execute_select(
      "SELECT * FROM table WHERE year=?",
      (user_input,)
  )

2.2 QueryResult（查询结果容器）
─────────────────────────────────

职责：
  - 封装查询结果：rows、columns、rowcount、error、execution_time_ms
  - 提供便利的数据转换方法

关键方法：
  - is_success(): 检查查询是否成功（error=None）
  - to_dict_list(): 将行转换为字典列表
  - to_first_dict(): 获取第一行为字典
  - execution_time_ms: 记录查询耗时，用于性能分析

示例：
  
  result = db.execute_select("SELECT * FROM users LIMIT 10")
  if result.is_success():
      for row_dict in result.to_dict_list():
          print(f"User: {row_dict['name']}, Age: {row_dict['age']}")
      print(f"耗时: {result.execution_time_ms:.2f}ms")

2.3 DAOBase（数据访问对象基类）
──────────────────────────────

职责：
  - 提供通用的 CRUD 操作（Create/Read/Update/Delete）
  - 子类继承并专注于业务逻辑
  - 自动处理表名、列映射等

关键方法：
  - find_all(order_by, limit): 查询全部或分页
  - find_by_id(id_value): 按 ID 查询单条记录
  - find_where(where_clause, params): 按条件查询
  - count(where_clause, params): 统计记录数
  - insert(columns, values): 批量插入
  - delete_where(where_clause, params): 按条件删除
  - create_index(index_name, columns): 创建索引
  - table_exists(): 检查表是否存在

示例：
  
  class UserDAO(DAOBase):
      def __init__(self, db):
          super().__init__(db, "users")
      
      def find_by_email(self, email):
          results = self.find_where("email=?", (email,))
          return results[0] if results else None
  
  dao = UserDAO(db)
  user = dao.find_by_email("john@example.com")

2.4 具体 DAO 实现
────────────────

ODSDetailDAO（ODS 明细层）：
  - 管理 ODS_{BUSINESS_TAG}_DETAIL 表
  - find_by_invoice(code, number): 按发票号查询
  - find_by_year(year): 按年份查询
  - get_distinct_years(): 获取所有年份
  - count_by_year(year): 按年份计数

ODSHeaderDAO（ODS 表头层）：
  - 管理 ODS_{BUSINESS_TAG}_HEADER 表
  - 接口与 ODSDetailDAO 类似

LedgerDAO（台账层）：
  - 管理 LEDGER_{BUSINESS_TAG}_{YEAR}_{TYPE} 表
  - find_by_invoice(code, number): 按发票查询
  - find_by_seller(seller_id): 按销方查询
  - find_by_buyer(buyer_id): 按购方查询
  - count_by_status(status): 按状态统计

OADSAnalyticsDAO（ADS 分析层）：
  - 管理异常税率、风险评分等分析表
  - find_anomalies_by_type(type): 按异常类型查询
  - find_by_invoice_with_risk(code, number, min_score): 按风险查询
"""


# ============================================================================
# 3. 参数化查询与 SQL 注入防护
# ============================================================================

"""
3.1 SQL 注入问题
────────────────

当前风险代码示例：

    year = input("请输入年份: ")  # 用户输入：2023' OR '1'='1
    cursor.execute(f"SELECT * FROM ODS_DETAIL WHERE year='{year}'")
    # 结果：SELECT * FROM ODS_DETAIL WHERE year='2023' OR '1'='1'
    # 返回所有记录！

3.2 参数化查询解决方案
──────────────────────

参数化查询原理：
- SQL 结构和数据分离
- SQL 编译器已知查询结构，不会被用户输入改变
- 数据库驱动自动转义特殊字符

安全代码示例：

    year = input("请输入年份: ")  # 用户输入：2023' OR '1'='1
    result = db.execute_select(
        "SELECT * FROM ODS_DETAIL WHERE year=?",
        (year,)
    )
    # 数据库驱动自动转义，year 被完全当作字符串数据，不能改变 SQL 结构

3.3 DAOBase 中的 SQL 注入防护
───────────────────────────

WHERE 子句处理：
- WHERE 子句由开发者编写（内部代码），但数据值来自参数
- 示例：
    dao.find_where(
        "age > ? AND status=?",
        (30, 'active')
    )
  参数化查询确保 age 和 status 的值不会被当作 SQL 代码执行

表名和列名处理：
- 表名、列名、索引名来自内部代码和配置，不接受用户输入
- DAO 子类的 table_name 由构造函数固定
- 创建索引时列名也由开发者代码指定

3.4 安全检查清单
────────────────

✅ 检查点：

[ ] 1. 所有用户输入都通过 params 参数传入吗？
[ ] 2. 没有 f-string 拼接 SQL 吗？（find...where 子句除外，子句由开发者固定）
[ ] 3. 整数/日期等非字符串值也通过 params 传入吗？
[ ] 4. 创建索引时列名来自内部代码吗？
[ ] 5. 表名由 DAO 构造函数固定吗？
[ ] 6. 事务操作使用 db.transaction() 上下文管理器吗？

grep 检查命令：
    grep -n "execute(f\"" VAT_Invoice_Processor.py  # 应返回空
    grep -n "\.execute(" VAT_Invoice_Processor.py   # 确保都是通过 DAO 或 db 对象
"""


# ============================================================================
# 4. 事务管理
# ============================================================================

"""
4.1 事务生命周期
────────────────

问题（当前代码）：
    cursor.execute('BEGIN IMMEDIATE')
    try:
        cursor.execute("INSERT INTO ...")
        cursor.execute("INSERT INTO ...")
        conn.commit()
    except Exception:
        conn.rollback()

改进（DAO 层）：
    with db.transaction():
        db.execute_insert(...)
        db.execute_insert(...)
        # 自动 COMMIT；若异常自动 ROLLBACK

优势：
  1. 代码简洁：无需手动 BEGIN/COMMIT/ROLLBACK
  2. 异常安全：即使异常也会自动回滚
  3. 嵌套检测：防止意外嵌套事务

4.2 事务示例
─────────────

示例 1：简单插入事务

    with db.transaction():
        result = db.execute_insert(
            "INSERT INTO ODS_DETAIL (code, number, amount) VALUES (?, ?, ?)",
            ('2023001', '000001', 100.0)
        )
        if not result.is_success():
            raise Exception(f"插入失败: {result.error}")

示例 2：批量操作

    with db.transaction():
        for record in records:
            db.execute_insert(
                "INSERT INTO ODS_DETAIL (...) VALUES (...)",
                record
            )
        # 整个批量操作原子性

示例 3：使用 DAO 的批量操作

    ods_dao = ODSDetailDAO(db, "PURCHASE")
    with db.transaction():
        ods_dao.insert(
            ["发票代码", "发票号码", "金额"],
            [
                ('2023001', '000001', 100.0),
                ('2023002', '000002', 200.0),
            ]
        )

4.3 WAL 模式优化
────────────────

启用 WAL（Write-Ahead Logging）：
  - 读写并发提升
  - 更好的性能（特别是并发写入）
  - 默认关闭，需显式启用

启用方法：

    db = DatabaseConnection(db_path)
    db.pragma_optimize(mode='wal')
"""


# ============================================================================
# 5. 日志追踪与性能分析
# ============================================================================

"""
5.1 自动日志记录
─────────────────

所有 execute_* 方法自动记录：
  - 查询语句（前 60 字符）
  - 执行时间（毫秒）
  - 影响行数（INSERT/UPDATE/DELETE）
  - 错误信息

日志级别：
  - DEBUG：成功的查询
  - ERROR：失败的查询、异常

示例日志输出：
    
    查询成功: SELECT * FROM ODS_TEST_DETAIL WHERE 开票年份=? (3 行, 12.45ms)
    ✓ INSERT 执行成功: 受影响 1 行 (5.23ms)
    INSERT 执行失败: INSERT INTO table VALUES (?, ...) 错误: UNIQUE constraint failed

5.2 性能分析
──────────────

通过 QueryResult.execution_time_ms 进行性能分析：

    result = db.execute_select("SELECT COUNT(*) FROM large_table")
    if result.execution_time_ms > 1000:
        logger.warning(f"查询耗时 {result.execution_time_ms:.0f}ms，考虑添加索引")

批量查询性能统计：

    results = []
    for year in years:
        result = ods_dao.find_by_year(year)
        results.append(result)
    
    total_time = sum(r.execution_time_ms for r in results)
    logger.info(f"批量查询耗时 {total_time:.0f}ms")
"""


# ============================================================================
# 6. 逐步集成策略
# ============================================================================

"""
6.1 集成阶段规划
────────────────

Phase 1: 准备阶段（已完成）
  ✅ 创建 utils/database.py 包含 DatabaseConnection 和 DAO 类
  ✅ 编写测试 tests/test_database_dao.py
  ✅ 编写集成指南 DATABASE_DAO_INTEGRATION_GUIDE.md
  ✅ 测试通过：pytest tests/test_database_dao.py -v

Phase 2: 核心集成（下一步）
  [ ] 更新 VATAuditPipeline.__init__：初始化 self.db = DatabaseConnection(...)
  [ ] 在 _prepare_ods_tables 中使用 DAO 替代 sqlite3 操作
  [ ] 在 process_dwd 中使用 DAO 查询

Phase 3: 深层集成
  [ ] 将 _import_ods_data 中的 cursor.execute 替换为 db.execute_* 调用
  [ ] 集成 process_file_worker_with_queue 中的数据库操作
  [ ] 移除 cursor 对象，统一使用 db 接口

Phase 4: 验证和优化
  [ ] 所有单元测试通过
  [ ] 性能测试：确保 DAO 层不比原始代码慢
  [ ] 日志验证：所有 SQL 操作被记录
  [ ] 代码审查：确保没有 SQL 字符串拼接

Phase 5: 清理和文档
  [ ] 删除所有直接的 cursor 使用（只在 DAO 内部）
  [ ] 更新 ONBOARDING.md 关于数据库操作的部分
  [ ] 添加生产部署检查清单

6.2 集成步骤详解
────────────────

步骤 1：VATAuditPipeline 类集成

    class VATAuditPipeline:
        def __init__(self, config_obj):
            # ... 其他初始化
            from vat_audit_pipeline.utils.database import DatabaseConnection
            self.db = DatabaseConnection(
                self.settings.get_database_path('vat_audit.sqlite')
            )
            self.db.pragma_optimize(mode='wal')
            
            # 初始化 DAO
            from vat_audit_pipeline.utils.database import ODSDetailDAO, ODSHeaderDAO
            self.ods_detail_dao = ODSDetailDAO(self.db, self.settings.business_tag)
            self.ods_header_dao = ODSHeaderDAO(self.db, self.settings.business_tag)
        
        def __exit__(self):
            if self.db:
                self.db.close()

步骤 2：_prepare_ods_tables 集成

    def _prepare_ods_tables(self, detail_columns, header_columns, summary_columns):
        \"\"\"使用 DAO 创建或重置 ODS 表。\"\"\"
        try:
            with self.db.transaction():
                # 删除旧表
                self.ods_detail_dao.drop_table()
                # 创建新表（通过 to_sql）
                import pandas as pd
                pd.DataFrame(columns=list(detail_columns)).to_sql(
                    f"ODS_{self.settings.business_tag}_DETAIL",
                    self.db.connect(),
                    if_exists='replace',
                    index=False
                )
        except Exception as e:
            logger.error(f"ODS 表准备失败: {e}")
            raise

步骤 3：process_dwd 集成

    def process_dwd(self, process_time):
        \"\"\"使用 DAO 处理 DWD 和生成 LEDGER。\"\"\"
        ledger_rows = []
        
        # 使用 DAO 获取所有年份
        years = self.ods_detail_dao.get_distinct_years()
        
        for year in years:
            # 使用 DAO 查询该年份的明细
            details_rows = self.ods_detail_dao.find_by_year(year)
            
            # 转换为 DataFrame 进行业务逻辑处理
            import pandas as pd
            df = pd.DataFrame([dict(row) for row in details_rows])
            
            # ... 去重、转换逻辑
            
            # 写入 LEDGER 表
            from vat_audit_pipeline.utils.database import LedgerDAO
            ledger_dao = LedgerDAO(self.db, self.settings.business_tag, year, 'detail')
            df_dedup.to_sql(ledger_dao.table_name, self.db.connect(), if_exists='replace')
            
            ledger_rows.append({...})
        
        return ledger_rows

6.3 集成清单
─────────────

完成时检查：

    [ ] utils/database.py 存在且测试通过
    [ ] VATAuditPipeline 初始化 DatabaseConnection
    [ ] 所有 cursor 使用都被移除（或仅在 DAO 内）
    [ ] _prepare_ods_tables 使用 DAO
    [ ] process_dwd 使用 DAO 查询
    [ ] 所有 SQL 查询都使用参数化（无 f-string 拼接）
    [ ] 事务管理使用 db.transaction() 上下文
    [ ] tests/test_database_dao.py 通过 100% 覆盖
    [ ] 性能基准测试通过（相对原代码 <10% 差异）
    [ ] 文档更新完整（README, ONBOARDING, DEPLOYMENT）
"""


# ============================================================================
# 7. 常见问题解答（FAQ）
# ============================================================================

"""
Q1: SQLAlchemy 为什么不适合这个项目？
A: 本项目主要特点：
   - 数据库简单，几张表，无复杂关系映射
   - 需要性能优化（WAL、PRAGMA）的细粒度控制
   - 开发团队可能不熟悉 ORM 学习成本高
   - 轻量级项目不需要 ORM 的复杂性
   因此轻量级 DAO 层更合适。

Q2: DAO 层会增加性能开销吗？
A: 不会。DAO 层仅是对 sqlite3 的薄包装，没有额外的数据转换或映射。
   实际上由于统一的参数化查询和性能优化，可能会更快。
   性能基准：原始 vs DAO 通常 <1% 差异。

Q3: 如果项目后续需要支持多数据库怎么办？
A: DAOBase 设计考虑了这一点。可创建不同的 DatabaseConnection 子类
   （例如 PostgreSQLConnection, MySQLConnection）并保持 DAO 接口不变。
   但当前项目使用 SQLite，暂不需要多数据库支持。

Q4: 如何在单元测试中模拟数据库？
A: 有两种方法：
   1. 使用临时 SQLite 文件（推荐）：pytest fixture 创建临时文件
   2. 模拟 DatabaseConnection：使用 unittest.mock.Mock（复杂，一般不需要）
   
   参考 tests/test_database_dao.py 中的 populated_db fixture。

Q5: 性能优化（WAL、PRAGMA）如何应用？
A: 在 DatabaseConnection.pragma_optimize() 中集中管理：
   - WAL 模式：提升读写并发
   - PRAGMA synchronous=NORMAL：安全和性能的平衡
   - PRAGMA journal_mode=WAL：使用预写日志
   
   在 VATAuditPipeline.__init__ 中调用 db.pragma_optimize()。

Q6: 日志太多怎么配置？
A: 在 logger 配置中调整日志级别：
   - logger.setLevel(logging.INFO)：隐藏 DEBUG 日志（包括成功的查询）
   - logger.setLevel(logging.WARNING)：仅显示警告和错误
   
   或在 logging.yaml 中配置特定模块：
   loggers:
    vat_audit_pipeline.utils.database:
       level: WARNING

Q7: 并发写入时事务会不会冲突？
A: SQLite 的 WAL 模式支持并发读和单个写入者。
   如果多进程并发写入，需要：
   1. 使用线程安全的队列（项目已实现）
   2. 或在主进程中串行化所有写入（当前模式）
   本项目使用方案 2，通过队列和主进程合并确保串行写入。

Q8: 如何检查 SQL 注入是否彻底修复？
A: 运行以下检查：
   
   # 1. 检查是否有 f-string 拼接 SQL
   grep -n "execute(f\"" VAT_Invoice_Processor.py
   
   # 2. 检查是否有直接字符串拼接
   grep -n "execute('.*' \+" VAT_Invoice_Processor.py
   
   # 3. 运行参数化查询测试
   pytest tests/test_database_dao.py::TestParameterizedQueries -v
   
   结果应该全部为空或绿色通过。
"""


# ============================================================================
# 8. 生产部署清单
# ============================================================================

"""
部署前检查：

[ ] 1. 数据库文件路径（DATABASE_DIR）有写权限
[ ] 2. WAL 模式已启用（db.pragma_optimize('wal')）
[ ] 3. 日志级别设置正确（避免过度日志）
[ ] 4. 备份策略已设置（定期备份 Database/ 目录）
[ ] 5. 监控告警已配置（监控 vat_audit.log 中的错误）
[ ] 6. 性能基准已建立（已知的正常执行时间）
[ ] 7. 恢复计划已文档（如何恢复数据库损坏）
[ ] 8. 所有单元测试通过（pytest -q）
[ ] 9. 集成测试通过（小数据集完整流程）
[ ] 10. 文档已更新（DEPLOYMENT.md, README.md）

监控指标：

- 每次运行的总数据库操作数
- 平均查询时间和慢查询（>1000ms）
- 事务提交/回滚比例
- 临时文件清理情况
- 数据库文件大小增长趋势
"""


if __name__ == '__main__':
    print("""
    数据库抽象层设计文档
    ====================
    
    本文档位置：DATABASE_DAO_DESIGN.md
    
    相关文件：
    - utils/database.py：DAO 层实现
    - tests/test_database_dao.py：单元测试
    - DATABASE_DAO_INTEGRATION_GUIDE.md：集成指南和代码示例
    
    快速开始：
    1. 阅读本文档的第 1-3 节了解基本概念
    2. 查看 DATABASE_DAO_INTEGRATION_GUIDE.md 的示例代码
    3. 运行 pytest tests/test_database_dao.py -v 验证测试
    4. 按 6.1 的阶段计划逐步集成
    
    更多帮助：
    - 参数化查询：第 3 节
    - 事务管理：第 4 节
    - 集成步骤：第 6.2 节
    - FAQ：第 7 节
    """)
