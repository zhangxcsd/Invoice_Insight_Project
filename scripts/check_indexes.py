import sqlite3
import os
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Database', 'VAT_INV_Audit_Repo.db')
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' ORDER BY tbl_name, name")
rows = c.fetchall()
for name, tbl, sql in rows:
    print(f"{name} on {tbl}: {sql}")
conn.close()