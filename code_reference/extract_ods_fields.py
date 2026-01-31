import re
import os

SQL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ODS_TABLE.SQL')

def extract_fields(sql_file, table_name):
    with open(sql_file, encoding='utf-8') as f:
        sql = f.read()
    pattern = rf'CREATE TABLE {table_name} \((.*?)\)[\s\S]*?;', re.DOTALL
    match = re.search(pattern[0], sql, re.DOTALL)
    if not match:
        print(f"未找到表: {table_name}")
        return []
    fields_block = match.group(1)
    fields = []
    for line in fields_block.splitlines():
        line = line.strip()
        if not line or line.startswith('--') or line.startswith('PRIMARY') or line.startswith('INDEX'):
            continue
        m = re.match(r'`(\w+)` ([A-Z0-9_()\',]+)', line)
        if m:
            fields.append((m.group(1), m.group(2)))
    return fields

if __name__ == "__main__":
    for tbl in ["ODS_VAT_INV_HEADER_FULL_2023", "ODS_VAT_INV_DETAIL_FULL_2023"]:
        print(f"{tbl} 字段顺序与类型：")
        for name, typ in extract_fields(SQL_FILE, tbl):
            print(f"  {name:30} {typ}")
