"""
ETL脚本模板：DWD层 → DWS层
- 读取DWD表，聚合、汇总，写入DWS表
- 字段顺序、类型、注释等建议自动从SQL文件提取
"""
import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'VAT_INV_Audit_Repo.db')
DWD_HEADER_TABLE = 'DWD_VAT_INV_HEADER_FULL_2023'
DWS_HEADER_TABLE = 'DWS_VAT_INV_HEADER_MONTH_2023'

# TODO: 可自动提取字段顺序/类型
DWD_HEADER_COLUMNS = []  # 后续补充
DWS_HEADER_COLUMNS = []  # 后续补充

def etl_dwd_to_dws():
    conn = sqlite3.connect(DB_PATH)
    # 读取DWD表
    df = pd.read_sql(f'SELECT * FROM {DWD_HEADER_TABLE}', conn)
    # TODO: 聚合、汇总等ETL处理
    # df = ...
    # 写入DWS表
    df.to_sql(DWS_HEADER_TABLE, conn, if_exists='replace', index=False)
    print(f"DWD→DWS数据已写入: {DWS_HEADER_TABLE}")
    conn.close()

if __name__ == "__main__":
    etl_dwd_to_dws()
