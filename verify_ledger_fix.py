#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证 LEDGER 表是否已成功填充数据"""

import sqlite3
import os
import glob

# 找到最新的数据库文件
db_files = sorted(glob.glob('Database/*.db'), key=os.path.getmtime, reverse=True)
if not db_files:
    print('❌ 没有找到数据库文件')
    exit(1)

db_path = db_files[0]
print(f'📊 使用数据库: {db_path}')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()


# 查询所有以新规范 ODS_VAT_INV_HEADER_FULL_ 和 ODS_VAT_INV_DETAIL_FULL_ 开头的表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE 'ODS_VAT_INV_HEADER_FULL_%' OR name LIKE 'ODS_VAT_INV_DETAIL_FULL_%') ORDER BY name")
tables = cursor.fetchall()

print(f'\n✅ 找到 {len(tables)} 个 ODS 表：\n')

total_rows = 0
for table_name, in tables:
    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    count = cursor.fetchone()[0]
    total_rows += count
    status = '✅' if count > 0 else '❌'
    print(f'{status} {table_name}: {count:>6} 行')

print(f'\n📈 总计: {total_rows} 行')

# 分析 HEADER 表是否都有数据
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ODS_VAT_INV_HEADER_FULL_%' ORDER BY name")
header_tables = cursor.fetchall()

print(f'\n🔍 HEADER 表详情：\n')
for table_name, in header_tables:
    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    count = cursor.fetchone()[0]
    status = '✅ 有数据' if count > 0 else '❌ 无数据'
    print(f'{status}: {table_name} ({count} 行)')

conn.close()
