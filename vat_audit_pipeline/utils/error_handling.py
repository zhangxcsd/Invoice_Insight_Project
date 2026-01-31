"""
统一错误处理机制

提供：
1. 结构化异常类（FileReadError、DatabaseError、DataValidationError 等）
2. ErrorCollector 类用于集中收集、分类和输出错误
3. 错误上下文追踪和报告功能

设计原则：
- 异常应该被分类（文件、数据库、数据验证等）
- 每个异常都包含足够的上下文信息
- ErrorCollector 支持在处理流程中累积错误而不中断
- 最后统一输出错误报告
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ErrorLevel(Enum):
    """错误严重级别"""

    CRITICAL = "CRITICAL"  # 严重，流程无法继续
    ERROR = "ERROR"  # 错误，某个操作失败
    WARNING = "WARNING"  # 警告，异常但可继续
    INFO = "INFO"  # 信息，记录用途


class ErrorCategory(Enum):
    """错误分类"""

    FILE_READ = "FILE_READ"  # 文件读取错误
    FILE_WRITE = "FILE_WRITE"  # 文件写入错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"  # 文件不存在
    PERMISSION = "PERMISSION"  # 权限错误

    DATABASE_CONNECTION = "DB_CONNECTION"  # 数据库连接错误
    DATABASE_QUERY = "DB_QUERY"  # 数据库查询错误
    DATABASE_TRANSACTION = "DB_TRANSACTION"  # 事务错误

    DATA_VALIDATION = "DATA_VALIDATION"  # 数据验证错误
    DATA_ENCODING = "DATA_ENCODING"  # 数据编码错误
    DATA_TYPE = "DATA_TYPE"  # 数据类型错误

    EXCEL_PARSE = "EXCEL_PARSE"  # Excel 解析错误
    EXCEL_SHEET = "EXCEL_SHEET"  # Excel 工作表错误

    CONFIG_ERROR = "CONFIG_ERROR"  # 配置错误
    MEMORY_ERROR = "MEMORY_ERROR"  # 内存错误
    UNKNOWN = "UNKNOWN"  # 未知错误


class VATAuditException(Exception):
    """
    VAT 审计项目的基础异常类。

    属性：
        category: 错误分类
        level: 错误级别
        message: 错误信息
        context: 错误上下文（如文件名、行号等）
        original_error: 原始异常对象
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        level: ErrorLevel = ErrorLevel.ERROR,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.category = category
        self.level = level
        self.context = context or {}
        self.original_error = original_error
        self.timestamp = datetime.now()
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.category.value}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于序列化和报告"""

        return {
            "timestamp": self.timestamp.isoformat(),
            "category": self.category.value,
            "level": self.level.value,
            "message": self.message,
            "context": self.context,
            "original_error": str(self.original_error) if self.original_error else None,
        }


# ============================================================================
# 文件相关异常
# ============================================================================


class FileError(VATAuditException):
    """文件相关错误的基类"""

    def __init__(self, file_path: str, message: str, **kwargs):
        self.file_path = file_path
        context = kwargs.pop("context", {})
        context["file_path"] = file_path
        super().__init__(message, context=context, **kwargs)


class FileReadError(FileError):
    """文件读取错误"""

    def __init__(self, file_path: str, message: str, original_error: Exception = None):
        super().__init__(
            file_path,
            f"读取文件失败: {message}",
            category=ErrorCategory.FILE_READ,
            original_error=original_error,
        )


class FileWriteError(FileError):
    """文件写入错误"""

    def __init__(self, file_path: str, message: str, original_error: Exception = None):
        super().__init__(
            file_path,
            f"写入文件失败: {message}",
            category=ErrorCategory.FILE_WRITE,
            original_error=original_error,
        )


class FileNotFoundError_(FileError):
    """文件不存在"""

    def __init__(self, file_path: str, original_error: Exception = None):
        super().__init__(
            file_path,
            "文件不存在",
            category=ErrorCategory.FILE_NOT_FOUND,
            original_error=original_error,
        )


class PermissionError_(FileError):
    """权限错误"""

    def __init__(
        self,
        file_path: str,
        operation: str = "访问",
        original_error: Exception = None,
    ):
        super().__init__(
            file_path,
            f"无权限{operation}文件",
            category=ErrorCategory.PERMISSION,
            original_error=original_error,
        )


# ============================================================================
# 数据库相关异常
# ============================================================================


class DatabaseError(VATAuditException):
    """数据库相关错误的基类"""

    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        context = kwargs.pop("context", {})
        if query:
            context["query"] = query[:100]  # 只保存前 100 字符
        super().__init__(message, context=context, **kwargs)


class DatabaseConnectionError(DatabaseError):
    """数据库连接错误"""

    def __init__(self, db_path: str, message: str, original_error: Exception = None):
        super().__init__(
            f"数据库连接失败 ({db_path}): {message}",
            category=ErrorCategory.DATABASE_CONNECTION,
            context={"db_path": db_path},
            original_error=original_error,
        )


class DatabaseQueryError(DatabaseError):
    """数据库查询错误"""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        original_error: Exception = None,
    ):
        super().__init__(
            f"数据库查询失败: {message}",
            query=query,
            category=ErrorCategory.DATABASE_QUERY,
            original_error=original_error,
        )


class DatabaseTransactionError(DatabaseError):
    """数据库事务错误"""

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(
            f"数据库事务失败: {message}",
            category=ErrorCategory.DATABASE_TRANSACTION,
            original_error=original_error,
        )


# ============================================================================
# 数据相关异常
# ============================================================================


class DataError(VATAuditException):
    """数据处理相关错误的基类"""


class DataValidationError(DataError):
    """数据验证错误"""

    def __init__(self, field_name: str, value: Any, message: str):
        super().__init__(
            f"数据验证失败 (字段: {field_name}): {message}",
            category=ErrorCategory.DATA_VALIDATION,
            context={"field_name": field_name, "value": str(value)[:50]},
        )


class DataEncodingError(DataError):
    """数据编码错误"""

    def __init__(self, file_path: str, detected_encoding: str, message: str = ""):
        msg = f"数据编码错误 ({detected_encoding})"
        if message:
            msg += f": {message}"
        super().__init__(
            msg,
            category=ErrorCategory.DATA_ENCODING,
            context={"file_path": file_path, "encoding": detected_encoding},
        )


class DataTypeError(DataError):
    """数据类型错误"""

    def __init__(self, field_name: str, expected_type: str, actual_type: str):
        super().__init__(
            f"数据类型错误 (字段: {field_name}, 期望: {expected_type}, 实际: {actual_type})",
            category=ErrorCategory.DATA_TYPE,
            context={
                "field_name": field_name,
                "expected": expected_type,
                "actual": actual_type,
            },
        )


# ============================================================================
# Excel 相关异常
# ============================================================================


class ExcelError(VATAuditException):
    """Excel 相关错误的基类"""

    def __init__(self, file_path: str, message: str, **kwargs):
        self.file_path = file_path
        context = kwargs.pop("context", {})
        context["file_path"] = file_path
        super().__init__(message, context=context, **kwargs)


class ExcelParseError(ExcelError):
    """Excel 解析错误"""

    def __init__(self, file_path: str, message: str, original_error: Exception = None):
        super().__init__(
            file_path,
            f"解析 Excel 文件失败: {message}",
            category=ErrorCategory.EXCEL_PARSE,
            original_error=original_error,
        )


class ExcelSheetError(ExcelError):
    """Excel 工作表错误"""

    def __init__(self, file_path: str, sheet_name: str, message: str):
        super().__init__(
            file_path,
            f"工作表错误 ({sheet_name}): {message}",
            category=ErrorCategory.EXCEL_SHEET,
            context={"sheet_name": sheet_name},
        )


# ============================================================================
# 配置相关异常
# ============================================================================


class ConfigError(VATAuditException):
    """配置错误"""

    def __init__(self, config_key: str, message: str):
        super().__init__(
            f"配置错误 ({config_key}): {message}",
            category=ErrorCategory.CONFIG_ERROR,
            context={"config_key": config_key},
        )


# ============================================================================
# 内存相关异常
# ============================================================================


class MemoryError_(VATAuditException):
    """内存错误"""

    def __init__(
        self,
        file_path: str,
        file_size_mb: float,
        message: str = "",
        original_error: Exception = None,
    ):
        msg = f"内存不足 (文件大小: {file_size_mb:.1f}MB)"
        if message:
            msg += f": {message}"
        super().__init__(
            msg,
            category=ErrorCategory.MEMORY_ERROR,
            level=ErrorLevel.CRITICAL,
            context={"file_path": file_path, "file_size_mb": file_size_mb},
            original_error=original_error,
        )


# ============================================================================
# ErrorCollector 类
# ============================================================================


@dataclass
class ErrorStatistics:
    """错误统计信息"""

    total: int = 0
    by_category: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_level: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "by_category": dict(self.by_category),
            "by_level": dict(self.by_level),
            "critical": self.critical_count,
            "error": self.error_count,
            "warning": self.warning_count,
            "info": self.info_count,
        }


class ErrorCollector:
    """
    错误收集器，用于集中管理、分类和输出错误。

    特点：
    - 支持累积多个错误而不中断流程
    - 自动分类错误（按分类、级别等）
    - 提供灵活的错误报告格式
    - 可选的自动日志记录

    使用示例：
        error_collector = ErrorCollector()

        try:
            # 某个操作
        except Exception as e:
            error_collector.collect(
                FileReadError(file_path, str(e), original_error=e)
            )

        # 流程完毕，生成报告
        report = error_collector.get_report()
        if error_collector.has_critical():
            logger.critical(report)
    """

    def __init__(self, auto_log: bool = True):
        """
        初始化错误收集器。

        Args:
            auto_log: 是否自动记录到日志
        """

        self.errors: List[VATAuditException] = []
        self.auto_log = auto_log
        self.start_time = datetime.now()

    def collect(self, error: VATAuditException) -> None:
        """
        收集一个错误。

        Args:
            error: VATAuditException 实例或其子类
        """

        if not isinstance(error, VATAuditException):
            raise TypeError(f"Expected VATAuditException, got {type(error)}")

        self.errors.append(error)

        if self.auto_log:
            self._log_error(error)

    def collect_exception(
        self,
        exception: Exception,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        level: ErrorLevel = ErrorLevel.ERROR,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        从通用异常创建并收集一个错误。

        Args:
            exception: 原始异常
            category: 错误分类
            level: 错误级别
            message: 自定义错误信息（如果为 None，使用异常的 str()）
            context: 额外的上下文信息
        """

        msg = message or str(exception)
        error = VATAuditException(msg, category, level, context, exception)
        self.collect(error)

    def _log_error(self, error: VATAuditException) -> None:
        """内部方法：将错误记录到日志"""

        log_func = {
            ErrorLevel.CRITICAL: logger.critical,
            ErrorLevel.ERROR: logger.error,
            ErrorLevel.WARNING: logger.warning,
            ErrorLevel.INFO: logger.info,
        }.get(error.level, logger.error)

        context_str = f" | Context: {error.context}" if error.context else ""
        log_func(f"{error}{context_str}")

    def has_errors(self) -> bool:
        """是否有任何错误"""

        return len(self.errors) > 0

    def has_critical(self) -> bool:
        """是否有严重错误"""

        return any(e.level == ErrorLevel.CRITICAL for e in self.errors)

    def has_errors_of_level(self, level: ErrorLevel) -> bool:
        """是否有指定级别的错误"""

        return any(e.level == level for e in self.errors)

    def has_errors_of_category(self, category: ErrorCategory) -> bool:
        """是否有指定分类的错误"""

        return any(e.category == category for e in self.errors)

    def get_errors_by_category(self, category: ErrorCategory) -> List[VATAuditException]:
        """获取指定分类的所有错误"""

        return [e for e in self.errors if e.category == category]

    def get_errors_by_level(self, level: ErrorLevel) -> List[VATAuditException]:
        """获取指定级别的所有错误"""

        return [e for e in self.errors if e.level == level]

    def get_statistics(self) -> ErrorStatistics:
        """获取错误统计信息"""

        stats = ErrorStatistics()
        stats.total = len(self.errors)

        for error in self.errors:
            stats.by_category[error.category.value] += 1
            stats.by_level[error.level.value] += 1

            if error.level == ErrorLevel.CRITICAL:
                stats.critical_count += 1
            elif error.level == ErrorLevel.ERROR:
                stats.error_count += 1
            elif error.level == ErrorLevel.WARNING:
                stats.warning_count += 1
            elif error.level == ErrorLevel.INFO:
                stats.info_count += 1

        return stats

    def get_report(self, detailed: bool = True) -> str:
        """
        生成错误报告。

        Args:
            detailed: 是否包含详细信息（包括上下文和原始异常）

        Returns:
            格式化的错误报告字符串
        """

        if not self.has_errors():
            return "✓ 未发现错误"

        lines: List[str] = []
        lines.append("\n" + "=" * 80)
        lines.append("错误收集报告")
        lines.append("=" * 80)

        # 统计信息
        stats = self.get_statistics()
        lines.append("\n📊 统计信息：")
        lines.append(f"  总错误数：{stats.total}")
        lines.append(f"  严重错误：{stats.critical_count}")
        lines.append(f"  一般错误：{stats.error_count}")
        lines.append(f"  警告：{stats.warning_count}")
        lines.append(f"  信息：{stats.info_count}")

        # 按分类分组显示
        errors_by_cat: Dict[ErrorCategory, List[VATAuditException]] = defaultdict(list)
        for error in self.errors:
            errors_by_cat[error.category].append(error)

        lines.append("\n📂 按分类统计：")
        for category, errors in sorted(errors_by_cat.items()):
            lines.append(f"  {category.value}: {len(errors)} 个")

        if detailed:
            # 详细错误列表
            lines.append("\n📝 详细错误列表：")
            lines.append("-" * 80)

            for i, error in enumerate(self.errors, start=1):
                lines.append(f"\n{i}. [{error.level.value}] {error.category.value}")
                lines.append(f"   消息：{error.message}")

                if error.context:
                    lines.append("   上下文：")
                    for key, value in error.context.items():
                        lines.append(f"     - {key}: {value}")

                if error.original_error:
                    lines.append(
                        f"   原始异常：{type(error.original_error).__name__}: {error.original_error}"
                    )

        lines.append("\n" + "=" * 80)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于序列化"""

        return {
            "errors": [e.to_dict() for e in self.errors],
            "statistics": self.get_statistics().to_dict(),
            "start_time": self.start_time.isoformat(),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
        }

    def clear(self) -> None:
        """清空所有错误（用于重新开始）"""

        self.errors.clear()

    def export_to_file(self, file_path: str, detailed: bool = True) -> None:
        """
        导出错误报告到文件。

        Args:
            file_path: 输出文件路径
            detailed: 是否包含详细信息
        """

        try:
            report = self.get_report(detailed=detailed)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info(f"✓ 错误报告已导出到: {file_path}")
        except Exception as e:
            logger.error(f"✗ 导出错误报告失败: {e}")


# ============================================================================
# 便利函数
# ============================================================================


def convert_exception_to_vat_error(
    e: Exception,
    file_path: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> VATAuditException:
    """
    将标准 Python 异常转换为 VAT 审计异常。

    Args:
        e: 原始异常
        file_path: 相关文件路径（如有）
        context: 额外的上下文信息

    Returns:
        对应的 VATAuditException 子类实例
    """

    # 根据异常类型选择合适的 VATAuditException 子类
    if isinstance(e, FileNotFoundError):
        return FileNotFoundError_(file_path or "unknown", original_error=e)

    if isinstance(e, PermissionError):
        return PermissionError_(file_path or "unknown", original_error=e)

    if isinstance(e, MemoryError):
        return MemoryError_(file_path or "unknown", 0.0, original_error=e)

    if "xlsx" in str(e).lower() or "openpyxl" in str(e).lower():
        return ExcelParseError(file_path or "unknown", str(e), original_error=e)

    if "database" in str(e).lower() or "sql" in str(e).lower():
        return DatabaseQueryError(str(e), original_error=e)

    # 默认为通用异常
    return VATAuditException(
        str(e),
        category=ErrorCategory.UNKNOWN,
        context=context,
        original_error=e,
    )


__all__ = [
    "ErrorLevel",
    "ErrorCategory",
    "VATAuditException",
    "ErrorStatistics",
    "ErrorCollector",
    "FileError",
    "FileReadError",
    "FileWriteError",
    "FileNotFoundError_",
    "PermissionError_",
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "DatabaseTransactionError",
    "DataError",
    "DataValidationError",
    "DataEncodingError",
    "DataTypeError",
    "ExcelError",
    "ExcelParseError",
    "ExcelSheetError",
    "ConfigError",
    "MemoryError_",
    "convert_exception_to_vat_error",
]
