"""
数据库 DAO 层单元测试

测试覆盖：
- 参数化查询安全性
- 事务管理
- 错误处理
- 各 DAO 类的基本操作

运行方式：
    pytest tests/test_database_dao.py -v
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from datetime import datetime

from utils.database import (
    DatabaseConnection,
    DAOBase,
    ODSDetailDAO,
    ODSHeaderDAO,
    LedgerDAO,
    QueryResult,
    DatabaseConnectionError,
    DatabaseQueryError,
    SQLInjectionError,
)


@pytest.fixture
def temp_db():
    """创建临时测试数据库。"""
    fd, path = tempfile.mkstemp(suffix='.sqlite')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def db_connection(temp_db):
    """创建数据库连接固件。"""
    db = DatabaseConnection(temp_db)
    yield db
    db.close()


@pytest.fixture
def populated_db(db_connection):
    """创建并填充测试数据库。"""
    with db_connection.transaction():
        # 创建表
        db_connection.execute_script("""
            CREATE TABLE test_invoices (
                id INTEGER PRIMARY KEY,
                invoice_code TEXT NOT NULL,
                invoice_number TEXT NOT NULL,
                amount REAL,
                year TEXT,
                UNIQUE(invoice_code, invoice_number)
            );
            
            CREATE TABLE ODS_TEST_DETAIL (
                发票代码 TEXT,
                发票号码 TEXT,
                金额 REAL,
                开票年份 TEXT,
                销方识别号 TEXT,
                购方识别号 TEXT,
                PRIMARY KEY (发票代码, 发票号码)
            );
            
            CREATE TABLE ODS_TEST_HEADER (
                发票代码 TEXT,
                发票号码 TEXT,
                金额 REAL,
                开票年份 TEXT,
                PRIMARY KEY (发票代码, 发票号码)
            );
        """)
        
        # 插入测试数据
        test_data = [
            ('2023001', '000001', 100.0, '2023', '110000000000001', '110000000000002'),
            ('2023002', '000002', 200.0, '2023', '110000000000001', '110000000000003'),
            ('2023003', '000003', 300.0, '2023', '110000000000002', '110000000000004'),
            ('2024001', '000001', 150.0, '2024', '110000000000001', '110000000000002'),
        ]
        
        for code, num, amount, year, seller, buyer in test_data:
            db_connection.execute_insert(
                """INSERT INTO ODS_TEST_DETAIL 
                   (发票代码, 发票号码, 金额, 开票年份, 销方识别号, 购方识别号)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (code, num, amount, year, seller, buyer)
            )
    
    return db_connection


class TestDatabaseConnection:
    """测试 DatabaseConnection 类。"""

    def test_connect_and_close(self, db_connection):
        """测试连接和关闭。"""
        assert db_connection._conn is not None or db_connection._conn is None
        conn = db_connection.connect()
        assert conn is not None

    def test_context_manager(self, temp_db):
        """测试上下文管理器。"""
        with DatabaseConnection(temp_db) as db:
            assert db._conn is not None
        assert db._conn is None

    def test_pragma_optimize(self, db_connection):
        """测试 PRAGMA 优化。"""
        db_connection.pragma_optimize(mode='wal')
        result = db_connection.execute_pragma("PRAGMA journal_mode")
        assert result.is_success()

    def test_execute_select_success(self, populated_db):
        """测试 SELECT 查询成功。"""
        result = populated_db.execute_select(
            "SELECT COUNT(*) FROM ODS_TEST_DETAIL"
        )
        assert result.is_success()
        assert result.rowcount >= 0
        assert len(result.columns) > 0

    def test_execute_select_with_params(self, populated_db):
        """测试参数化 SELECT 查询。"""
        result = populated_db.execute_select(
            "SELECT * FROM ODS_TEST_DETAIL WHERE 开票年份=?",
            ('2023',)
        )
        assert result.is_success()
        assert result.rowcount == 3

    def test_execute_select_injection_protection(self, populated_db):
        """测试 SQL 注入防护。"""
        # 安全的参数化查询不应该有问题
        result = populated_db.execute_select(
            "SELECT * FROM ODS_TEST_DETAIL WHERE 发票代码=?",
            ("'; DROP TABLE ODS_TEST_DETAIL; --",)
        )
        # 表不应该被删除
        result2 = populated_db.execute_select("SELECT COUNT(*) FROM ODS_TEST_DETAIL")
        assert result2.is_success()

    def test_non_select_raises_error(self, populated_db):
        """测试非 SELECT 查询抛出异常。"""
        # execute_select 不应该接受 INSERT/UPDATE/DELETE
        with pytest.raises(SQLInjectionError):
            populated_db.execute_select("INSERT INTO test_table VALUES (1)")

    def test_execute_insert(self, populated_db):
        """测试 INSERT 操作。"""
        result = populated_db.execute_insert(
            "INSERT INTO ODS_TEST_DETAIL (发票代码, 发票号码, 金额, 开票年份) VALUES (?, ?, ?, ?)",
            ('2025001', '000001', 500.0, '2025')
        )
        assert result.is_success()
        assert result.rowcount > 0

    def test_execute_update(self, populated_db):
        """测试 UPDATE 操作。"""
        result = populated_db.execute_update(
            "UPDATE ODS_TEST_DETAIL SET 金额=? WHERE 发票代码=?",
            (999.0, '2023001')
        )
        assert result.is_success()

    def test_execute_delete(self, populated_db):
        """测试 DELETE 操作。"""
        result = populated_db.execute_delete(
            "DELETE FROM ODS_TEST_DETAIL WHERE 开票年份=?",
            ('2024',)
        )
        assert result.is_success()
        assert result.rowcount == 1

    def test_transaction_commit(self, populated_db):
        """测试事务提交。"""
        with populated_db.transaction():
            result = populated_db.execute_insert(
                "INSERT INTO ODS_TEST_DETAIL (发票代码, 发票号码, 金额, 开票年份) VALUES (?, ?, ?, ?)",
                ('9999001', '999999', 9999.0, '9999')
            )
            assert result.is_success()
        
        # 验证数据已提交
        result = populated_db.execute_select(
            "SELECT * FROM ODS_TEST_DETAIL WHERE 发票代码=?",
            ('9999001',)
        )
        assert result.rowcount > 0

    def test_transaction_rollback(self, db_connection):
        """测试事务回滚。"""
        # 创建表
        db_connection.execute_script(
            "CREATE TABLE test_rollback (id INTEGER PRIMARY KEY, value TEXT)"
        )
        
        # 尝试在事务中插入并触发异常
        try:
            with db_connection.transaction():
                db_connection.execute_insert(
                    "INSERT INTO test_rollback (value) VALUES (?)",
                    ('should_rollback',)
                )
                # 触发异常
                raise ValueError("测试异常")
        except Exception:
            pass
        
        # 验证数据已回滚
        result = db_connection.execute_select("SELECT COUNT(*) FROM test_rollback")
        assert result.rows[0][0] == 0

    def test_query_result_to_dict_list(self, populated_db):
        """测试 QueryResult 转换为字典列表。"""
        result = populated_db.execute_select(
            "SELECT 发票代码, 发票号码, 金额 FROM ODS_TEST_DETAIL WHERE 开票年份=? LIMIT 1",
            ('2023',)
        )
        dict_list = result.to_dict_list()
        assert len(dict_list) > 0
        assert '发票代码' in dict_list[0]

    def test_query_result_to_first_dict(self, populated_db):
        """测试 QueryResult 获取第一行字典。"""
        result = populated_db.execute_select(
            "SELECT 发票代码, 金额 FROM ODS_TEST_DETAIL LIMIT 1"
        )
        first_dict = result.to_first_dict()
        assert first_dict is not None
        assert isinstance(first_dict, dict)


class TestDAOBase:
    """测试 DAOBase 基类。"""

    def test_count_all(self, populated_db):
        """测试计数所有行。"""
        dao = DAOBase(populated_db, "ODS_TEST_DETAIL")
        count = dao.count()
        assert count == 4

    def test_count_with_where(self, populated_db):
        """测试条件计数。"""
        dao = DAOBase(populated_db, "ODS_TEST_DETAIL")
        count = dao.count("开票年份=?", ('2023',))
        assert count == 3

    def test_find_all(self, populated_db):
        """测试查询所有行。"""
        dao = DAOBase(populated_db, "ODS_TEST_DETAIL")
        records = dao.find_all()
        assert len(records) == 4

    def test_table_exists(self, populated_db):
        """测试表存在性检查。"""
        dao = DAOBase(populated_db, "ODS_TEST_DETAIL")
        assert dao.table_exists() is True
        
        dao_nonexist = DAOBase(populated_db, "NONEXISTENT_TABLE")
        assert dao_nonexist.table_exists() is False


class TestODSDetailDAO:
    """测试 ODSDetailDAO 类。"""

    def test_find_by_invoice(self, populated_db):
        """测试按发票号查找。"""
        dao = ODSDetailDAO(populated_db, "TEST")
        record = dao.find_by_invoice('2023001', '000001')
        assert record is not None
        assert record['发票代码'] == '2023001'
        assert record['金额'] == 100.0

    def test_find_by_year(self, populated_db):
        """测试按年份查找。"""
        dao = ODSDetailDAO(populated_db, "TEST")
        records = dao.find_by_year('2023')
        assert len(records) == 3
        assert all(r['开票年份'] == '2023' for r in records)

    def test_get_distinct_years(self, populated_db):
        """测试获取不重复年份。"""
        dao = ODSDetailDAO(populated_db, "TEST")
        years = dao.get_distinct_years()
        assert '2023' in years
        assert '2024' in years

    def test_count_by_year(self, populated_db):
        """测试按年份计数。"""
        dao = ODSDetailDAO(populated_db, "TEST")
        count_2023 = dao.count_by_year('2023')
        assert count_2023 == 3


class TestLedgerDAO:
    """测试 LedgerDAO 类。"""

    @pytest.fixture
    def ledger_db(self, populated_db):
        """创建包含 LEDGER 表的数据库。"""
        populated_db.execute_script("""
            CREATE TABLE LEDGER_TEST_2023_INVOICE_DETAIL (
                发票代码 TEXT PRIMARY KEY,
                发票号码 TEXT,
                金额 REAL,
                销方识别号 TEXT,
                购方识别号 TEXT
            );
        """)
        return populated_db

    def test_init_detail_ledger(self, ledger_db):
        """测试初始化明细 LEDGER DAO。"""
        dao = LedgerDAO(ledger_db, "TEST", "2023", "detail")
        assert dao.ledger_type == "detail"
        assert "INVOICE_DETAIL" in dao.table_name

    def test_init_header_ledger(self, ledger_db):
        """测试初始化表头 LEDGER DAO。"""
        dao = LedgerDAO(ledger_db, "TEST", "2023", "header")
        assert dao.ledger_type == "header"
        assert "INVOICE_HEADER" in dao.table_name

    def test_invalid_ledger_type(self, ledger_db):
        """测试非法的 LEDGER 类型。"""
        with pytest.raises(ValueError):
            LedgerDAO(ledger_db, "TEST", "2023", "invalid")


class TestParameterizedQueries:
    """测试参数化查询防护。"""

    def test_sql_injection_attempt_fails(self, populated_db):
        """测试 SQL 注入尝试（应被阻止）。"""
        # 尝试注入 SQL
        injection_payload = "2023' OR '1'='1"
        result = populated_db.execute_select(
            "SELECT * FROM ODS_TEST_DETAIL WHERE 开票年份=?",
            (injection_payload,)
        )
        # 应该返回 0 行（因为没有匹配的年份）
        assert result.rowcount == 0

    def test_special_characters_in_params(self, populated_db):
        """测试包含特殊字符的参数。"""
        result = populated_db.execute_insert(
            "INSERT INTO ODS_TEST_DETAIL (发票代码, 发票号码, 开票年份) VALUES (?, ?, ?)",
            ("ABC'123", 'XYZ"456', "2025")
        )
        assert result.is_success()

    def test_unicode_in_params(self, populated_db):
        """测试 Unicode 参数。"""
        result = populated_db.execute_insert(
            "INSERT INTO ODS_TEST_DETAIL (发票代码, 发票号码, 开票年份) VALUES (?, ?, ?)",
            ("测试001", "测试号码", "2025")
        )
        assert result.is_success()


class TestTransactionManagement:
    """测试事务管理。"""

    def test_nested_transaction_error(self, db_connection):
        """测试嵌套事务会抛出错误。"""
        db_connection.execute_script("CREATE TABLE test_nested (id INTEGER)")
        
        with pytest.raises(DatabaseQueryError):
            with db_connection.transaction():
                with db_connection.transaction():
                    pass

    def test_concurrent_operations(self, populated_db):
        """测试并发操作（单线程模拟）。"""
        # 执行多个查询和修改
        for i in range(10):
            result = populated_db.execute_insert(
                "INSERT INTO ODS_TEST_DETAIL (发票代码, 发票号码, 开票年份) VALUES (?, ?, ?)",
                (f"CONC{i:03d}", f"00000{i}", "2025")
            )
            assert result.is_success()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
