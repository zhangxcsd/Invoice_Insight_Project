import sqlite3
import pandas as pd

db_path = 'Database/VAT_INV_Audit_Repo.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=" * 80)
print("ODS_VAT_INV_HEADER 中 开票年份 数据来源调查")
print("=" * 80)

# 查看 HEADER 表中不同格式年份对应的样本数据
print("\n1. '2023' 格式的样本数据（10000 条）:")
print("-" * 80)
c.execute("""
    SELECT 开票日期, 开票年份, SUBSTR(开票日期, 1, 4) as year_from_date
    FROM ODS_VAT_INV_HEADER
    WHERE 开票年份 = '2023'
    LIMIT 5
""")
rows = c.fetchall()
for row in rows:
    print(f"  开票日期: {row[0]} | 开票年份: {repr(row[1])} | 从日期提取: {row[2]}")

print("\n2. '2023.0' 格式的样本数据（4789 条）:")
print("-" * 80)
c.execute("""
    SELECT 开票日期, 开票年份, SUBSTR(开票日期, 1, 4) as year_from_date
    FROM ODS_VAT_INV_HEADER
    WHERE 开票年份 = '2023.0'
    LIMIT 5
""")
rows = c.fetchall()
for row in rows:
    print(f"  开票日期: {row[0]} | 开票年份: {repr(row[1])} | 从日期提取: {row[2]}")

print("\n3. '2022.0' 格式的样本数据（4343 条）:")
print("-" * 80)
c.execute("""
    SELECT 开票日期, 开票年份, SUBSTR(开票日期, 1, 4) as year_from_date
    FROM ODS_VAT_INV_HEADER
    WHERE 开票年份 = '2022.0'
    LIMIT 5
""")
rows = c.fetchall()
for row in rows:
    print(f"  开票日期: {row[0]} | 开票年份: {repr(row[1])} | 从日期提取: {row[2]}")

print("\n4. '2021.0' 格式的样本数据（185 条）:")
print("-" * 80)
c.execute("""
    SELECT 开票日期, 开票年份, SUBSTR(开票日期, 1, 4) as year_from_date
    FROM ODS_VAT_INV_HEADER
    WHERE 开票年份 = '2021.0'
    LIMIT 5
""")
rows = c.fetchall()
for row in rows:
    print(f"  开票日期: {row[0]} | 开票年份: {repr(row[1])} | 从日期提取: {row[2]}")

# 分析数据来源
print("\n5. 数据来源分析:")
print("-" * 80)

print("\n  对于 '2023.0' 格式的数据：")
c.execute("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN SUBSTR(开票日期, 1, 4) = '2023' THEN 1 ELSE 0 END) as date_2023,
           SUM(CASE WHEN SUBSTR(开票日期, 1, 4) = '2022' THEN 1 ELSE 0 END) as date_2022,
           SUM(CASE WHEN SUBSTR(开票日期, 1, 4) = '2024' THEN 1 ELSE 0 END) as date_2024,
           SUM(CASE WHEN 开票日期 IS NULL THEN 1 ELSE 0 END) as null_date
    FROM ODS_VAT_INV_HEADER
    WHERE 开票年份 = '2023.0'
""")
row = c.fetchone()
print(f"    总记录数: {row[0]}")
print(f"    开票日期为 2023-: {row[1] or 0}")
print(f"    开票日期为 2022-: {row[2] or 0}")
print(f"    开票日期为 2024-: {row[3] or 0}")
print(f"    开票日期为 NULL: {row[4] or 0}")

print("\n  对于 '2022.0' 格式的数据：")
c.execute("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN SUBSTR(开票日期, 1, 4) = '2022' THEN 1 ELSE 0 END) as date_2022,
           SUM(CASE WHEN SUBSTR(开票日期, 1, 4) = '2023' THEN 1 ELSE 0 END) as date_2023,
           SUM(CASE WHEN SUBSTR(开票日期, 1, 4) = '2021' THEN 1 ELSE 0 END) as date_2021,
           SUM(CASE WHEN 开票日期 IS NULL THEN 1 ELSE 0 END) as null_date
    FROM ODS_VAT_INV_HEADER
    WHERE 开票年份 = '2022.0'
""")
row = c.fetchone()
print(f"    总记录数: {row[0]}")
print(f"    开票日期为 2022-: {row[1] or 0}")
print(f"    开票日期为 2023-: {row[2] or 0}")
print(f"    开票日期为 2021-: {row[3] or 0}")
print(f"    开票日期为 NULL: {row[4] or 0}")

# 检查是否存在某些列中包含浮点数年份的情况
print("\n6. 检查源数据中是否直接包含 '2023.0' 这样的字符串：")
print("-" * 80)

# 获取所有列名
c.execute("PRAGMA table_info('ODS_VAT_INV_HEADER')")
columns = [col[1] for col in c.fetchall()]

# 检查那些可能包含年份数据的列
possible_year_cols = [col for col in columns if '年' in col or 'year' in col.lower()]
print(f"  可能包含年份的列: {possible_year_cols}")

# 总结
print("\n7. 结论:")
print("=" * 80)
print("""
根据数据分析，'2023.0' 等格式可能的来源：

1. ❌ 不是从 开票日期 列提取的（因为日期字段中没有浮点数）
2. ⚠️ 可能来自源 Excel 文件中的某个"开票年份"或"年份"列（直接复制）
3. ⚠️ 可能是数据类型转换的问题（浮点数 → 字符串）

建议：
  - 查看导入代码，看 HEADER 的 开票年份 是如何导入的
  - 检查源 Excel 文件中是否存在 开票年份 或类似的列
  - 确认是否有来自不同的源数据格式
""")

conn.close()
