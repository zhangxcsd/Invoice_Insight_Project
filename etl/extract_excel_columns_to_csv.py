"""
自动提取Excel各sheet字段名并输出为csv
- "信息汇总表"sheet → ODS明细表字段
- "发票基础信息"sheet → ODS主表字段
"""
import os
import pandas as pd

EXCEL_PATH = r'Source_Data/天诚（山东）健康科技有限公司/进项发票/天诚21年取得发票全量发票查询导出结果 (53).xlsx'
OUTPUT_DIR = 'etl/excel_columns_output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_columns(excel_path, sheet_keyword, output_csv):
    xl = pd.ExcelFile(excel_path)
    for sheet in xl.sheet_names:
        if sheet_keyword in sheet:
            df = xl.parse(sheet, nrows=0)
            columns = list(df.columns)
            pd.DataFrame({'字段名': columns}).to_csv(output_csv, index=False, encoding='utf-8-sig')
            print(f"已输出: {output_csv}")
            return columns
    print(f"未找到包含'{sheet_keyword}'的sheet")
    return []

def main():
    extract_columns(EXCEL_PATH, '发票基础信息', os.path.join(OUTPUT_DIR, 'ods_header_columns.csv'))
    extract_columns(EXCEL_PATH, '信息汇总表', os.path.join(OUTPUT_DIR, 'ods_detail_columns.csv'))

if __name__ == "__main__":
    main()
