<!-- 
错误处理集成指南 - 示例和最佳实践
-->

# 错误处理集成指南

本指南展示如何在项目代码中集成和使用统一的错误处理机制。

## 📚 目录

1. [快速开始](#快速开始)
2. [基础用法](#基础用法)
3. [集成模式](#集成模式)
4. [常见场景](#常见场景)
5. [最佳实践](#最佳实践)
6. [故障排查](#故障排查)

---

## 快速开始

### 安装和初始化

```python
from vat_audit_pipeline.utils.error_handling import (
    ErrorCollector,
    FileReadError,
    DatabaseQueryError,
    DataValidationError,
    ErrorCategory,
    ErrorLevel
)

# 初始化错误收集器（启用自动日志记录）
error_collector = ErrorCollector(auto_log=True)
```

### 最简单的例子

```python
import logging
from vat_audit_pipeline.utils.error_handling import ErrorCollector, FileReadError

logger = logging.getLogger(__name__)

def read_data_file(file_path: str):
    error_collector = ErrorCollector()
    
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError as e:
        error_collector.collect(FileReadError(file_path, str(e), e))
    except Exception as e:
        error_collector.collect_exception(
            e, 
            message=f"读取文件时发生未知错误: {file_path}"
        )
    
    # 如果有错误，生成报告
    if error_collector.has_errors():
        print(error_collector.get_report())
        return None
    
    return None

# 使用
result = read_data_file("non_existent.txt")
```

---

## 基础用法

### 1. 创建和使用异常

#### 文件相关异常

```python
from vat_audit_pipeline.utils.error_handling import (
    FileReadError, 
    FileWriteError, 
    FileNotFoundError_,
    PermissionError_
)

# 文件读取错误
try:
    with open("data.csv", "r") as f:
        data = f.read()
except FileNotFoundError as e:
    raise FileNotFoundError_("data.csv", original_error=e)
except IOError as e:
    raise FileReadError("data.csv", "I/O 错误", original_error=e)

# 文件写入错误
try:
    with open("output.csv", "w") as f:
        f.write(data)
except PermissionError as e:
    raise PermissionError_("output.csv", "写入", original_error=e)
except IOError as e:
    raise FileWriteError("output.csv", "I/O 错误", original_error=e)
```

#### 数据库相关异常

```python
from vat_audit_pipeline.utils.error_handling import (
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseTransactionError
)

# 连接错误
try:
    conn = sqlite3.connect(":memory:")
except Exception as e:
    raise DatabaseConnectionError(
        db_path="vat_audit.db",
        message="无法连接到数据库",
        original_error=e
    )

# 查询错误
try:
    cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
except Exception as e:
    raise DatabaseQueryError(
        message="查询发票失败",
        query="SELECT * FROM invoices WHERE id = ?",
        original_error=e
    )

# 事务错误
try:
    conn.commit()
except Exception as e:
    raise DatabaseTransactionError(
        message="提交事务失败",
        original_error=e
    )
```

#### 数据相关异常

```python
from vat_audit_pipeline.utils.error_handling import (
    DataValidationError,
    DataEncodingError,
    DataTypeError
)

# 数据验证错误
if not isinstance(invoice_amount, (int, float)):
    raise DataTypeError(
        field_name="invoice_amount",
        expected_type="float",
        actual_type=type(invoice_amount).__name__
    )

# 编码错误
detected_encoding = "GBK"  # 检测到 GBK 但期望 UTF-8
if detected_encoding != "UTF-8":
    raise DataEncodingError(
        file_path="data.csv",
        detected_encoding=detected_encoding,
        message="文件编码不是 UTF-8"
    )

# 验证错误
if not (0 <= invoice_amount <= 1000000):
    raise DataValidationError(
        field_name="invoice_amount",
        value=invoice_amount,
        message="金额超出允许范围 [0, 1000000]"
    )
```

#### Excel 相关异常

```python
from vat_audit_pipeline.utils.error_handling import ExcelParseError, ExcelSheetError

try:
    wb = openpyxl.load_workbook(excel_file)
except Exception as e:
    raise ExcelParseError(
        excel_file,
        "无法解析 Excel 文件",
        original_error=e
    )

try:
    ws = wb[sheet_name]
except KeyError as e:
    raise ExcelSheetError(
        excel_file,
        sheet_name,
        "工作表不存在"
    )
```

### 2. 使用 ErrorCollector

```python
from vat_audit_pipeline.utils.error_handling import ErrorCollector

# 创建收集器
collector = ErrorCollector(auto_log=True)

# 收集错误
try:
    result = process_data()
except Exception as e:
    collector.collect_exception(
        e,
        message="数据处理失败"
    )

# 检查是否有错误
if collector.has_errors():
    print("处理过程中出现错误")
    
    # 检查严重性
    if collector.has_critical():
        print("存在严重错误，处理中止")
        exit(1)
    
    # 获取报告
    report = collector.get_report()
    print(report)
```

### 3. 批量处理时的错误收集

```python
def process_multiple_files(file_list: List[str]):
    """处理多个文件，收集所有错误后生成报告"""
    error_collector = ErrorCollector(auto_log=False)  # 先不自动日志记录
    results = []
    
    for file_path in file_list:
        try:
            data = read_and_process(file_path)
            results.append(data)
        except FileNotFoundError as e:
            error_collector.collect(FileNotFoundError_(file_path, e))
        except Exception as e:
            error_collector.collect_exception(
                e,
                message=f"处理文件失败: {file_path}"
            )
    
    # 处理完毕，统一输出
    if error_collector.has_errors():
        print(error_collector.get_report())
        
        # 导出报告到文件
        error_collector.export_to_file("Outputs/error_report.txt")
    
    return results, error_collector
```

---

## 集成模式

### 模式 1: 函数级别的错误处理

```python
def load_invoice_data(file_path: str) -> Optional[pd.DataFrame]:
    """
    加载发票数据，返回 DataFrame 或 None。
    错误会被收集并返回。
    """
    error_collector = ErrorCollector()
    
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError_(file_path)
        
        # 读取 Excel
        df = pd.read_excel(file_path)
        
        # 验证数据
        if df.empty:
            error_collector.collect_exception(
                ValueError("数据为空"),
                message="Excel 文件没有数据"
            )
            return None
        
        return df
    
    except FileNotFoundError_ as e:
        error_collector.collect(e)
    except Exception as e:
        error_collector.collect_exception(e, message="加载文件时发生错误")
    
    if error_collector.has_errors():
        logger.error(error_collector.get_report())
    
    return None
```

### 模式 2: 类级别的错误管理

```python
class InvoiceProcessor:
    """发票处理器，维护全局错误收集器"""
    
    def __init__(self):
        self.error_collector = ErrorCollector(auto_log=True)
        self.stats = {
            'processed': 0,
            'failed': 0,
            'warnings': 0
        }
    
    def process_invoices(self, file_paths: List[str]) -> Dict[str, Any]:
        """处理多个文件"""
        self.error_collector.clear()  # 清空前次的错误
        
        for file_path in file_paths:
            try:
                self._process_single_file(file_path)
                self.stats['processed'] += 1
            except Exception as e:
                self.error_collector.collect_exception(
                    e,
                    context={'file_path': file_path}
                )
                self.stats['failed'] += 1
        
        return {
            'stats': self.stats,
            'errors': self.error_collector.to_dict(),
            'has_critical': self.error_collector.has_critical()
        }
    
    def _process_single_file(self, file_path: str):
        """处理单个文件"""
        # 具体实现...
        pass
    
    def get_summary(self) -> str:
        """获取处理摘要"""
        stats = self.error_collector.get_statistics()
        return f"处理统计: {self.stats} | 错误统计: {stats.to_dict()}"
```

### 模式 3: 上下文管理器（Context Manager）

```python
from contextlib import contextmanager

@contextmanager
def error_handling_context(stage_name: str):
    """错误处理上下文管理器"""
    error_collector = ErrorCollector()
    
    try:
        yield error_collector
    except Exception as e:
        error_collector.collect_exception(
            e,
            context={'stage': stage_name}
        )
    finally:
        if error_collector.has_errors():
            print(f"[{stage_name}] {error_collector.get_report()}")

# 使用
with error_handling_context("数据验证") as errors:
    # 验证数据
    validate_invoice_data(data)
```

---

## 常见场景

### 场景 1: Excel 文件处理

```python
def process_excel_invoices(excel_file: str) -> Tuple[List[Dict], ErrorCollector]:
    """
    从 Excel 文件读取发票数据。
    
    Returns:
        (发票列表, 错误收集器)
    """
    error_collector = ErrorCollector()
    invoices = []
    
    try:
        # 尝试加载 Excel
        wb = openpyxl.load_workbook(excel_file)
    except FileNotFoundError as e:
        error_collector.collect(FileNotFoundError_(excel_file, e))
        return [], error_collector
    except Exception as e:
        error_collector.collect(ExcelParseError(excel_file, str(e), e))
        return [], error_collector
    
    # 遍历工作表
    for sheet_name in wb.sheetnames:
        try:
            ws = wb[sheet_name]
        except Exception as e:
            error_collector.collect(ExcelSheetError(excel_file, sheet_name, str(e)))
            continue
        
        # 读取行
        for row in ws.iter_rows(min_row=2, values_only=True):
            try:
                invoice = {
                    'invoice_id': row[0],
                    'amount': float(row[1]),  # 可能失败
                    'date': row[2]
                }
                
                # 验证数据
                if not invoice['invoice_id']:
                    raise DataValidationError(
                        'invoice_id',
                        invoice['invoice_id'],
                        '发票 ID 不能为空'
                    )
                
                invoices.append(invoice)
            
            except DataValidationError as e:
                error_collector.collect(e)
            except ValueError as e:
                error_collector.collect_exception(
                    e,
                    message=f"数据类型错误: {e}",
                    context={'sheet': sheet_name}
                )
            except Exception as e:
                error_collector.collect_exception(e, context={'sheet': sheet_name})
    
    return invoices, error_collector
```

### 场景 2: 数据库操作

```python
def save_invoices_to_db(invoices: List[Dict], db_path: str) -> ErrorCollector:
    """
    将发票保存到数据库。
    
    Returns:
        错误收集器
    """
    error_collector = ErrorCollector()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
    except Exception as e:
        error_collector.collect(DatabaseConnectionError(db_path, str(e), e))
        return error_collector
    
    for invoice in invoices:
        try:
            cursor.execute(
                "INSERT INTO invoices (id, amount, date) VALUES (?, ?, ?)",
                (invoice['invoice_id'], invoice['amount'], invoice['date'])
            )
        except sqlite3.IntegrityError as e:
            error_collector.collect(DatabaseQueryError(
                "重复的发票 ID",
                context={'invoice_id': invoice['invoice_id']}
            ))
        except Exception as e:
            error_collector.collect_exception(
                e,
                message=f"插入发票失败: {invoice['invoice_id']}"
            )
    
    try:
        conn.commit()
    except Exception as e:
        error_collector.collect(DatabaseTransactionError("提交失败", e))
        conn.rollback()
    finally:
        conn.close()
    
    return error_collector
```

### 场景 3: CSV 导出

```python
def export_to_csv(data: pd.DataFrame, output_path: str) -> bool:
    """
    导出数据到 CSV，返回是否成功。
    """
    error_collector = ErrorCollector()
    
    try:
        # 创建目录
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 写入文件
        data.to_csv(output_path, encoding='utf-8-sig', index=False)
        logger.info(f"✓ 已导出到 {output_path}")
        return True
    
    except PermissionError as e:
        error_collector.collect(PermissionError_(output_path, "写入", e))
    except IOError as e:
        error_collector.collect(FileWriteError(output_path, str(e), e))
    except Exception as e:
        error_collector.collect_exception(e, message="导出失败")
    
    if error_collector.has_errors():
        logger.error(error_collector.get_report())
        return False
    
    return True
```

---

## 最佳实践

### 1. 错误消息的清晰性

```python
# ❌ 不好：太泛泛
raise VATAuditException("发生错误")

# ✅ 好：具体说明发生了什么
raise FileReadError(
    "invoices.xlsx",
    "文件格式无效，期望 Excel 2007+ 格式"
)
```

### 2. 上下文信息的完整性

```python
# ❌ 不好：缺乏上下文
try:
    process_data()
except Exception:
    error_collector.collect_exception(e)

# ✅ 好：包含相关上下文
try:
    process_data()
except Exception as e:
    error_collector.collect_exception(
        e,
        message=f"处理文件时出错: {file_path}",
        context={
            'file_path': file_path,
            'stage': 'data_validation',
            'row_number': row_num
        }
    )
```

### 3. 适当的日志级别

```python
# 严重错误（需要立即处理）
error_collector.collect(VATAuditException(
    "无法连接数据库",
    level=ErrorLevel.CRITICAL
))

# 一般错误（流程继续但记录）
error_collector.collect(VATAuditException(
    "某个字段值无效，跳过此行",
    level=ErrorLevel.ERROR
))

# 警告（可能的问题）
error_collector.collect(VATAuditException(
    "发票日期格式不标准但可以解析",
    level=ErrorLevel.WARNING
))
```

### 4. 报告导出

```python
# 处理完毕后导出报告
error_collector.export_to_file("Outputs/error_report.txt", detailed=True)

# 也可以导出为 JSON 用于程序处理
import json
error_dict = error_collector.to_dict()
with open("Outputs/error_report.json", "w") as f:
    json.dump(error_dict, f, indent=2, ensure_ascii=False)
```

### 5. 错误恢复策略

```python
def process_with_fallback(file_path: str):
    """
    处理文件，如果失败则尝试备选方案。
    """
    error_collector = ErrorCollector()
    
    # 尝试主方案
    try:
        return load_with_openpyxl(file_path)
    except Exception as e:
        error_collector.collect(ExcelParseError(file_path, str(e), e))
    
    # 尝试备选方案
    try:
        logger.warning("尝试使用备选解析器...")
        return load_with_pandas(file_path)
    except Exception as e:
        error_collector.collect(ExcelParseError(file_path, f"备选方案也失败: {e}", e))
        logger.error(error_collector.get_report())
        return None
```

---

## 故障排查

### 问题 1: 错误没有被记录

**原因**: 可能是日志级别设置过高，或日志处理器未配置正确。

```python
# 检查日志配置
import logging

# 确保日志级别足够低
logging.getLogger('vat_audit_pipeline.utils.error_handling').setLevel(logging.DEBUG)

# 或者禁用自动日志记录，手动处理
error_collector = ErrorCollector(auto_log=False)
# ... 处理
if error_collector.has_errors():
    print(error_collector.get_report())
```

### 问题 2: 如何检查特定类型的错误

```python
from vat_audit_pipeline.utils.error_handling import ErrorCategory, ErrorLevel

# 检查是否有文件相关的错误
has_file_errors = error_collector.has_errors_of_category(ErrorCategory.FILE_READ)

# 获取所有严重错误
critical_errors = error_collector.get_errors_by_level(ErrorLevel.CRITICAL)

# 获取特定分类的错误
db_errors = error_collector.get_errors_by_category(ErrorCategory.DATABASE_QUERY)
```

### 问题 3: 如何保留原始异常信息

```python
# 所有 VATAuditException 都保存了原始异常
error = error_collector.errors[0]

if error.original_error:
    print(f"原始异常: {type(error.original_error).__name__}")
    print(f"追踪栈: {error.original_error.__traceback__}")
    import traceback
    traceback.print_tb(error.original_error.__traceback__)
```

---

## 总结

统一的错误处理机制提供了：

✅ **结构化异常** - 易于分类和处理
✅ **集中管理** - 统一的错误收集和报告
✅ **丰富的上下文** - 完整的错误信息用于调试
✅ **灵活的报告** - 多种格式的输出和导出
✅ **类型安全** - 明确的异常层次和分类

遵循这些指南，可以显著提高代码的健壮性和可维护性。
