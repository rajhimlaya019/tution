# create_db.py
import sqlite3

conn = sqlite3.connect("db.sqlite3")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    student_class TEXT,
    address TEXT
)
""")

conn.commit()
conn.close()
print("✅ Database created and students table ready.")
