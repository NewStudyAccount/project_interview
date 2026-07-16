import sqlite3
import json
import sys

DB_PATH = r"C:\Users\AI\.local\share\mimocode\mimocode.db"

def query_db(sql, params=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "tables"
    
    if action == "tables":
        results = query_db("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name")
        for r in results:
            print(f"{r['type']}: {r['name']}")
    
    elif action == "schema":
        table = sys.argv[2]
        results = query_db(f"SELECT sql FROM sqlite_master WHERE name = '{table}'")
        for r in results:
            print(r['sql'])
    
    elif action == "sessions":
        # List sessions for the project
        results = query_db("""
            SELECT s.id, s.project_id, s.title, s.time_created, s.time_updated,
                   (SELECT COUNT(*) FROM message m WHERE m.session_id = s.id) as msg_count
            FROM session s
            WHERE s.project_id = 'cc57ae6d-dc3c-471e-ae32-e6af261566a2'
            ORDER BY s.time_updated DESC
        """)
        for r in results:
            print(f"{r['id']} | {r['title']} | msgs={r['msg_count']} | created={r['time_created']} | updated={r['time_updated']}")
    
    elif action == "session_messages":
        sid = sys.argv[2]
        results = query_db("""
            SELECT m.id, m.agent_id, json_extract(m.data, '$.role') as role, 
                   substr(m.data, 1, 200) as preview
            FROM message m
            WHERE m.session_id = ?
            ORDER BY m.time_created
        """, (sid,))
        for r in results:
            print(f"  msg={r['id']} agent={r['agent_id'] or 'main'} role={r['role']}")
            print(f"    preview: {r['preview'][:150]}...")
    
    elif action == "search_user_statements":
        keyword = sys.argv[2]
        results = query_db(f"""
            SELECT m.session_id, substr(json_extract(m.data, '$.content'), 1, 500) as content
            FROM message m
            WHERE json_extract(m.data, '$.role') = 'user'
              AND json_extract(m.data, '$.content') LIKE '%{keyword}%'
            ORDER BY m.time_created DESC
            LIMIT 20
        """)
        for r in results:
            print(f"  session={r['session_id']}")
            print(f"    content: {r['content'][:300]}")
            print()
    
    elif action == "all_sessions":
        results = query_db("""
            SELECT s.id, s.project_id, s.title, s.time_created, s.time_updated,
                   (SELECT COUNT(*) FROM message m WHERE m.session_id = s.id) as msg_count
            FROM session s
            ORDER BY s.time_updated DESC
            LIMIT 50
        """)
        for r in results:
            print(f"{r['id']} | proj={r['project_id'][:12]}... | {r['title']} | msgs={r['msg_count']} | updated={r['time_updated']}")
    
    elif action == "project_list":
        results = query_db("""
            SELECT DISTINCT project_id, COUNT(*) as session_count
            FROM session
            GROUP BY project_id
            ORDER BY session_count DESC
        """)
        for r in results:
            print(f"  project={r['project_id']} sessions={r['session_count']}")
    
    elif action == "parts":
        sid = sys.argv[2]
        results = query_db("""
            SELECT p.id, p.message_id, json_extract(p.data, '$.type') as part_type,
                   json_extract(p.data, '$.tool') as tool,
                   substr(p.data, 1, 300) as preview
            FROM part p
            WHERE p.session_id = ?
            ORDER BY p.time_created
            LIMIT 100
        """, (sid,))
        for r in results:
            print(f"  part={r['id']} msg={r['message_id']} type={r['part_type']} tool={r['tool']}")
            print(f"    preview: {r['preview'][:200]}")
            print()
    
    elif action == "search_content":
        keyword = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        results = query_db(f"""
            SELECT m.session_id, json_extract(m.data, '$.role') as role,
                   substr(m.data, 1, 800) as data_preview
            FROM message m
            WHERE m.data LIKE '%{keyword}%'
            ORDER BY m.time_created DESC
            LIMIT {limit}
        """)
        for r in results:
            print(f"  session={r['session_id']} role={r['role']}")
            print(f"    data: {r['data_preview'][:400]}")
            print()
