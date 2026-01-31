import sqlite3
import pandas as pd

DB = 'Database/VAT_INV_Audit_Repo.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

print('Checking ODS_VAT_INV_DETAIL schema...')
try:
    c.execute("PRAGMA table_info('ODS_VAT_INV_DETAIL')")
    cols = c.fetchall()
    print('columns count', len(cols))
    print([c[1] for c in cols])
except Exception as e:
    print('Failed to fetch ODS schema:', e)


print('\nChecking sample from ODS_VAT_INV_DETAIL_FULL_2025 (税率, 税率_数值)...')
try:
    df_led = pd.read_sql('SELECT 税率, 税率_数值 FROM ODS_VAT_INV_DETAIL_FULL_2025 LIMIT 5', conn)
    print(df_led)
except Exception as e:
    print('ledger query failed', e)

conn.close()
