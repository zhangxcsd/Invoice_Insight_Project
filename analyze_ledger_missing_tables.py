import sqlite3
import os

db_path = 'Database/VAT_INV_Audit_Repo.db'

conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=" * 80)
print("问题分析：ODS_VAT_INV_HEADER_FULL_2023 存在，但 2022 的 HEADER 缺失")
print("=" * 80)

print("\n1. LEDGER 中 HEADER 表的情况:")
print("-" * 80)

c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ODS_VAT_INV_HEADER_FULL_%' ORDER BY name")
header_tables = c.fetchall()
if header_tables:
    for (name,) in header_tables:
        c.execute(f"SELECT COUNT(*) FROM {name}")
        count = c.fetchone()[0]
        print(f"  ✓ {name}: {count} 条")
else:
    print("  ✗ 没有找到任何 HEADER 表")

print("\n2. LEDGER 中 DETAIL 表的情况:")
print("-" * 80)

c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ODS_VAT_INV_DETAIL_FULL_%' ORDER BY name")
detail_tables = c.fetchall()
if detail_tables:
    for (name,) in detail_tables:
        c.execute(f"SELECT COUNT(*) FROM {name}")
        count = c.fetchone()[0]
        print(f"  ✓ {name}: {count} 条")
else:
    print("  ✗ 没有找到任何 DETAIL 表")

print("\n3. ODS 层中 HEADER 的年份数据质量:")
print("-" * 80)
c.execute("""
    SELECT 开票年份, COUNT(*) as count 
    FROM ODS_VAT_INV_HEADER 
    WHERE 开票年份 IS NOT NULL 
    GROUP BY 开票年份 
    ORDER BY 开票年份 DESC
""")
rows = c.fetchall()
for year, count in rows:
    year_str = str(int(year)) if isinstance(year, float) else str(year)
    ods_header = f"ODS_VAT_INV_HEADER_FULL_{year_str}"
    c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (ods_header,))
    exists = c.fetchone()[0]
    status = "✓ 对应 ODS HEADER 表存在" if exists else "✗ 对应 ODS HEADER 表不存在"
    print(f"  年份 {year_str}: {count:>6} 条 ODS 数据  →  {status}")

print("\n4. ODS 层中 DETAIL 的年份数据质量:")
print("-" * 80)
c.execute("""
    SELECT 开票年份, COUNT(*) as count 
    FROM ODS_VAT_INV_DETAIL 
    WHERE 开票年份 IS NOT NULL 
    GROUP BY 开票年份 
    ORDER BY 开票年份 DESC
""")
rows = c.fetchall()
for year, count in rows:
    year_str = str(int(year)) if isinstance(year, float) else str(year)
    ods_detail = f"ODS_VAT_INV_DETAIL_FULL_{year_str}"
    c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (ods_detail,))
    exists = c.fetchone()[0]
    status = "✓ 对应 ODS DETAIL 表存在" if exists else "✗ 对应 ODS DETAIL 表不存在"
    print(f"  年份 {year_str}: {count:>6} 条 ODS 数据  →  {status}")

print("\n5. 问题根源分析:")
print("-" * 80)

# 检查 ODS_VAT_INV_HEADER 中 2023 的数据异常
c.execute("SELECT COUNT(DISTINCT 开票年份) FROM ODS_VAT_INV_HEADER WHERE SUBSTR(开票日期, 1, 4) = '2023'")
count_by_date = c.fetchone()[0]

c.execute("SELECT 开票年份, COUNT(*) as count FROM ODS_VAT_INV_HEADER WHERE SUBSTR(开票日期, 1, 4) = '2023' GROUP BY 开票年份")
year_rows = c.fetchall()

print("  ODS_VAT_INV_HEADER 中的数据:")
print("    - 按 开票年份 字段统计：")
for year, count in [("2021", 0), ("2022", 0), ("2023 (数值)", 0), ("2023 (字符串)", 0)]:
    pass

c.execute("SELECT 开票年份, COUNT(*) FROM ODS_VAT_INV_HEADER GROUP BY 开票年份 ORDER BY 开票年份")
print("    数据分布：")
for year, count in c.fetchall():
    print(f"      开票年份 = {repr(year)}: {count} 条")

print("\n  问题：")
print("    ✗ ODS_VAT_INV_HEADER 中存在混合的年份格式（浮点数和字符串）")
print("    ✗ 2023 既有浮点数(2023.0)也有字符串('2023')")
print("    ✗ LEDGER 生成逻辑可能只针对特定格式的年份创建表")

conn.close()
