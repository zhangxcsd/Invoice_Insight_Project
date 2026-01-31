"""
ETL脚本模板：ODS层 → DWD层
- 读取ODS表，清洗、去重、标准化，写入DWD表
- 字段顺序、类型、注释等建议自动从SQL文件提取
- 后续可扩展批量处理、调度、日志等
"""
import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'VAT_INV_Audit_Repo.db')
ODS_HEADER_TABLE = 'ODS_VAT_INV_HEADER_FULL_2023'
DWD_HEADER_TABLE = 'DWD_VAT_INV_HEADER_FULL_2023'

# TODO: 可自动提取字段顺序/类型
ODS_HEADER_COLUMNS = []  # 可用extract_ods_fields.py自动生成
DWD_HEADER_COLUMNS = []  # 后续补充

def etl_ods_to_dwd():
    conn = sqlite3.connect(DB_PATH)
    # 读取ODS表
    df = pd.read_sql(f'SELECT * FROM {ODS_HEADER_TABLE}', conn)
    # TODO: 清洗、去重、标准化等ETL处理
    # df = ...
    # 写入DWD表
    df.to_sql(DWD_HEADER_TABLE, conn, if_exists='replace', index=False)
    print(f"ODS→DWD数据已写入: {DWD_HEADER_TABLE}")
    conn.close()

if __name__ == "__main__":
    etl_ods_to_dwd()
