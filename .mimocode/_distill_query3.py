import sqlite3
import json

db = sqlite3.connect(r'C:\Users\AI\.local\share\mimocode\mimocode.db')
cursor = db.cursor()

# Check task schema
cursor.execute("PRAGMA table_info(task)")
print("=== TASK SCHEMA ===")
for col in cursor.fetchall():
    print(f"  {col}")

# Get task data
cursor.execute("SELECT * FROM task LIMIT 5")
print("\n=== TASK SAMPLES ===")
cols = [d[0] for d in cursor.description]
print(f"  Columns: {cols}")
for row in cursor.fetchall():
    print(f"  {row}")

# Get all user messages across sessions to see what work was done
print("\n=== USER MESSAGES (full, per session) ===")
cursor.execute("""
    SELECT 
        m.session_id,
        s.title as session_title,
        json_extract(m.data, '$.content') as content,
        m.time_created
    FROM message m
    JOIN session s ON s.id = m.session_id
    WHERE json_extract(m.data, '$.role') = 'user'
    ORDER BY m.time_created DESC
""")
for row in cursor.fetchall():
    session_id = row[0]
    session_title = (row[1] or '')[:60]
    content = (row[2] or '')[:300]
    ts = row[3]
    print(f"\n  [{session_id}] {session_title} (ts={ts})")
    print(f"    {content}")

db.close()
