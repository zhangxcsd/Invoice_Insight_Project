import pandas as pd
import os

source_data_dir = 'd:\\PythonCode\\VAT_Audit_Project\\Source_Data\\天诚（山东）健康科技有限公司\\销项发票'

# 找到第一个Excel文件
for file in os.listdir(source_data_dir):
    if file.endswith('.xlsx'):
        filepath = os.path.join(source_data_dir, file)
        print(f"Reading {file}...")
        
        # 获取所有sheet名称
        xls = pd.ExcelFile(filepath)
        print(f"Sheets: {xls.sheet_names}\n")
        
        # 读取第一个sheet看看有没有开票日期列
        for sheet_name in xls.sheet_names[:2]:
            try:
                df = pd.read_excel(filepath, sheet_name=sheet_name)
                print(f"Sheet: {sheet_name}")
                print(f"Shape: {df.shape}")
                print(f"Columns: {df.columns.tolist()[:10]}")
                
                # 检查是否有开票日期列
                if '开票日期' in df.columns:
                    print(f"开票日期 sample values (first 3):")
                    for val in df['开票日期'].head(3):
                        print(f"  {val} (type: {type(val).__name__})")
                else:
                    print("开票日期 column not found")
                    
            except Exception as e:
                print(f"Error reading sheet {sheet_name}: {e}")
            print()
        
        break
