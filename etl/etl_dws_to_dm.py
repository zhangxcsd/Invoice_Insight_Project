"""
ETL脚本模板：DWS层 → DM层
- 读取DWS表，专题分析、加工，写入DM表
- 字段顺序、类型、注释等建议自动从SQL文件提取
"""
import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'VAT_INV_Audit_Repo.db')
DWS_HEADER_TABLE = 'DWS_VAT_INV_HEADER_MONTH_2023'
DM_HEADER_TABLE = 'DM_TOPIC_HEADER_2023'

# TODO: 可自动提取字段顺序/类型
DWS_HEADER_COLUMNS = []  # 后续补充
DM_HEADER_COLUMNS = []  # 后续补充

def etl_dws_to_dm():
    conn = sqlite3.connect(DB_PATH)
    # 读取DWS表
    df = pd.read_sql(f'SELECT * FROM {DWS_HEADER_TABLE}', conn)
    # TODO: 专题分析、加工等ETL处理
    # df = ...
    # 写入DM表
    df.to_sql(DM_HEADER_TABLE, conn, if_exists='replace', index=False)
    print(f"DWS→DM数据已写入: {DM_HEADER_TABLE}")
    conn.close()

if __name__ == "__main__":
    etl_dws_to_dm()
