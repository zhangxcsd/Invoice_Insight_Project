"""
发票大数据平台 ODS层数据质量校验脚本

【脚本背景与适用范围】
本脚本用于对ODS层（原始数据层）发票主表与明细表进行批量数据质量校验，确保数据完整性、一致性和账务准确性。适用于已完成ODS层ETL导入、并按年度分表（如ODS_VAT_INV_HEADER_FULL_2023、ODS_VAT_INV_DETAIL_FULL_2023等）场景。可多次运行，支持全量/增量数据的持续质量监控。


【主要功能】
0. 唯一性校验：首先检查主表(header)和明细表(detail)的header_uuid列（主表）和detail_uuid列（明细表）是否有重复，确保唯一性，这是后续所有校验的基础。
1. 主表(header)与明细表(detail)的header_uuid互相存在性校验：
    - 明细表中header_uuid未在主表出现的，标记明细表clean_status为“主表缺失”
    - 主表中header_uuid未在明细表出现的，标记主表clean_status为“明细缺失”
2. 明细金额(jshj)自动汇总回写主表detail_total_amount字段
3. 按balance_tolerance等规则，自动校验主表“平账”状态：
    - 计算主表与明细金额差异(balance_diff)
    - 根据容差(balance_tolerance)判定is_balanced（平账/差异可接受/不平账。注：初始化导入时is_balanced的初始化值为“未校验”），后续可进行批量处理未校验）
    - 更新balance_check_time、balance_check_by字段记录校验时间和操作脚本
4. 处理所有年度分表，支持批量校验
5. 所有处理逻辑可参照ODS/ADS/SQL定义，便于后续DWD/ADS层复用和扩展。
    默认值和具体处理方式应结合实际业务需求、数据上下游约定，以及后续DWD/ADS层的复用需求进行合理设定，而非一刀切地严格照搬。这样既保证规范性，也兼顾灵活性和可维护性。

【主表与明细表命名规范说明】
主表（header）表名格式：ODS_VAT_INV_HEADER_FULL_年份（如ODS_VAT_INV_HEADER_FULL_2023）
明细表（detail）表名格式：ODS_VAT_INV_DETAIL_FULL_年份（如ODS_VAT_INV_DETAIL_FULL_2023）
如后续有其他类型表，建议统一采用类似命名规范，避免歧义。

【后续演进建议】
- 如DWD/ADS等层有类似校验需求，可将通用校验逻辑抽象为独立模块或工具包，实现多层复用
- 可扩展更多质量规则（如字段格式、唯一性、取值范围等）
- 可对接质量报告自动生成、异常明细导出等功能

【使用说明】
1. 需先完成主表和明细表的ETL导入，且表名按年度分表（如ODS_VAT_INV_HEADER_FULL_2023等）
2. 可多次运行，自动批量校验所有年度表
3. 支持增量/全量数据的质量监控
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


        # === 0. UUID唯一性异常标记 ===
        # 只对created_at最早的那一条保留为正常，其余全部标记为UUID重复
        # 标记字段：clean_status、updated_at、updated_by
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        script_name = 'data_quality_check.py'
        # 主表header_uuid唯一性
        if 'created_at' in df_header.columns:
            dup_groups = df_header.groupby('header_uuid')
            idx_to_mark = []
            for uuid, group in dup_groups:
                if len(group) > 1:
                    group_sorted = group.sort_values('created_at', ascending=True)
                    idx_to_mark.extend(group_sorted.index[1:].tolist())
            if idx_to_mark:
                print(f'主表有{len(idx_to_mark)}条header_uuid重复，样例: {df_header.loc[idx_to_mark, "header_uuid"].unique()[:5]}')
                df_header.loc[idx_to_mark, 'clean_status'] = 'UUID重复'
                df_header.loc[idx_to_mark, 'updated_at'] = now
                df_header.loc[idx_to_mark, 'updated_by'] = script_name
        # 明细表detail_uuid唯一性
        if 'created_at' in df_detail.columns:
            dup_groups = df_detail.groupby('detail_uuid')
            idx_to_mark = []
            for uuid, group in dup_groups:
                if len(group) > 1:
                    group_sorted = group.sort_values('created_at', ascending=True)
                    idx_to_mark.extend(group_sorted.index[1:].tolist())
            if idx_to_mark:
                print(f'明细表有{len(idx_to_mark)}条detail_uuid重复，样例: {df_detail.loc[idx_to_mark, "detail_uuid"].unique()[:5]}')
                df_detail.loc[idx_to_mark, 'clean_status'] = 'UUID重复'
                df_detail.loc[idx_to_mark, 'updated_at'] = now
                df_detail.loc[idx_to_mark, 'updated_by'] = script_name

        # === 1. 主表缺失/明细缺失异常标记 ===
        # 只对未被UUID重复标记的记录进行主明细缺失校验
        # 标记字段：clean_status、updated_at、updated_by
        header_set = set(df_header.loc[df_header['clean_status'].isnull(), 'header_uuid'])
        detail_set = set(df_detail.loc[df_detail['clean_status'].isnull(), 'header_uuid'])
        # 明细表header_uuid未在主表出现的
        mask = (~df_detail['header_uuid'].isin(header_set)) & (df_detail['clean_status'].isnull())
        if mask.any():
            print(f'明细表有{mask.sum()}条header_uuid未在主表找到')
            df_detail.loc[mask, 'clean_status'] = '主表缺失'
            df_detail.loc[mask, 'updated_at'] = now
            df_detail.loc[mask, 'updated_by'] = script_name
        # 主表header_uuid未在明细表出现的
        mask2 = (~df_header['header_uuid'].isin(detail_set)) & (df_header['clean_status'].isnull())
        if mask2.any():
            print(f'主表有{mask2.sum()}条header_uuid未在明细表找到')
            df_header.loc[mask2, 'clean_status'] = '明细缺失'
            df_header.loc[mask2, 'updated_at'] = now
            df_header.loc[mask2, 'updated_by'] = script_name

        # === 2. 汇总明细jshj，回写主表detail_total_amount ===
        # 目的（WHY）：为每个header_uuid计算明细合计金额，用于后续平账比较
        # 做什么（WHAT）：按header_uuid汇总detail.jshj，写入header.detail_total_amount
        detail_sum = df_detail.groupby('header_uuid')['jshj'].sum().reset_index()
        df_header = df_header.merge(detail_sum, on='header_uuid', how='left', suffixes=('', '_detail_sum'))
        df_header['detail_total_amount'] = df_header['jshj_detail_sum']

        # === 3. 平账校验（仅处理未被标记异常且尚未平账的记录）===
        # WHY：
        #   - 只对当前“干净且未校验”的主表记录做自动平账，避免覆盖异常记录和人工干预结果
        # WHAT：
        #   - 对 clean_status 为空 且 is_balanced == '未校验' 的记录，根据 diff 与 balance_tolerance 判定：
        #       diff == 0           → 平账
        #       0 < diff <= 容差    → 差异可接受
        #       diff > 容差         → 不平账
        #   - 仅对状态从“未校验”变为其他值的记录，更新 balance_check_time / balance_check_by
        tolerance = df_header['balance_tolerance'].fillna(0.1)
        diff = (df_header['detail_total_amount'] - df_header['jshj']).abs()
        # 只处理：未被数据清洗标记异常 + 当前仍处于“未校验”状态的记录
        bal_mask = (df_header['clean_status'].isnull()) & (df_header['is_balanced'] == '未校验')
        # 保存原始状态，用于判断本次是否真正发生状态变更
        orig_is_balanced = df_header['is_balanced'].copy()
        # 按差额和容差更新平账状态
        df_header.loc[bal_mask & (diff == 0), 'is_balanced'] = '平账'
        df_header.loc[bal_mask & (diff > 0) & (diff <= tolerance), 'is_balanced'] = '差异可接受'
        df_header.loc[bal_mask & (diff > tolerance), 'is_balanced'] = '不平账'
        df_header.loc[bal_mask, 'balance_diff'] = diff[bal_mask]
        # 仅对状态从“未校验”变更为其他值的记录，回写平账检查时间与责任人
        changed = bal_mask & (df_header['is_balanced'] != orig_is_balanced)
        df_header.loc[changed, 'balance_check_time'] = now
        df_header.loc[changed, 'balance_check_by'] = script_name

        # === 4. 回写主表、明细表 ===
        # WHY：将当次质量校验结果持久化，供后续层级和人工核查使用
        # WHAT：删除中间列，整表覆盖写回当年主表和明细表
        df_header.drop(columns=['jshj_detail_sum'], inplace=True, errors='ignore')
        df_header.to_sql(header_table, conn, if_exists='replace', index=False)
        df_detail.to_sql(detail_table, conn, if_exists='replace', index=False)
        print(f'年度{year}校验完成，主表/明细表已更新异常标记和平账状态')
    conn.close()

if __name__ == "__main__":
    main()
