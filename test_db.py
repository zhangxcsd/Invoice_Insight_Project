import sqlite3

conn = sqlite3.connect('d:\\PythonCode\\VAT_Audit_Project\\Database\\VAT_INV_Audit_Repo.db')
c = conn.cursor()

# Check DETAIL table structure
c.execute("PRAGMA table_info('ODS_VAT_INV_DETAIL')")
cols = [row[1] for row in c.fetchall()]
print('Columns in DETAIL:', cols)
print()

# Check if 开票年份 exists and has values
c.execute('SELECT COUNT(开票年份) FROM ODS_VAT_INV_DETAIL')
print('Non-null 开票年份 count:', c.fetchone()[0])

c.execute('SELECT DISTINCT 开票年份 FROM ODS_VAT_INV_DETAIL ORDER BY 开票年份')
years = [row[0] for row in c.fetchall()]
print('Unique years:', years)

# Check table counts
c.execute("SELECT COUNT(*) FROM ODS_VAT_INV_DETAIL")
print('DETAIL total rows:', c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM ODS_VAT_INV_HEADER")
print('HEADER total rows:', c.fetchone()[0])

# List all ODS tables
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ODS_%'")
ods_tables = [row[0] for row in c.fetchall()]
print('\nAll ODS tables:', ods_tables)

conn.close()
