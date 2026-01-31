import sqlite3

conn = sqlite3.connect('d:\\PythonCode\\VAT_Audit_Project\\Database\\VAT_INV_Audit_Repo.db')
c = conn.cursor()

# Check if 开票日期 has data
c.execute('SELECT 开票日期, 开票年份 FROM ODS_VAT_INV_DETAIL LIMIT 5')
for row in c.fetchall():
    print(f'开票日期: {row[0]}, 开票年份: {row[1]}, type: {type(row[0])}')

conn.close()
