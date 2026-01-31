"""
ETL脚本模板：DM层 → ADS层
- 读取DM表，生成最终报表/线索，写入ADS表
- 字段顺序、类型、注释等建议自动从SQL文件提取
"""
import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'VAT_INV_Audit_Repo.db')
DM_HEADER_TABLE = 'DM_TOPIC_HEADER_2023'
ADS_HEADER_TABLE = 'ADS_FINAL_REPORT_2023'

# TODO: 可自动提取字段顺序/类型
DM_HEADER_COLUMNS = []  # 后续补充
ADS_HEADER_COLUMNS = []  # 后续补充

def etl_dm_to_ads():
    conn = sqlite3.connect(DB_PATH)
    # 读取DM表
    df = pd.read_sql(f'SELECT * FROM {DM_HEADER_TABLE}', conn)
    # TODO: 生成最终报表/线索等ETL处理
    # df = ...
    # 写入ADS表
    df.to_sql(ADS_HEADER_TABLE, conn, if_exists='replace', index=False)
    print(f"DM→ADS数据已写入: {ADS_HEADER_TABLE}")
    conn.close()

if __name__ == "__main__":
    etl_dm_to_ads()
