"""
发票主表ETL导入脚本
- 读取Excel“发票基础信息”sheet，字段自动对齐ODS主表，生成header_uuid等技术字段，批次号/来源文件由用户输入
- 字段校验、日志、异常处理
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pandas as pd
import sqlite3
import hashlib
import logging
import fnmatch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'database', 'VAT_INV_Audit_Repo.db')
ODS_HEADER_TABLE = 'ODS_VAT_INV_HEADER_FULL_2023'
ODS_HEADER_COLUMNS = [
    "header_uuid", "created_at", "created_by", "updated_at", "updated_by", "import_batch_id", "source_system", "source_file", "sync_status", "clean_status",
    "detail_total_amount", "is_balanced", "balance_diff", "balance_tolerance", "balance_check_time", "balance_check_by", "balance_notes",
    "related_blue_invoice_uuid", "fpdm", "fphm", "sdfphm", "xfsbh", "xfmc", "gfsbh", "gfmc", "kprq", "invoice_date", "invoice_time",
    "je", "se", "jshj", "fply", "fppz", "fpzt", "sfzsfp", "fpfxdj", "kpr", "bz"
]
EXCEL_TO_ODS_HEADER = {
    "发票代码": "fpdm", "发票号码": "fphm", "数电发票号码": "sdfphm", "销方识别号": "xfsbh", "销方名称": "xfmc", "购方识别号": "gfsbh", "购买方名称": "gfmc", "开票日期": "kprq", "金额": "je", "税额": "se", "价税合计": "jshj", "发票来源": "fply", "发票票种": "fppz", "发票状态": "fpzt", "是否正数发票": "sfzsfp", "发票风险等级": "fpfxdj", "开票人": "kpr", "备注": "bz"
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

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
    all_dfs = []
    for excel_path in excel_files:
        try:
            rel_excel_path = os.path.relpath(excel_path, BASE_DIR)
            dtype_map = {k: str for k in ['发票代码', '发票号码', '数电发票号码'] if k in pd.read_excel(excel_path, nrows=0).columns}
            df_dict = pd.read_excel(excel_path, sheet_name=None, dtype=dtype_map if dtype_map else None)
            header_sheet = [k for k in df_dict if '发票基础信息' in k]
            if not header_sheet:
                logging.warning(f'{rel_excel_path}: 未找到“发票基础信息”sheet，跳过')
                continue
            df = df_dict[header_sheet[0]]
            if len(set(EXCEL_TO_ODS_HEADER.keys()) & set(df.columns)) < 5:
                logging.warning(f'{rel_excel_path}: 字段重合度过低，疑似混采或模板错误，跳过')
                continue
            df = align_excel_to_ods(df, EXCEL_TO_ODS_HEADER, ODS_HEADER_COLUMNS)
            df['__source_file__'] = rel_excel_path
            all_dfs.append(df)
        except Exception as e:
            logging.error(f'导入失败: {excel_path}, 错误: {e}')
    if not all_dfs:
        logging.error('无有效主表数据，终止处理。')
        return
    all_df = pd.concat(all_dfs, ignore_index=True)
    # 剔除合计行：fpdm、fphm、sdfphm全为None/空字符串/空格
    def is_all_empty(row):
        return all((pd.isnull(row[col]) or str(row[col]).strip().replace('　', '') == "") for col in ['fpdm', 'fphm', 'sdfphm'])
    before = len(all_df)
    all_df = all_df[~all_df.apply(is_all_empty, axis=1)]
    removed = before - len(all_df)
    if removed > 0:
        logging.info(f'剔除合计/无效行 {removed} 条（fpdm、fphm、sdfphm全为空/空字符串/空格）')
    # 技术字段补齐、主键生成
    for col in ['fpdm', 'fphm', 'sdfphm']:
        if col in all_df.columns:
            all_df[col] = all_df[col].apply(lambda x: str(x) if pd.notnull(x) else x)
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
    all_df['invoice_date'], all_df['invoice_time'] = zip(*all_df['kprq'].map(extract_date_time))
    import re
    def extract_blue_uuid(bz):
        if pd.isnull(bz):
            return None
        s = str(bz)
        # 规则1：对应正数发票代码+号码
        m = re.search(r'对应正数发票代码[:：]?(\d{10,20})[，, ]*号码[:：]?(\d{6,20})', s)
        if m:
            return str(m.group(1)) + str(m.group(2))
        # 规则2：被红冲蓝字发票代码和号码同时出现，拼接
        m_code = re.search(r'被红冲蓝字发票代码[:：]?(\d{10,20})', s)
        m_num = re.search(r'被红冲蓝字发票号码[:：]?(\d{6,20})', s)
        if m_code and m_num:
            return str(m_code.group(1)) + str(m_num.group(1))
        # 规则3：被红冲蓝字...号码
        m2 = re.search(r'被红冲蓝字.*?号码[:：]?(\d{10,30})', s)
        if m2:
            return str(m2.group(1))
        return None
    all_df['related_blue_invoice_uuid'] = all_df['bz'].map(extract_blue_uuid)
    all_df['header_uuid'] = all_df.apply(gen_header_uuid, axis=1)
    all_df['import_batch_id'] = batch_id
    all_df['source_system'] = source_system
    all_df['source_file'] = all_df['__source_file__']
    # 自动补齐主表四个关键字段的默认值
    from datetime import datetime
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    all_df['created_at'] = now_str if 'created_at' not in all_df.columns else all_df['created_at'].fillna(now_str)
    all_df['created_by'] = 'SYSTEM' if 'created_by' not in all_df.columns else all_df['created_by'].fillna('SYSTEM')
    all_df['is_balanced'] = '未校验' if 'is_balanced' not in all_df.columns else all_df['is_balanced'].fillna('未校验')
    all_df['balance_tolerance'] = 0.1 if 'balance_tolerance' not in all_df.columns else all_df['balance_tolerance'].fillna(0.1)
    # ====== 高性能唯一性校验（专用索引表）与导出 ======
    cursor = conn.cursor()
    # 新建 header_uuid 索引表，仅存储 header_uuid，并加唯一索引
    cursor.execute('''CREATE TABLE IF NOT EXISTS ODS_VAT_INV_HEADER_UUID_INDEX (
        header_uuid TEXT PRIMARY KEY
    )''')
    # 查询所有已存在 header_uuid（只查索引表，极高性能）
    existing_uuids = set(row[0] for row in cursor.execute("SELECT header_uuid FROM ODS_VAT_INV_HEADER_UUID_INDEX"))
    # 本批次内重复uuid
    header_uuid_counts = all_df['header_uuid'].value_counts()
    repeated_header_uuids = set(header_uuid_counts[header_uuid_counts > 1].index.tolist())
    # 历史库和本批次重复uuid合集
    all_repeated_uuids = repeated_header_uuids | existing_uuids
    # 只保留唯一 header_uuid 的数据入库，所有重复（无论历史还是本批次）都导出
    duplicated_header = all_df[all_df['header_uuid'].isin(all_repeated_uuids)]
    to_insert = all_df[~all_df['header_uuid'].isin(all_repeated_uuids)].copy()
    if not duplicated_header.empty:
        ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        header_outfile = f'ODS_被去重的主表_HEADER_{batch_id}_{ts}.xlsx'
        header_outpath = os.path.join(BASE_DIR, 'Outputs', header_outfile)
        duplicated_header.to_excel(header_outpath, index=False)
        logging.warning(f'入库前检测到header_uuid与索引表重复 {len(duplicated_header)} 条，已导出到: {header_outpath}，所有重复主键已全部剔除，仅唯一数据入库')
    # 后续处理只针对唯一 header_uuid 的 to_insert
    # 在 to_insert 上补充 year 列并过滤
    to_insert['year'] = to_insert['invoice_date'].apply(lambda x: str(x)[:4] if pd.notnull(x) and len(str(x)) >= 4 else None)
    invalid_year = to_insert['year'].isnull().sum()
    if invalid_year > 0:
        logging.warning(f'有{invalid_year}条主表数据因kprq/invoice_date缺失被丢弃')
    to_insert = to_insert[to_insert['year'].notnull()]
    logging.info(f'主表数据各年度分布: {to_insert["year"].value_counts().to_dict()}')
    allowed_fields = [
        "created_at", "created_by", "source_system", "is_balanced", "balance_tolerance"
    ]
    for year, df_year in to_insert.groupby('year'):
        table_name = f'ODS_VAT_INV_HEADER_FULL_{year}'
        # 自动建表（如不存在）
        conn.execute(f'''CREATE TABLE IF NOT EXISTS {table_name} (
            header_uuid TEXT PRIMARY KEY, created_at TEXT, created_by TEXT, updated_at TEXT, updated_by TEXT, import_batch_id TEXT, source_system TEXT, source_file TEXT, sync_status TEXT, clean_status TEXT,
            detail_total_amount REAL, is_balanced TEXT, balance_diff REAL, balance_tolerance REAL, balance_check_time TEXT, balance_check_by TEXT, balance_notes TEXT,
            related_blue_invoice_uuid TEXT, fpdm TEXT, fphm TEXT, sdfphm TEXT, xfsbh TEXT, xfmc TEXT, gfsbh TEXT, gfmc TEXT, kprq TEXT, invoice_date TEXT, invoice_time TEXT,
            je REAL, se REAL, jshj REAL, fply TEXT, fppz TEXT, fpzt TEXT, sfzsfp TEXT, fpfxdj TEXT, kpr TEXT, bz TEXT
        )''')
        df_year.drop(columns=['year', '__source_file__'], inplace=True)
        df_year.to_sql(table_name, conn, if_exists='append', index=False)
        logging.info(f'导入: {table_name}, 行数: {len(df_year)}')
        total_rows += len(df_year)
    # 入库后批量插入新 header_uuid 到索引表，保持索引表与业务表同步
    if not to_insert.empty:
        cursor.executemany("INSERT OR IGNORE INTO ODS_VAT_INV_HEADER_UUID_INDEX (header_uuid) VALUES (?)", [(uuid,) for uuid in to_insert['header_uuid']])
        conn.commit()
    conn.close()
    logging.info(f'全部主表数据导入完成，总行数: {total_rows}')

if __name__ == "__main__":
    main()
