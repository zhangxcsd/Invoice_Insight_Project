import sqlite3
import time

conn = sqlite3.connect('d:\\PythonCode\\VAT_Audit_Project\\Database\\VAT_INV_Audit_Repo.db')
c = conn.cursor()

# 测试查询性能：查看索引是否被使用
print("=" * 60)
print("查询性能测试 - 使用开票年份列")
print("=" * 60)

# 检查索引
c.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%year%'")
indexes = c.fetchall()
print(f"\n发现的开票年份相关索引：")
for idx in indexes:
    print(f"  - {idx[0]}")

# 查询选项1：使用EXPLAIN QUERY PLAN查看执行计划
print("\n" + "=" * 60)
print("执行计划分析 - 直接查询开票年份")
print("=" * 60)
c.execute("EXPLAIN QUERY PLAN SELECT DISTINCT 开票年份 FROM ODS_VAT_INV_DETAIL WHERE 开票年份 IS NOT NULL ORDER BY 开票年份")
print("\n查询执行计划：")
for row in c.fetchall():
    print(f"  {row}")

# 比较：不使用开票年份列的查询
print("\n" + "=" * 60)
print("执行计划分析 - 使用substr()提取年份")
print("=" * 60)
c.execute("EXPLAIN QUERY PLAN SELECT DISTINCT substr(开票日期,1,4) as y FROM ODS_VAT_INV_DETAIL")
print("\n查询执行计划：")
for row in c.fetchall():
    print(f"  {row}")

# 实际执行时间对比
print("\n" + "=" * 60)
print("执行时间对比")
print("=" * 60)

# 方案1：使用开票年份列
start = time.time()
c.execute("SELECT DISTINCT 开票年份 FROM ODS_VAT_INV_DETAIL WHERE 开票年份 IS NOT NULL ORDER BY 开票年份")
years1 = [row[0] for row in c.fetchall()]
time1 = time.time() - start
print(f"\n方案1（使用开票年份列）：{time1*1000:.2f}ms，结果：{years1}")

# 方案2：使用substr()
start = time.time()
c.execute("SELECT DISTINCT substr(开票日期,1,4) as y FROM ODS_VAT_INV_DETAIL ORDER BY y")
years2 = [row[0] for row in c.fetchall()]
time2 = time.time() - start
print(f"方案2（使用substr()）：{time2*1000:.2f}ms，结果：{years2}")

print(f"\n性能提升：{time2/time1:.1f}x 倍（越大越好）")

conn.close()
