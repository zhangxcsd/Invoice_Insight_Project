# 数据库 DAO 层快速参考卡

## 🚀 30 秒快速开始

```python
from vat_audit_pipeline.utils.database import DatabaseConnection, ODSDetailDAO

# 初始化
db = DatabaseConnection('path/to/db.sqlite')
ods_dao = ODSDetailDAO(db, 'PURCHASE')

# 查询
years = ods_dao.get_distinct_years()
records = ods_dao.find_by_year('2023')

# 事务
with db.transaction():
    db.execute_insert("INSERT INTO ... VALUES (?, ?)", (val1, val2))

# 关闭
db.close()
```

---

## 📚 核心 API

### DatabaseConnection

| 方法 | 用途 | 返回 |
|------|------|------|
| `connect()` | 建立连接 | Connection |
| `execute_select(query, params)` | SELECT 查询 | QueryResult |
| `execute_insert(query, params)` | INSERT 操作 | QueryResult |
| `execute_update(query, params)` | UPDATE 操作 | QueryResult |
| `execute_delete(query, params)` | DELETE 操作 | QueryResult |
| `transaction()` | 事务上下文 | Context |
| `pragma_optimize(mode)` | 性能优化 | None |
| `close()` | 关闭连接 | None |

### QueryResult

| 属性/方法 | 说明 |
|-----------|------|
| `.rows` | 查询返回的行（元组列表） |
| `.columns` | 列名列表 |
| `.rowcount` | 受影响的行数 |
| `.error` | 错误信息（无错误为 None） |
| `.execution_time_ms` | 执行时间（毫秒） |
| `.is_success()` | 是否成功 |
| `.to_dict_list()` | 转换为字典列表 |
| `.to_first_dict()` | 获取第一行字典 |

### DAOBase

| 方法 | 用途 |
|------|------|
| `find_all(order_by, limit)` | 查询全部 |
| `find_by_id(id_value, id_column)` | 按 ID 查询 |
| `find_where(where_clause, params, order_by, limit)` | 按条件查询 |
| `count(where_clause, params)` | 统计行数 |
| `insert(columns, values)` | 批量插入 |
| `delete_where(where_clause, params)` | 按条件删除 |
| `create_index(index_name, columns, unique)` | 创建索引 |
| `table_exists()` | 检查表存在 |
| `truncate()` | 清空表 |

### 具体 DAO（ODSDetailDAO / ODSHeaderDAO / LedgerDAO）

| 方法 | 用途 |
|------|------|
| `find_by_invoice(code, number)` | 按发票号查询 |
| `find_by_year(year)` | 按年份查询 |
| `get_distinct_years()` | 获取所有年份 |
| `count_by_year(year)` | 按年份统计 |

---

## 🔒 参数化查询

### ❌ 危险做法

```python
# 不要这样做！
year = user_input
cursor.execute(f"SELECT * FROM table WHERE year='{year}'")
```

### ✅ 正确做法

```python
# 这样做是安全的
result = db.execute_select(
    "SELECT * FROM table WHERE year=?",
    (year,)  # 参数通过元组传入
)
```

---

## 💾 事务管理

### ❌ 手动管理

```python
cursor.execute('BEGIN IMMEDIATE')
try:
    cursor.execute(...)
    conn.commit()
except:
    conn.rollback()
```

### ✅ 自动管理

```python
with db.transaction():
    db.execute_insert(...)
    # 自动 COMMIT；异常自动 ROLLBACK
```

---

## 📖 常用模式

### 模式 1：简单查询

```python
result = db.execute_select("SELECT * FROM users LIMIT 10")
if result.is_success():
    for row in result.to_dict_list():
        print(row['name'])
else:
    logger.error(f"查询失败: {result.error}")
```

### 模式 2：批量插入

```python
with db.transaction():
    for record in records:
        result = db.execute_insert(
            "INSERT INTO table (col1, col2) VALUES (?, ?)",
            record
        )
        if not result.is_success():
            raise Exception(f"插入失败: {result.error}")
```

### 模式 3：按条件查询

```python
dao = SomeDAO(db, table_name)
records = dao.find_where(
    "year=? AND amount > ?",
    ('2023', 1000),
    order_by="date DESC",
    limit=100
)
```

### 模式 4：性能分析

```python
result = db.execute_select(...)
if result.execution_time_ms > 1000:
    logger.warning(f"慢查询: {result.execution_time_ms:.0f}ms")
```

---

## 🔧 DAO 初始化

### 通用 DAO

```python
dao = DAOBase(db, "my_table")
```

### ODS 层 DAO

```python
ods_detail = ODSDetailDAO(db, "PURCHASE")
ods_header = ODSHeaderDAO(db, "PURCHASE")
```

### Ledger DAO

```python
ledger = LedgerDAO(db, "PURCHASE", "2023", "detail")
# 或
ledger = LedgerDAO(db, "PURCHASE", "2023", "header")
```

### ADS 分析 DAO

```python
ads = OADSAnalyticsDAO(db, "ADS_PURCHASE_TAX_ANOMALY")
```

---

## ⚙️ 性能优化

### 启用 WAL 模式

```python
db = DatabaseConnection(db_path)
db.pragma_optimize(mode='wal')  # 并发读写更快
```

### 创建索引

```python
dao.create_index(
    "idx_table_col",
    ["column1", "column2"]
)
```

### 使用条件查询减少数据

```python
records = dao.find_where(
    "status=?",
    ('active',),
    limit=1000  # 分页查询
)
```

---

## 🧪 单元测试

### 运行所有测试

```bash
pytest tests/test_database_dao.py -v
```

### 运行特定测试

```bash
pytest tests/test_database_dao.py::TestDatabaseConnection -v
```

### 运行 SQL 注入测试

```bash
pytest tests/test_database_dao.py::TestParameterizedQueries -v
```

---

## 📝 异常处理

### 异常类型

```python
from vat_audit_pipeline.utils.database import (
    DatabaseConnectionError,  # 连接失败
    DatabaseQueryError,       # 查询异常
    SQLInjectionError         # SQL 注入风险
)
```

### 处理异常

```python
try:
    result = db.execute_select(...)
except DatabaseConnectionError as e:
    logger.error(f"连接失败: {e}")
except DatabaseQueryError as e:
    logger.error(f"查询异常: {e}")
except Exception as e:
    logger.error(f"未知异常: {e}")
finally:
    db.close()
```

---

## 📚 更多信息

| 资源 | 用途 |
|------|------|
| `DATABASE_DAO_DESIGN.md` | 深度设计（8 章） |
| `DATABASE_DAO_INTEGRATION_GUIDE.md` | 集成指南（8 个示例） |
| `IMPLEMENTATION_EXAMPLE_DAO.py` | 实际集成示例 |
| `DATABASE_DAO_SUMMARY.md` | 实现总结 |
| `utils/database.py` | 源码注释 |
| `tests/test_database_dao.py` | 测试用例 |

---

## 🎯 下一步

1. ✅ 运行测试：`pytest tests/test_database_dao.py -v`
2. ✅ 阅读设计文档：`DATABASE_DAO_DESIGN.md`
3. ✅ 查看集成示例：`IMPLEMENTATION_EXAMPLE_DAO.py`
4. ⏳ 开始 Phase 2 集成（预计 6-10 天）

---

## 💡 常见问题

**Q: 如何初始化 DAO？**  
A: `dao = ODSDetailDAO(db, 'BUSINESS_TAG')`

**Q: 如何避免 SQL 注入？**  
A: 使用参数化查询，所有用户输入通过 `params` 参数传入

**Q: 如何管理事务？**  
A: 使用 `with db.transaction():` 上下文管理器

**Q: 如何性能分析？**  
A: 检查 `result.execution_time_ms`

**Q: 需要安装额外库吗？**  
A: 不需要，仅使用 Python 标准库 `sqlite3`

---

## 📞 支持

遇到问题？查看：
1. `DATABASE_DAO_DESIGN.md` 的 FAQ 部分
2. `tests/test_database_dao.py` 的测试用例
3. `utils/database.py` 的源码注释

---

**更新时间：** 2026 年 1 月 4 日  
**版本：** 1.0  
**状态：** ✅ 生产就绪
