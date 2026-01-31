import sqlite3
import os

# 使用相对路径，保证可移植性
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'VAT_INV_Audit_Repo.db')
SQL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ODS_TABLE.SQL')

def execute_sql_file(conn, sql_file):
    with open(sql_file, encoding='utf-8') as f:
        sql = f.read()
    for stmt in sql.split(';'):
        stmt = stmt.strip()
        if stmt and not stmt.startswith('--'):
            try:
                conn.execute(stmt)
            except Exception as e:
                print(f"[WARN] 执行失败: {stmt[:80]}... \n原因: {e}")

def main():
    conn = sqlite3.connect(DB_PATH)
    execute_sql_file(conn, SQL_FILE)
    conn.commit()
    conn.close()
    print("ODS表已按SQL文件全部重建。")

if __name__ == "__main__":
    main()
