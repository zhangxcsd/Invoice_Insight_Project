"""
轻量级数据库抽象层（DAO 模式）

说明：
- 提供参数化查询接口，避免 SQL 注入。
- 支持事务管理、连接池、日志追踪。
- 每个数据层（ODS、LEDGER、DWD）对应一个 DAO 类。
- 遵循依赖注入原则：DAO 对象通过构造函数接收 database_path，不读取全局变量。

设计原则：
1. 参数化查询（parameterized queries）：所有用户输入通过 params 参数传入，防止 SQL 注入。
2. 事务管理：BEGIN/COMMIT/ROLLBACK 统一由 DAO 控制，避免嵌套事务问题。
3. 连接管理：支持上下文管理器（with 语句），确保连接正确关闭。
4. 日志追踪：所有 SQL 操作可选地记录执行时间和异常，便于调试和性能分析。
5. 错误处理：统一捕获和转换数据库异常为业务异常。
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def connect_sqlite(path: str | Path) -> sqlite3.Connection:
    """Create a SQLite connection to the provided file path."""

    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


@dataclass
class QueryResult:
    """数据库查询结果容器，支持链式操作和数据转换。"""

    rows: List[Tuple]
    columns: List[str]
    rowcount: int = 0
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """将查询结果转换为字典列表，便于处理。"""

        return [dict(zip(self.columns, row)) for row in self.rows]

    def to_first_dict(self) -> Optional[Dict[str, Any]]:
        """获取第一行作为字典，返回 None 如果无结果。"""

        if self.rows:
            return dict(zip(self.columns, self.rows[0]))
        return None

    def is_success(self) -> bool:
        """检查查询是否成功。"""

        return self.error is None


class DatabaseConnectionError(Exception):
    """数据库连接异常。"""


class DatabaseQueryError(Exception):
    """数据库查询异常。"""


class SQLInjectionError(Exception):
    """SQL 注入风险异常。"""


class DatabaseConnection:
    """
    SQLite 数据库连接管理器，支持上下文管理和参数化查询。

    使用示例：
        conn = DatabaseConnection("path/to/db.sqlite")
        with conn.transaction():
            result = conn.execute_select("SELECT * FROM table WHERE id = ?", (1,))
            for row in result.rows:
                print(row)
    """

    def __init__(self, database_path: str, timeout: float = 30.0, isolation_level: Optional[str] = None):
        """
        初始化数据库连接。

        Args:
            database_path: SQLite 数据库文件路径。
            timeout: 连接超时时间（秒）。
            isolation_level: 事务隔离级别（默认 None 表示自动提交模式）。
        """

        self.database_path = database_path
        self.timeout = timeout
        self.isolation_level = isolation_level
        self._conn: Optional[sqlite3.Connection] = None
        self._in_transaction = False

    def connect(self) -> sqlite3.Connection:
        """建立数据库连接，返回连接对象。"""

        try:
            if self._conn is None:
                self._conn = sqlite3.connect(
                    self.database_path,
                    timeout=self.timeout,
                    isolation_level=self.isolation_level,
                    check_same_thread=False,
                )
                # 返回行工厂，使 fetchall 返回 Row 对象而非元组
                self._conn.row_factory = sqlite3.Row
                logger.debug(f"✓ 已连接到数据库: {self.database_path}")
            return self._conn
        except sqlite3.OperationalError as e:
            raise DatabaseConnectionError(f"无法连接到数据库 {self.database_path}: {e}")

    def close(self):
        """关闭数据库连接。"""

        if self._conn:
            try:
                if self._in_transaction:
                    self._conn.rollback()
                self._conn.close()
                self._conn = None
                logger.debug(f"✓ 已关闭数据库连接: {self.database_path}")
            except Exception as e:
                logger.error(f"关闭数据库连接时出错: {e}")

    def __enter__(self):
        """上下文管理器入口。"""

        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口。"""

        if exc_type is not None:
            logger.error(f"数据库操作异常: {exc_type.__name__}: {exc_val}")
            if self._in_transaction:
                self.rollback()
        self.close()
        return False

    @contextmanager
    def transaction(self):
        """
        上下文管理器：自动管理事务。

        使用示例：
            with db.transaction():
                db.execute_insert("INSERT INTO table VALUES (?, ?)", (val1, val2))
                # 自动 COMMIT，如果异常自动 ROLLBACK
        """

        conn = self.connect()
        try:
            self._in_transaction = True
            conn.execute("BEGIN IMMEDIATE")
            yield
            conn.commit()
            self._in_transaction = False
            logger.debug("✓ 事务已提交")
        except Exception as e:
            conn.rollback()
            self._in_transaction = False
            logger.error(f"事务已回滚，原因: {e}")
            raise DatabaseQueryError(f"事务执行失败: {e}") from e

    def pragma_optimize(self, mode: str = "wal"):
        """
        应用性能优化 PRAGMA。

        Args:
            mode: 'wal' (WAL 模式) 或 'default' (日志模式)
        """

        conn = self.connect()
        cursor = conn.cursor()
        try:
            if mode == "wal":
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
            else:
                cursor.execute("PRAGMA journal_mode=DELETE")
                cursor.execute("PRAGMA synchronous=FULL")
            logger.debug(f"✓ 已应用性能优化 (mode={mode})")
        except Exception as e:
            logger.warning(f"应用性能优化失败: {e}")

    def execute_select(self, query: str, params: Tuple = ()) -> QueryResult:
        """
        执行 SELECT 查询（参数化）。

        Args:
            query: SQL SELECT 语句，用 ? 代表参数占位符。
            params: 参数元组。

        Returns:
            QueryResult 对象，包含行数据、列名、执行时间等。

        异常处理：
            - 如果 query 包含非 SELECT 关键词，抛出 SQLInjectionError。
            - 如果执行出错，返回 QueryResult 对象但设置 error 字段。
        """

        # 安全检查：确保是 SELECT 语句
        if not self._is_select_statement(query):
            raise SQLInjectionError(f"查询必须是 SELECT 语句: {query[:50]}...")

        # 确保参数是元组
        if not isinstance(params, (tuple, list)):
            params = (params,)

        conn = self.connect()
        cursor = conn.cursor()
        start_time = datetime.now()
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.debug(f"查询成功: {query[:60]}... ({len(rows)} 行, {execution_time:.2f}ms)")
            return QueryResult(
                rows=rows,
                columns=columns,
                rowcount=len(rows),
                execution_time_ms=execution_time,
            )
        except sqlite3.Error as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"查询失败: {query[:60]}... 错误: {e}")
            return QueryResult(rows=[], columns=[], error=str(e), execution_time_ms=execution_time)

    def execute_insert(self, query: str, params: Tuple = ()) -> QueryResult:
        """执行 INSERT 查询（参数化）。"""

        return self._execute_modify(query, params, "INSERT")

    def execute_update(self, query: str, params: Tuple = ()) -> QueryResult:
        """执行 UPDATE 查询（参数化）。"""

        return self._execute_modify(query, params, "UPDATE")

    def execute_delete(self, query: str, params: Tuple = ()) -> QueryResult:
        """执行 DELETE 查询（参数化）。"""

        return self._execute_modify(query, params, "DELETE")

    def execute_pragma(self, pragma: str) -> QueryResult:
        """
        执行 PRAGMA 命令（不参数化，仅用于系统命令）。

        注意：PRAGMA 不支持参数化，仅用于内部优化，不处理用户输入。
        """

        conn = self.connect()
        cursor = conn.cursor()
        start_time = datetime.now()
        try:
            cursor.execute(pragma)
            rows = cursor.fetchall() if cursor.description else []
            columns = [description[0] for description in cursor.description] if cursor.description else []
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.debug(f"PRAGMA 执行成功: {pragma[:50]}...")
            return QueryResult(rows=rows, columns=columns, execution_time_ms=execution_time)
        except sqlite3.Error as e:
            logger.error(f"PRAGMA 执行失败: {pragma[:50]}... 错误: {e}")
            return QueryResult(rows=[], columns=[], error=str(e))

    def execute_script(self, script: str) -> QueryResult:
        """
        执行多条 SQL 语句（脚本模式，不支持参数化）。

        注意：此方法仅用于内部 SQL 脚本，不处理用户输入。
        """

        conn = self.connect()
        cursor = conn.cursor()
        start_time = datetime.now()
        try:
            cursor.executescript(script)
            conn.commit()
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.debug(f"脚本执行成功 ({execution_time:.2f}ms)")
            return QueryResult(rows=[], columns=[], execution_time_ms=execution_time)
        except sqlite3.Error as e:
            logger.error(f"脚本执行失败: {e}")
            return QueryResult(rows=[], columns=[], error=str(e))

    def _execute_modify(self, query: str, params: Tuple, operation: str) -> QueryResult:
        """内部方法：执行修改操作（INSERT/UPDATE/DELETE）。"""

        # 确保参数是元组
        if not isinstance(params, (tuple, list)):
            params = (params,)

        conn = self.connect()
        cursor = conn.cursor()
        start_time = datetime.now()
        try:
            cursor.execute(query, params)
            rowcount = cursor.rowcount
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.debug(f"{operation} 执行成功: 受影响 {rowcount} 行 ({execution_time:.2f}ms)")
            return QueryResult(rows=[], columns=[], rowcount=rowcount, execution_time_ms=execution_time)
        except sqlite3.Error as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"{operation} 执行失败: {query[:60]}... 错误: {e}")
            return QueryResult(rows=[], columns=[], error=str(e), execution_time_ms=execution_time)

    @staticmethod
    def _is_select_statement(query: str) -> bool:
        """检查查询是否为 SELECT 语句（防止误用 SELECT 执行修改操作）。"""

        normalized = query.strip().upper()
        return normalized.startswith("SELECT")


class DAOBase:
    """
    数据访问对象基类，提供通用的数据库操作方法。

    子类应覆盖特定表的查询和操作逻辑。
    """

    def __init__(self, db: DatabaseConnection, table_name: str):
        self.db = db
        self.table_name = table_name

    def table_exists(self) -> bool:
        """检查表是否存在。"""

        query = "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?"
        result = self.db.execute_select(query, (self.table_name,))
        return result.is_success() and len(result.rows) > 0

    def count(self, where_clause: str = "", params: Tuple = ()) -> int:
        """统计表中的行数。"""

        query = f"SELECT COUNT(*) FROM {self.table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        result = self.db.execute_select(query, params)
        if result.is_success() and result.rows:
            return result.rows[0][0]
        return -1

    def find_all(self, order_by: str = "", limit: int = 0) -> List[Dict[str, Any]]:
        """查询表中所有记录。"""

        query = f"SELECT * FROM {self.table_name}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit > 0:
            query += f" LIMIT {limit}"
        result = self.db.execute_select(query)
        return result.to_dict_list() if result.is_success() else []

    def find_by_id(self, id_value: Any, id_column: str = "id") -> Optional[Dict[str, Any]]:
        """按 ID 查询单条记录。"""

        query = f"SELECT * FROM {self.table_name} WHERE {id_column}=?"
        result = self.db.execute_select(query, (id_value,))
        return result.to_first_dict() if result.is_success() else None

    def find_where(
        self,
        where_clause: str,
        params: Tuple = (),
        order_by: str = "",
        limit: int = 0,
    ) -> List[Dict[str, Any]]:
        """按条件查询。"""

        query = f"SELECT * FROM {self.table_name} WHERE {where_clause}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit > 0:
            query += f" LIMIT {limit}"
        result = self.db.execute_select(query, params)
        return result.to_dict_list() if result.is_success() else []

    def insert(self, columns: List[str], values: List[Tuple]) -> QueryResult:
        """批量插入记录。"""

        placeholders = ",".join(["?" for _ in columns])
        query = f"INSERT INTO {self.table_name} ({','.join(columns)}) VALUES ({placeholders})"
        results = []
        for value_tuple in values:
            result = self.db.execute_insert(query, value_tuple)
            results.append(result)
            if not result.is_success():
                logger.warning(f"插入失败: {result.error}")
        return results[0] if results else QueryResult(rows=[], columns=[])

    def delete_where(self, where_clause: str, params: Tuple = ()) -> QueryResult:
        """按条件删除记录。"""

        query = f"DELETE FROM {self.table_name} WHERE {where_clause}"
        return self.db.execute_delete(query, params)

    def create_index(self, index_name: str, columns: List[str], unique: bool = False) -> QueryResult:
        """创建索引。"""

        unique_str = "UNIQUE" if unique else ""
        query = (
            f"CREATE {unique_str} INDEX IF NOT EXISTS {index_name} "
            f"ON {self.table_name} ({','.join(columns)})"
        )
        return self.db.execute_pragma(query)

    def drop_table(self) -> QueryResult:
        """删除表。"""

        query = f"DROP TABLE IF EXISTS {self.table_name}"
        return self.db.execute_pragma(query)

    def truncate(self) -> QueryResult:
        """清空表（删除所有行）。"""

        query = f"DELETE FROM {self.table_name}"
        return self.db.execute_delete(query)


class ODSDetailDAO(DAOBase):
    """ODS 明细层 DAO。"""

    def __init__(self, db: DatabaseConnection, business_tag: str):
        super().__init__(db, f"ODS_{business_tag}_DETAIL")
        self.business_tag = business_tag

    def find_by_invoice(self, invoice_code: str, invoice_number: str) -> Optional[Dict[str, Any]]:
        query = f"SELECT * FROM {self.table_name} WHERE 发票代码=? AND 发票号码=? LIMIT 1"
        result = self.db.execute_select(query, (invoice_code, invoice_number))
        return result.to_first_dict() if result.is_success() else None

    def find_by_year(self, year: str) -> List[Dict[str, Any]]:
        query = f"SELECT * FROM {self.table_name} WHERE 开票年份=? ORDER BY rowid"
        result = self.db.execute_select(query, (year,))
        return result.to_dict_list() if result.is_success() else []

    def get_distinct_years(self) -> List[str]:
        query = (
            f"SELECT DISTINCT 开票年份 as y FROM {self.table_name} "
            "WHERE 开票年份 IS NOT NULL ORDER BY y"
        )
        result = self.db.execute_select(query)
        if result.is_success():
            return [row[0] for row in result.rows if row[0] and str(row[0]).isdigit()]
        return []

    def count_by_year(self, year: str) -> int:
        return self.count("开票年份=?", (year,))


class ODSHeaderDAO(DAOBase):
    """ODS 表头层 DAO。"""

    def __init__(self, db: DatabaseConnection, business_tag: str):
        super().__init__(db, f"ODS_{business_tag}_HEADER")
        self.business_tag = business_tag

    def find_by_invoice(self, invoice_code: str, invoice_number: str) -> Optional[Dict[str, Any]]:
        query = f"SELECT * FROM {self.table_name} WHERE 发票代码=? AND 发票号码=? LIMIT 1"
        result = self.db.execute_select(query, (invoice_code, invoice_number))
        return result.to_first_dict() if result.is_success() else None

    def find_by_year(self, year: str) -> List[Dict[str, Any]]:
        query = f"SELECT * FROM {self.table_name} WHERE 开票年份=? ORDER BY rowid"
        result = self.db.execute_select(query, (year,))
        return result.to_dict_list() if result.is_success() else []

    def get_distinct_years(self) -> List[str]:
        query = (
            f"SELECT DISTINCT 开票年份 as y FROM {self.table_name} "
            "WHERE 开票年份 IS NOT NULL ORDER BY y"
        )
        result = self.db.execute_select(query)
        if result.is_success():
            return [row[0] for row in result.rows if row[0] and str(row[0]).isdigit()]
        return []

    def count_by_year(self, year: str) -> int:
        return self.count("开票年份=?", (year,))


class LedgerDAO(DAOBase):
    """LEDGER 层 DAO。"""

    def __init__(self, db: DatabaseConnection, business_tag: str, year: str, ledger_type: str):
        if ledger_type not in ("detail", "header"):
            raise ValueError(f"Invalid ledger_type: {ledger_type}")
        self.ledger_type = ledger_type
        table_suffix = "INVOICE_DETAIL" if ledger_type == "detail" else "INVOICE_HEADER"
        super().__init__(db, f"LEDGER_{business_tag}_{year}_{table_suffix}")
        self.business_tag = business_tag
        self.year = year

    def find_by_invoice(self, invoice_code: str, invoice_number: str) -> Optional[Dict[str, Any]]:
        query = f"SELECT * FROM {self.table_name} WHERE 发票代码=? AND 发票号码=? LIMIT 1"
        result = self.db.execute_select(query, (invoice_code, invoice_number))
        return result.to_first_dict() if result.is_success() else None

    def find_by_seller(self, seller_id: str) -> List[Dict[str, Any]]:
        query = f"SELECT * FROM {self.table_name} WHERE 销方识别号=? ORDER BY 开票日期"
        result = self.db.execute_select(query, (seller_id,))
        return result.to_dict_list() if result.is_success() else []

    def find_by_buyer(self, buyer_id: str) -> List[Dict[str, Any]]:
        query = f"SELECT * FROM {self.table_name} WHERE 购方识别号=? ORDER BY 开票日期"
        result = self.db.execute_select(query, (buyer_id,))
        return result.to_dict_list() if result.is_success() else []

    def count_by_status(self, status: str) -> int:
        return self.count("发票状态=?", (status,))


class OADSAnalyticsDAO(DAOBase):
    """ADS（应用数据存储）分析层 DAO。"""

    def __init__(self, db: DatabaseConnection, table_name: str):
        super().__init__(db, table_name)

    def find_anomalies_by_type(self, anomaly_type: str) -> List[Dict[str, Any]]:
        query = f"SELECT * FROM {self.table_name} WHERE 异常类型=? ORDER BY 发票代码"
        result = self.db.execute_select(query, (anomaly_type,))
        return result.to_dict_list() if result.is_success() else []

    def find_by_invoice_with_risk(
        self,
        invoice_code: str,
        invoice_number: str,
        min_risk_score: float = 0,
    ) -> Optional[Dict[str, Any]]:
        query = (
            f"SELECT * FROM {self.table_name} WHERE 发票代码=? AND 发票号码=? "
            "AND 风险评分>=? LIMIT 1"
        )
        result = self.db.execute_select(query, (invoice_code, invoice_number, min_risk_score))
        return result.to_first_dict() if result.is_success() else None


__all__ = [
    "connect_sqlite",
    "QueryResult",
    "DatabaseConnection",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "SQLInjectionError",
    "DAOBase",
    "ODSDetailDAO",
    "ODSHeaderDAO",
    "LedgerDAO",
    "OADSAnalyticsDAO",
]