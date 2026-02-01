
"""
发票明细表ETL导入脚本
- 读取Excel“信息汇总表”sheet，字段自动对齐ODS明细表，生成detail_uuid、logic_line_no等技术字段，批次号/来源文件由用户输入
- 字段校验、日志、异常处理
"""

import sys, os
import pandas as pd
import sqlite3
import fnmatch
import logging
import hashlib

# 项目根目录，所有相对路径的基准点
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 明细表数据库路径（与主表一致，便于统一管理）
DB_PATH = os.path.join(BASE_DIR, 'database', 'VAT_INV_Audit_Repo.db')

# 全部ODS明细表字段
ODS_DETAIL_COLUMNS = [
    "detail_uuid", "header_uuid", "logic_line_no", "updated_at", "updated_by", "import_batch_id", "source_system", "source_file", "sync_status", "clean_status",
    "fpdm", "fphm", "sdfphm", "xfsbh", "xfmc", "gfsbh", "gfmc", "kprq", "invoice_date", "invoice_time", "ssflbm", "tdywlx", "hwlwmc", "ggxh", "dw", "sl", "dj", "je", "slv", "se", "jshj",
    "fply", "fppz", "fpzt", "sfzsfp", "fpfxdj", "kpr", "bz"
]
# Excel字段到ODS字段映射
EXCEL_TO_ODS_DETAIL = {
    "发票代码": "fpdm", "发票号码": "fphm", "数电发票号码": "sdfphm", "销方识别号": "xfsbh", "销方名称": "xfmc", "购方识别号": "gfsbh", "购买方名称": "gfmc", "开票日期": "kprq", "税收分类编码": "ssflbm", "特定业务类型": "tdywlx", "货物或应税劳务名称": "hwlwmc", "规格型号": "ggxh", "单位": "dw", "数量": "sl", "单价": "dj", "金额": "je", "税率": "slv", "税额": "se", "价税合计": "jshj", "发票来源": "fply", "发票票种": "fppz", "发票状态": "fpzt", "是否正数发票": "sfzsfp", "发票风险等级": "fpfxdj", "开票人": "kpr", "备注": "bz"
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def gen_detail_uuid(row):
    key = (str(row.get('fpdm', '')) + str(row.get('fphm', '')) + str(row.get('sdfphm', '')) + str(row.get('logic_line_no', ''))).replace('－', '-').replace('　', '').replace(' ', '')
    return hashlib.md5(key.encode('utf-8')).hexdigest()

def gen_header_uuid(row):
    key = (str(row.get('fpdm', '')) + str(row.get('fphm', '')) + str(row.get('sdfphm', ''))).replace('－', '-').replace('　', '').replace(' ', '')
    return hashlib.md5(key.encode('utf-8')).hexdigest()

def align_excel_to_ods(df, mapping, ods_columns):
    cols = {k: v for k, v in mapping.items() if k in df.columns}
    df = df.rename(columns=cols)
    for ods_col in ods_columns:
        if ods_col not in df.columns:
            df[ods_col] = None
    df = df[ods_columns]
    return df

def find_all_excels(root_dir):
    matches = []
    for root, dirnames, filenames in os.walk(root_dir):
        for pattern in ('*.xlsx', '*.xls'):
            for filename in fnmatch.filter(filenames, pattern):
                matches.append(os.path.join(root, filename))
    return matches

def main():
    # 合并所有Excel后再生成invoice_date和invoice_time
    def extract_date_time(val):
        import re
        if pd.isnull(val):
            return None, None
        if isinstance(val, pd.Timestamp):
            d = val.strftime('%Y-%m-%d')
            t = val.strftime('%H:%M:%S') if val.hour+val.minute+val.second > 0 else None
            return d, t
        s = str(val).strip()
        m = re.match(r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})', s)
        date_part = m.group(1).replace('/', '-') if m else None
        m2 = re.search(r'(\d{1,2}:\d{2}(:\d{2})?)', s)
        time_part = m2.group(1) if m2 else None
        if time_part and len(time_part.split(':'))==2:
            time_part += ':00'
        return date_part, time_part
    # ...existing code...
    import os
    from datetime import datetime
    outputs_dir = os.path.join(BASE_DIR, 'Outputs')
    os.makedirs(outputs_dir, exist_ok=True)
    # 统一相对路径，递归遍历Source_Data下所有Excel
    source_data_dir = os.path.join(BASE_DIR, 'Source_Data')
    excel_files = find_all_excels(source_data_dir)
    if not excel_files:
        logging.error(f'未找到任何Excel文件: {source_data_dir}')
        return
    batch_id = input('请输入本次导入批次号: ').strip()
    source_system = '金税导出'  # 默认值，ODS表已设定
    conn = sqlite3.connect(DB_PATH)
    total_rows = 0
    # 1. 批量读取所有文件，字段适配后合并为总DataFrame
    all_dfs = []
    for excel_path in excel_files:
        try:
            rel_excel_path = os.path.relpath(excel_path, BASE_DIR)
            dtype_map = {k: str for k in ['发票代码', '发票号码', '数电发票号码', '税收分类编码'] if k in pd.read_excel(excel_path, nrows=0).columns}
            df_dict = pd.read_excel(excel_path, sheet_name=None, dtype=dtype_map if dtype_map else None)
            detail_sheet = [k for k in df_dict if k.replace(' ', '').replace('　', '').startswith('信息汇总表')]
            df = None
            if not detail_sheet:
                logging.warning(f'{rel_excel_path}: 未找到“信息汇总表”sheet（含变体），自动尝试所有sheet字段名...')
                best_match = None
                best_overlap = 0
                for sheet_name, df_tmp in df_dict.items():
                    cols = set([str(c).strip().replace('　', '').replace(' ', '') for c in df_tmp.columns])
                    overlap = len(set(EXCEL_TO_ODS_DETAIL.keys()) & cols)
                    logging.info(f'{rel_excel_path}: sheet: {sheet_name}, 字段: {list(df_tmp.columns)}, 关键字段重合数: {overlap}')
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_match = sheet_name
                if best_match and best_overlap >= 3:
                    logging.warning(f'{rel_excel_path}: 自动选择字段重合度最高的sheet: {best_match} (重合字段数: {best_overlap})')
                    df_raw = df_dict[best_match]
                else:
                    continue
            else:
                df_raw = df_dict[detail_sheet[0]]
            df_raw.columns = [str(c).strip().replace('　', '').replace(' ', '') for c in df_raw.columns]
            df_raw = align_excel_to_ods(df_raw, EXCEL_TO_ODS_DETAIL, ODS_DETAIL_COLUMNS)
            df_raw['__source_file__'] = rel_excel_path  # 记录来源文件，便于核查
            all_dfs.append(df_raw)
        except Exception as e:
            logging.error(f'导入失败: {excel_path}, 错误: {e}')
    if not all_dfs:
        logging.error('无有效明细数据，终止处理。')
        return
    all_df = pd.concat(all_dfs, ignore_index=True)
    all_df['invoice_date'], all_df['invoice_time'] = zip(*all_df['kprq'].map(extract_date_time))
    # 在 detail_uuid 去重前，统计和打印 kprq 字段的分布，便于确认原始数据问题
    logging.info(f'原始明细数据 kprq 字段样本: {all_df["kprq"].head(10).tolist()}')
    kprq_null = all_df["kprq"].isnull().sum()
    kprq_empty = (all_df["kprq"].astype(str).str.strip() == '').sum()
    logging.info(f'原始明细数据 kprq 字段缺失行数: {kprq_null}，空字符串行数: {kprq_empty}，总行数: {len(all_df)}')
    # 统计 kprq 字段的年度分布
    def extract_year(val):
        import re
        if pd.isnull(val):
            return None
        s = str(val).strip()
        m = re.match(r'(\d{4})[/-]\d{1,2}[/-]\d{1,2}', s)
        return m.group(1) if m else None
    all_df['year'] = all_df['kprq'].map(extract_year)
    year_counts = all_df['year'].value_counts().to_dict()
    logging.info(f'原始明细数据各年度分布: {year_counts}')
    # 先为 all_df 赋值分组行号，再生成 detail_uuid
    all_df['_logic_line_no_check'] = all_df.groupby(['fpdm','fphm','sdfphm']).cumcount() + 1
    all_df['logic_line_no'] = all_df['_logic_line_no_check']
    # 补全所有logic_line_no为null的行（极端情况）
    if all_df['logic_line_no'].isnull().any():
        all_df['logic_line_no'] = all_df['logic_line_no'].fillna(1).astype(int)
    all_df['header_uuid'] = all_df.apply(lambda row: gen_header_uuid(row), axis=1)
    all_df['_detail_uuid_check'] = all_df.apply(lambda row: gen_detail_uuid({
        'fpdm': row.get('fpdm', ''),
        'fphm': row.get('fphm', ''),
        'sdfphm': row.get('sdfphm', ''),
        'logic_line_no': row['logic_line_no']
    }), axis=1)
    # ====== 批量填充ODS所有字段，确保每个字段有值 ======
    # import_batch_id、source_system、source_file、updated_at、updated_by、sync_status、clean_status等技术字段
    now_str = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    all_df['import_batch_id'] = batch_id
    all_df['source_system'] = source_system
    if '__source_file__' in all_df.columns:
        all_df['source_file'] = all_df['__source_file__']
    else:
        all_df['source_file'] = ''
    all_df['updated_at'] = None
    all_df['updated_by'] = None
    all_df['sync_status'] = None
    all_df['clean_status'] = None
    # 其余ODS字段如无值统一填空
    for col in ODS_DETAIL_COLUMNS:
        if col not in all_df.columns:
            all_df[col] = ''
    # 再次确保logic_line_no无null
    if all_df['logic_line_no'].isnull().any():
        all_df['logic_line_no'] = all_df['logic_line_no'].fillna(1).astype(int)
    # 按年度分别统计 detail_uuid 重复情况
    for year, df_year in all_df.groupby('year'):
        if year is None:
            continue
        detail_uuid_counts = df_year['_detail_uuid_check'].value_counts()
        repeated_detail_uuids = detail_uuid_counts[detail_uuid_counts > 1].index.tolist()
        logging.info(f'年度 {year} 明细表重复 detail_uuid 数量: {len(repeated_detail_uuids)}')
    # 去除所有重复列，只保留最后一列，彻底避免 Series 歧义：
    all_df = all_df.loc[:, ~all_df.columns.duplicated(keep='last')]

    # ====== 高性能唯一性校验（专用索引表）与导出 ======
    cursor = conn.cursor()
    # 新建 detail_uuid 索引表，仅存储 detail_uuid，并加唯一索引
    cursor.execute('''CREATE TABLE IF NOT EXISTS ODS_VAT_INV_DETAIL_UUID_INDEX (
        detail_uuid TEXT PRIMARY KEY
    )''')
    # 查询所有已存在 detail_uuid（只查索引表，极高性能）
    existing_uuids = set(row[0] for row in cursor.execute("SELECT detail_uuid FROM ODS_VAT_INV_DETAIL_UUID_INDEX"))
    # 本批次内重复uuid
    detail_uuid_counts = all_df['_detail_uuid_check'].value_counts()
    repeated_detail_uuids = set(detail_uuid_counts[detail_uuid_counts > 1].index.tolist())
    # 历史库和本批次重复uuid合集
    all_repeated_uuids = repeated_detail_uuids | existing_uuids
    duplicated_detail = all_df[all_df['_detail_uuid_check'].isin(all_repeated_uuids)]
    to_insert = all_df[~all_df['_detail_uuid_check'].isin(all_repeated_uuids)].copy()
    # 保证导出和入库前都只保留ODS字段
    duplicated_detail = duplicated_detail[[col for col in ODS_DETAIL_COLUMNS if col in duplicated_detail.columns]]
    to_insert = to_insert[[col for col in ODS_DETAIL_COLUMNS if col in to_insert.columns]]
    # 补全DataFrame重组后logic_line_no的缺失
    for df_tmp in [duplicated_detail, to_insert]:
        if 'logic_line_no' in df_tmp.columns and df_tmp['logic_line_no'].isnull().any():
            df_tmp['logic_line_no'] = df_tmp['logic_line_no'].fillna(1).astype(int)
    # detail_uuid字段赋值，防止缺失
    if 'detail_uuid' not in to_insert.columns or to_insert['detail_uuid'].isnull().any():
        to_insert['detail_uuid'] = to_insert.apply(lambda row: gen_detail_uuid(row), axis=1)
    if 'detail_uuid' not in duplicated_detail.columns or duplicated_detail['detail_uuid'].isnull().any():
        duplicated_detail['detail_uuid'] = duplicated_detail.apply(lambda row: gen_detail_uuid(row), axis=1)
    if not duplicated_detail.empty:
        ts = pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M-%S')
        detail_outfile = f'ODS_被去重的明细表_DETAIL_{ts}.xlsx'
        detail_outpath = os.path.join(BASE_DIR, 'Outputs', detail_outfile)
        duplicated_detail.to_excel(detail_outpath, index=False)
        logging.warning(f'入库前检测到detail_uuid与索引表重复 {len(duplicated_detail)} 条，已导出到: {detail_outpath}，所有重复主键已全部剔除，仅唯一数据入库')
    # 后续处理只针对唯一 detail_uuid 的 to_insert
    all_df = to_insert
    # fpdm, fphm, sdfphm, ssflbm强制转为字符串，防止小数点问题
    for col in ['fpdm', 'fphm', 'sdfphm', 'ssflbm']:
        if col in all_df.columns:
            all_df[col] = all_df[col].apply(lambda x: str(int(x)) if pd.notnull(x) and isinstance(x, float) and x.is_integer() else str(x) if pd.notnull(x) else x)
    # sl/dj保留excel原始精度，若超8位则截断到8位，不做四舍五入
    for col in ['sl', 'dj']:
        if col in all_df.columns:
            all_df[col] = all_df[col].apply(lambda x: (str(x)[:str(x).find('.')+9] if '.' in str(x) and len(str(x).split('.')[-1])>8 else str(x)) if pd.notnull(x) else x)
            # 转回float以便写入数据库
            all_df[col] = all_df[col].astype(float)
    # 从kprq识别invoice_date和invoice_time
    def extract_date_time(val):
        import re
        if pd.isnull(val):
            return None, None
        if isinstance(val, pd.Timestamp):
            d = val.strftime('%Y-%m-%d')
            t = val.strftime('%H:%M:%S') if val.hour+val.minute+val.second > 0 else None
            return d, t
        s = str(val).strip()
        m = re.match(r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})', s)
        date_part = m.group(1).replace('/', '-') if m else None
        m2 = re.search(r'(\d{1,2}:\d{2}(:\d{2})?)', s)
        time_part = m2.group(1) if m2 else None
        if time_part and len(time_part.split(':'))==2:
            time_part += ':00'
        return date_part, time_part
    # 健壮性处理：year为空的行丢弃，统计分布（修正：year基于kprq字段识别）
    all_df['year'] = all_df['kprq'].apply(lambda x: str(x)[:4] if pd.notnull(x) and len(str(x)) >= 4 else None)
    invalid_year = all_df['year'].isnull().sum()
    if invalid_year > 0:
        logging.warning(f'有{invalid_year}条明细数据因kprq缺失被丢弃')
    all_df = all_df[all_df['year'].notnull()]
    logging.info(f'明细数据各年度分布: {all_df["year"].value_counts().to_dict()}')
    for year, df_year in all_df.groupby('year'):
        table_name = f'ODS_VAT_INV_DETAIL_FULL_{year}'
        # 自动建表（如不存在）
        conn.execute(f'''CREATE TABLE IF NOT EXISTS {table_name} (
            detail_uuid TEXT PRIMARY KEY, header_uuid TEXT, logic_line_no INT, updated_at TEXT, updated_by TEXT, import_batch_id TEXT, source_system TEXT, source_file TEXT, sync_status TEXT, clean_status TEXT,
            fpdm TEXT, fphm TEXT, sdfphm TEXT, xfsbh TEXT, xfmc TEXT, gfsbh TEXT, gfmc TEXT, kprq TEXT, invoice_date TEXT, invoice_time TEXT, ssflbm TEXT, tdywlx TEXT, hwlwmc TEXT, ggxh TEXT, dw TEXT, sl REAL, dj REAL, je REAL, slv REAL, se REAL, jshj REAL,
            fply TEXT, fppz TEXT, fpzt TEXT, sfzsfp TEXT, fpfxdj TEXT, kpr TEXT, bz TEXT
        )''')
        df_year.drop(columns=['year'], inplace=True)
        # 只保留 ODS_DETAIL_COLUMNS 字段，去除 __source_file__ 等多余字段
        df_year = df_year[[col for col in ODS_DETAIL_COLUMNS if col in df_year.columns]]
        # 入库前严格主键去重和比对
        df_year['detail_uuid'] = df_year['detail_uuid'].astype(str).str.strip().str.lower()
        # 剔除空/None/nan主键
        invalid_mask = df_year['detail_uuid'].isnull() | (df_year['detail_uuid'] == 'none') | (df_year['detail_uuid'] == '') | (df_year['detail_uuid'] == 'nan')
        invalid_count = invalid_mask.sum()
        if invalid_count > 0:
            logging.warning(f'年度{year}：{invalid_count}条数据因detail_uuid为空/无效被剔除')
        df_year = df_year[~invalid_mask]
        # DataFrame 内部主键去重
        before_drop = len(df_year)
        df_year = df_year.drop_duplicates(subset=['detail_uuid'])
        dropped = before_drop - len(df_year)
        if dropped > 0:
            logging.warning(f'年度{year}：{dropped}条数据因DataFrame内部detail_uuid重复被剔除')
        # 数据库主键比对也统一 strip/lower
        existing_detail_uuids = set(str(row[0]).strip().lower() for row in conn.execute(f"SELECT detail_uuid FROM {table_name}"))
        insert_rows = []
        for idx, row in df_year.iterrows():
            uuid = row['detail_uuid']
            if uuid not in existing_detail_uuids:
                insert_rows.append(row)
        if insert_rows:
            df_insert = pd.DataFrame(insert_rows)
            df_insert = df_insert[[col for col in ODS_DETAIL_COLUMNS if col in df_insert.columns]]
            df_insert.to_sql(table_name, conn, if_exists='append', index=False)
            logging.info(f'导入: {table_name}, 行数: {len(df_insert)}')
            total_rows += len(df_insert)
        else:
            logging.info(f'导入: {table_name}, 行数: 0（全部主键已存在）')
    # 入库后批量插入新 detail_uuid 到索引表，保持索引表与业务表同步
    if not all_df.empty:
        cursor.executemany("INSERT OR IGNORE INTO ODS_VAT_INV_DETAIL_UUID_INDEX (detail_uuid) VALUES (?)", [(uuid,) for uuid in all_df['detail_uuid']])
        conn.commit()
    conn.close()
    logging.info(f'全部明细表数据导入完成，总行数: {total_rows}')

if __name__ == "__main__":
    main()
