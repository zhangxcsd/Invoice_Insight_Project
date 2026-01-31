import sqlite3
import pandas as pd
conn = sqlite3.connect('Database/VAT_INV_Audit_Repo.db')
try:
    yrs = pd.read_sql("SELECT DISTINCT substr(开票日期,1,4) as y FROM ODS_VAT_INV_TEMP_TRANSIT", conn)
    print('years sample:', yrs.head())
except Exception as e:
    print('select failed:', repr(e))
    # try sampling raw column values
    try:
        df = pd.read_sql("SELECT 开票日期 FROM ODS_VAT_INV_TEMP_TRANSIT LIMIT 20", conn)
        print(df)
    except Exception as e2:
        print('sampling failed too:', repr(e2))
finally:
    conn.close()
