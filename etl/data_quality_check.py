"""
数据质量校验脚本
- 校验主表和明细表header_uuid互相存在性，异常时更新clean_status
- 汇总明细jshj，回写主表detail_total_amount，并按balance_tolerance等规则更新is_balanced、balance_diff、balance_check_time等字段
- 处理逻辑和字段默认值严格参照ODS/ADS/SQL定义

使用说明：
1. 需先完成主表和明细表的ETL导入，且表名按年度分表（如ODS_VAT_INV_HEADER_FULL_2023等）
2. 可多次运行，自动批量校验所有年度表
"""
import os
import sqlite3
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'VAT_INV_Audit_Repo.db')

# 获取所有年度表名
def get_year_tables(conn, prefix):
    sql = f"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '{prefix}_%'"
    return [row[0] for row in conn.execute(sql)]

def main():
    conn = sqlite3.connect(DB_PATH)
    # 1. 校验所有年度主表和明细表
    header_tables = get_year_tables(conn, 'ODS_VAT_INV_HEADER_FULL')
    detail_tables = get_year_tables(conn, 'ODS_VAT_INV_DETAIL_FULL')
    for year in sorted(set([t.split('_')[-1] for t in header_tables+detail_tables])):
        header_table = f'ODS_VAT_INV_HEADER_FULL_{year}'
        detail_table = f'ODS_VAT_INV_DETAIL_FULL_{year}'
        if not (header_table in header_tables and detail_table in detail_tables):
            continue
        print(f'\n校验年度: {year}')
        df_header = pd.read_sql_query(f'SELECT * FROM {header_table}', conn)
        df_detail = pd.read_sql_query(f'SELECT * FROM {detail_table}', conn)
        # 1.1 明细表header_uuid在主表中不存在，标记clean_status
        header_set = set(df_header['header_uuid'])
        detail_set = set(df_detail['header_uuid'])
        mask = ~df_detail['header_uuid'].isin(header_set)
        if mask.any():
            print(f'明细表有{mask.sum()}条header_uuid未在主表找到')
            df_detail.loc[mask, 'clean_status'] = '主表缺失'
        # 1.2 主表header_uuid在明细表中不存在，标记clean_status
        mask2 = ~df_header['header_uuid'].isin(detail_set)
        if mask2.any():
            print(f'主表有{mask2.sum()}条header_uuid未在明细表找到')
            df_header.loc[mask2, 'clean_status'] = '明细缺失'
        # 2. 汇总明细jshj，回写主表detail_total_amount
        detail_sum = df_detail.groupby('header_uuid')['jshj'].sum().reset_index()
        df_header = df_header.merge(detail_sum, on='header_uuid', how='left', suffixes=('', '_detail_sum'))
        df_header['detail_total_amount'] = df_header['jshj_detail_sum']
        # 3. 平账校验
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tolerance = df_header['balance_tolerance'].fillna(0.1)
        diff = (df_header['detail_total_amount'] - df_header['jshj']).abs()
        df_header['balance_diff'] = diff
        # 默认值处理
        df_header['is_balanced'] = df_header['is_balanced'].fillna('未校验')
        df_header['balance_check_time'] = df_header['balance_check_time'].fillna(now)
        # 校验逻辑
        df_header.loc[diff.isna(), 'is_balanced'] = '未校验'
        df_header.loc[diff==0, 'is_balanced'] = '平账'
        df_header.loc[(diff>0) & (diff<=tolerance), 'is_balanced'] = '差异可接受'
        df_header.loc[diff>tolerance, 'is_balanced'] = '不平账'
        df_header.loc[diff.notna(), 'balance_check_time'] = now
        # 回写主表、明细表
        df_header.drop(columns=['jshj_detail_sum'], inplace=True, errors='ignore')
        df_header.to_sql(header_table, conn, if_exists='replace', index=False)
        df_detail.to_sql(detail_table, conn, if_exists='replace', index=False)
        print(f'年度{year}校验完成，主表/明细表已更新异常标记和平账状态')
    conn.close()

if __name__ == "__main__":
    main()
