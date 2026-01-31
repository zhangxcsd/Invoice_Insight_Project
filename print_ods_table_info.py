import sqlite3

DB_PATH = 'D:/PythonCode/Invoice_Insight_Project/database/VAT_INV_Audit_Repo.db'
HEADER_TABLE = "ODS_VAT_INV_HEADER_FULL_2023"
DETAIL_TABLE = "ODS_VAT_INV_DETAIL_FULL_2023"

def print_table_info(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    rows = cursor.fetchall()
    print(f"\n[{table_name} 字段信息]")
    for row in rows:
        print(f"{row[0]:2d} | {row[1]}")
    if not rows:
        print("[表不存在]")

def main():
    conn = sqlite3.connect(DB_PATH)
    print_table_info(conn, HEADER_TABLE)
    print_table_info(conn, DETAIL_TABLE)
    conn.close()

if __name__ == "__main__":
    main()
