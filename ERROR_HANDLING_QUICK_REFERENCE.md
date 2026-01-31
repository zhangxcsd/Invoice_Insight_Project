<!-- 错误处理快速参考指南 -->

# 错误处理快速参考

快速查询表，用于在代码中快速集成错误处理。

## 📋 异常类列表

### 文件异常
| 异常类 | 何时使用 | 示例 |
|-------|--------|------|
| `FileReadError` | 文件读取失败 | `FileReadError("data.csv", "编码错误", original_error)` |
| `FileWriteError` | 文件写入失败 | `FileWriteError("output.xlsx", "磁盘已满")` |
| `FileNotFoundError_` | 文件不存在 | `FileNotFoundError_("missing.txt")` |
| `PermissionError_` | 无权限访问 | `PermissionError_("protected.txt", "读取")` |

### 数据库异常
| 异常类 | 何时使用 | 示例 |
|-------|--------|------|
| `DatabaseConnectionError` | 连接失败 | `DatabaseConnectionError("vat.db", "连接被拒绝")` |
| `DatabaseQueryError` | 查询失败 | `DatabaseQueryError("语法错误", query="SELECT...")` |
| `DatabaseTransactionError` | 事务失败 | `DatabaseTransactionError("提交失败")` |

### 数据异常
| 异常类 | 何时使用 | 示例 |
|-------|--------|------|
| `DataValidationError` | 数据验证失败 | `DataValidationError("amount", 9999999, "超出范围")` |
| `DataEncodingError` | 编码不匹配 | `DataEncodingError("data.csv", "GBK", "期望 UTF-8")` |
| `DataTypeError` | 类型不匹配 | `DataTypeError("field", "str", "int")` |

### Excel 异常
| 异常类 | 何时使用 | 示例 |
|-------|--------|------|
| `ExcelParseError` | Excel 解析失败 | `ExcelParseError("data.xlsx", "文件损坏")` |
| `ExcelSheetError` | 工作表问题 | `ExcelSheetError("data.xlsx", "Sheet1", "不存在")` |

### 其他异常
| 异常类 | 何时使用 | 示例 |
|-------|--------|------|
| `ConfigError` | 配置错误 | `ConfigError("db.path", "路径无效")` |
| `MemoryError_` | 内存不足 | `MemoryError_("large.xlsx", 2048.5)` |

---

## 🚀 快速模式

### 模式 1: 基础异常处理

```python
from vat_audit_pipeline.utils.error_handling import ErrorCollector, FileReadError

collector = ErrorCollector()

try:
    with open("data.csv") as f:
        data = f.read()
except FileNotFoundError as e:
    collector.collect(FileNotFoundError_("data.csv", e))
except Exception as e:
    collector.collect_exception(e, message="读取失败")
```

### 模式 2: 单函数处理

```python
def load_data(file_path: str) -> Optional[dict]:
    error_collector = ErrorCollector()
    
    try:
        return process(file_path)
    except Exception as e:
        error_collector.collect_exception(e)
        return None
```

### 模式 3: 批量处理

```python
collector = ErrorCollector(auto_log=False)

for file in files:
    try:
        process(file)
    except Exception as e:
        collector.collect_exception(e, context={'file': file})

if collector.has_errors():
    print(collector.get_report())
    collector.export_to_file("Outputs/errors.txt")
```

---

## 🔍 常用检查

```python
# 检查是否有错误
if collector.has_errors():
    # 处理错误

# 检查严重性
if collector.has_critical():
    # 立即停止

# 按级别检查
if collector.has_errors_of_level(ErrorLevel.CRITICAL):
    # 严重错误

# 按分类检查
if collector.has_errors_of_category(ErrorCategory.FILE_READ):
    # 文件相关错误
```

---

## 📊 报告和导出

```python
# 获取简单报告
print(collector.get_report(detailed=False))

# 获取详细报告
print(collector.get_report(detailed=True))

# 导出到文件
collector.export_to_file("Outputs/error_report.txt")

# 转换为字典（JSON）
import json
data = collector.to_dict()
with open("errors.json", "w") as f:
    json.dump(data, f)

# 获取统计信息
stats = collector.get_statistics()
print(f"总错误数: {stats.total}")
print(f"严重错误: {stats.critical_count}")
```

---

## 🎯 错误级别速查

| 级别 | 说明 | 何时使用 |
|-----|------|--------|
| `CRITICAL` | 严重，流程无法继续 | 无法连接数据库、内存不足 |
| `ERROR` | 错误，某个操作失败 | 文件读取失败、数据验证失败 |
| `WARNING` | 警告，异常但可继续 | 数据格式不标准但可解析 |
| `INFO` | 信息，记录用途 | 调试信息 |

---

## 🔄 错误分类速查

| 分类 | 相关异常 |
|-----|---------|
| `FILE_READ` | FileReadError |
| `FILE_WRITE` | FileWriteError |
| `FILE_NOT_FOUND` | FileNotFoundError_ |
| `PERMISSION` | PermissionError_ |
| `DB_CONNECTION` | DatabaseConnectionError |
| `DB_QUERY` | DatabaseQueryError |
| `DB_TRANSACTION` | DatabaseTransactionError |
| `DATA_VALIDATION` | DataValidationError |
| `DATA_ENCODING` | DataEncodingError |
| `DATA_TYPE` | DataTypeError |
| `EXCEL_PARSE` | ExcelParseError |
| `EXCEL_SHEET` | ExcelSheetError |
| `CONFIG_ERROR` | ConfigError |
| `MEMORY_ERROR` | MemoryError_ |

---

## 📌 常见任务

### 读取文件并处理错误

```python
from vat_audit_pipeline.utils.error_handling import FileReadError, FileNotFoundError_

try:
    with open(file_path) as f:
        return f.read()
except FileNotFoundError as e:
    raise FileNotFoundError_(file_path, e)
except IOError as e:
    raise FileReadError(file_path, str(e), e)
```

### 数据库查询

```python
from vat_audit_pipeline.utils.error_handling import DatabaseQueryError

try:
    cursor.execute(query, params)
    return cursor.fetchall()
except Exception as e:
    raise DatabaseQueryError("查询失败", query=query, original_error=e)
```

### 数据验证

```python
from vat_audit_pipeline.utils.error_handling import DataValidationError, DataTypeError

if not isinstance(value, expected_type):
    raise DataTypeError(field_name, expected_type.__name__, type(value).__name__)

if not is_valid(value):
    raise DataValidationError(field_name, value, "验证失败")
```

### 批量处理多个文件

```python
collector = ErrorCollector(auto_log=False)
results = []

for file_path in file_list:
    try:
        results.append(process_file(file_path))
    except FileNotFoundError as e:
        collector.collect(FileNotFoundError_(file_path, e))
    except Exception as e:
        collector.collect_exception(e, context={'file': file_path})

# 报告
if collector.has_errors():
    print(collector.get_report())
    
    # 是否继续？
    if collector.has_critical():
        exit(1)

return results
```

---

## 🆘 故障排查

| 问题 | 解决方案 |
|------|--------|
| 未记录错误 | 检查日志级别，或设置 `auto_log=True` |
| 错误信息不清楚 | 添加具体的消息和上下文信息 |
| 需要看原始异常 | 使用 `error.original_error` |
| 需要追踪错误发生位置 | 使用 `context` 参数添加文件、行号等信息 |

---

## 📚 相关文件

- **实现**: [utils/error_handling.py](utils/error_handling.py)
- **测试**: [tests/test_error_handling.py](tests/test_error_handling.py)
- **详细指南**: [ERROR_HANDLING_INTEGRATION_GUIDE.md](ERROR_HANDLING_INTEGRATION_GUIDE.md)
- **DAO 集成**: [utils/database.py](utils/database.py) - 数据库异常用法示例
