import pandas as pd

# 模拟代码
summary_columns = set(['发票代码', '开票日期', 'AUDIT_SRC_FILE', 'AUDIT_IMPORT_TIME', '开票年份', '税率_数值'])
detail_columns = set(['发票号码', '开票日期', 'AUDIT_SRC_FILE', 'AUDIT_IMPORT_TIME', '开票年份', '税率_数值'])

# 模拟summary sheet
df = pd.DataFrame({
    '发票代码': ['001', '002'],
    '开票日期': ['2021-12-31', '2021-12-30']
})

print("Before adding audit columns:")
print(df.columns.tolist())
print()

df['AUDIT_SRC_FILE'] = 'test.xlsx'
df['AUDIT_IMPORT_TIME'] = '2026-01-03'

print("After adding audit columns:")
print(df.columns.tolist())
print()

# 提取开票年份列
if '开票日期' in df.columns:
    df['开票年份'] = df['开票日期'].astype(str).str[:4]
else:
    df['开票年份'] = None

print("After adding 开票年份:")
print(df.columns.tolist())
print(df)
print()

# reindex
df = df.reindex(columns=list(summary_columns))

print("After reindex:")
print(df.columns.tolist())
print(df)
print()

# Check if 开票年份 is in summary_columns
print(f"Is '开票年份' in summary_columns? {'开票年份' in summary_columns}")
