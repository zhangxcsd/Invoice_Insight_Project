"""
错误处理模块的单元测试

覆盖：
- 异常类的创建和属性
- ErrorCollector 的基本功能
- 错误分类和统计
- 报告生成
- 异常转换
"""

import pytest
import logging
import json
import os
import tempfile
from datetime import datetime

from utils.error_handling import (
    # 枚举
    ErrorLevel,
    ErrorCategory,
    # 基类和异常
    VATAuditException,
    FileError,
    FileReadError,
    FileWriteError,
    FileNotFoundError_,
    PermissionError_,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseTransactionError,
    DataError,
    DataValidationError,
    DataEncodingError,
    DataTypeError,
    ExcelError,
    ExcelParseError,
    ExcelSheetError,
    ConfigError,
    MemoryError_,
    # ErrorCollector 和工具
    ErrorCollector,
    ErrorStatistics,
    convert_exception_to_vat_error
)


# ============================================================================
# 异常类测试
# ============================================================================

class TestVATAuditException:
    """测试基础异常类"""

    def test_basic_exception_creation(self):
        """测试基础异常创建"""
        exc = VATAuditException(
            "测试错误",
            category=ErrorCategory.UNKNOWN,
            level=ErrorLevel.ERROR
        )
        assert exc.message == "测试错误"
        assert exc.category == ErrorCategory.UNKNOWN
        assert exc.level == ErrorLevel.ERROR
        assert isinstance(exc.timestamp, datetime)

    def test_exception_with_context(self):
        """测试带上下文的异常"""
        context = {'file': 'test.txt', 'line': 10}
        exc = VATAuditException(
            "测试错误",
            context=context
        )
        assert exc.context == context

    def test_exception_with_original_error(self):
        """测试保存原始异常"""
        orig = ValueError("原始错误")
        exc = VATAuditException(
            "包装错误",
            original_error=orig
        )
        assert exc.original_error == orig
        # 验证 original_error 被保存为字符串
        assert str(exc.original_error) == "原始错误"

    def test_exception_to_dict(self):
        """测试异常转换为字典"""
        exc = VATAuditException(
            "测试",
            category=ErrorCategory.FILE_READ,
            level=ErrorLevel.CRITICAL,
            context={'file': 'test.csv'}
        )
        d = exc.to_dict()
        assert d['message'] == "测试"
        assert d['category'] == "FILE_READ"
        assert d['level'] == "CRITICAL"
        assert d['context'] == {'file': 'test.csv'}

    def test_exception_str_representation(self):
        """测试异常字符串表示"""
        exc = VATAuditException(
            "测试错误",
            category=ErrorCategory.DATABASE_QUERY
        )
        s = str(exc)
        # 注意：category 的值显示为 DB_QUERY（简写）
        assert "DB_QUERY" in s or "DATABASE_QUERY" in s
        assert "测试错误" in s


class TestFileExceptions:
    """测试文件相关异常"""

    def test_file_read_error(self):
        """测试文件读取错误"""
        orig = IOError("IO 错误")
        exc = FileReadError("data.csv", "无法读取文件", orig)
        assert exc.file_path == "data.csv"
        assert exc.category == ErrorCategory.FILE_READ
        assert "data.csv" in exc.context['file_path']

    def test_file_write_error(self):
        """测试文件写入错误"""
        exc = FileWriteError("output.xlsx", "磁盘已满")
        assert exc.file_path == "output.xlsx"
        assert exc.category == ErrorCategory.FILE_WRITE

    def test_file_not_found_error(self):
        """测试文件不存在错误"""
        exc = FileNotFoundError_("missing.txt")
        assert exc.category == ErrorCategory.FILE_NOT_FOUND

    def test_permission_error(self):
        """测试权限错误"""
        exc = PermissionError_("protected.txt", "读取")
        assert exc.category == ErrorCategory.PERMISSION
        assert "读取" in exc.message


class TestDatabaseExceptions:
    """测试数据库相关异常"""

    def test_database_connection_error(self):
        """测试数据库连接错误"""
        exc = DatabaseConnectionError("vat.db", "连接被拒绝")
        assert exc.category == ErrorCategory.DATABASE_CONNECTION
        assert "vat.db" in exc.context['db_path']

    def test_database_query_error(self):
        """测试数据库查询错误"""
        query = "SELECT * FROM invoices"
        exc = DatabaseQueryError("语法错误", query=query)
        assert exc.category == ErrorCategory.DATABASE_QUERY
        assert "SELECT" in exc.context['query']

    def test_database_transaction_error(self):
        """测试事务错误"""
        exc = DatabaseTransactionError("提交失败")
        assert exc.category == ErrorCategory.DATABASE_TRANSACTION


class TestDataExceptions:
    """测试数据相关异常"""

    def test_data_validation_error(self):
        """测试数据验证错误"""
        exc = DataValidationError("amount", 9999999, "超出范围")
        assert exc.category == ErrorCategory.DATA_VALIDATION
        assert "amount" in exc.context['field_name']

    def test_data_encoding_error(self):
        """测试编码错误"""
        exc = DataEncodingError("data.csv", "GBK", "期望 UTF-8")
        assert exc.category == ErrorCategory.DATA_ENCODING
        assert "GBK" in exc.context['encoding']

    def test_data_type_error(self):
        """测试数据类型错误"""
        exc = DataTypeError("invoice_id", "str", "int")
        assert exc.category == ErrorCategory.DATA_TYPE
        assert "invoice_id" in exc.context['field_name']


class TestExcelExceptions:
    """测试 Excel 相关异常"""

    def test_excel_parse_error(self):
        """测试 Excel 解析错误"""
        orig = Exception("损坏的文件")
        exc = ExcelParseError("data.xlsx", "无法解析", orig)
        assert exc.category == ErrorCategory.EXCEL_PARSE
        assert "data.xlsx" in exc.file_path

    def test_excel_sheet_error(self):
        """测试 Excel 工作表错误"""
        exc = ExcelSheetError("data.xlsx", "Sheet1", "工作表不存在")
        assert exc.category == ErrorCategory.EXCEL_SHEET
        assert "Sheet1" in exc.context['sheet_name']


class TestConfigError:
    """测试配置错误"""

    def test_config_error(self):
        """测试配置错误"""
        exc = ConfigError("db.path", "路径无效")
        assert exc.category == ErrorCategory.CONFIG_ERROR
        assert "db.path" in exc.context['config_key']


class TestMemoryError:
    """测试内存错误"""

    def test_memory_error(self):
        """测试内存错误"""
        exc = MemoryError_("large_file.xlsx", 1024.5, "可用内存不足")
        assert exc.category == ErrorCategory.MEMORY_ERROR
        assert exc.level == ErrorLevel.CRITICAL
        assert exc.context['file_size_mb'] == 1024.5


# ============================================================================
# ErrorCollector 测试
# ============================================================================

class TestErrorCollector:
    """测试错误收集器"""

    def test_collector_creation(self):
        """测试收集器创建"""
        collector = ErrorCollector(auto_log=True)
        assert collector.has_errors() is False
        assert len(collector.errors) == 0

    def test_collect_single_error(self):
        """测试收集单个错误"""
        collector = ErrorCollector(auto_log=False)
        exc = FileReadError("test.txt", "I/O 错误")
        
        collector.collect(exc)
        
        assert collector.has_errors() is True
        assert len(collector.errors) == 1
        assert collector.errors[0] == exc

    def test_collect_multiple_errors(self):
        """测试收集多个错误"""
        collector = ErrorCollector(auto_log=False)
        exc1 = FileReadError("test1.txt", "错误 1")
        exc2 = DatabaseQueryError("查询失败")
        exc3 = DataValidationError("field", "value", "验证失败")
        
        collector.collect(exc1)
        collector.collect(exc2)
        collector.collect(exc3)
        
        assert len(collector.errors) == 3

    def test_collect_exception(self):
        """测试从标准异常创建并收集"""
        collector = ErrorCollector(auto_log=False)
        orig = ValueError("原始异常")
        
        collector.collect_exception(
            orig,
            category=ErrorCategory.DATA_VALIDATION,
            message="数据类型错误"
        )
        
        assert collector.has_errors() is True
        assert collector.errors[0].original_error == orig

    def test_has_critical(self):
        """测试严重错误检查"""
        collector = ErrorCollector(auto_log=False)
        
        # 添加普通错误
        collector.collect(FileReadError("test.txt", "读取失败"))
        assert collector.has_critical() is False
        
        # 添加严重错误
        collector.collect(MemoryError_("large.xlsx", 2048))
        assert collector.has_critical() is True

    def test_has_errors_of_level(self):
        """测试按级别检查错误"""
        collector = ErrorCollector(auto_log=False)
        
        collector.collect(VATAuditException(
            "警告信息",
            level=ErrorLevel.WARNING
        ))
        collector.collect(VATAuditException(
            "错误信息",
            level=ErrorLevel.ERROR
        ))
        
        assert collector.has_errors_of_level(ErrorLevel.WARNING) is True
        assert collector.has_errors_of_level(ErrorLevel.CRITICAL) is False

    def test_has_errors_of_category(self):
        """测试按分类检查错误"""
        collector = ErrorCollector(auto_log=False)
        
        collector.collect(FileReadError("test.txt", "读取失败"))
        collector.collect(DatabaseQueryError("查询失败"))
        
        assert collector.has_errors_of_category(ErrorCategory.FILE_READ) is True
        assert collector.has_errors_of_category(ErrorCategory.DATABASE_QUERY) is True
        assert collector.has_errors_of_category(ErrorCategory.CONFIG_ERROR) is False

    def test_get_errors_by_category(self):
        """测试获取按分类分组的错误"""
        collector = ErrorCollector(auto_log=False)
        
        collector.collect(FileReadError("test1.txt", "错误 1"))
        collector.collect(FileWriteError("test2.txt", "错误 2"))
        collector.collect(DatabaseQueryError("查询失败"))
        
        file_errors = collector.get_errors_by_category(ErrorCategory.FILE_READ)
        assert len(file_errors) == 1
        
        db_errors = collector.get_errors_by_category(ErrorCategory.DATABASE_QUERY)
        assert len(db_errors) == 1

    def test_get_errors_by_level(self):
        """测试获取按级别分组的错误"""
        collector = ErrorCollector(auto_log=False)
        
        collector.collect(VATAuditException("错误 1", level=ErrorLevel.ERROR))
        collector.collect(VATAuditException("警告 1", level=ErrorLevel.WARNING))
        collector.collect(VATAuditException("错误 2", level=ErrorLevel.ERROR))
        
        errors = collector.get_errors_by_level(ErrorLevel.ERROR)
        assert len(errors) == 2
        
        warnings = collector.get_errors_by_level(ErrorLevel.WARNING)
        assert len(warnings) == 1

    def test_get_statistics(self):
        """测试获取错误统计"""
        collector = ErrorCollector(auto_log=False)
        
        collector.collect(FileReadError("test.txt", "读取失败"))
        collector.collect(DatabaseQueryError("查询失败"))
        collector.collect(VATAuditException("警告", level=ErrorLevel.WARNING))
        
        stats = collector.get_statistics()
        
        assert stats.total == 3
        assert stats.error_count == 2
        assert stats.warning_count == 1
        assert stats.by_category["FILE_READ"] == 1
        # DatabaseQueryError 的分类是 DB_QUERY
        assert stats.by_category["DB_QUERY"] == 1

    def test_get_report(self):
        """测试生成错误报告"""
        collector = ErrorCollector(auto_log=False)
        
        collector.collect(FileReadError("test.txt", "读取失败"))
        
        report = collector.get_report()
        
        assert "错误收集报告" in report
        assert "FILE_READ" in report
        assert "总错误数：1" in report

    def test_get_report_detailed(self):
        """测试详细报告"""
        collector = ErrorCollector(auto_log=False)
        
        exc = FileReadError("test.txt", "读取失败")
        collector.collect(exc)
        
        detailed_report = collector.get_report(detailed=True)
        simple_report = collector.get_report(detailed=False)
        
        assert "详细错误列表" in detailed_report
        assert "详细错误列表" not in simple_report

    def test_to_dict(self):
        """测试转换为字典"""
        collector = ErrorCollector(auto_log=False)
        
        collector.collect(FileReadError("test.txt", "读取失败"))
        
        d = collector.to_dict()
        
        assert 'errors' in d
        assert 'statistics' in d
        assert 'start_time' in d
        assert len(d['errors']) == 1

    def test_clear_errors(self):
        """测试清空错误"""
        collector = ErrorCollector(auto_log=False)
        
        collector.collect(FileReadError("test.txt", "读取失败"))
        assert collector.has_errors() is True
        
        collector.clear()
        assert collector.has_errors() is False
        assert len(collector.errors) == 0

    def test_export_to_file(self):
        """测试导出到文件"""
        collector = ErrorCollector(auto_log=False)
        
        collector.collect(FileReadError("test.txt", "读取失败"))
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "error_report.txt")
            collector.export_to_file(output_file)
            
            assert os.path.exists(output_file)
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "错误收集报告" in content
                assert "FILE_READ" in content

    def test_no_errors_report(self):
        """测试无错误时的报告"""
        collector = ErrorCollector(auto_log=False)
        
        report = collector.get_report()
        
        assert "未发现错误" in report


class TestErrorStatistics:
    """测试错误统计"""

    def test_statistics_to_dict(self):
        """测试统计转换为字典"""
        stats = ErrorStatistics(
            total=5,
            critical_count=1,
            error_count=3,
            warning_count=1
        )
        
        d = stats.to_dict()
        
        assert d['total'] == 5
        assert d['critical'] == 1
        assert d['error'] == 3
        assert d['warning'] == 1


# ============================================================================
# 异常转换测试
# ============================================================================

class TestExceptionConversion:
    """测试异常转换功能"""

    def test_convert_file_not_found(self):
        """测试转换 FileNotFoundError"""
        orig = FileNotFoundError("文件不存在")
        result = convert_exception_to_vat_error(orig, file_path="test.txt")
        
        assert isinstance(result, FileNotFoundError_)
        assert result.category == ErrorCategory.FILE_NOT_FOUND

    def test_convert_permission_error(self):
        """测试转换 PermissionError"""
        orig = PermissionError("没有权限")
        result = convert_exception_to_vat_error(orig, file_path="test.txt")
        
        assert isinstance(result, PermissionError_)
        assert result.category == ErrorCategory.PERMISSION

    def test_convert_memory_error(self):
        """测试转换 MemoryError"""
        orig = MemoryError("内存不足")
        result = convert_exception_to_vat_error(orig, file_path="large.xlsx")
        
        assert isinstance(result, MemoryError_)
        assert result.category == ErrorCategory.MEMORY_ERROR
        assert result.level == ErrorLevel.CRITICAL

    def test_convert_generic_exception(self):
        """测试转换通用异常"""
        orig = ValueError("一些错误")
        result = convert_exception_to_vat_error(orig)
        
        assert isinstance(result, VATAuditException)
        assert result.original_error == orig


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """集成测试"""

    def test_workflow_file_processing(self):
        """测试文件处理工作流"""
        collector = ErrorCollector(auto_log=False)
        
        # 模拟文件处理
        files = ["test1.txt", "missing.txt", "test3.txt"]
        
        for file_path in files:
            if "missing" in file_path:
                collector.collect(FileNotFoundError_(file_path))
            elif file_path == "test1.txt":
                # 成功处理
                pass
        
        # 检查结果
        assert collector.has_errors() is True
        assert len(collector.get_errors_by_category(ErrorCategory.FILE_NOT_FOUND)) == 1

    def test_workflow_data_validation(self):
        """测试数据验证工作流"""
        collector = ErrorCollector(auto_log=False)
        
        data = [
            {'id': '001', 'amount': 1000},
            {'id': '002', 'amount': 'invalid'},  # 错误
            {'id': None, 'amount': 500},  # 错误
            {'id': '004', 'amount': 2000}
        ]
        
        for item in data:
            try:
                if not isinstance(item['amount'], (int, float)):
                    raise DataTypeError('amount', 'float', type(item['amount']).__name__)
                if not item['id']:
                    raise DataValidationError('id', item['id'], "ID 不能为空")
            except (DataTypeError, DataValidationError) as e:
                collector.collect(e)
        
        stats = collector.get_statistics()
        assert stats.total == 2

    def test_error_collector_with_custom_logging(self, caplog):
        """测试错误收集器的日志记录"""
        with caplog.at_level(logging.ERROR):
            collector = ErrorCollector(auto_log=True)
            collector.collect(FileReadError("test.txt", "读取失败"))
        
        # 验证日志记录了错误
        assert "FILE_READ" in caplog.text or "读取失败" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
