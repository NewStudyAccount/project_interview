import sqlite3
import json

db = sqlite3.connect(r'C:\Users\AI\.local\share\mimocode\mimocode.db')
cursor = db.cursor()

# Get tool usage patterns across all sessions (excluding current distill session)
print("=== TOOL USAGE PATTERNS (all sessions) ===")
cursor.execute("""
    SELECT 
        json_extract(p.data, '$.tool') as tool,
        COUNT(*) as count
    FROM message m
    JOIN part p ON p.message_id = m.id
    WHERE json_extract(m.data, '$.role') = 'assistant'
      AND json_extract(p.data, '$.type') = 'tool'
    GROUP BY tool
    ORDER BY count DESC
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Get tool input patterns - look for repeated commands
print("\n=== REPEATED TOOL INPUT PATTERNS ===")
cursor.execute("""
    SELECT 
        json_extract(p.data, '$.tool') as tool,
        substr(json_extract(p.data, '$.state.input'), 1, 150) as input_preview,
        COUNT(*) as n
    FROM message m
    JOIN part p ON p.message_id = m.id
    WHERE json_extract(m.data, '$.role') = 'assistant'
      AND json_extract(p.data, '$.type') = 'tool'
      AND json_extract(p.data, '$.tool') = 'bash'
    GROUP BY tool, input_preview
    HAVING n > 1
    ORDER BY n DESC
    LIMIT 30
""")
for row in cursor.fetchall():
    print(f"  [{row[2]}x] {row[1]}")

# Search for repeated patterns in user messages - keywords
print("\n=== USER MESSAGE KEYWORD SEARCH ===")
keywords = ['again', 'every time', 'like last time', 'the usual', 'repeat', 'same as before', '继续', '再', '按照']
for kw in keywords:
    cursor.execute("""
        SELECT COUNT(*) FROM message m
        WHERE json_extract(m.data, '$.role') = 'user'
          AND json_extract(m.data, '$.content') LIKE ?
    """, (f'%{kw}%',))
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"  '{kw}': {count} matches")

# Get user messages with repeated keywords
print("\n=== USER MESSAGES WITH REPEAT KEYWORDS ===")
cursor.execute("""
    SELECT 
        m.session_id,
        json_extract(m.data, '$.content') as content
    FROM message m
    WHERE json_extract(m.data, '$.role') = 'user'
      AND (
        json_extract(m.data, '$.content') LIKE '%继续%'
        OR json_extract(m.data, '$.content') LIKE '%再%'
        OR json_extract(m.data, '$.content') LIKE '%按照%'
        OR json_extract(m.data, '$.content') LIKE '%same%'
        OR json_extract(m.data, '$.content') LIKE '%repeat%'
      )
    LIMIT 20
""")
for row in cursor.fetchall():
    content = row[1][:200] if row[1] else ''
    print(f"  [{row[0]}] {content}")

# Check for task patterns
print("\n=== TASKS ===")
cursor.execute("""
    SELECT id, session_id, title, status 
    FROM task 
    ORDER BY id DESC
    LIMIT 20
""")
for row in cursor.fetchall():
    print(f"  {row[0]} | {row[1]} | {row[2][:80]} | {row[3]}")

db.close()
