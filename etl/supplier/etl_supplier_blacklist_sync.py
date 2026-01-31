"""
供应商黑名单同步ETL脚本
- 读取DIM供应商黑名单，清洗、去重、标准化，写入DWD/DIM供应商表
- 可扩展日志、调度、字段顺序自动提取等
"""
import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'database', 'VAT_INV_Audit_Repo.db')
DIM_SUPPLIER_BLACKLIST_TABLE = 'DIM_SUPPLIER_BLACKLIST'
DWD_SUPPLIER_TABLE = 'DWD_SUPPLIER'

# TODO: 可自动提取字段顺序/类型
DIM_SUPPLIER_COLUMNS = []  # 后续补充
DWD_SUPPLIER_COLUMNS = []  # 后续补充

def etl_supplier_blacklist_sync():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(f'SELECT * FROM {DIM_SUPPLIER_BLACKLIST_TABLE}', conn)
    # TODO: 清洗、去重、标准化等ETL处理
    # df = ...
    df.to_sql(DWD_SUPPLIER_TABLE, conn, if_exists='replace', index=False)
    print(f"DIM供应商黑名单→DWD供应商表数据已写入: {DWD_SUPPLIER_TABLE}")
    conn.close()

if __name__ == "__main__":
    etl_supplier_blacklist_sync()
