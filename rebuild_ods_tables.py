import sqlite3

# 配置数据库路径（请根据实际情况修改）
DB_PATH = 'D:/PythonCode/Invoice_Insight_Project/database/VAT_INV_Audit_Repo.db'  # 已修正为实际数据库文件路径

# ODS表头字段顺序（严格按你要求）
ODS_HEADER_COLUMNS = [
    "header_uuid","source_system","created_at","created_by","updated_at","updated_by","import_batch_id","sync_status","clean_status",
    "detail_total_amount","is_balanced","balance_diff","balance_tolerance","balance_check_time","balance_check_by","balance_notes",
    "related_blue_invoice_uuid","fpdm","fphm","sdfphm","xfsbh","xfmc","gfsbh","gfmc","kprq","invoice_date","invoice_time",
    "je","se","jshj","fply","fppz","fpzt","sfzsfp","fpfxdj","kpr","bz"
]

# ODS明细表字段顺序（严格按你要求）
ODS_DETAIL_COLUMNS = [
    "detail_uuid","header_uuid","logic_line_no","updated_at","updated_by","import_batch_id","source_system","sync_status","clean_status",
    "fpdm","fphm","sdfphm","invoice_date","hwlwmc","ggxh","dw","sl","dj","je","slv","se","jshj"
]

# 目标表名（请根据实际业务年份修改）
HEADER_TABLE = "ODS_VAT_INV_HEADER_FULL_2023"
DETAIL_TABLE = "ODS_VAT_INV_DETAIL_FULL_2023"

def rebuild_table(conn, table_name, columns):
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    # 默认全部TEXT类型，可根据需要自定义类型
    col_defs = ", ".join([f'{col} TEXT' for col in columns])
    sql = f"CREATE TABLE {table_name} ({col_defs})"
    cursor.execute(sql)
    conn.commit()
    print(f"[OK] {table_name} 已重建，字段：{columns}")

def main():
    conn = sqlite3.connect(DB_PATH)
    rebuild_table(conn, HEADER_TABLE, ODS_HEADER_COLUMNS)
    rebuild_table(conn, DETAIL_TABLE, ODS_DETAIL_COLUMNS)
    conn.close()
    print("全部ODS表已重建完毕。请用 PRAGMA table_info 验证！")

if __name__ == "__main__":
    main()
