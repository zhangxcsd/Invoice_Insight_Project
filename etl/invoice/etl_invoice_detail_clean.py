"""
发票明细表清洗ETL脚本
- 读取ODS发票明细表，清洗、去重、标准化，写入DWD发票明细表
- 可扩展日志、调度、字段顺序自动提取等
"""
import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'database', 'VAT_INV_Audit_Repo.db')
ODS_DETAIL_TABLE = 'ODS_VAT_INV_DETAIL_FULL_2023'
DWD_DETAIL_TABLE = 'DWD_VAT_INV_DETAIL_FULL_2023'

# TODO: 可自动提取字段顺序/类型
ODS_DETAIL_COLUMNS = []  # 可用extract_ods_fields.py自动生成
DWD_DETAIL_COLUMNS = []  # 后续补充

def etl_invoice_detail_clean():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(f'SELECT * FROM {ODS_DETAIL_TABLE}', conn)
    # TODO: 清洗、去重、标准化等ETL处理
    # df = ...
    df.to_sql(DWD_DETAIL_TABLE, conn, if_exists='replace', index=False)
    print(f"ODS发票明细表→DWD发票明细表数据已写入: {DWD_DETAIL_TABLE}")
    conn.close()

if __name__ == "__main__":
    etl_invoice_detail_clean()
