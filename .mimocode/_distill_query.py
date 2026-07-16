import sqlite3
import json

db = sqlite3.connect(r'C:\Users\AI\.local\share\mimocode\mimocode.db')
cursor = db.cursor()

# List tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("=== TABLES ===")
for t in tables:
    print(t[0])

# Count sessions
cursor.execute("SELECT COUNT(*) FROM session")
print("\n=== SESSION COUNT ===")
print(cursor.fetchone()[0])

# Get recent sessions
cursor.execute("""
    SELECT id, time_created, title 
    FROM session 
    ORDER BY time_created DESC 
    LIMIT 20
""")
sessions = cursor.fetchall()
print("\n=== RECENT SESSIONS ===")
for s in sessions:
    print(f"  {s[0]} | {s[1]} | {s[2]}")

# Count messages per session
cursor.execute("""
    SELECT s.id, s.title, COUNT(m.id) as msg_count
    FROM session s
    LEFT JOIN message m ON m.session_id = s.id
    GROUP BY s.id
    ORDER BY MAX(m.time_created) DESC
    LIMIT 20
""")
print("\n=== SESSIONS BY MESSAGE COUNT ===")
for row in cursor.fetchall():
    print(f"  {row[0]} | msgs={row[2]} | {row[1]}")

db.close()
