import sqlite3
import pandas as pd
from collections import Counter

db_path = 'Database/VAT_INV_Audit_Repo.db'

conn = sqlite3.connect(db_path)
c = conn.cursor()

print("=" * 80)
print("ODS_VAT_INV_DETAIL 表中的 开票年份 字段格式检查")
print("=" * 80)

# 检查表的字段信息
print("\n1. 表结构信息:")
print("-" * 80)
c.execute("PRAGMA table_info('ODS_VAT_INV_DETAIL')")
cols = c.fetchall()
for col in cols:
    if col[1] == '开票年份':
        print(f"字段名: {col[1]}")
        print(f"数据类型: {col[2]}")
        print(f"是否可为NULL: {'是' if col[3] == 0 else '否'}")

# 检查数据格式
print("\n2. 开票年份 字段的数据分布:")
print("-" * 80)
c.execute("""
    SELECT 开票年份, COUNT(*) as count
    FROM ODS_VAT_INV_DETAIL
    GROUP BY 开票年份
    ORDER BY 开票年份
""")
rows = c.fetchall()
for year, count in rows:
    print(f"  开票年份 = {repr(year)}: {count:>6} 条")

# 检查数据类型
print("\n3. 开票年份 字段的类型和格式分析:")
print("-" * 80)
c.execute("""
    SELECT DISTINCT typeof(开票年份) as type_name, 开票年份
    FROM ODS_VAT_INV_DETAIL
    WHERE 开票年份 IS NOT NULL
    GROUP BY typeof(开票年份), 开票年份
    ORDER BY typeof(开票年份), 开票年份
""")
rows = c.fetchall()
type_format_map = {}
for type_name, year_val in rows:
    if type_name not in type_format_map:
        type_format_map[type_name] = []
    type_format_map[type_name].append(year_val)

for type_name in sorted(type_format_map.keys()):
    values = type_format_map[type_name]
    print(f"\n  SQLite 类型: {type_name}")
    print(f"  对应的值: {values}")
    for val in values:
        print(f"    - {repr(val)} (Python type: {type(val).__name__})")

# 详细的格式检查
print("\n4. 格式详细检查:")
print("-" * 80)
c.execute("""
    SELECT 
        开票年份,
        typeof(开票年份) as sqlite_type,
        LENGTH(CAST(开票年份 AS TEXT)) as length,
        CASE 
            WHEN 开票年份 LIKE '%.%' THEN '包含小数点'
            WHEN 开票年份 LIKE '____' THEN '纯4位数字'
            ELSE '其他格式'
        END as format_type
    FROM ODS_VAT_INV_DETAIL
    WHERE 开票年份 IS NOT NULL
    GROUP BY 开票年份
    ORDER BY 开票年份
""")
rows = c.fetchall()
for year, sqlite_type, length, format_type in rows:
    print(f"  年份: {repr(year):12} | SQLite类型: {sqlite_type:6} | 长度: {length} | 格式: {format_type}")

# 与 HEADER 的对比
print("\n5. 与 ODS_VAT_INV_HEADER 的格式对比:")
print("-" * 80)

print("\n  ODS_VAT_INV_DETAIL 的 开票年份 分布:")
c.execute("""
    SELECT 开票年份, COUNT(*) as count
    FROM ODS_VAT_INV_DETAIL
    WHERE 开票年份 IS NOT NULL
    GROUP BY 开票年份
    ORDER BY 开票年份
""")
detail_years = {}
for year, count in c.fetchall():
    detail_years[repr(year)] = count

print("  ODS_VAT_INV_HEADER 的 开票年份 分布:")
c.execute("""
    SELECT 开票年份, COUNT(*) as count
    FROM ODS_VAT_INV_HEADER
    WHERE 开票年份 IS NOT NULL
    GROUP BY 开票年份
    ORDER BY 开票年份
""")
header_years = {}
for year, count in c.fetchall():
    header_years[repr(year)] = count

# 对比展示
all_years = sorted(set(detail_years.keys()) | set(header_years.keys()))
print("\n  对比表:")
print(f"  {'年份':<15} | {'DETAIL 中':<12} | {'HEADER 中':<12} | {'是否一致':<8}")
print("  " + "-" * 60)
for year in all_years:
    detail_count = detail_years.get(year, 0)
    header_count = header_years.get(year, 0)
    both_exist = "✓ 一致" if (detail_count > 0 and header_count > 0) else "✗ 不同"
    print(f"  {year:<15} | {detail_count:<12} | {header_count:<12} | {both_exist:<8}")

# 检查 DETAIL 是否存在混合格式
print("\n6. 混合格式检查（DETAIL 部分）:")
print("-" * 80)
c.execute("""
    SELECT COUNT(DISTINCT 开票年份) as total_formats
    FROM ODS_VAT_INV_DETAIL
    WHERE 开票年份 IS NOT NULL
""")
total_formats = c.fetchone()[0]

if total_formats == 5:  # 预期是 5 个年份：2021, 2022, 2023, 2024, 2025
    print("✓ ODS_VAT_INV_DETAIL 中 开票年份 的格式统一（无混合格式）")
    print(f"  仅有 {total_formats} 种年份值")
else:
    print("✗ ODS_VAT_INV_DETAIL 中 开票年份 存在混合格式！")
    print(f"  检测到 {total_formats} 种不同的年份格式（应该只有 5 种）")

# 检查 HEADER 是否存在混合格式
print("\n7. 混合格式检查（HEADER 部分）:")
print("-" * 80)
c.execute("""
    SELECT COUNT(DISTINCT 开票年份) as total_formats
    FROM ODS_VAT_INV_HEADER
    WHERE 开票年份 IS NOT NULL
""")
total_formats_hdr = c.fetchone()[0]

if total_formats_hdr == 5:  # 预期是 5 个年份
    print("✓ ODS_VAT_INV_HEADER 中 开票年份 格式一致（无混合格式）")
    print(f"  仅有 {total_formats_hdr} 种年份值")
else:
    print("✗ ODS_VAT_INV_HEADER 中 开票年份 存在混合格式！")
    print(f"  检测到 {total_formats_hdr} 种不同的年份格式（应该只有 5 种）")

# 总结
print("\n8. 总结:")
print("=" * 80)
if total_formats == 5 and total_formats_hdr == 5:
    print("✓ 两个表的 开票年份 格式一致，都是统一的格式")
else:
    print("✗ 两个表的 开票年份 存在格式不一致")
    if total_formats != 5:
        print(f"  - DETAIL 表: {total_formats} 种格式（应为 5）")
    if total_formats_hdr != 5:
        print(f"  - HEADER 表: {total_formats_hdr} 种格式（应为 5）")

conn.close()
