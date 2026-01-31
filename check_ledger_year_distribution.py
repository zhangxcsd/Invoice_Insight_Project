import sqlite3
import os

db_path = 'Database/VAT_INV_Audit_Repo.db'

if not os.path.exists(db_path):
    print(f"数据库文件不存在: {db_path}")
else:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 查询所有 LEDGER 表
    print("=" * 70)
    print("所有 LEDGER 表:")
    print("=" * 70)
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'LEDGER_VAT_INV_%' ORDER BY name")
    ledger_tables = c.fetchall()
    for row in ledger_tables:
        print(f"  {row[0]}")
    
    # 查询 ODS 层的年份数据
    print("\n" + "=" * 70)
    print("ODS_VAT_INV_HEADER 中的年份分布:")
    print("=" * 70)
    try:
        c.execute("""
            SELECT 开票年份, COUNT(*) as count 
            FROM ODS_VAT_INV_HEADER 
            WHERE 开票年份 IS NOT NULL 
            GROUP BY 开票年份 
            ORDER BY 开票年份
        """)
        rows = c.fetchall()
        for year, count in rows:
            print(f"  {year}: {count:>8} 条记录")
    except Exception as e:
        print(f"  查询失败: {e}")
    
    # 查询 ODS_VAT_INV_DETAIL 中的年份分布
    print("\n" + "=" * 70)
    print("ODS_VAT_INV_DETAIL 中的年份分布:")
    print("=" * 70)
    try:
        c.execute("""
            SELECT 开票年份, COUNT(*) as count 
            FROM ODS_VAT_INV_DETAIL 
            WHERE 开票年份 IS NOT NULL 
            GROUP BY 开票年份 
            ORDER BY 开票年份
        """)
        rows = c.fetchall()
        for year, count in rows:
            print(f"  {year}: {count:>8} 条记录")
    except Exception as e:
        print(f"  查询失败: {e}")
    
    # 查询 DWD 层的年份分布
    print("\n" + "=" * 70)
    print("DWD 层的年份分布:")
    print("=" * 70)
    try:
        c.execute("""
            SELECT 开票年份, COUNT(*) as count 
            FROM DWD_VAT_INV_DETAIL 
            WHERE 开票年份 IS NOT NULL 
            GROUP BY 开票年份 
            ORDER BY 开票年份
        """)
        rows = c.fetchall()
        for year, count in rows:
            print(f"  {year}: {count:>8} 条记录")
    except Exception as e:
        print(f"  DWD_VAT_INV_DETAIL 查询失败: {e}")
    
    # 检查 LEDGER 表的年份和条数
    print("\n" + "=" * 70)
    print("LEDGER 表详情:")
    print("=" * 70)
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'LEDGER_VAT_INV_%' ORDER BY name")
    tables = c.fetchall()
    for (table_name,) in tables:
        try:
            c.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = c.fetchone()[0]
            print(f"  {table_name}: {count:>8} 条记录")
        except Exception as e:
            print(f"  {table_name}: 查询失败 - {e}")
    
    conn.close()
