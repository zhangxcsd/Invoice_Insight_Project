
"""
发票明细表ETL导入脚本
- 读取Excel“信息汇总表”sheet，字段自动对齐ODS明细表，生成detail_uuid、logic_line_no等技术字段，批次号/来源文件由用户输入
- 字段校验、日志、异常处理
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) )

import os
import pandas as pd
import sqlite3
import hashlib
import logging
import fnmatch
import difflib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'database', 'VAT_INV_Audit_Repo.db')
ODS_DETAIL_TABLE = 'ODS_VAT_INV_DETAIL_FULL_2023'
ODS_DETAIL_COLUMNS = [
    "detail_uuid", "header_uuid", "logic_line_no", "updated_at", "updated_by", "import_batch_id", "source_system", "source_file", "sync_status", "clean_status",
    "fpdm", "fphm", "sdfphm", "xfsbh", "xfmc", "gfsbh", "gfmc", "kprq", "invoice_date", "invoice_time", "ssflbm", "tdywlx", "hwlwmc", "ggxh", "dw", "sl", "dj", "je", "slv", "se", "jshj",
    "fply", "fppz", "fpzt", "sfzsfp", "fpfxdj", "kpr", "bz"
]
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
            # ====== 唯一性校验与导出（原始数据） ======
            # 字段名标准化：去除首尾空格、全角转半角
            df_raw.columns = [str(c).strip().replace('　', '').replace(' ', '') for c in df_raw.columns]
            # 生成原始header_uuid用于唯一性校验
            df_raw['_header_uuid_check'] = df_raw.apply(lambda row: gen_header_uuid({
                'fpdm': row.get('发票代码', row.get('fpdm', '')),
                'fphm': row.get('发票号码', row.get('fphm', '')),
                'sdfphm': row.get('数电发票号码', row.get('sdfphm', ''))
            }), axis=1)
            duplicated_header = df_raw[df_raw['_header_uuid_check'].duplicated(keep=False)]
            if not duplicated_header.empty:
                ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                header_outfile = f'ODS_被去重的发票信息_HEADER_{batch_id}_{ts}.xlsx'
                header_outpath = os.path.join(outputs_dir, header_outfile)
                duplicated_header.drop(columns=['_header_uuid_check']).to_excel(header_outpath, index=False)
                logging.warning(f'检测到header_uuid重复，已导出原始重复主表数据到: {header_outpath}')
                df_raw = df_raw[~df_raw['_header_uuid_check'].duplicated(keep=False)].copy()
            # 生成原始logic_line_no用于唯一性校验
            df_raw['_logic_line_no_check'] = df_raw.groupby('_header_uuid_check').cumcount() + 1
            # 生成原始detail_uuid用于唯一性校验
            df_raw['_detail_uuid_check'] = df_raw.apply(lambda row: gen_detail_uuid({
                'fpdm': row.get('发票代码', row.get('fpdm', '')),
                'fphm': row.get('发票号码', row.get('fphm', '')),
                'sdfphm': row.get('数电发票号码', row.get('sdfphm', '')),
                'logic_line_no': row['_logic_line_no_check']
            }), axis=1)
            duplicated_detail = df_raw[df_raw['_detail_uuid_check'].duplicated(keep=False)]
            if not duplicated_detail.empty:
                ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                detail_outfile = f'ODS_被去重的发票信息_DETAIL_{batch_id}_{ts}.xlsx'
                detail_outpath = os.path.join(outputs_dir, detail_outfile)
                duplicated_detail.drop(columns=['_header_uuid_check','_logic_line_no_check','_detail_uuid_check']).to_excel(detail_outpath, index=False)
                logging.warning(f'检测到detail_uuid重复，已导出原始重复明细数据到: {detail_outpath}')
                df_raw = df_raw[~df_raw['_detail_uuid_check'].duplicated(keep=False)].copy()
            # 去除唯一性校验辅助列
            df_raw.drop(columns=['_header_uuid_check','_logic_line_no_check','_detail_uuid_check'], inplace=True)
            # 后续只对无重复的原始数据做字段适配和技术字段生成
            df = df_raw.copy()
            # ...existing code...
            # 去除所有重复列，只保留最后一列，彻底避免 Series 歧义：
            # pandas 允许 DataFrame 存在同名列（如多次读取、拼接时），此时 df['列名'] 取到的是 Series（多列），
            # 而不是单一值，导致 row[col] 判断歧义和相关报错。此处只保留最后一列，保证后续取值唯一。
            df = df.loc[:, ~df.columns.duplicated(keep='last')]

            # 剔除合计/无效行：只要 'fpdm'、'fphm'、'sdfphm' 三字段全为空（None、空字符串或空格），该行就会被自动剔除。
            # 这通常能覆盖绝大多数合计行和无效行。
            def is_all_empty(row):
                for col in ['fpdm', 'fphm', 'sdfphm']:
                    val = row[col]
                    if isinstance(val, pd.Series):
                        print(f"调试：row[{col}] 是 Series，内容：{val}")
                        val = val.iloc[0]
                    if not (pd.isnull(val) or str(val).strip().replace('　', '') == ""):
                        return False
                return True
            before = len(df)
            df = df[~df.apply(is_all_empty, axis=1)]
            removed = before - len(df)
            if removed > 0:
                logging.info(f'剔除合计/无效行 {removed} 条（fpdm、fphm、sdfphm全为空/空字符串/空格）')
            # fpdm, fphm, sdfphm, ssflbm强制转为字符串，防止小数点问题
            for col in ['fpdm', 'fphm', 'sdfphm', 'ssflbm']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: str(int(x)) if pd.notnull(x) and isinstance(x, float) and x.is_integer() else str(x) if pd.notnull(x) else x)
            # sl/dj保留excel原始精度，若超8位则截断到8位，不做四舍五入
            for col in ['sl', 'dj']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: (str(x)[:str(x).find('.')+9] if '.' in str(x) and len(str(x).split('.')[-1])>8 else str(x)) if pd.notnull(x) else x)
                    # 转回float以便写入数据库
                    df[col] = df[col].astype(float)
            # 从kprq识别invoice_date和invoice_time
            # 年度分表处理思路：
            # 1. 采集时自动识别每条数据的年度（invoice_date字段年份）
            # 2. 按年度动态生成目标表名，如ODS_VAT_INV_DETAIL_FULL_2024
            # 3. 按年度分组写入对应表，若表不存在可自动建表（结构同2023表）
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
            df['invoice_date'], df['invoice_time'] = zip(*df['kprq'].map(extract_date_time))
            df['header_uuid'] = df.apply(gen_header_uuid, axis=1)
            # 检查header_uuid重复，若有则导出重复数据
            duplicated_header = df[df['header_uuid'].duplicated(keep=False)]
            if not duplicated_header.empty:
                ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                header_outfile = f'ODS_被去重的发票信息_HEADER_{batch_id}_{ts}.xlsx'
                header_outpath = os.path.join(outputs_dir, header_outfile)
                duplicated_header.to_excel(header_outpath, index=False)
                logging.warning(f'检测到header_uuid重复，已导出重复主表数据到: {header_outpath}')
                # 去重，仅保留首条
                df = df[~df['header_uuid'].duplicated(keep='first')].copy()
            df['logic_line_no'] = df.groupby(['header_uuid']).cumcount() + 1
            # 若有NaN，丢弃异常行并日志提示
            invalid_logic_line = df['logic_line_no'].isnull().sum()
            if invalid_logic_line > 0:
                logging.warning(f'有{invalid_logic_line}条明细数据因logic_line_no生成异常被丢弃')
                # 输出部分异常行样本
                logging.warning(f'异常样本: {df[df["logic_line_no"].isnull()][["fpdm","fphm","sdfphm"]].head()}')
            df = df[df['logic_line_no'].notnull()].copy()
            df.loc[:, 'logic_line_no'] = df['logic_line_no'].astype(int)
            df['header_uuid'] = df.apply(gen_header_uuid, axis=1)
            df['detail_uuid'] = df.apply(gen_detail_uuid, axis=1)
            # 检查detail_uuid重复，若有则导出重复数据
            duplicated_detail = df[df['detail_uuid'].duplicated(keep=False)]
            if not duplicated_detail.empty:
                ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                detail_outfile = f'ODS_被去重的发票信息_DETAIL_{batch_id}_{ts}.xlsx'
                detail_outpath = os.path.join(outputs_dir, detail_outfile)
                duplicated_detail.to_excel(detail_outpath, index=False)
                logging.warning(f'检测到detail_uuid重复，已导出重复明细数据到: {detail_outpath}')
                # 去重，仅保留首条
                df = df[~df['detail_uuid'].duplicated(keep='first')].copy()
            df['import_batch_id'] = batch_id
            df['source_system'] = source_system
            df['source_file'] = os.path.basename(rel_excel_path)
            # 健壮性处理：year为空的行丢弃，统计分布
            df['year'] = df['invoice_date'].apply(lambda x: str(x)[:4] if pd.notnull(x) and len(str(x)) >= 4 else None)
            invalid_year = df['year'].isnull().sum()
            if invalid_year > 0:
                logging.warning(f'有{invalid_year}条明细数据因kprq/invoice_date缺失被丢弃')
            df = df[df['year'].notnull()]
            logging.info(f'明细数据各年度分布: {df["year"].value_counts().to_dict()}')
            for year, df_year in df.groupby('year'):
                table_name = f'ODS_VAT_INV_DETAIL_FULL_{year}'
                # 自动建表（如不存在）
                conn.execute(f'''CREATE TABLE IF NOT EXISTS {table_name} (
                    detail_uuid TEXT, header_uuid TEXT, logic_line_no INT, updated_at TEXT, updated_by TEXT, import_batch_id TEXT, source_system TEXT, source_file TEXT, sync_status TEXT, clean_status TEXT,
                    fpdm TEXT, fphm TEXT, sdfphm TEXT, xfsbh TEXT, xfmc TEXT, gfsbh TEXT, gfmc TEXT, kprq TEXT, invoice_date TEXT, invoice_time TEXT, ssflbm TEXT, tdywlx TEXT, hwlwmc TEXT, ggxh TEXT, dw TEXT, sl REAL, dj REAL, je REAL, slv REAL, se REAL, jshj REAL,
                    fply TEXT, fppz TEXT, fpzt TEXT, sfzsfp TEXT, fpfxdj TEXT, kpr TEXT, bz TEXT
                )''')
                df_year.drop(columns=['year'], inplace=True)
                df_year.to_sql(table_name, conn, if_exists='append', index=False)
                logging.info(f'导入: {rel_excel_path} -> {table_name}, 行数: {len(df_year)}')
                total_rows += len(df_year)
        except Exception as e:
            logging.error(f'导入失败: {excel_path}, 错误: {e}')
    conn.close()
    logging.info(f'全部明细表数据导入完成，总行数: {total_rows}')

if __name__ == "__main__":
    main()
