# VAT_Invoice_Processor 快速参考指南

## 📚 主要入口

### VATAuditPipeline 类 - 完整审计流程
```python
from VAT_Invoice_Processor import VATAuditPipeline

pipeline = VATAuditPipeline()
pipeline.run()  # 执行完整的审计流程
```

**关键方法：**
- `__init__()` - 初始化并加载配置
- `load_config()` - 从 config.yaml 加载配置
- `scan_excel_files()` - 扫描输入目录
- `scan_excel_metadata()` - 识别工作表分类
- `init_database()` - 初始化数据库
- `run()` - 执行完整流程
- `clean_temp_files()` - 清理临时文件

## 🔧 核心函数分类

### 文件处理
| 函数 | 用途 | 返回 |
|------|------|------|
| `validate_input_file(file_path, max_mb)` | 验证文件可读性和大小 | Tuple[bool, str] |
| `is_xls_file(file_path)` | 检测 XLS 格式 | bool |
| `read_excel_with_engine(file, sheet)` | 读取 Excel 数据 | pd.DataFrame |

### 数据处理
| 函数 | 用途 | 返回 |
|------|------|------|
| `process_single_sheet(...)` | 处理单个工作表 | Tuple[int, str, str] |
| `stream_read_and_write_csv(...)` | 大文件流式读写 | int |
| `cast_and_record(df, fname, sheet, ...)` | 类型转换和统计 | pd.DataFrame |

### 系统资源
| 函数 | 用途 | 返回 |
|------|------|------|
| `get_memory_usage_mb()` | 查询进程内存 | float |
| `get_available_memory_mb()` | 查询可用内存 | float |
| `measure_disk_busy_percent()` | 磁盘 I/O 监控 | Optional[float] |
| `should_use_streaming_for_file(...)` | 决定是否流式处理 | bool |

### 并行处理
| 函数 | 用途 | 返回 |
|------|------|------|
| `calculate_optimal_workers(...)` | 动态计算 worker 数 | int |
| `process_file_worker(args)` | 串行处理 worker | Dict[str, Any] |
| `process_file_worker_with_queue(args)` | 队列模式 worker | Dict[str, Any] |

### 数据管道
| 函数 | 用途 | 返回 |
|------|------|------|
| `process_ods(...)` | ODS 层处理（导入） | Dict[str, Any] |
| `process_dwd(conn, time)` | DWD 层处理（去重） | Tuple[List, List, List] |
| `export_duplicates(...)` | 导出重复数据 | Dict[str, Optional[str]] |
| `process_ads(conn)` | ADS 层处理（审计） | None |

### 输出和清理
| 函数 | 用途 | 返回 |
|------|------|------|
| `write_error_logs(logs, time, ...)` | 导出错误日志 | Tuple[str, str] |
| `suggest_remedy_for_error(type, msg)` | 生成修复建议 | str |
| `cleanup_temp_files(path)` | 清理临时文件 | None |

## 🚀 常见场景

### 场景 1: 运行完整审计流程
```python
from VAT_Invoice_Processor import VATAuditPipeline

pipeline = VATAuditPipeline()
pipeline.run()
# 输出：
#   - ODS 层数据入库
#   - DWD 台账生成
#   - 重复数据识别
#   - 清单和报告导出
```

### 场景 2: 单文件处理
```python
from VAT_Invoice_Processor import read_excel_with_engine, cast_and_record

df = read_excel_with_engine('input.xlsx', sheet_name='Sheet1')
cast_stats = []
cast_failures = []
df = cast_and_record(df, 'input.xlsx', 'Sheet1', cast_stats, cast_failures)
print(f"类型转换统计: {cast_stats}")
```

### 场景 3: 大文件流式处理
```python
from VAT_Invoice_Processor import should_use_streaming_for_file, stream_read_and_write_csv

if should_use_streaming_for_file('large_file.xlsx'):
    rows = stream_read_and_write_csv(
        'large_file.xlsx', 'Sheet1', ['col1', 'col2'],
        'output.csv', 'large_file.xlsx', 'Sheet1',
        [], [], '2024-01-02T12:00:00'
    )
    print(f"处理了 {rows} 行")
```

### 场景 4: 资源监控
```python
from VAT_Invoice_Processor import (
    get_memory_usage_mb,
    get_available_memory_mb,
    measure_disk_busy_percent
)

mem_used = get_memory_usage_mb()
mem_avail = get_available_memory_mb()
disk_busy = measure_disk_busy_percent()

print(f"内存使用: {mem_used:.1f}MB / 可用: {mem_avail:.1f}MB")
print(f"磁盘繁忙度: {disk_busy:.1f}%" if disk_busy else "磁盘繁忙度: 不可获")
```

### 场景 5: 数据库操作
```python
import sqlite3
from VAT_Invoice_Processor import merge_temp_csvs_to_db

conn = sqlite3.connect('data.db')
table_cols = {
    'ODS_VAT_DETAIL': ['col1', 'col2', ...],
    'ODS_VAT_HEADER': ['col1', 'col2', ...],
}
errors = []
merge_temp_csvs_to_db('/tmp/worker_output', conn, table_cols, errors)
conn.close()

if errors:
    print(f"发现 {len(errors)} 个错误")
    for err in errors:
        print(f"  {err}")
```

### 场景 6: 错误处理和日志
```python
from VAT_Invoice_Processor import suggest_remedy_for_error, write_error_logs

# 获取修复建议
advice = suggest_remedy_for_error('MemoryError', 'out of memory')
print(f"建议: {advice}")

# 导出错误日志
error_logs = [
    {'file': 'test.xlsx', 'stage': 'read', 'error_type': 'ValueError', 'message': '...'},
]
csv_path, json_path = write_error_logs(error_logs, '2024-01-02T12:00:00', 'Outputs/')
print(f"错误日志已导出: {csv_path}, {json_path}")
```

## 📊 数据流图

```
输入文件 (Source_Data/)
    ↓
[scan_excel_files] ← 验证文件大小和格式
    ↓
[scan_excel_metadata] ← 识别工作表分类
    ↓
[process_ods] ← ODS 层处理
    ├─ [process_file_worker/process_file_worker_with_queue]
    ├─ [stream_read_and_write_csv] ← 大文件流式处理
    ├─ [cast_and_record] ← 类型转换
    └─ [merge_temp_csvs_to_db] ← 批量入库
    ↓
[process_dwd] ← DWD 层去重
    └─ [export_duplicates] ← 导出重复数据
    ↓
[process_ads] ← ADS 审计分析
    ↓
输出清单和报告 (Outputs/)
    ├─ ods_sheet_manifest_*.csv
    ├─ 发票台账重复数据清单.xlsx
    └─ 审计异常税率检测.csv
```

## 🔍 类型参考

### 常用类型别名
```python
from typing import List, Dict, Optional, Tuple, Union, Any

# 工作表元数据
Dict[str, List[str]]  # {sheet_name: [col1, col2, ...]}

# 处理结果
Dict[str, Any]  # {key: value, ...}

# 返回值
Tuple[int, str, str]  # (rows, classification, path)
Tuple[bool, str]  # (success, message)

# 可选参数
Optional[str]  # 可能为 None
Optional[List[str]]  # 可能为 None 或列表

# 错误日志列表
List[Dict[str, Any]]  # [{file: '...', error_type: '...', ...}, ...]
```

## ⚙️ 配置关键参数

从 `config.yaml` 读取的关键配置：

```yaml
# 业务配置
business_tag: "VAT"  # 业务标识

# 路径配置
input_dir: "Source_Data"
database_dir: "Database"
output_dir: "Outputs"

# 并行配置
parallel_enabled: true
worker_count: 4

# 内存配置
memory_monitoring:
  enabled: true
  large_file_streaming_mb: 100
  stream_switch_threshold_percent: 75

# I/O 节流
io_throttle:
  enabled: true
  busy_threshold_percent: 75
```

## 📝 最佳实践

### 1. 错误处理
```python
try:
    df = read_excel_with_engine('file.xlsx')
except FileNotFoundError:
    logger.error("文件不存在")
except MemoryError:
    # 自动降级为流式处理
    pass
```

### 2. 大文件处理
```python
if should_use_streaming_for_file('large_file.xlsx'):
    rows = stream_read_and_write_csv(...)
else:
    df = read_excel_with_engine('large_file.xlsx')
```

### 3. 资源监控
```python
mem_used = get_memory_usage_mb()
if mem_used > threshold:
    # 清理或进行垃圾回收
    gc.collect()
```

### 4. 并行处理
```python
workers = calculate_optimal_workers(
    excel_files, worker_count,
    disk_busy_percent=disk_busy
)
# 使用 workers 数量创建 Process Pool
```

### 5. 日志导出
```python
csv_path, json_path = write_error_logs(
    errors, process_time, output_dir
)
# 供后续审计和问题诊断
```

## 🔗 相关文件

- [VAT_Invoice_Processor.py](VAT_Invoice_Processor.py) - 主程序
- [config.yaml](config.yaml) - 配置文件
- [config_manager.py](config_manager.py) - 配置管理
- [DOCUMENTATION_COMPLETION_SUMMARY.md](DOCUMENTATION_COMPLETION_SUMMARY.md) - 文档完善总结
- [README.md](README.md) - 项目说明

## 📞 获取帮助

### Docstring 查询
```python
from VAT_Invoice_Processor import VATAuditPipeline
help(VATAuditPipeline.run)  # 查看完整 docstring
```

### 类型检查
```bash
mypy VAT_Invoice_Processor.py
```

### 语法验证
```bash
python -m py_compile VAT_Invoice_Processor.py
```

---

**更新时间**：2024-01-02  
**版本**：1.0（文档完善版）  
**验证状态**：✅ 无语法错误，类型注解完整
